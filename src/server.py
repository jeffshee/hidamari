import logging
import random
import signal
import time
import multiprocessing as mp
from multiprocessing import Process
import setproctitle

from gi.repository import GLib
from pydbus import SessionBus

try:
    from commons import *
    from player.video_player import main as video_player_main
    from player.web_player import main as web_player_main
    from gui.control import main as gui_main
    from menu import show_systray_icon
    from monitor import *
    from utils import ConfigUtil, EndSessionHandler, get_video_paths
except ModuleNotFoundError:
    from hidamari.commons import *
    from hidamari.player.video_player import main as video_player_main
    from hidamari.player.web_player import main as web_player_main
    from hidamari.gui.control import main as gui_main
    from hidamari.menu import show_systray_icon
    from hidamari.utils import ConfigUtil, EndSessionHandler, get_video_paths
    from hidamari.monitor import *

loop = GLib.MainLoop()
logger = logging.getLogger(LOGGER_NAME)


class HidamariServer(object):
    """
    <node>
    <interface name='io.github.jeffshee.hidamari.server'>
        <method name='null'/>
        <method name='video'>
            <arg type='s' name='video_path' direction='in'/>
            <arg type='s' name='monitor' direction='in'/>
        </method>
        <method name='stream'>
            <arg type='s' name='stream_url' direction='in'/>
        </method>
        <method name='webpage'>
            <arg type='s' name='webpage_url' direction='in'/>
        </method>
        <method name='pause_playback'/>
        <method name='start_playback'/>
        <method name="reload"/>
        <method name="feeling_lucky"/>
        <method name='show_gui'/>
        <method name='quit'/>
        <property name="mode" type="s" access="read"/>
        <property name="volume" type="i" access="readwrite"/>
        <property name="blur_radius" type="i" access="readwrite"/>
        <property name="is_mute" type="b" access="readwrite"/>
        <property name="is_playing" type="b" access="read"/>
        <property name="is_paused_by_user" type="b" access="readwrite"/>
        <property name="is_static_wallpaper" type="b" access="readwrite"/>
        <property name="is_pause_when_maximized" type="b" access="readwrite"/>
        <property name="is_mute_when_maximized" type="b" access="readwrite"/>
    </interface>
    </node>
    """

    def __init__(self, version, pkgdatadir, localedir, args):
        setproctitle.setproctitle("hidamari-server")

        self.version = version
        self.pkgdatadir = pkgdatadir
        self.localedir = localedir
        self.args = args
        self._prev_mode = None
        self._player_count = 0

        # Processes
        # Switch to `forkserver` since v3.2 for performance. BTW `fork` didn't work (it crashes).
        # Ref: https://bnikolic.co.uk/blog/python/parallelism/2019/11/13/python-forkserver-preload.html
        mp.set_start_method("forkserver")
        self.gui_process = None
        self.sys_icon_process = None
        self.player_process = None

        signal.signal(signal.SIGINT, lambda *_: self.quit())
        signal.signal(signal.SIGTERM, lambda *_: self.quit())
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, lambda *_: self.quit())
        # Monitoring EndSession (OS reboot, shutdown, etc.)
        EndSessionHandler(self.quit)

        # Configuration
        if args.reset:
            ConfigUtil().generate_template()
        self._load_config()

        # Player process
        self.reload()

        # Show main GUI
        if not args.background:
            self.show_gui()

        logger.info("[Server] Started")

    def _load_config(self):
        self.config = ConfigUtil().load()

    def _save_config(self):
        ConfigUtil().save(self.config)

    def _setup_player(self, mode, data_source=None, monitor=None):
        """Setup and run player"""
        logger.info(f"[Mode] {mode}")
        self.config[CONFIG_KEY_MODE] = mode

        # Set data source if specified
        if data_source and monitor:
            self.config[CONFIG_KEY_DATA_SOURCE][monitor] = data_source
        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = data_source # always update default source

        # Quit current then create a new player
        self._quit_player()

        # Terminate old player process and wait for it to finish
        if self.player_process:
            self.player_process.terminate()
            self.player_process.join(timeout=5)  # Wait up to 5 seconds
            if self.player_process.is_alive():
                logger.warning("[Server] Player process didn't terminate, killing it")
                self.player_process.kill()
                self.player_process.join(timeout=2)
            self.player_process = None

        if mode in [MODE_VIDEO, MODE_STREAM]:
            self.player_process = Process(
                name=f"hidamari-player-{self._player_count}", target=video_player_main)
        elif mode == MODE_WEBPAGE:
            self.player_process = Process(
                name=f"hidamari-player-{self._player_count}", target=web_player_main)
        elif mode == MODE_NULL:
            pass
        else:
            raise ValueError("[Server] Unknown mode")
        if self.player_process is not None:
            self.player_process.start()
            self._player_count += 1

        # Refresh systray icon if the mode changed
        if self.config[CONFIG_KEY_SYSTRAY]:
            if self._prev_mode != self.mode:
                if self.sys_icon_process:
                    self.sys_icon_process.terminate()
                    self.sys_icon_process.join(timeout=3)
                    if self.sys_icon_process.is_alive():
                        self.sys_icon_process.kill()
                        self.sys_icon_process.join(timeout=1)
                self.sys_icon_process = Process(
                    name="hidamari-systray", target=show_systray_icon, args=(mode,))
                self.sys_icon_process.start()
            self._prev_mode = self.mode

    @staticmethod
    def _quit_player():
        """Quit current player"""
        player = get_instance(DBUS_NAME_PLAYER)
        if player:
            player.quit_player()

    def video(self, video_path=None, monitor=None):
        self._setup_player(MODE_VIDEO, video_path, monitor)

    def stream(self, stream_url=None):
        self._setup_player(MODE_STREAM, stream_url)

    def webpage(self, webpage_url=None):
        self._setup_player(MODE_WEBPAGE, webpage_url)

    @staticmethod
    def pause_playback():
        player = get_instance(DBUS_NAME_PLAYER)
        if player:
            player.pause_playback()

    @staticmethod
    def start_playback():
        player = get_instance(DBUS_NAME_PLAYER)
        if player:
            player.start_playback()

    def reload(self):
        if self.config[CONFIG_KEY_MODE] == MODE_VIDEO:
            self.video()
        elif self.config[CONFIG_KEY_MODE] == MODE_STREAM:
            self.stream()
        elif self.config[CONFIG_KEY_MODE] == MODE_WEBPAGE:
            self.webpage()
        elif self.config[CONFIG_KEY_MODE] == MODE_NULL:
            pass
        else:
            raise ValueError("[Server] Unknown mode")

    def feeling_lucky(self):
        """Random play a video from the directory"""
        monitors = Monitors().get_monitors()
        for monitor in monitors:
            file_list = get_video_paths()   
            # Remove current data source from the random selection
            if self.config[CONFIG_KEY_DATA_SOURCE][monitor] in file_list:
                file_list.remove(self.config[CONFIG_KEY_DATA_SOURCE][monitor])
            if file_list:
                video_path = random.choice(file_list)
                self.config[CONFIG_KEY_MODE] = MODE_VIDEO
                self.config[CONFIG_KEY_DATA_SOURCE][monitor] = video_path
                self._save_config()
            self.video(video_path)

    def show_gui(self):
        """Show main GUI"""
        self.gui_process = Process(name="hidamari-gui", target=gui_main, args=(
            self.version, self.pkgdatadir, self.localedir,))
        self.gui_process.start()

    def quit(self):
        try:
            self._quit_player()
        except GLib.Error:
            pass
        
        # Quit all processes with proper cleanup
        for process in [self.player_process, self.gui_process, self.sys_icon_process]:
            if process and process.is_alive():
                process.terminate()
                process.join(timeout=3)
                if process.is_alive():
                    logger.warning(f"[Server] Process {process.name} didn't terminate, killing it")
                    process.kill()
                    process.join(timeout=1)
        
        loop.quit()
        logger.info("[Server] Stopped")

    @property
    def mode(self):
        return self.config[CONFIG_KEY_MODE]

    @property
    def volume(self):
        return self.config[CONFIG_KEY_VOLUME]

    @volume.setter
    def volume(self, volume):
        self.config[CONFIG_KEY_VOLUME] = volume
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None:
            player.volume = volume

    @property
    def blur_radius(self):
        return self.config[CONFIG_KEY_BLUR_RADIUS]

    @blur_radius.setter
    def blur_radius(self, blur_radius):
        self.config[CONFIG_KEY_BLUR_RADIUS] = blur_radius
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None:
            player.reload_config()

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config[CONFIG_KEY_MUTE] = is_mute
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None:
            player.is_mute = is_mute

    @property
    def is_playing(self):
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None:
            return player.is_playing
        return False

    @property
    def is_paused_by_user(self):
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None and player.mode in [MODE_VIDEO, MODE_STREAM]:
            return player.is_paused_by_user
        return None

    @is_paused_by_user.setter
    def is_paused_by_user(self, is_paused_by_user):
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None and player.mode in [MODE_VIDEO, MODE_STREAM]:
            player.is_paused_by_user = is_paused_by_user

    @property
    def is_static_wallpaper(self):
        return self.config[CONFIG_KEY_STATIC_WALLPAPER]

    @is_static_wallpaper.setter
    def is_static_wallpaper(self, is_static_wallpaper):
        self.config[CONFIG_KEY_STATIC_WALLPAPER] = is_static_wallpaper
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None:
            player.reload_config()

    @property
    def is_pause_when_maximized(self):
        return self.config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED]

    @is_pause_when_maximized.setter
    def is_pause_when_maximized(self, is_pause_when_maximized):
        self.config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED] = is_pause_when_maximized
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None:
            player.reload_config()

    @property
    def is_mute_when_maximized(self):
        return self.config[CONFIG_KEY_MUTE_WHEN_MAXIMIZED]

    @is_mute_when_maximized.setter
    def is_mute_when_maximized(self, is_mute_when_maximized):
        self.config[CONFIG_KEY_MUTE_WHEN_MAXIMIZED] = is_mute_when_maximized
        player = get_instance(DBUS_NAME_PLAYER)
        if player is not None:
            player.reload_config()


def get_instance(dbus_name):
    bus = SessionBus()
    try:
        instance = bus.get(dbus_name)
    except GLib.Error:
        return None
    return instance

def main(version, pkgdatadir, localedir, args):
    server = get_instance(DBUS_NAME_SERVER)
    if server is not None:
        server.show_gui()
    else:
        # Pause before launching
        time.sleep(args.p)
        bus = SessionBus()
        server = HidamariServer(version, pkgdatadir, localedir, args)
        try:
            bus.publish(DBUS_NAME_SERVER, server)
            loop.run()
        except RuntimeError:
            raise Exception("Failed to create server")
