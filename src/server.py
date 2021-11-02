import argparse
import logging
import multiprocessing as mp
import random
import signal
import time
from multiprocessing import Process

from gi.repository import GLib
from pydbus import SessionBus

from commons import *
from player.base_player import main as base_player_main
from player.video_player import main as video_player_main
from player.web_player import main as web_player_main
from ui.gui import main as gui_main
from ui.menu import show_systray_icon
from utils import ConfigUtil, EndSessionHandler, list_local_video_dir

loop = GLib.MainLoop()
logger = logging.getLogger(LOGGER_NAME)


class HidamariServer(object):
    """
    <node>
    <interface name='io.github.jeffshee.hidamari.server'>
        <method name='null'/>
        <method name='video'>
            <arg type='s' name='video_path' direction='in'/>
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
        <property name="is_detect_maximized" type="b" access="readwrite"/>
    </interface>
    </node>
    """

    def __init__(self, args):
        signal.signal(signal.SIGINT, lambda *_: self.quit())
        signal.signal(signal.SIGTERM, lambda *_: self.quit())
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, lambda *_: self.quit())
        EndSessionHandler(self.quit)

        os.makedirs(VIDEO_WALLPAPER_DIR, exist_ok=True)
        self._load_config()

        mp.set_start_method("spawn")
        self.gui_process = None
        self.sys_icon_process = None
        self.player_process = None

        self._prev_mode = None

        # Initial loading for player process
        self.reload()

        if args and not args.background:
            self.show_gui()

        logger.info("[Server] Started")

    def _load_config(self):
        self.config = ConfigUtil().load()

    def _save_config(self):
        ConfigUtil().save(self.config)

    def _setup_player(self, mode, data_source=None):
        """Setup and run player"""
        logger.info(f"[Mode] {mode}")
        self.config[CONFIG_KEY_MODE] = mode
        # Set data source if specified
        if data_source:
            self.config[CONFIG_KEY_DATA_SOURCE] = data_source
        self._save_config()

        self._quit_player()

        # Create new player
        if mode in [MODE_VIDEO, MODE_STREAM]:
            self.player_process = Process(target=video_player_main)
        elif mode == MODE_WEBPAGE:
            self.player_process = Process(target=web_player_main)
        else:
            self.player_process = Process(target=base_player_main)
        self.player_process.start()

        if self._prev_mode != self.mode:
            # Refresh systray icon if the mode changed
            if self.sys_icon_process:
                self.sys_icon_process.terminate()
            self.sys_icon_process = Process(target=show_systray_icon)
            self.sys_icon_process.start()
        self._prev_mode = self.mode

    @staticmethod
    def _quit_player():
        """Quit current player"""
        player = get_instance(DBUS_NAME_PLAYER)
        if player:
            player.quit_player()

    def null(self):
        self._setup_player(MODE_NULL)

    def video(self, video_path=None):
        self._setup_player(MODE_VIDEO, video_path)

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
        if self.config[CONFIG_KEY_MODE] == MODE_NULL:
            # Welcome to Hidamari, first time user ;)
            self.null()
        elif self.config[CONFIG_KEY_MODE] == MODE_VIDEO:
            self.video()
        elif self.config[CONFIG_KEY_MODE] == MODE_STREAM:
            self.stream()
        elif self.config[CONFIG_KEY_MODE] == MODE_WEBPAGE:
            self.webpage()
        else:
            raise ValueError("Unknown mode")

    def feeling_lucky(self):
        """Random play a video from the directory"""
        file_list = list_local_video_dir()
        # Remove current data source from the random selection
        if self.config[CONFIG_KEY_DATA_SOURCE] in file_list:
            file_list.remove(self.config[CONFIG_KEY_DATA_SOURCE])
        if file_list:
            self.video(random.choice(file_list))

    def show_gui(self):
        """Show main GUI"""
        self.gui_process = Process(target=gui_main)
        self.gui_process.start()

    def quit(self):
        try:
            self._quit_player()
        except GLib.Error:
            pass
        # Quit all processes
        for process in [self.player_process, self.gui_process, self.sys_icon_process]:
            if process:
                process.terminate()
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
        self._save_config()
        player = get_instance(DBUS_NAME_PLAYER)
        if player:
            player.volume = volume

    @property
    def blur_radius(self):
        return self.config[CONFIG_KEY_BLUR_RADIUS]

    @blur_radius.setter
    def blur_radius(self, blur_radius):
        self.config[CONFIG_KEY_BLUR_RADIUS] = blur_radius
        self._save_config()
        player = get_instance(DBUS_NAME_PLAYER)
        if player and player.mode != MODE_NULL:
            player.reload_config()

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config[CONFIG_KEY_MUTE] = is_mute
        self._save_config()
        player = get_instance(DBUS_NAME_PLAYER)
        if player:
            player.is_mute = is_mute

    @property
    def is_playing(self):
        player = get_instance(DBUS_NAME_PLAYER)
        if player:
            return player.is_playing
        return False

    @property
    def is_paused_by_user(self):
        player = get_instance(DBUS_NAME_PLAYER)
        if player and player.mode in [MODE_VIDEO, MODE_STREAM]:
            return player.is_paused_by_user
        return None

    @is_paused_by_user.setter
    def is_paused_by_user(self, is_paused_by_user):
        player = get_instance(DBUS_NAME_PLAYER)
        if player and player.mode in [MODE_VIDEO, MODE_STREAM]:
            player.is_paused_by_user = is_paused_by_user

    @property
    def is_static_wallpaper(self):
        return self.config[CONFIG_KEY_STATIC_WALLPAPER]

    @is_static_wallpaper.setter
    def is_static_wallpaper(self, is_static_wallpaper):
        self.config[CONFIG_KEY_STATIC_WALLPAPER] = is_static_wallpaper
        self._save_config()
        player = get_instance(DBUS_NAME_PLAYER)
        if player and player.mode != MODE_NULL:
            player.reload_config()

    @property
    def is_detect_maximized(self):
        return self.config[CONFIG_KEY_DETECT_MAXIMIZED]

    @is_detect_maximized.setter
    def is_detect_maximized(self, is_detect_maximized):
        self.config[CONFIG_KEY_DETECT_MAXIMIZED] = is_detect_maximized
        self._save_config()
        player = get_instance(DBUS_NAME_PLAYER)
        if player and player.mode != MODE_NULL:
            player.reload_config()


