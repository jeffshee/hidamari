import pathlib

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, Gdk, WebKit2

from base_player import BasePlayer
from commons import *


class WebPlayer(BasePlayer):
    def __init__(self, config):
        super().__init__(config)
        self.start_all_monitors()
        # For some weird reason the context menu must be built here but not at the base class.
        # Otherwise it freezes your PC and you will need a reboot ¯\_(ツ)_/¯
        self.menu = self._build_context_menu()
        for child in self.menu.get_children():
            # Remove unsupported action
            if child.get_label() == "Pause Playback":
                self.menu.remove(child)
        self.menu.show_all()

    @property
    def mode(self):
        return self.config[CONFIG_KEY_MODE]

    @mode.setter
    def mode(self, mode):
        self.config[CONFIG_KEY_MODE] = mode

    @property
    def volume(self):
        return self.config[CONFIG_KEY_VOLUME]

    @volume.setter
    def volume(self, volume):
        # TODO can we set volume of webview?
        self.config[CONFIG_KEY_VOLUME] = volume

    @property
    def data_source(self):
        return self.config[CONFIG_KEY_DATA_SOURCE]

    @data_source.setter
    def data_source(self, data_source: str):
        self.config[CONFIG_KEY_DATA_SOURCE] = data_source
        if self.mode != MODE_WEBPAGE:
            raise ValueError("Invalid mode")

        # Convert to uri if necessary
        if not data_source.startswith("http://") and \
                not data_source.startswith("https://") and not data_source.startswith("file://"):
            data_source = pathlib.Path(data_source).resolve().as_uri()

        for monitor in self.monitors:
            monitor.web_load_uri(data_source)
            if not monitor.is_primary:
                monitor.web_set_is_mute(True)
        self.volume = self.config[CONFIG_KEY_VOLUME]
        self.is_mute = self.config[CONFIG_KEY_MUTE]

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config[CONFIG_KEY_MUTE] = is_mute
        for monitor in self.monitors:
            if monitor.is_primary:
                monitor.web_set_is_mute(is_mute)

    @property
    def is_playing(self):
        return True

    def pause_playback(self):
        pass

    def start_playback(self):
        pass

    def start_all_monitors(self):
        for monitor in self.monitors:
            if monitor.is_webview_initialized:
                continue
            webview = WebKit2.WebView()

            # Window settings
            window = Gtk.Window()
            window.add(webview)
            window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
            window.set_size_request(monitor.width, monitor.height)
            window.move(monitor.x, monitor.y)

            # Button event
            webview.connect("button-press-event", self._on_button_press_event)
            window.show_all()

            monitor.initialize(window, webview=webview)

        self.data_source = self.config[CONFIG_KEY_DATA_SOURCE]

    def _on_monitor_added(self, _, gdk_monitor, *args):
        super(WebPlayer, self)._on_monitor_added(_, gdk_monitor, *args)
        self.start_all_monitors()

    def _on_menuitem_reload(self, *args):
        for monitor in self.monitors:
            monitor.web_reload()
