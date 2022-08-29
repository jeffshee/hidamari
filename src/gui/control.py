import sys
import logging
import threading

# TODO port to Gtk4
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GdkPixbuf

from pydbus import SessionBus

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], '..'))
    from commons import *
    from gui.gui_utils import get_video_paths, get_thumbnail
    from utils import ConfigUtil, setup_autostart, is_wayland
except ModuleNotFoundError:
    from hidamari.commons import *
    from hidamari.gui.gui_utils import get_video_paths, get_thumbnail
    from hidamari.utils import ConfigUtil, setup_autostart, is_wayland

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(LOGGER_NAME)

APP_ID = f"{PROJECT}.gui"
APP_TITLE = "Hidamari"
APP_UI_PATH = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "control.ui")


class ControlPanel(Gtk.Application):
    def __init__(self, version, *args, **kwargs):
        super(ControlPanel, self).__init__(
            *args,
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
            **kwargs
        )

        # Builder init
        self.builder = Gtk.Builder()
        self.builder.set_application(self)
        self.builder.add_from_file(APP_UI_PATH)
        # Handlers declared in `control.ui``
        signals = {"on_volume_changed": self.on_volume_changed,
                   "on_streaming_activate": self.on_streaming_activate,
                   "on_streaming_refresh": self.on_streaming_refresh,
                   "on_web_page_activate": self.on_web_page_activate,
                   "on_web_page_refresh": self._reload_icon_view,
                   "on_blur_radius_changed": self.on_blur_radius_changed}
        self.builder.connect_signals(signals)

        # Variables init
        self.version = version
        self.window = None
        self.server = None
        self.icon_view = None
        self.video_paths = None

        self.is_autostart = os.path.isfile(AUTOSTART_DESKTOP_PATH)

        self._connect_server()
        self._load_config()

    def _connect_server(self):
        try:
            self.server = SessionBus().get(DBUS_NAME_SERVER)
        except GLib.Error:
            logger.error("[GUI] Couldn't connect to server")

    def _load_config(self):
        self.config = ConfigUtil().load()

    def _save_config(self):
        ConfigUtil().save(self.config)

    def do_startup(self):
        Gtk.Application.do_startup(self)

        actions = [
            ("local_video_dir", lambda *_: subprocess.run(
                ["xdg-open", os.path.realpath(VIDEO_WALLPAPER_DIR)])),
            ("local_video_refresh", self._reload_icon_view),
            ("local_video_apply", self.on_local_video_apply),
            ("local_web_page_apply", self.on_local_web_page_apply),
            ("play_pause", self.on_play_pause),
            ("feeling_lucky", self.on_feeling_lucky),
            ("about", self.on_about),
            ("quit", self.on_quit),
        ]

        for action_name, handler in actions:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", handler)
            self.add_action(action)

        statefuls = [
            ("mute", self.config[CONFIG_KEY_MUTE], self.on_mute),
            ("autostart", self.is_autostart, self.on_autostart),
            ("static_wallpaper", self.config[CONFIG_KEY_STATIC_WALLPAPER],
             self.on_static_wallpaper),
            ("detect_maximized", self.config[CONFIG_KEY_DETECT_MAXIMIZED],
             self.on_detect_maximized)
        ]

        for action_name, state, handler in statefuls:
            action = Gio.SimpleAction.new_stateful(
                action_name, None, GLib.Variant.new_boolean(state))
            action.connect("change-state", handler)
            self.add_action(action)

        if is_wayland():
            toggle = self.builder.get_object("ToggleDetectMaximized")
            toggle.set_visible(False)
            
        self._reload_all_widgets()

    def do_activate(self):
        if self.window is None:
            self.window: Gtk.ApplicationWindow = self.builder.get_object(
                "ApplicationWindow")
            self.window.set_title("Hidamari")
            self.window.set_application(self)
            self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.present()

        if self.server is None:
            self._show_dbus_error()

        if self.config[CONFIG_KEY_FIRST_TIME]:
            self._show_welcome()
            self.config[CONFIG_KEY_FIRST_TIME] = False
            self._save_config()

    def _show_dbus_error(self):
        dialog = Gtk.MessageDialog(parent=self.window, modal=True, destroy_with_parent=True,
                                   text="Oops!", message_type=Gtk.MessageType.ERROR,
                                   secondary_text="Couldn't connect to server",
                                   buttons=Gtk.ButtonsType.OK)
        dialog.run()
        dialog.destroy()

    def _show_welcome(self):
        # Welcome dialog
        dialog = Gtk.MessageDialog(parent=self.window, modal=True, destroy_with_parent=True,
                                   text="Welcome to Hidamari 🤗", message_type=Gtk.MessageType.INFO,
                                   secondary_text="You can bring up the Menu by <b>Right click</b> on the desktop",
                                   secondary_use_markup=True,
                                   buttons=Gtk.ButtonsType.OK)
        dialog.run()
        dialog.destroy()

    def on_local_video_apply(self, *_):
        selected = self.icon_view.get_selected_items()
        if len(selected) != 0:
            index = selected[0].get_indices()[0]
            video_path = self.video_paths[index]
            logger.info(f"[GUI] Local Video: {video_path}")
            self.config[CONFIG_KEY_MODE] = MODE_VIDEO
            self.config[CONFIG_KEY_DATA_SOURCE] = video_path
            self._save_config()
            if self.server is not None:
                self.server.video(self.video_paths[index])

    def on_local_web_page_apply(self, *_):
        file_chooser: Gtk.FileChooserButton = self.builder.get_object(
            "FileChooser")
        choose: Gio.File = file_chooser.get_file()
        file_path = choose.get_path()
        logger.info(f"[GUI] Local Webpage: {file_path}")
        self.config[CONFIG_KEY_MODE] = MODE_WEBPAGE
        self.config[CONFIG_KEY_DATA_SOURCE] = file_path
        self._save_config()
        if self.server is not None:
            self.server.webpage(choose.get_path())

    def on_play_pause(self, *_):
        if self.server is None:
            return
        prev_state = self.server.is_paused_by_user
        self.server.is_paused_by_user = not prev_state
        if not prev_state:
            self.server.pause_playback()
        else:
            self.server.start_playback()

    def on_feeling_lucky(self, *_):
        if self.server is not None:
            self.server.feeling_lucky()

    def set_mute_toggle_icon(self):
        toggle_icon: Gtk.Image = self.builder.get_object("ToggleMuteIcon")
        volume, is_mute = self.config[CONFIG_KEY_VOLUME], self.config[CONFIG_KEY_MUTE]
        if volume == 0 or is_mute:
            icon_name = "audio-volume-muted"
        elif volume < 30:
            icon_name = "audio-volume-low"
        elif volume < 60:
            icon_name = "audio-volume-medium"
        else:
            icon_name = "audio-volume-high"
        toggle_icon.set_from_icon_name(icon_name=icon_name, size=0)

    def set_scale_volume_sensitive(self):
        scale = self.builder.get_object("ScaleVolume")
        if self.config[CONFIG_KEY_MUTE]:
            scale.set_sensitive(False)
        else:
            scale.set_sensitive(True)

    def set_spin_blur_radius_sensitive(self):
        spin = self.builder.get_object("SpinBlurRadius")
        if self.config[CONFIG_KEY_STATIC_WALLPAPER]:
            spin.set_sensitive(True)
        else:
            spin.set_sensitive(False)

    def on_volume_changed(self, adjustment):
        self.config[CONFIG_KEY_VOLUME] = int(adjustment.get_value())
        logger.info(f"[GUI] Volume: {self.config[CONFIG_KEY_VOLUME]}")
        self._save_config()
        if self.server is not None:
            self.server.volume = self.config[CONFIG_KEY_VOLUME]
        self.set_mute_toggle_icon()

    def on_blur_radius_changed(self, adjustment):
        self.config[CONFIG_KEY_BLUR_RADIUS] = int(adjustment.get_value())
        logger.info(
            f"[GUI] Blur radius: {self.config[CONFIG_KEY_BLUR_RADIUS]}")
        self._save_config()
        if self.server is not None:
            self.server.blur_radius = self.config[CONFIG_KEY_BLUR_RADIUS]

    def on_mute(self, action, state):
        action.set_state(state)
        self.config[CONFIG_KEY_MUTE] = bool(state)
        logger.info(f"[GUI] {action.get_name()}: {state}")
        self._save_config()
        if self.server is not None:
            self.server.is_mute = self.config[CONFIG_KEY_MUTE]
        self.set_mute_toggle_icon()
        self.set_scale_volume_sensitive()

    def on_autostart(self, action, state):
        action.set_state(state)
        self.is_autostart = bool(state)
        logger.info(f"[GUI] {action.get_name()}: {state}")
        setup_autostart(state)

    def on_static_wallpaper(self, action, state):
        action.set_state(state)
        self.config[CONFIG_KEY_STATIC_WALLPAPER] = bool(state)
        logger.info(f"[GUI] {action.get_name()}: {state}")
        self._save_config()
        if self.server is not None:
            self.server.is_static_wallpaper = self.config[CONFIG_KEY_STATIC_WALLPAPER]
        self.set_spin_blur_radius_sensitive()

    def on_detect_maximized(self, action, state):
        action.set_state(state)
        self.config[CONFIG_KEY_DETECT_MAXIMIZED] = bool(state)
        logger.info(f"[GUI] {action.get_name()}: {state}")
        self._save_config()
        if self.server is not None:
            self.server.is_detect_maximized = self.config[CONFIG_KEY_DETECT_MAXIMIZED]

    def on_about(self, *_):
        self.builder.add_from_file(APP_UI_PATH)
        about_dialog: Gtk.AboutDialog = self.builder.get_object("AboutDialog")
        about_dialog.set_transient_for(self.window)
        about_dialog.set_version(self.version)
        about_dialog.set_modal(True)
        about_dialog.present()

    def on_streaming_activate(self, entry: Gtk.Entry):
        url = entry.get_text()
        logger.info(f"[GUI] Streaming: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_STREAM
        self.config[CONFIG_KEY_DATA_SOURCE] = url
        self._save_config()
        if self.server is not None:
            self.server.stream(url)

    def on_streaming_refresh(self, entry: Gtk.Entry, *_):
        url = entry.get_text()
        logger.info(f"[GUI] Streaming: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_STREAM
        self.config[CONFIG_KEY_DATA_SOURCE] = url
        self._save_config()
        if self.server is not None:
            self.server.stream(url)

    def on_web_page_activate(self, entry: Gtk.Entry):
        url = entry.get_text()
        logger.info(f"[GUI] Webpage: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_WEBPAGE
        self.config[CONFIG_KEY_DATA_SOURCE] = url
        self._save_config()
        if self.server is not None:
            self.server.webpage(url)

    def on_web_page_refresh(self, entry: Gtk.Entry, *_):
        url = entry.get_text()
        logger.info(f"[GUI] Webpage: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_WEBPAGE
        self.config[CONFIG_KEY_DATA_SOURCE] = url
        self._save_config()
        if self.server is not None:
            self.server.webpage(url)

    def on_quit(self, *_):
        if self.server is not None:
            try:
                self.server.quit()
            except GLib.Error:
                # Ignore NoReply error
                pass
        self.quit()

    def _reload_all_widgets(self):
        self._reload_icon_view()
        self.set_mute_toggle_icon()
        self.set_scale_volume_sensitive()
        self.set_spin_blur_radius_sensitive()
        toggle_mute: Gtk.ToggleButton = self.builder.get_object("ToggleMute")
        toggle_mute.set_state = self.config[CONFIG_KEY_MUTE]

        scale_volume: Gtk.Scale = self.builder.get_object("ScaleVolume")
        adjustment_volume: Gtk.Adjustment = self.builder.get_object(
            "AdjustmentVolume")
        # Temporary block signal
        adjustment_volume.handler_block_by_func(self.on_volume_changed)
        scale_volume.set_value(self.config[CONFIG_KEY_VOLUME])
        adjustment_volume.handler_unblock_by_func(self.on_volume_changed)

        spin_blur_radius: Gtk.Scale = self.builder.get_object("SpinBlurRadius")
        adjustment_blur: Gtk.Adjustment = self.builder.get_object(
            "AdjustmentBlur")
        # Temporary block signal
        adjustment_blur.handler_block_by_func(self.on_blur_radius_changed)
        spin_blur_radius.set_value(self.config[CONFIG_KEY_BLUR_RADIUS])
        adjustment_blur.handler_unblock_by_func(self.on_blur_radius_changed)

        toggle_mute: Gtk.ToggleButton = self.builder.get_object(
            "ToggleAutostart")
        toggle_mute.set_state = self.is_autostart

    def _reload_icon_view(self, *_):
        self.video_paths = get_video_paths()
        list_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        self.icon_view: Gtk.IconView = self.builder.get_object("IconView")
        self.icon_view.set_pixbuf_column(0)
        self.icon_view.set_text_column(1)
        self.icon_view.set_model(list_store)
        for idx, video_path in enumerate(self.video_paths):
            pixbuf = Gtk.IconTheme().get_default().load_icon("video-x-generic", 96, 0)
            list_store.append([pixbuf, os.path.basename(video_path)])
            thread = threading.Thread(
                target=get_thumbnail, args=(video_path, list_store, idx))
            thread.daemon = True
            thread.start()


def main(version):
    app = ControlPanel(version)
    app.run(sys.argv)


if __name__ == "__main__":
    main("dev")
