import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib
from pydbus import SessionBus
from hidamari.commons import *


class GUI(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(GUI, self).__init__(
            *args,
            application_id=APPLICATION_ID_GUI,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
            **kwargs
        )
        self.builder = Gtk.Builder()
        self.builder.set_application(self)
        self.builder.add_from_file(GUI_GLADE_PATH)

        signals = {"on_volume_changed": self.on_volume_changed,
                   "on_streaming_activate": self.on_streaming_activate,
                   "on_streaming_refresh": self.on_streaming_refresh,
                   "on_web_page_activate": self.on_web_page_activate,
                   "on_web_page_refresh": self.on_web_page_refresh,
                   "on_blur_radius_changed": self.on_blur_radius_changed}
        self.builder.connect_signals(signals)

        self.window = None
        self.local_video_icon_view = None
        self.local_video_list = None

        self.is_autostart = os.path.isfile(AUTOSTART_DESKTOP_PATH)

        bus = SessionBus()
        try:
            self.server = bus.get(DBUS_NAME_SERVER)
        except GLib.Error:
            dialog = Gtk.MessageDialog(text="Oops!", message_type=Gtk.MessageType.ERROR,
                                       secondary_text="Couldn't connect to server",
                                       buttons=Gtk.ButtonsType.OK)
            dialog.run()
            dialog.destroy()
            print("Error: Couldn't connect to server")

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

        action = Gio.SimpleAction.new("local_web_page_apply", None)
        action.connect("activate", self.on_local_web_page_apply)
        self.add_action(action)

        action = Gio.SimpleAction.new("play_pause", None)
        action.connect("activate", self.on_play_pause)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("mute", None, GLib.Variant.new_boolean(self.server.is_mute))
        action.connect("change-state", self.on_mute)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("autostart", None, GLib.Variant.new_boolean(self.is_autostart))
        action.connect("change-state", self.on_autostart)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("static_wallpaper", None,
                                               GLib.Variant.new_boolean(self.server.is_static_wallpaper))
        action.connect("change-state", self.on_static_wallpaper)
        self.add_action(action)

        action = Gio.SimpleAction.new_stateful("detect_maximized", None,
                                               GLib.Variant.new_boolean(self.server.is_detect_maximized))
        action.connect("change-state", self.on_detect_maximized)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.on_preferences)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        self._reload_all_widgets()

    def do_activate(self):
        if not self.window:
            self.window: Gtk.ApplicationWindow = self.builder.get_object("ApplicationWindow")
            self.window.set_title("Hidamari")
            self.window.set_application(self)
            self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.present()

    @staticmethod
    def on_local_video_dir(action, param):
        from hidamari.utils import xdg_open_video_dir
        xdg_open_video_dir()

    def on_local_video_refresh(self, action, param):
        self._reload_local_video_icon_view()

    def on_local_video_apply(self, action, param):
        selected = self.local_video_icon_view.get_selected_items()
        if len(selected) != 0:
            index = selected[0].get_indices()[0]
            print("Local Video:", self.local_video_list[index])
            self.server.video(self.local_video_list[index])

    def on_local_web_page_apply(self, action, param):
        file_chooser: Gtk.FileChooserButton = self.builder.get_object("FileChooser")
        choose: Gio.File = file_chooser.get_file()
        print("Local Webpage:", choose.get_path())
        self.server.webpage(choose.get_path())

    def set_play_pause_icon(self):
        play_pause_icon: Gtk.Image = self.builder.get_object("ButtonPlayPauseIcon")
        if not self.server.is_paused_by_user:
            icon_name = "media-playback-pause"
        else:
            icon_name = "media-playback-start"
        play_pause_icon.set_from_icon_name(icon_name=icon_name, size=0)

    def on_play_pause(self, action, param):
        is_paused_by_user = self.server.is_paused_by_user
        self.server.is_paused_by_user = not is_paused_by_user
        if not is_paused_by_user:
            self.server.pause_playback()
        else:
            self.server.start_playback()
        self.set_play_pause_icon()

    def set_mute_toggle_icon(self):
        toggle_icon: Gtk.Image = self.builder.get_object("ToggleMuteIcon")
        if self.server.volume == 0 or self.server.is_mute:
            icon_name = "audio-volume-muted"
        elif self.server.volume < 30:
            icon_name = "audio-volume-low"
        elif self.server.volume < 60:
            icon_name = "audio-volume-medium"
        else:
            icon_name = "audio-volume-high"
        toggle_icon.set_from_icon_name(icon_name=icon_name, size=0)

    def set_scale_volume_sensitive(self):
        scale = self.builder.get_object("ScaleVolume")
        if self.server.is_mute:
            scale.set_sensitive(False)
        else:
            scale.set_sensitive(True)

    def set_spin_blur_radius_sensitive(self):
        spin = self.builder.get_object("SpinBlurRadius")
        if self.server.is_static_wallpaper:
            spin.set_sensitive(True)
        else:
            spin.set_sensitive(False)

    def on_volume_changed(self, adjustment):
        self.server.volume = int(adjustment.get_value())
        print("Volume:", self.server.volume)
        self.set_mute_toggle_icon()

    def on_blur_radius_changed(self, adjustment):
        self.server.blur_radius = int(adjustment.get_value())
        print("Blur radius:", self.server.blur_radius)

    def on_mute(self, action, state):
        action.set_state(state)
        self.server.is_mute = state
        print("GUI:", action.get_name(), state)
        self.set_mute_toggle_icon()
        self.set_scale_volume_sensitive()

    def on_autostart(self, action, state):
        action.set_state(state)
        self.is_autostart = state
        print("GUI:", action.get_name(), state)
        from hidamari.utils import setup_autostart
        setup_autostart(state)

    def on_static_wallpaper(self, action, state):
        action.set_state(state)
        self.server.is_static_wallpaper = state
        print("GUI:", action.get_name(), state)
        self.set_spin_blur_radius_sensitive()

    def on_detect_maximized(self, action, state):
        action.set_state(state)
        self.server.is_detect_maximized = state
        print("GUI:", action.get_name(), state)

    def on_about(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_file(GUI_GLADE_PATH)
        about_dialog: Gtk.AboutDialog = builder.get_object("AboutDialog")
        about_dialog.set_transient_for(self.window)
        about_dialog.set_modal(True)
        about_dialog.present()

    def on_preferences(self, action, param):
        print(action.get_name(), param)

    def on_streaming_activate(self, entry: Gtk.Entry):
        url = entry.get_text()
        print("Streaming:", url)
        self.server.stream(url)

    def on_streaming_refresh(self, entry: Gtk.Entry, *args):
        url = entry.get_text()
        print("Streaming:", url)
        self.server.stream(url)

    def on_web_page_activate(self, entry: Gtk.Entry):
        url = entry.get_text()
        print("Webpage:", url)
        self.server.webpage(url)

    def on_web_page_refresh(self, entry: Gtk.Entry, *args):
        url = entry.get_text()
        print("Webpage:", url)
        self.server.webpage(url)

    def on_quit(self, action, param):
        try:
            # Ignore NoReply error
            self.server.quit()
        except GLib.Error:
            pass
        self.quit()

    def _reload_all_widgets(self):
        self._reload_local_video_icon_view()
        self.set_play_pause_icon()
        self.set_mute_toggle_icon()
        self.set_scale_volume_sensitive()
        self.set_spin_blur_radius_sensitive()
        toggle_mute: Gtk.ToggleButton = self.builder.get_object("ToggleMute")
        toggle_mute.set_state = self.server.is_mute

        scale_volume: Gtk.Scale = self.builder.get_object("ScaleVolume")
        adjustment_volume: Gtk.Adjustment = self.builder.get_object("AdjustmentVolume")
        # Temporary block signal
        adjustment_volume.handler_block_by_func(self.on_volume_changed)
        scale_volume.set_value(self.server.volume)
        adjustment_volume.handler_unblock_by_func(self.on_volume_changed)

        spin_blur_radius: Gtk.Scale = self.builder.get_object("SpinBlurRadius")
        adjustment_blur: Gtk.Adjustment = self.builder.get_object("AdjustmentBlur")
        adjustment_blur.handler_block_by_func(self.on_blur_radius_changed)
        spin_blur_radius.set_value(self.server.blur_radius)
        adjustment_blur.handler_unblock_by_func(self.on_blur_radius_changed)

        toggle_mute: Gtk.ToggleButton = self.builder.get_object("ToggleAutostart")
        toggle_mute.set_state = self.is_autostart

    def _reload_local_video_icon_view(self):
        from hidamari.utils import list_local_video_dir, get_thumbnail_gnome
        from gi.repository.GdkPixbuf import Pixbuf
        list_store = Gtk.ListStore(Pixbuf, str)

        self.local_video_list = list_local_video_dir()
        self.local_video_icon_view: Gtk.IconView = self.builder.get_object("IconView")
        self.local_video_icon_view.set_model(list_store)
        self.local_video_icon_view.set_pixbuf_column(0)
        self.local_video_icon_view.set_text_column(1)
        for idx, video in enumerate(self.local_video_list):
            icon_theme = Gtk.IconTheme().get_default()
            pixbuf = icon_theme.load_icon("video-x-generic", 96, 0)
            list_store.append([pixbuf, os.path.basename(video)])
            thread = threading.Thread(target=get_thumbnail_gnome, args=(video, list_store, idx))
            thread.daemon = True
            thread.start()


def main():
    app = GUI()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
