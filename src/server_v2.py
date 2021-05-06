import os
import signal

import pkg_resources
from gi.repository import GLib
from pydbus import SessionBus
from pydbus.generic import signal as dbus_signal

from utils_v2 import ConfigUtil

DBUS_NAME = "io.github.jeffshee.hidamari"
VIDEO_WALLPAPER_PATH = os.environ["HOME"] + "/Videos/Hidamari"

# Make sure that X11 is the backend. This makes sure Wayland reverts to XWayland.
os.environ['GDK_BACKEND'] = "x11"
# Suppress VLC Log
os.environ["VLC_VERBOSE"] = "-1"

MODE_VIDEO = "video"
MODE_STREAM = "stream"
MODE_WEBPAGE = "webpage"


# TODO
# Complete GUI
# Rename some variables in config, etc. to make everything more consistent
# Debug mode
# Context menu may cause system freeze

class HidamariService(object):
    def __init__(self):
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, self.quit)

        self._someProperty = "initial value"
        self.config = ConfigUtil().load()
        self.player = None
        if self.config["mode"] is None:
            # Welcome to Hidamari, first time user ;)
            self.dbus_published_callback = self.null
        elif self.config["mode"] == MODE_VIDEO:
            self.dbus_published_callback = self.video
        elif self.config["mode"] == MODE_STREAM:
            self.dbus_published_callback = self.stream
        elif self.config["mode"] == MODE_WEBPAGE:
            self.dbus_published_callback = self.webpage
        else:
            raise ValueError("Unknown mode")

    # Load dbus xml
    dbus = pkg_resources.resource_string(__name__, "dbus.xml").decode("utf-8")
    # Signals
    PropertiesChanged = dbus_signal()

    def null(self):
        print("null")
        from null_player import NullPlayer
        self.player = NullPlayer(self.config)

    def _setup_player(self, mode, data_source=None):
        self.config["mode"] = mode
        # Set data source if specified
        if data_source is not None:
            self.config["data_source"] = data_source

        # Quit current player
        if self.player is not None:
            self.player.release()
            self.player = None

        if self.player is None:
            # Create new player
            if mode in [MODE_VIDEO, MODE_STREAM]:
                from player_v2 import Player
                self.player = Player(self.config)
            elif mode == MODE_WEBPAGE:
                from web_player_v2 import WebPlayer
                self.player = WebPlayer(self.config)
        else:
            self.player.mode = mode
            self.player.data_source = self.config["data_source"]

    def video(self, video_path=None):
        print("video")
        self._setup_player(MODE_VIDEO, video_path)

    def stream(self, stream_url=None):
        print("stream")
        self._setup_player(MODE_STREAM, stream_url)

    def webpage(self, webpage_url=None):
        print("webpage")
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
    def volume(self):
        return self.config["audio_volume"]

    @volume.setter
    def volume(self, volume):
        self.config["audio_volume"] = volume
        if self.player is not None:
            self.player.volume = volume

    @property
    def is_mute(self):
        return self.config["mute_audio"]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config["mute_audio"] = is_mute
        if self.player is not None:
            self.player.is_mute = is_mute

    @property
    def is_playing(self):
        if self.player is not None:
            return self.player.is_playing
        return False

    @property
    def is_static_wallpaper(self):
        return self.config["static_wallpaper"]

    @is_static_wallpaper.setter
    def is_static_wallpaper(self, is_static_wallpaper):
        self.config["static_wallpaper"] = is_static_wallpaper
        if self.player is not None:
            self.player.config = self.config

    @property
    def is_detect_maximized(self):
        return self.config["detect_maximized"]

    @is_detect_maximized.setter
    def is_detect_maximized(self, is_detect_maximized):
        self.config["detect_maximized"] = is_detect_maximized
        if self.player is not None:
            self.player.config = self.config

    @property
    def SomeProperty(self):
        return self._someProperty

    @SomeProperty.setter
    def SomeProperty(self, value):
        self._someProperty = value
        self.PropertiesChanged("io.github.jeffshee.hidamari", {"SomeProperty": self.SomeProperty}, [])

    def Hello(self):
        """returns the string 'Hello, World!'"""
        return "Hello, World!"

    def EchoString(self, s):
        """returns whatever is passed to it"""
        return s


if __name__ == "__main__":
    loop = GLib.MainLoop()
    bus = SessionBus()
    try:
        hidamari = HidamariService()
        bus.publish(DBUS_NAME, hidamari)
        hidamari.dbus_published_callback()
        loop.run()
    except RuntimeError:
        pass
