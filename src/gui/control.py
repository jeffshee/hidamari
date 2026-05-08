import json
import sys
import logging
import threading
import requests
import multiprocessing as mp
import setproctitle

# TODO: Port to Gtk4/adwaita someday...
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GdkPixbuf, Gdk

from pydbus import SessionBus
import yt_dlp

try:
    import os

    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    from commons import *
    from monitor import *
    from gui.gui_utils import get_thumbnail, get_thumbnail_pixbuf, get_video_duration, debounce
    from utils import (
        ConfigUtil,
        build_playlist_media_info,
        get_video_paths,
        is_gnome,
        is_wayland,
        normalize_playlist_media_info,
        setup_autostart,
    )
except ModuleNotFoundError:
    from hidamari.monitor import *
    from hidamari.commons import *
    from hidamari.gui.gui_utils import get_thumbnail, get_thumbnail_pixbuf, get_video_duration, debounce
    from hidamari.utils import (
        build_playlist_media_info,
        ConfigUtil,
        get_video_paths,
        setup_autostart,
        is_gnome,
        is_wayland,
        normalize_playlist_media_info,
    )

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(LOGGER_NAME)

APP_ID = f"{PROJECT}.gui"
APP_TITLE = "Hidamari"
APP_UI_RESOURCE_PATH = "/io/jeffshee/Hidamari/control.ui"
PLAYLIST_WARNING_COLOR = "#c97a00"
PLAYLIST_COL_PIXBUF = 0
PLAYLIST_COL_INDEX = 1
PLAYLIST_COL_NAME = 2
PLAYLIST_COL_DURATION = 3
PLAYLIST_COL_FOREGROUND = 4
PLAYLIST_COL_TOOLTIP = 5
PLAYLIST_COL_PATH = 6


