import logging
import signal

from gi.repository import GLib
from pydbus import SessionBus

from commons import *
from hidamari.utils import ConfigUtil

loop = GLib.MainLoop()
logger = logging.getLogger(LOGGER_NAME)


class HidamariServer(object):
    """
    <node>
    <interface name='io.github.jeffshee.hidamari'>
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
        <method name='quit'/>
        <property name="mode" type="i" access="read"/>
        <property name="volume" type="i" access="readwrite"/>
        <property name="blur_radius" type="i" access="readwrite"/>
        <property name="is_mute" type="b" access="readwrite"/>
        <property name="is_playing" type="b" access="readwrite"/>
        <property name="is_static_wallpaper" type="b" access="readwrite"/>
        <property name="is_detect_maximized" type="b" access="readwrite"/>
    </interface>
    </node>
    """

    def __init__(self):
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, self.quit)

        self._load_config()
        self.player = None
        if self.config[CONFIG_KEY_MODE] is None:
            # Welcome to Hidamari, first time user ;)
            self.dbus_published_callback = self.null
            # Setup
            os.makedirs(VIDEO_WALLPAPER_DIR, exist_ok=True)
        elif self.config[CONFIG_KEY_MODE] == MODE_VIDEO:
            self.dbus_published_callback = self.video
        elif self.config[CONFIG_KEY_MODE] == MODE_STREAM:
            self.dbus_published_callback = self.stream
        elif self.config[CONFIG_KEY_MODE] == MODE_WEBPAGE:
            self.dbus_published_callback = self.webpage
        else:
            raise ValueError("Unknown mode")
        self.gui_process = None

    def _load_config(self):
        self.config = ConfigUtil().load()

    def _save_config(self):
        ConfigUtil().save(self.config)

    def _setup_player(self, mode, data_source=None):
        logger.info(f"[Mode] {mode}")
        self.config[CONFIG_KEY_MODE] = mode
        # Set data source if specified
        if data_source:
            self.config[CONFIG_KEY_DATA_SOURCE] = data_source
        self._save_config()

        # Quit current player
        if self.player:
            self.player.release()
            self.player = None

        if self.player is None:
            # Create new player
            if mode in [MODE_VIDEO, MODE_STREAM]:
                from video_player import VideoPlayer
                self.player = VideoPlayer(self.config)
            elif mode == MODE_WEBPAGE:
                from web_player import WebPlayer
                self.player = WebPlayer(self.config)
        else:
            self.player.mode = mode
            self.player.data_source = self.config[CONFIG_KEY_DATA_SOURCE]

    def null(self):
        logger.info(f"[Mode] {MODE_NULL}")
        from null_player import NullPlayer
        self.player = NullPlayer(self.config)

    def video(self, video_path=None):
        self._setup_player(MODE_VIDEO, video_path)

    def stream(self, stream_url=None):
        self._setup_player(MODE_STREAM, stream_url)

    def webpage(self, webpage_url=None):
        self._setup_player(MODE_WEBPAGE, webpage_url)

    def pause_playback(self):
        if self.player:
            self.player.pause_playback()

    def start_playback(self):
        if self.player:
            self.player.start_playback()

    def quit(self, *args):
        """removes this object from the DBUS connection and exits"""
        if self.player:
            self.player.quit()
        if not self.gui_process:
            print("dd")
            self.gui_process.terminate()
        loop.quit()

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
        if self.player:
            self.player.volume = volume

    @property
    def blur_radius(self):
        return self.config[CONFIG_KEY_BLUR_RADIUS]

    @blur_radius.setter
    def blur_radius(self, blur_radius):
        self.config[CONFIG_KEY_BLUR_RADIUS] = blur_radius
        self._save_config()
        if self.player:
            self.player.config = self.config

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config[CONFIG_KEY_MUTE] = is_mute
        self._save_config()
        if self.player:
            self.player.is_mute = is_mute

    @property
    def is_playing(self):
        if self.player:
            return self.player.is_playing
        return False

    @is_playing.setter
    def is_playing(self, is_playing):
        if self.player:
            self.player.is_paused_by_user = not is_playing

    @property
    def is_static_wallpaper(self):
        return self.config[CONFIG_KEY_STATIC_WALLPAPER]

    @is_static_wallpaper.setter
    def is_static_wallpaper(self, is_static_wallpaper):
        self.config[CONFIG_KEY_STATIC_WALLPAPER] = is_static_wallpaper
        self._save_config()
        if self.player:
            self.player.config = self.config

    @property
    def is_detect_maximized(self):
        return self.config[CONFIG_KEY_DETECT_MAXIMIZED]

    @is_detect_maximized.setter
    def is_detect_maximized(self, is_detect_maximized):
        self.config[CONFIG_KEY_DETECT_MAXIMIZED] = is_detect_maximized
        self._save_config()
        if self.player:
            self.player.config = self.config

    def show_gui(self):
        import multiprocessing as mp
        from multiprocessing import Process
        from ui.gui import main
        mp.set_start_method("spawn")
        self.gui_process = Process(target=main)
        self.gui_process.start()


def run():
    bus = SessionBus()
    hidamari = HidamariServer()
    try:
        bus.publish(DBUS_NAME_SERVER, hidamari)
        hidamari.dbus_published_callback()
        hidamari.show_gui()
        loop.run()
    except RuntimeError:
        # raise Exception("Failed to create server")
        hidamari.show_gui()


if __name__ == "__main__":
    run()
