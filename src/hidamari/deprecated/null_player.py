import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from base_player import BasePlayer
from hidamari.commons import *


class NullPlayer(BasePlayer):
    def __init__(self, config):
        super().__init__(config)
        self.start_all_monitors()

        self.menu = self._build_context_menu()
        for child in self.menu.get_children():
            # Remove unsupported action
            if child.get_label() not in ["Show Hidamari", "Quit Hidamari", "GNOME Settings"]:
                self.menu.remove(child)
        self.menu.show_all()
        # Welcome dialog
        dialog = Gtk.MessageDialog(text="Welcome to Hidamari 🤗", message_type=Gtk.MessageType.INFO,
                                   secondary_text="<b>Right click</b> on the desktop to access the Main Menu",
                                   secondary_use_markup=True,
                                   buttons=Gtk.ButtonsType.OK)
        dialog.run()
        dialog.destroy()

    @property
    def mode(self):
        return self.config[CONFIG_KEY_MODE]

    @mode.setter
    def mode(self, mode):
        self.config[CONFIG_KEY_MODE] = mode

    @property
    def data_source(self):
        return self.config[CONFIG_KEY_DATA_SOURCE]

    @data_source.setter
    def data_source(self, data_source: str):
        self.config[CONFIG_KEY_DATA_SOURCE] = data_source

    @property
    def volume(self):
        return self.config[CONFIG_KEY_VOLUME]

    @volume.setter
    def volume(self, volume):
        self.config[CONFIG_KEY_VOLUME] = volume

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @property
    def is_playing(self):
        return False

    def pause_playback(self):
        pass

    def start_playback(self):
        pass

    def start_all_monitors(self):
        for monitor in self.monitors:
            if monitor.is_initialized:
                continue

            # Window settings
            window = Gtk.Window()
            window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
            window.set_size_request(monitor.width, monitor.height)
            window.move(monitor.x, monitor.y)

            # Button event
            window.connect("button-press-event", self._on_button_press_event)
            window.show_all()

            window.set_opacity(0.0)

            monitor.initialize(window)

    def _on_monitor_added(self, _, gdk_monitor, *args):
        super(NullPlayer, self)._on_monitor_added(_, gdk_monitor, *args)
        self.start_all_monitors()
