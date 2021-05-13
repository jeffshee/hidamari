import signal

import pkg_resources
from gi.repository import GLib
from pydbus import SessionBus

from commons import *
from utils import ConfigUtil

# Make sure that X11 is the backend. This makes sure Wayland reverts to XWayland.
os.environ['GDK_BACKEND'] = "x11"
# Suppress VLC Log
os.environ["VLC_VERBOSE"] = "-1"

loop = GLib.MainLoop()


class HidamariService(object):
    def __init__(self):
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, self.quit)
        # Ignore SIGHUP to handle shutdown event correctly
        # https://askubuntu.com/questions/819730/no-sigterm-before-sigkill-shutdown-with-systemd-on-ubuntu-16-04
        signal.signal(signal.SIGHUP, lambda *args: None)

        self.config = ConfigUtil().load()
        self.player = None
        if self.config[CONFIG_KEY_MODE] is None:
            # Welcome to Hidamari, first time user ;)
            self.dbus_published_callback = self.null
        elif self.config[CONFIG_KEY_MODE] == MODE_VIDEO:
            self.dbus_published_callback = self.video
        elif self.config[CONFIG_KEY_MODE] == MODE_STREAM:
            self.dbus_published_callback = self.stream
        elif self.config[CONFIG_KEY_MODE] == MODE_WEBPAGE:
            self.dbus_published_callback = self.webpage
        else:
            raise ValueError("Unknown mode")

    # Load dbus xml
    dbus = pkg_resources.resource_string(__name__, "dbus.xml").decode("utf-8")

    def null(self):
        print("Mode: Null")
        from null_player import NullPlayer
        self.player = NullPlayer(self.config)

    def _setup_player(self, mode, data_source=None):
        self.config[CONFIG_KEY_MODE] = mode
        # Set data source if specified
        if data_source is not None:
            self.config[CONFIG_KEY_DATA_SOURCE] = data_source

        # Quit current player
        if self.player is not None:
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

    def video(self, video_path=None):
        print("Mode: Video")
        self._setup_player(MODE_VIDEO, video_path)

    def stream(self, stream_url=None):
        print("Mode: Stream")
        self._setup_player(MODE_STREAM, stream_url)

    def webpage(self, webpage_url=None):
        print("Mode: Webpage")
        self._setup_player(MODE_WEBPAGE, webpage_url)

    def pause_playback(self):
        if self.player is not None:
            self.player.pause_playback()

    def start_playback(self):
        if self.player is not None:
            self.player.start_playback()

    def quit(self, *args):
        """removes this object from the DBUS connection and exits"""
        if self.player is not None:
            self.player.quit()
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
        if self.player is not None:
            self.player.volume = volume

    @property
    def blur_radius(self):
        return self.config[CONFIG_KEY_BLUR_RADIUS]

    @blur_radius.setter
    def blur_radius(self, blur_radius):
        self.config[CONFIG_KEY_BLUR_RADIUS] = blur_radius
        if self.player is not None:
            self.player.config = self.config

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config[CONFIG_KEY_MUTE] = is_mute
        if self.player is not None:
            self.player.is_mute = is_mute

    @property
    def is_playing(self):
        if self.player is not None:
            return self.player.is_playing
        return False

    @is_playing.setter
    def is_playing(self, is_playing):
        if self.player is not None:
            self.player.user_pause_playback = not is_playing

    @property
    def is_static_wallpaper(self):
        return self.config[CONFIG_KEY_STATIC_WALLPAPER]

    @is_static_wallpaper.setter
    def is_static_wallpaper(self, is_static_wallpaper):
        self.config[CONFIG_KEY_STATIC_WALLPAPER] = is_static_wallpaper
        if self.player is not None:
            self.player.config = self.config

    @property
    def is_detect_maximized(self):
        return self.config[CONFIG_KEY_DETECT_MAXIMIZED]

    @is_detect_maximized.setter
    def is_detect_maximized(self, is_detect_maximized):
        self.config[CONFIG_KEY_DETECT_MAXIMIZED] = is_detect_maximized
        if self.player is not None:
            self.player.config = self.config


def run():
    bus = SessionBus()
    try:
        hidamari = HidamariService()
        bus.publish(DBUS_NAME, hidamari)
        hidamari.dbus_published_callback()
        loop.run()
    except RuntimeError:
        print("Error: Failed to create server")


if __name__ == "__main__":
    run()
