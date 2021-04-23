import os
import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib

GUI_GLADE_PATH = os.path.join(sys.path[0], "gui_v2.glade")
APPLICATION_ID = "io.github.jeffshee.hidamari"


class GUI(Gtk.Application):
    def __init__(self):
        super(GUI, self).__init__(application_id=APPLICATION_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.builder = Gtk.Builder()
        self.builder.set_application(self)
        self.builder.add_from_file(GUI_GLADE_PATH)

        signals = {"on_volume_changed": self.on_volume_changed,
                   "on_streaming_activate": self.on_streaming_activate,
                   "on_streaming_refresh": self.on_streaming_refresh,
                   "on_web_page_activate": self.on_web_page_activate,
                   "on_web_page_refresh": self.on_web_page_refresh}
        self.builder.connect_signals(signals)

        self.window = None

        self.mute = False
        self.autostart = False
        self.static_wallpaper = False
        self.detect_maximized = False
        self.volume = 0
        self.is_playing = True

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("local_video_dir", None)
        action.connect("activate", self.on_local_video_dir)
        self.add_action(action)

        action = Gio.SimpleAction.new("local_video_refresh", None)
        action.connect("activate", self.on_local_video_refresh)
        self.add_action(action)

        action = Gio.SimpleAction.new("local_video_apply", None)
        action.connect("activate", self.on_local_video_apply)
        self.add_action(action)

        action = Gio.SimpleAction.new("streaming_apply", None)
        action.connect("activate", self.on_streaming_apply)
        self.add_action(action)

        action = Gio.SimpleAction.new("web_page_apply", None)
        action.connect("activate", self.on_web_page_apply)
        self.add_action(action)

        action = Gio.SimpleAction.new("play_pause", None)
        action.connect("activate", self.on_play_pause)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("mute", None, GLib.Variant.new_boolean(self.mute))
        action.connect("change-state", self.on_mute)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("autostart", None, GLib.Variant.new_boolean(self.autostart))
        action.connect("change-state", self.on_autostart)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("static_wallpaper", None,
                                               GLib.Variant.new_boolean(self.static_wallpaper))
        action.connect("change-state", self.on_static_wallpaper)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("detect_maximized", None,
                                               GLib.Variant.new_boolean(self.detect_maximized))
        action.connect("change-state", self.on_detect_maximized)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.on_preferences)
        self.add_action(action)

    def do_activate(self):
        if not self.window:
            self.window: Gtk.ApplicationWindow = self.builder.get_object("ApplicationWindow")
            self.window.set_title("Hidamari")
            self.window.set_application(self)
            self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.present()

    def on_local_video_dir(self, action, param):
        print(action.get_name(), param)

    def on_local_video_refresh(self, action, param):
        print(action.get_name(), param)

    def on_local_video_apply(self, action, param):
        print(action.get_name(), param)

    def on_streaming_apply(self, action, param):
        print(action.get_name(), param)

    def on_web_page_apply(self, action, param):
        print(action.get_name(), param)

    def set_play_pause_icon(self):
        play_pause_icon: Gtk.Image = self.builder.get_object("ButtonPlayPauseIcon")
        if self.is_playing:
            icon_name = "player_pause"
        else:
            icon_name = "player_play"
        play_pause_icon.set_from_icon_name(icon_name=icon_name, size=0)

    def on_play_pause(self, action, param):
        self.is_playing = not self.is_playing
        print(action.get_name(), self.is_playing)
        self.set_play_pause_icon()

    def set_mute_toggle_icon(self):
        toggle_icon: Gtk.Image = self.builder.get_object("ToggleMuteIcon")
        if self.volume == 0 or self.mute:
            icon_name = "audio-volume-muted"
        elif self.volume < 30:
            icon_name = "audio-volume-low"
        elif self.volume < 60:
            icon_name = "audio-volume-medium"
        else:
            icon_name = "audio-volume-high"
        toggle_icon.set_from_icon_name(icon_name=icon_name, size=0)

    def set_scale_volume_sensitive(self):
        scale = self.builder.get_object("ScaleVolume")
        if self.mute:
            scale.set_sensitive(False)
        else:
            scale.set_sensitive(True)

    def on_volume_changed(self, adjustment):
        self.volume = adjustment.get_value()
        print("volume", self.volume)
        self.set_mute_toggle_icon()

    def on_mute(self, action, state):
        action.set_state(state)
        self.mute = state
        print(action.get_name(), state)
        self.set_mute_toggle_icon()
        self.set_scale_volume_sensitive()

    def on_autostart(self, action, state):
        action.set_state(state)
        self.autostart = state
        print(action.get_name(), state)

    def on_static_wallpaper(self, action, state):
        action.set_state(state)
        self.static_wallpaper = state
        print(action.get_name(), state)

    def on_detect_maximized(self, action, state):
        action.set_state(state)
        self.detect_maximized = state
        print(action.get_name(), state)

    def on_about(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_file(GUI_GLADE_PATH)
        about_dialog: Gtk.AboutDialog = builder.get_object("AboutDialog")
        about_dialog.set_transient_for(self.window)
        about_dialog.set_modal(True)
        about_dialog.present()

    def on_preferences(self, action, param):
        print(action.get_name(), param)

    def on_streaming_activate(self, entry):
        print(entry)

    def on_streaming_refresh(self, entry, *args):
        print(entry)

    def on_web_page_activate(self, entry):
        print(entry)

    def on_web_page_refresh(self, entry, *args):
        print(entry)


if __name__ == "__main__":
    app = GUI()
    app.run(sys.argv)
