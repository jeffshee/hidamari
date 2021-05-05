import sys
import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from base_player import BasePlayer


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

        subprocess.Popen([sys.executable, "gui_v2.py"])

    @property
    def mode(self):
        return self.config["mode"]

    @mode.setter
    def mode(self, mode):
        self.config["mode"] = mode

    @property
    def data_source(self):
        return self.config["data_source"]

    @data_source.setter
    def data_source(self, data_source: str):
        self.config["data_source"] = data_source

    @property
    def volume(self):
        return self.config["audio_volume"]

    @volume.setter
    def volume(self, volume):
        self.config["audio_volume"] = volume

    @property
    def is_mute(self):
        return self.config["mute_audio"]

    # @is_mute.setter
    # def is_mute(self, is_mute):
    #     self.config["mute_audio"] = is_mute

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

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer()
        return True
