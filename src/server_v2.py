import signal

import os
from gi.repository import GLib
from pydbus import SessionBus
from pydbus.generic import signal as dbus_signal
import pkg_resources

DBUS_NAME = "io.github.jeffshee.hidamari"
VIDEO_WALLPAPER_PATH = os.environ["HOME"] + "/Videos/Hidamari"

# Make sure that X11 is the backend. This makes sure Wayland reverts to XWayland.
os.environ['GDK_BACKEND'] = "x11"
# Suppress VLC Log
os.environ["VLC_VERBOSE"] = "-1"

loop = GLib.MainLoop()

VERSION = 2

MODE_VIDEO = "video"
MODE_STREAM = "stream"
MODE_WEBPAGE = "webpage"

# Dummy
config = {
    "version": VERSION,
    "mode": MODE_VIDEO,
    "data_source": "/home/jeffshee/Videos/Hidamari/Rem.mp4",
    "mute_audio": False,
    "audio_volume": 50,
    "static_wallpaper": True,
    "static_wallpaper_blur_radius": 5,
    "detect_maximized": True
}
# config = {
#     "version": VERSION,
#     "mode": MODE_STREAM,
#     "data_source": "https://www.youtube.com/watch?v=Y-lYuGIWqu0&list=LL&index=6",
#     "mute_audio": False,
#     "audio_volume": 50,
#     "static_wallpaper": True,
#     "static_wallpaper_blur_radius": 5,
#     "detect_maximized": True
# }

# config = {
#     "version": VERSION,
#     "mode": MODE_WEBPAGE,
#     "data_source": "https://alteredqualia.com/three/examples/webgl_pasta.html",
#     "mute_audio": False,
#     "audio_volume": 50,
#     "static_wallpaper": True,
#     "static_wallpaper_blur_radius": 5,
#     "detect_maximized": True
# }
# config = {
#     "version": VERSION,
#     "mode": MODE_WEBPAGE,
#     "data_source": "/home/jeffshee/test.html",
#     "mute_audio": False,
#     "audio_volume": 50,
#     "static_wallpaper": True,
#     "static_wallpaper_blur_radius": 5,
#     "detect_maximized": True
# }


class HidamariService(object):
    def __init__(self):
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, self.quit)

        self._someProperty = "initial value"
        self.config = config
        self.player = None
        if config["mode"] == MODE_VIDEO:
            self.video()
        elif config["mode"] == MODE_STREAM:
            self.stream()
        elif config["mode"] == MODE_WEBPAGE:
            self.webpage()
        else:
            raise ValueError("Unknown mode")

    # Load dbus xml
    dbus = pkg_resources.resource_string(__name__, "dbus.xml").decode("utf-8")
    # Signals
    PropertiesChanged = dbus_signal()

    def video(self, video_path=None):
        print("video")

        # Set data source if specified
        if video_path is not None:
            self.config["data_source"] = video_path

        # Quit current player if different
        if self.config["mode"] == MODE_WEBPAGE:
            self.config["mode"] = MODE_VIDEO
            self.player.release()
            self.player = None

        if self.player is None:
            # Create new player
            from player_v2 import Player
            self.player = Player(self.config)
        else:
            self.player.mode = MODE_VIDEO
            self.player.data_source = self.config["data_source"]

    def stream(self, stream_url=None):
        print("stream")

        # Set data source if specified
        if stream_url is not None:
            self.config["data_source"] = stream_url

        # Quit current player if different
        if self.config["mode"] == MODE_WEBPAGE and self.player is not None:
            self.config["mode"] = MODE_STREAM
            self.player.release()
            self.player = None

        if self.player is None:
            # Create new player
            from player_v2 import Player
            self.player = Player(self.config)
        else:
            self.player.mode = MODE_STREAM
            self.player.data_source = self.config["data_source"]

    def webpage(self, webpage_url=None):
        print("webpage")

        # Set data source if specified
        if webpage_url is not None:
            self.config["data_source"] = webpage_url

        # Quit current player if different
        if self.config["mode"] != MODE_WEBPAGE and self.player is not None:
            self.config["mode"] = MODE_WEBPAGE
            self.player.release()
            self.player = None

        if self.player is None:
            # Create new player
            from web_player_v2 import WebPlayer
            self.player = WebPlayer(self.config)
        else:
            self.player.mode = MODE_WEBPAGE
            self.player.data_source = self.config["data_source"]

    def pause(self):
        pass

    def play(self):
        pass

    def quit(self, *args):
        """removes this object from the DBUS connection and exits"""
        if self.player is not None:
            self.player.quit()
        else:
            loop.quit()

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


bus = SessionBus()
try:
    bus.publish(DBUS_NAME, HidamariService())
    loop.run()
except RuntimeError:
    pass