class ControlPanel(Gtk.Application):
    def __init__(self, version, *args, **kwargs):
        super(ControlPanel, self).__init__(
            *args,
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
            **kwargs,
        )
        setproctitle.setproctitle(mp.current_process().name)
        # Builder init
        self.builder = Gtk.Builder()
        self.builder.set_application(self)
        try:
            self.builder.add_from_resource(APP_UI_RESOURCE_PATH)
        except GLib.Error:
            self.builder.add_from_file(os.path.abspath("./assets/control.ui"))
        # Handlers declared in `control.ui``
        signals = {
            "on_volume_changed": self.on_volume_changed,
            "on_streaming_activate": self.on_streaming_activate,
            "on_web_page_activate": self.on_web_page_activate,
            "on_blur_radius_changed": self.on_blur_radius_changed,
        }
        self.builder.connect_signals(signals)

        # Variables init
        self.version = version
        self.window = None
        self.server = None
        self.icon_view = None
        self.video_paths = None
        self.all_key = "all"

        self.is_autostart = os.path.isfile(AUTOSTART_DESKTOP_PATH)
        self._playlist_paths = []
        self.playlist_store = None

        self._connect_server()
        self._load_config()

        self._playlist_paths = list(self.config.get(CONFIG_KEY_PLAYLIST, []))
        self._playlist_media_info = dict(self.config.get(CONFIG_KEY_PLAYLIST_MEDIA_INFO, {}))

        # initialize monitors
        self.monitors = Monitors()
        # get video paths
        video_paths = self.config[CONFIG_KEY_DATA_SOURCE]
        for monitor in self.monitors.get_monitors():
            # check if monitor exists in paths
            if monitor in video_paths:
                self.monitors.get_monitor(monitor).set_wallpaper(video_paths[monitor])
            else:
                self.monitors.get_monitor(monitor).set_wallpaper(video_paths['Default'])

        self._setup_context_menu() # setup context menu for selecting monitors

    def _connect_server(self):
        try:
            self.server = SessionBus().get(DBUS_NAME_SERVER)
        except GLib.Error:
            logger.error("[GUI] Couldn't connect to server")
    
    def _setup_context_menu(self):
        self.contextMenu_monitors = Gtk.Menu()
        self.contextMenu_monitors.show_all()
        
        for monitor_name,monitor in self.monitors.get_monitors().items():
            item = Gtk.MenuItem(label=f"Set For {monitor_name}")
            item.connect("activate", self.on_set_as, monitor)
            self.contextMenu_monitors.append(item)

        item = Gtk.MenuItem(label=f"Set For All")
        item.connect("activate", self.on_set_as, self.all_key)
        self.contextMenu_monitors.append(item)

        separator = Gtk.SeparatorMenuItem()
        self.contextMenu_monitors.append(separator)

        item_playlist = Gtk.MenuItem(label="Add to Playlist")
        item_playlist.connect("activate", self.on_add_to_playlist_context)
        self.contextMenu_monitors.append(item_playlist)

    def _load_config(self):
        self.config = ConfigUtil().load()
        self._playlist_media_info = dict(self.config.get(CONFIG_KEY_PLAYLIST_MEDIA_INFO, {}))

    def _save_config(self):
        ConfigUtil().save(self.config)

    @debounce(1)
    def _save_config_delay(self):
        self._save_config()

    def _get_playlist_media_info(self, video_path):
        return normalize_playlist_media_info(self._playlist_media_info.get(video_path, {}))

    def _set_playlist_media_info(self, video_path, media_info):
        normalized = normalize_playlist_media_info(media_info)
        if self._playlist_media_info.get(video_path) == normalized:
            return False
        self._playlist_media_info[video_path] = normalized
        self.config[CONFIG_KEY_PLAYLIST_MEDIA_INFO] = dict(self._playlist_media_info)
        return True

    def _prune_playlist_media_info(self):
        kept_paths = set(self._playlist_paths)
        pruned = {
            path: info for path, info in self._playlist_media_info.items()
            if path in kept_paths
        }
        if pruned == self._playlist_media_info:
            return False
        self._playlist_media_info = pruned
        self.config[CONFIG_KEY_PLAYLIST_MEDIA_INFO] = dict(self._playlist_media_info)
        return True

    def _build_playlist_display_markup(self, video_path):
        name = GLib.markup_escape_text(os.path.basename(video_path))
        media_info = self._get_playlist_media_info(video_path)
        if media_info.get("is_problematic"):
            return f"{name} <b>[AV1 / CPU]</b>"
        return name

    def _get_playlist_row_color(self, video_path):
        media_info = self._get_playlist_media_info(video_path)
        if media_info.get("is_problematic"):
            return PLAYLIST_WARNING_COLOR
        return ""

    def _get_playlist_warning_text(self, video_path):
        return self._get_playlist_media_info(video_path).get("warning_text") or ""

    def _find_playlist_iter(self, video_path):
        if self.playlist_store is None:
            return None
        tree_iter = self.playlist_store.get_iter_first()
        while tree_iter is not None:
            if self.playlist_store[tree_iter][PLAYLIST_COL_PATH] == video_path:
                return tree_iter
            tree_iter = self.playlist_store.iter_next(tree_iter)
        return None

    def _refresh_playlist_row(self, tree_iter, video_path):
        self.playlist_store[tree_iter][PLAYLIST_COL_NAME] = self._build_playlist_display_markup(video_path)
        self.playlist_store[tree_iter][PLAYLIST_COL_FOREGROUND] = self._get_playlist_row_color(video_path)
        self.playlist_store[tree_iter][PLAYLIST_COL_TOOLTIP] = self._get_playlist_warning_text(video_path)
        self.playlist_store[tree_iter][PLAYLIST_COL_PATH] = video_path

    def _append_playlist_row(self, video_path, duration="--:--"):
        generic_icon = Gtk.IconTheme.get_default().load_icon("video-x-generic", 48, 0)
        row = self.playlist_store.append([
            generic_icon,
            str(len(self.playlist_store) + 1),
            "",
            duration,
            "",
            "",
            video_path,
        ])
        self._refresh_playlist_row(row, video_path)
        return row

    def _queue_playlist_metadata_load(self, video_path):
        thread = threading.Thread(
            target=self._load_playlist_metadata, args=(video_path,), daemon=True)
        thread.start()

    def _apply_playlist_metadata(self, video_path, pixbuf, duration, media_info):
        tree_iter = self._find_playlist_iter(video_path)
        if tree_iter is None:
            return False
        if pixbuf is not None:
            self.playlist_store[tree_iter][PLAYLIST_COL_PIXBUF] = pixbuf
        if duration:
            self.playlist_store[tree_iter][PLAYLIST_COL_DURATION] = duration
        if self._set_playlist_media_info(video_path, media_info):
            self._save_config_delay()
        self._refresh_playlist_row(tree_iter, video_path)
        return False

    def do_startup(self):
        Gtk.Application.do_startup(self)

        actions = [
            (
                "local_video_dir",
                lambda *_: subprocess.run(
                    ["xdg-open", os.path.realpath(VIDEO_WALLPAPER_DIR)]
                ),
            ),
            ("local_video_refresh", self._reload_icon_view),
            ("local_video_apply", self.on_local_video_apply),
            ("local_web_page_apply", self.on_local_web_page_apply),
            ("play_pause", self.on_play_pause),
            ("feeling_lucky", self.on_feeling_lucky),
            (
                "config",
                lambda *_: subprocess.run(["xdg-open", os.path.realpath(CONFIG_PATH)]),
            ),
            ("about", self.on_about),
            ("quit", self.on_quit),
            ("add_all_to_playlist", self.on_add_all_to_playlist),
            ("playlist_clear", self.on_playlist_clear),
            ("playlist_remove", self.on_playlist_remove),
            ("playlist_move_up", self.on_playlist_move_up),
            ("playlist_move_down", self.on_playlist_move_down),
            ("playlist_apply", self.on_playlist_apply),
        ]

        for action_name, handler in actions:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", handler)
            self.add_action(action)

        statefuls = [
            ("mute", self.config[CONFIG_KEY_MUTE], self.on_mute),
            ("autostart", self.is_autostart, self.on_autostart),
            (
                "static_wallpaper",
                self.config[CONFIG_KEY_STATIC_WALLPAPER],
                self.on_static_wallpaper,
            ),
            (
                "pause_when_maximized",
                self.config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED],
                self.on_pause_when_maximized,
            ),
            (
                "mute_when_maximized",
                self.config[CONFIG_KEY_MUTE_WHEN_MAXIMIZED],
                self.on_mute_when_maximized,
            ),
        ]

        for action_name, state, handler in statefuls:
            action = Gio.SimpleAction.new_stateful(
                action_name, None, GLib.Variant.new_boolean(state)
            )
            action.connect("change-state", handler)
            self.add_action(action)

        if is_wayland():
            self.builder.get_object("TogglePauseWhenMaximized").set_visible(False)
            self.builder.get_object("ToggleMuteWhenMaximized").set_visible(False)

        if not is_gnome():
            # Disable static wallpaper functionality for non-GNOME DE
            self.builder.get_object("ToggleStaticWallpaper").set_visible(False)
            self.builder.get_object("LabelBlurRadius").set_visible(False)
            self.builder.get_object("SpinBlurRadius").set_visible(False)

        self._reload_all_widgets()

    def do_activate(self):
        if self.window is None:
            self.window: Gtk.ApplicationWindow = self.builder.get_object(
                "ApplicationWindow"
            )
            self.window.set_title("Hidamari")
            self.window.set_application(self)
            self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.present()

        mode = self.config.get(CONFIG_KEY_MODE, MODE_NULL)
        stack = self.builder.get_object("stack1")
        mode_to_tab = {
            MODE_VIDEO: "video",
            MODE_PLAYLIST: "playlist",
            MODE_STREAM: "stream",
            MODE_WEBPAGE: "webpage",
        }
        tab_name = mode_to_tab.get(mode)
        if stack and tab_name:
            stack.set_visible_child_name(tab_name)

        if self.server is None:
            self._show_error("Couldn't connect to server")

        if self.config[CONFIG_KEY_FIRST_TIME]:
            self._show_welcome()
            self.config[CONFIG_KEY_FIRST_TIME] = False
            self._save_config()

    def _show_welcome(self):
        # Welcome dialog
        dialog = Gtk.MessageDialog(
            parent=self.window,
            modal=True,
            destroy_with_parent=True,
            text="Welcome to Hidamari 🤗",
            message_type=Gtk.MessageType.INFO,
            #    secondary_text="You can bring up the Menu by <b>Right click</b> on the desktop",
            secondary_text="Quickstart for adding local videos:\n ・Click the folder icon to open the Hidamari folder\n ・Put your videos there\n ・Click the refresh button",
            secondary_use_markup=True,
            buttons=Gtk.ButtonsType.OK,
        )
        dialog.run()
        dialog.destroy()

    def _show_error(self, error):
        dialog = Gtk.MessageDialog(
            parent=self.window,
            modal=True,
            destroy_with_parent=True,
            text="Oops!",
            message_type=Gtk.MessageType.ERROR,
            secondary_text=error,
            buttons=Gtk.ButtonsType.OK,
        )
        dialog.run()
        dialog.destroy()

    def on_local_video_apply(self, *_):
        selected = self.icon_view.get_selected_items()
        if len(selected) != 0:
            # show menu
            self.contextMenu_monitors.show_all()
            self.contextMenu_monitors.popup(None, None, None, None, 0, Gtk.get_current_event_time())
        else:
            dialog = Gtk.MessageDialog(
                parent=self.window,
                modal=True,
                destroy_with_parent=True,
                text="No Video Selected",
                message_type=Gtk.MessageType.INFO,
                secondary_text="There are no video selected.\nPlease choose one first.",
                secondary_use_markup=True,
                buttons=Gtk.ButtonsType.OK,
            )
            dialog.run()
            dialog.destroy()

    def on_set_as(self, widget, monitor):
        index = self.icon_view.get_selected_items()[0].get_indices()[0]
        video_path = self.video_paths[index]
        logger.info(f"[GUI] Local Video Set To {video_path} For Monitor {monitor}")
        self.config[CONFIG_KEY_MODE] = MODE_VIDEO
        paths = self.config[CONFIG_KEY_DATA_SOURCE] if not None else []
        # all option
        if monitor == self.all_key:
            for name,monitor in self.monitors.get_monitors().items():
                paths[name] = video_path
                monitor.set_wallpaper(video_path)
        else:
            paths[monitor.name] = video_path
            self.monitors.get_monitor(monitor.name).set_wallpaper(video_path)

        # also update the Default video
        paths['Default'] = video_path
        self.config[CONFIG_KEY_DATA_SOURCE] = paths
        self._save_config()
        print(video_path, monitor.name)
        if self.server is not None:
            self.server.video(video_path, monitor.name)
        self.set_audio_controls_for_mode()

    def on_local_web_page_apply(self, *_):
        file_chooser: Gtk.FileChooserButton = self.builder.get_object("FileChooser")
        choose: Gio.File = file_chooser.get_file()
        if choose is None:
            self._show_error("Please choose a HTML file")
            return
        file_path = choose.get_path()
        logger.info(f"[GUI] Local Webpage: {file_path}")
        self.config[CONFIG_KEY_MODE] = MODE_WEBPAGE
        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = file_path #! we dont want to break the config, webpage and stream modes will kept in Default source
        self._save_config()
        if self.server is not None:
            self.server.webpage(choose.get_path())
        self.set_audio_controls_for_mode()

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

    def _is_audio_disabled_mode(self) -> bool:
        """Modes where the player does not access the audio subsystem (e.g. playlist)."""
        return self.config.get(CONFIG_KEY_MODE) == MODE_PLAYLIST

    def set_mute_toggle_icon(self):
        toggle_icon: Gtk.Image = self.builder.get_object("ToggleMuteIcon")
        volume, is_mute = self.config[CONFIG_KEY_VOLUME], self.config[CONFIG_KEY_MUTE]
        if self._is_audio_disabled_mode() or volume == 0 or is_mute:
            icon_name = "audio-volume-muted-symbolic"
        elif volume < 30:
            icon_name = "audio-volume-low-symbolic"
        elif volume < 60:
            icon_name = "audio-volume-medium-symbolic"
        else:
            icon_name = "audio-volume-high-symbolic"
        toggle_icon.set_from_icon_name(icon_name=icon_name, size=0)

    def set_scale_volume_sensitive(self):
        scale = self.builder.get_object("ScaleVolume")
        if self._is_audio_disabled_mode() or self.config[CONFIG_KEY_MUTE]:
            scale.set_sensitive(False)
        else:
            scale.set_sensitive(True)

    def set_audio_controls_for_mode(self):
        """Reflect the current mode in the audio controls (volume + mute).

        In playlist mode the libVLC Instance is created without aout
        (--no-audio --aout=none), so changing volume/mute has no audible
        effect - we disable the controls AND the underlying Gio actions to
        keep the hamburger menu / keyboard accelerators consistent with
        the greyed-out widgets.
        """
        audio_disabled = self._is_audio_disabled_mode()
        scale = self.builder.get_object("ScaleVolume")
        toggle_mute = self.builder.get_object("ToggleMute")
        tooltip = "Audio is disabled in playlist mode" if audio_disabled else None
        if scale is not None:
            scale.set_tooltip_text(tooltip)
        if toggle_mute is not None:
            toggle_mute.set_sensitive(not audio_disabled)
            toggle_mute.set_tooltip_text(tooltip)
        # Disable the Gio.SimpleAction itself so any trigger (popover menu
        # items via app.mute, keyboard accelerators, programmatic
        # app.activate_action) is blocked - not just clicks on the widget.
        mute_action = self.lookup_action("mute")
        if mute_action is not None:
            mute_action.set_enabled(not audio_disabled)
        self.set_scale_volume_sensitive()
        self.set_mute_toggle_icon()

    def set_spin_blur_radius_sensitive(self):
        spin = self.builder.get_object("SpinBlurRadius")
        if self.config[CONFIG_KEY_STATIC_WALLPAPER]:
            spin.set_sensitive(True)
        else:
            spin.set_sensitive(False)

    def on_volume_changed(self, adjustment):
        self.config[CONFIG_KEY_VOLUME] = int(adjustment.get_value())
        logger.info(f"[GUI] Volume: {self.config[CONFIG_KEY_VOLUME]}")
        self._save_config_delay()
        if self.server is not None:
            self.server.volume = self.config[CONFIG_KEY_VOLUME]
        self.set_mute_toggle_icon()

    def on_blur_radius_changed(self, adjustment):
        self.config[CONFIG_KEY_BLUR_RADIUS] = int(adjustment.get_value())
        logger.info(f"[GUI] Blur radius: {self.config[CONFIG_KEY_BLUR_RADIUS]}")
        self._save_config_delay()
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

    def on_pause_when_maximized(self, action, state):
        action.set_state(state)
        self.config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED] = bool(state)
        logger.info(f"[GUI] {action.get_name()}: {state}")
        self._save_config()
        if self.server is not None:
            self.server.is_pause_when_maximized = self.config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED]

    def on_mute_when_maximized(self, action, state):
        action.set_state(state)
        self.config[CONFIG_KEY_MUTE_WHEN_MAXIMIZED] = bool(state)
        logger.info(f"[GUI] {action.get_name()}: {state}")
        self._save_config()
        if self.server is not None:
            self.server.is_mute_when_maximized = self.config[CONFIG_KEY_MUTE_WHEN_MAXIMIZED]

    def on_about(self, *_):
        try:
            self.builder.add_from_resource(APP_UI_RESOURCE_PATH)
        except GLib.Error:
            self.builder.add_from_file(os.path.abspath("./assets/control.ui"))
        about_dialog: Gtk.AboutDialog = self.builder.get_object("AboutDialog")
        about_dialog.set_transient_for(self.window)
        about_dialog.set_version(self.version)
        about_dialog.set_modal(True)
        about_dialog.present()

    def _check_url(self, url):
        # Check if the url is valid
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            logger.error(f"[GUI] Failed to access {url}. Error:\n{e}")
            self._show_error(f"Failed to access {url}. Error:\n{e}")
            return False
        if response.status_code >= 400:
            logger.error(
                f"[GUI] Failed to access {url}. Error code: {response.status_code}"
            )
            self._show_error(
                f"Failed to access {url}. Error code: {response.status_code}"
            )
            return False
        return True

    def _check_yt_dlp(self, raw_url):
        # Check if the url is valid (yt_dlp)
        try:
            with yt_dlp.YoutubeDL({"noplaylist": True}) as ydl:
                ydl.extract_info(raw_url, download=False)
        except yt_dlp.utils.DownloadError as e:
            s = " ".join(str(e).split(" ")[1:])
            logger.error(f"[GUI] Failed to stream {raw_url}. Error:\n{s}")
            self._show_error(f"Failed to stream {raw_url}. Error:\n{s}")
            return False
        return True

    def on_streaming_activate(self, entry: Gtk.Entry, *_):
        url = entry.get_text()
        if not self._check_yt_dlp(url):
            return
        logger.info(f"[GUI] Streaming: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_STREAM
        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = url #! we dont want to break the config, webpage and stream modes will kept in Default source
        self._save_config()
        if self.server is not None:
            self.server.stream(url)
        self.set_audio_controls_for_mode()

    def on_web_page_activate(self, entry: Gtk.Entry, *_):
        url = entry.get_text()
        if not self._check_url(url):
            return
        logger.info(f"[GUI] Webpage: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_WEBPAGE
        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = url #! we dont want to break the config, webpage and stream modes will kept in Default source
        self._save_config()
        if self.server is not None:
            self.server.webpage(url)
        self.set_audio_controls_for_mode()
    
    def on_icon_view_button_press(self, widget, event):
        if event.button == Gdk.BUTTON_SECONDARY:  # Right click
            path_info = widget.get_path_at_pos(event.x, event.y)
            if path_info is not None:
                tree_path = Gtk.TreePath(path_info[0])
                self.icon_view.grab_focus()  
                widget.select_path(tree_path)
                self.contextMenu_monitors.show_all()
                self.contextMenu_monitors.popup(None, None, None, None, 0, Gtk.get_current_event_time())
                return True 
        return False

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
        self._setup_playlist_tab()
        self.set_audio_controls_for_mode()
        self.set_spin_blur_radius_sensitive()
        toggle_mute: Gtk.ToggleButton = self.builder.get_object("ToggleMute")
        toggle_mute.set_state = self.config[CONFIG_KEY_MUTE]

        scale_volume: Gtk.Scale = self.builder.get_object("ScaleVolume")
        adjustment_volume: Gtk.Adjustment = self.builder.get_object("AdjustmentVolume")
        # Temporary block signal
        adjustment_volume.handler_block_by_func(self.on_volume_changed)
        scale_volume.set_value(self.config[CONFIG_KEY_VOLUME])
        adjustment_volume.handler_unblock_by_func(self.on_volume_changed)

        spin_blur_radius: Gtk.Scale = self.builder.get_object("SpinBlurRadius")
        adjustment_blur: Gtk.Adjustment = self.builder.get_object("AdjustmentBlur")
        # Temporary block signal
        adjustment_blur.handler_block_by_func(self.on_blur_radius_changed)
        spin_blur_radius.set_value(self.config[CONFIG_KEY_BLUR_RADIUS])
        adjustment_blur.handler_unblock_by_func(self.on_blur_radius_changed)

        toggle_mute: Gtk.ToggleButton = self.builder.get_object("ToggleAutostart")
        toggle_mute.set_state = self.is_autostart

    def _setup_playlist_tab(self):
        tree_view: Gtk.TreeView = self.builder.get_object("PlaylistTreeView")

        if not tree_view.get_model():
            self._ensure_playlist_store()
            tree_view.set_model(self.playlist_store)
            tree_view.set_tooltip_column(PLAYLIST_COL_TOOLTIP)

            renderer_thumb = Gtk.CellRendererPixbuf()
            col_thumb = Gtk.TreeViewColumn("", renderer_thumb, pixbuf=PLAYLIST_COL_PIXBUF)
            col_thumb.set_min_width(56)
            tree_view.append_column(col_thumb)

            renderer_index = Gtk.CellRendererText()
            col_index = Gtk.TreeViewColumn("#", renderer_index, text=PLAYLIST_COL_INDEX, foreground=PLAYLIST_COL_FOREGROUND)
            col_index.set_min_width(40)
            tree_view.append_column(col_index)

            renderer_name = Gtk.CellRendererText()
            col_name = Gtk.TreeViewColumn("Video", renderer_name, markup=PLAYLIST_COL_NAME, foreground=PLAYLIST_COL_FOREGROUND)
            col_name.set_expand(True)
            tree_view.append_column(col_name)

            renderer_duration = Gtk.CellRendererText()
            col_duration = Gtk.TreeViewColumn("Duration", renderer_duration, text=PLAYLIST_COL_DURATION, foreground=PLAYLIST_COL_FOREGROUND)
            col_duration.set_min_width(70)
            tree_view.append_column(col_duration)

        spin_repeat: Gtk.SpinButton = self.builder.get_object("SpinPlaylistRepeatCount")
        spin_repeat.set_value(self.config.get(CONFIG_KEY_PLAYLIST_REPEAT_COUNT, 1))

    def _ensure_playlist_store(self):
        if self.playlist_store is None:
            self.playlist_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str, str, str, str)
            for vp in self._playlist_paths:
                self._append_playlist_row(vp)
                self._queue_playlist_metadata_load(vp)

    def _load_playlist_metadata(self, video_path):
        pixbuf = get_thumbnail_pixbuf(video_path, size=48)
        duration = get_video_duration(video_path)
        media_info = build_playlist_media_info(video_path)
        GLib.idle_add(self._apply_playlist_metadata, video_path, pixbuf, duration, media_info)

    def on_add_to_playlist_context(self, *_):
        selected = self.icon_view.get_selected_items()
        if not selected:
            return
        index = selected[0].get_indices()[0]
        video_path = self.video_paths[index]

        if video_path in self._playlist_paths:
            logger.info(f"[GUI] Video already in playlist: {video_path}")
            return

        self._ensure_playlist_store()
        self._playlist_paths.append(video_path)
        self._append_playlist_row(video_path)
        self._queue_playlist_metadata_load(video_path)
        self._set_playlist_pending(True)
        logger.info(f"[GUI] Added to playlist: {video_path}")

    def on_add_all_to_playlist(self, *_):
        if not self.video_paths:
            return
        self._ensure_playlist_store()
        added = 0
        for video_path in self.video_paths:
            if video_path not in self._playlist_paths:
                self._playlist_paths.append(video_path)
                self._append_playlist_row(video_path)
                self._queue_playlist_metadata_load(video_path)
                added += 1
        if added > 0:
            self._set_playlist_pending(True)
        logger.info(f"[GUI] Added {added} videos to playlist")

    def _playlist_renumber(self):
        for i, row in enumerate(self.playlist_store):
            row[1] = str(i + 1)

    def _set_playlist_pending(self, pending):
        label = self.builder.get_object("LabelPlaylistPending")
        if label:
            label.set_visible(pending)

    def on_playlist_clear(self, *_):
        if self.playlist_store is not None:
            self.playlist_store.clear()
        self._playlist_paths.clear()
        self._playlist_media_info.clear()
        self.config[CONFIG_KEY_PLAYLIST_MEDIA_INFO] = {}
        self._set_playlist_pending(True)

    def on_playlist_remove(self, *_):
        tree_view: Gtk.TreeView = self.builder.get_object("PlaylistTreeView")
        selection = tree_view.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is not None:
            path = model.get_path(tree_iter)
            index = path.get_indices()[0]
            model.remove(tree_iter)
            del self._playlist_paths[index]
            self._playlist_renumber()
            self._set_playlist_pending(True)

    def on_playlist_move_up(self, *_):
        tree_view: Gtk.TreeView = self.builder.get_object("PlaylistTreeView")
        selection = tree_view.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is not None:
            path = model.get_path(tree_iter)
            index = path.get_indices()[0]
            if index > 0:
                prev_iter = model.get_iter(Gtk.TreePath(index - 1))
                model.swap(tree_iter, prev_iter)
                self._playlist_paths[index], self._playlist_paths[index - 1] = \
                    self._playlist_paths[index - 1], self._playlist_paths[index]
                self._playlist_renumber()
                self._set_playlist_pending(True)

    def on_playlist_move_down(self, *_):
        tree_view: Gtk.TreeView = self.builder.get_object("PlaylistTreeView")
        selection = tree_view.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is not None:
            path = model.get_path(tree_iter)
            index = path.get_indices()[0]
            if index < len(model) - 1:
                next_iter = model.get_iter(Gtk.TreePath(index + 1))
                model.swap(tree_iter, next_iter)
                self._playlist_paths[index], self._playlist_paths[index + 1] = \
                    self._playlist_paths[index + 1], self._playlist_paths[index]
                self._playlist_renumber()
                self._set_playlist_pending(True)

    def on_playlist_apply(self, *_):
        if not self._playlist_paths:
            self._show_error("Playlist is empty.\nPlease add videos first.")
            return

        spin_repeat: Gtk.SpinButton = self.builder.get_object("SpinPlaylistRepeatCount")
        repeat_count = int(spin_repeat.get_value())

        self.config[CONFIG_KEY_PLAYLIST] = list(self._playlist_paths)
        self.config[CONFIG_KEY_PLAYLIST_REPEAT_COUNT] = repeat_count
        self.config[CONFIG_KEY_MODE] = MODE_PLAYLIST
        self._prune_playlist_media_info()
        self.config[CONFIG_KEY_PLAYLIST_MEDIA_INFO] = dict(self._playlist_media_info)
        self._save_config()
        self._set_playlist_pending(False)

        logger.info(f"[GUI] Playlist applied: {len(self._playlist_paths)} videos, repeat={repeat_count}")

        if self.server is not None:
            playlist_json = json.dumps(self._playlist_paths)
            self.server.playlist(playlist_json, repeat_count)
        self.set_audio_controls_for_mode()

    def _reload_icon_view(self, *_):
        self.video_paths = get_video_paths()
        list_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        self.icon_view: Gtk.IconView = self.builder.get_object("IconView")
        self.icon_view.set_pixbuf_column(0)
        self.icon_view.set_text_column(1)
        self.icon_view.set_model(list_store)
        self.icon_view.connect("button-press-event", self.on_icon_view_button_press)
        for idx, video_path in enumerate(self.video_paths):
            pixbuf = Gtk.IconTheme().get_default().load_icon("video-x-generic", 96, 0)
            list_store.append([pixbuf, os.path.basename(video_path)])
            thread = threading.Thread(
                target=self._load_icon_view_item, args=(video_path, list_store, idx)
            )
            thread.daemon = True
            thread.start()

    def _load_icon_view_item(self, video_path, list_store, idx):
        get_thumbnail(video_path, list_store, idx)
        duration = get_video_duration(video_path)
        name = os.path.basename(video_path)
        GLib.idle_add(self._update_icon_view_text, list_store, idx, f"{name}\n{duration}")

    def _update_icon_view_text(self, list_store, idx, text):
        try:
            list_store[idx][1] = text
        except (IndexError, ValueError):
            pass
        return False


def main(
    version="devel", pkgdatadir="/app/share/hidamari", localedir="/app/share/locale"
):
    try:
        resource = Gio.Resource.load(os.path.join(pkgdatadir, "hidamari.gresource"))
        resource._register()
        icon_theme = Gtk.IconTheme.get_default()
        icon_theme.add_resource_path("/io/jeffshee/Hidamari/icons")
    except GLib.Error:
        logger.error("[GUI] Couldn't load resource")

    app = ControlPanel(version)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
