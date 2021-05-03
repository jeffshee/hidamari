import gi
import vlc

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


class Monitor:
    """
    A wrapper of Gdk.Monitor
    """

    def __init__(self, gdk_monitor: Gdk.Monitor):
        self.gdk_monitor = gdk_monitor
        # Window and VLC widget or WebView dedicated for each monitor
        self.__window = None
        self.__vlc_widget = None
        self.__webview = None

    def initialize(self, window: Gtk.Window, vlc_widget=None, webview=None):
        self.__window = window
        self.__vlc_widget = vlc_widget
        self.__webview = webview

    @property
    def is_vlc_initialized(self):
        return self.__window is not None and self.__vlc_widget is not None

    @property
    def is_webview_initialized(self):
        return self.__window is not None and self.__webview is not None

    @property
    def x(self):
        return self.gdk_monitor.get_geometry().x

    @property
    def y(self):
        return self.gdk_monitor.get_geometry().y

    @property
    def width(self):
        return self.gdk_monitor.get_geometry().width * self.gdk_monitor.get_scale_factor()

    @property
    def height(self):
        return self.gdk_monitor.get_geometry().height * self.gdk_monitor.get_scale_factor()

    @property
    def is_primary(self):
        return self.gdk_monitor.is_primary()

    # Expose frequently used functions
    def vlc_play(self):
        if self.is_vlc_initialized:
            self.__vlc_widget.player.play()

    def vlc_is_playing(self):
        if self.is_vlc_initialized:
            return self.__vlc_widget.player.is_playing()

    def vlc_pause(self):
        if self.is_vlc_initialized:
            self.__vlc_widget.player.pause()

    def vlc_media_new(self, *args):
        if self.is_vlc_initialized:
            return self.__vlc_widget.instance.media_new(*args)

    def vlc_set_media(self, *args):
        if self.is_vlc_initialized:
            self.__vlc_widget.player.set_media(*args)

    def vlc_audio_set_volume(self, *args):
        if self.is_vlc_initialized:
            self.__vlc_widget.player.audio_set_volume(*args)

    def vlc_get_position(self, *args):
        if self.is_vlc_initialized:
            return self.__vlc_widget.player.get_position()

    def vlc_set_position(self, *args):
        if self.is_vlc_initialized:
            self.__vlc_widget.player.set_position(*args)

    def vlc_snapshot(self, *args):
        if self.is_vlc_initialized:
            return self.__vlc_widget.player.video_take_snapshot(*args)

    def vlc_add_audio_track(self, audio):
        if self.is_vlc_initialized:
            self.__vlc_widget.player.add_slave(vlc.MediaSlaveType(1), audio, True)

    def web_load_uri(self, uri):
        if self.is_webview_initialized:
            self.__webview.load_uri(uri)

    def web_set_is_mute(self, is_mute):
        if self.is_webview_initialized:
            self.__webview.set_is_muted(is_mute)

    def web_reload(self):
        if self.is_webview_initialized:
            self.__webview.reload()

    def win_move(self, *args):
        if self.is_vlc_initialized or self.is_webview_initialized:
            self.__window.move(*args)

    def win_resize(self, *args):
        if self.is_vlc_initialized or self.is_webview_initialized:
            self.__window.resize(*args)

    def __eq__(self, other):
        if isinstance(other, Monitor):
            return self.gdk_monitor == other.gdk_monitor
        return False

    def __del__(self):
        if self.is_vlc_initialized:
            self.__vlc_widget.player.release()
            self.__window.close()
        elif self.is_webview_initialized:
            self.__window.close()