def get_instance(dbus_name):
    bus = SessionBus()
    try:
        instance = bus.get(dbus_name)
    except GLib.Error:
        return None
    return instance


def main(args):
    server = get_instance(DBUS_NAME_SERVER)
    if server:
        server.show_gui()
    else:
        # Pause before launching
        time.sleep(args.p)
        bus = SessionBus()
        server = HidamariServer(args)
        try:
            bus.publish(DBUS_NAME_SERVER, server)
            loop.run()
        except RuntimeError:
            raise Exception("Failed to create server")


if __name__ == "__main__":
    # Make sure that X11 is the backend. This makes sure Wayland reverts to XWayland.
    os.environ["GDK_BACKEND"] = "x11"
    # Suppress VLC Log
    os.environ["VLC_VERBOSE"] = "-1"

    parser = argparse.ArgumentParser(description="Hidamari launcher")
    parser.add_argument("-p", "--pause", dest="p", type=int, default=0,
                        help="Add pause before launching Hidamari. [sec]")
    parser.add_argument("-b", "--background", action="store_true", help="Launch only the live wallpaper.")
    parser.add_argument("-d", "--debug", action="store_true", help="Print debug messages.")
    args = parser.parse_args()

    # Setup logger
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # Log system information
    logger.debug(f"[Desktop] {os.environ.get('XDG_CURRENT_DESKTOP', 'Not found')}")
    logger.debug(f"[Display Server] {os.environ.get('XDG_SESSION_TYPE', 'Not found')}")
    logger.debug(f"[Args] {vars(args)}")

    # Clear sys.argv as it has influence to the Gtk.Application
    sys.argv = [sys.argv[0]]
    main(args)
