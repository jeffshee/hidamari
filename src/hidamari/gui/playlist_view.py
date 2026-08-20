import copy
import sys
import threading

import gi
import pydbus
import vlc

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf, Gdk, Gio, Pango

# Custom DnD target used to drag a video from the library IconView and drop it
# onto the playlist area; distinct from IconView's own internal "GTK_TREE_MODEL_ROW"
# reorder target so it can't be confused with (or interfere with) drag-reordering.
DND_TARGET_VIDEO_INDEX = Gtk.TargetEntry.new("HIDAMARI_VIDEO_INDEX", Gtk.TargetFlags.SAME_APP, 0)

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    from gui.imports import *
    from gui.gui_utils import get_thumbnail, HoverPreview
    from utils import ConfigUtil, PlaylistUtil, get_video_paths
except ModuleNotFoundError:
    from hidamari.gui.imports import *
    from hidamari.gui.gui_utils import get_thumbnail, HoverPreview
    from hidamari.utils import ConfigUtil, PlaylistUtil, get_video_paths


class PlaylistView:
    def __init__(self, config: ConfigUtil, server):
        self.config = config
        self.server = server
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_resource(APP_UI_RESOURCE_PATH + "playlist_view.ui")
        except GLib.Error:
            self.builder.add_from_file(os.path.abspath("./src/hidamari/assets/playlist_view.ui"))

        self.widget = self.builder.get_object("PlaylistView")
        
        # get items from view
        self.monitor_combobox = self.builder.get_object("ComboBoxMonitor")
        self.videos_view = self.builder.get_object("IconViewVideos")
        self.playlist_name_entry = self.builder.get_object("EntryPlayListName")
        self.playlist_icon_view = self.builder.get_object("IconViewPlaylist")
        self.playlist_listbox = self.builder.get_object("ListBoxPlaylist")
        self.apply_button = self.builder.get_object("ButtonApply")
        self.delete_button = self.builder.get_object("ButtonDeletePlaylist")
        self.playlist_scrolled_window = self.builder.get_object("ScrolledWindowPlaylist")
        self.add_to_playlist_button = self.builder.get_object("ButtonAddToPlaylist")
        self.remove_from_playlist_button = self.builder.get_object("ButtonRemoveFromPlaylist")
        self.move_left_button = self.builder.get_object("ButtonMoveLeft")
        self.move_right_button = self.builder.get_object("ButtonMoveRight")
        self.add_or_save_button = self.builder.get_object("ButtonPlayListAdd")
        self.reload_videos_button = self.builder.get_object("ButtonReloadVideos")
        self.distribution_mode_combobox = self.builder.get_object("ComboBoxDistributionMode")

        # index 0 = PER_MONITOR, index 1 = ALL (kept in sync with DISTRIBUTION_MODES below)
        self.DISTRIBUTION_MODES = [PLAYLIST_MODE_PER_MONITOR, PLAYLIST_MODE_ALL]
        self.distribution_mode_combobox.remove_all()
        self.distribution_mode_combobox.append_text("Per Monitor")
        self.distribution_mode_combobox.append_text("All Monitors (Equal Split)")

        # initialize monitors
        self.monitors = Monitors()
        self.monitor_combobox.remove_all()
        self.playlists = None
        self.current_playlist = None
        self.current_playlist_name = None
        # Snapshot of the currently-loaded playlist as last loaded/saved, used to
        # detect unsaved edits before switching away (see _is_dirty).
        self.saved_snapshot = None

        # get video paths
        video_paths = self.config[CONFIG_KEY_DATA_SOURCE]
        for monitor in self.monitors.get_monitors():
            # check if monitor exists in paths
            if monitor in video_paths:
                self.monitors.get_monitor(monitor).set_wallpaper(video_paths[monitor])
            else:
                self.monitors.get_monitor(monitor).set_wallpaper(video_paths['Default'])
                
            # add monitor name to combo box
            self.monitor_combobox.append_text(monitor)

        # connect signals
        self.monitor_combobox.connect("changed", self.on_monitor_changed)
        self.playlist_listbox.connect("row-activated", self.on_playlist_changed)
        self.playlist_listbox.connect("button-press-event", self.on_playlist_listbox_button_press)
        self.videos_view.connect("selection-changed", self.on_video_selection_changed)
        self.apply_button.connect("clicked", self.on_playlist_apply)
        self.add_to_playlist_button.connect("clicked", self.on_add_to_playlist)
        self.remove_from_playlist_button.connect("clicked", self.on_remove_from_playlist)
        self.move_left_button.connect("clicked", self.on_move_left)
        self.move_right_button.connect("clicked", self.on_move_right)
        self.add_or_save_button.connect("clicked", self.on_add_or_save_playlist)
        self.playlist_icon_view.connect("selection-changed", self.on_video_selection_changed_in_playlist)
        self.playlist_name_entry.connect("changed", self.on_playlist_name_changed)
        self.reload_videos_button.connect("clicked", self.on_reload_icon_view)
        self.distribution_mode_combobox.connect("changed", self.on_distribution_mode_changed)
        self.delete_button.connect("clicked", self.on_delete_playlist)
        self.videos_view.connect("item-activated", self.on_video_activated)
        self.videos_view.connect("button-press-event", self.on_video_button_press)
        self.playlist_icon_view.connect("item-activated", self.on_playlist_video_activated)

        # Drag-and-drop: drag a video from the library IconView, drop it onto the
        # playlist area to add it. Targets the ScrolledWindow (not playlist_icon_view
        # itself) so it doesn't touch playlist_icon_view's own reorderable DnD setup.
        self.videos_view.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, [DND_TARGET_VIDEO_INDEX], Gdk.DragAction.COPY)
        self.videos_view.connect("drag-data-get", self.on_video_drag_data_get)
        self.playlist_scrolled_window.drag_dest_set(
            Gtk.DestDefaults.ALL, [DND_TARGET_VIDEO_INDEX], Gdk.DragAction.COPY)
        self.playlist_scrolled_window.connect("drag-data-received", self.on_playlist_drag_data_received)

        # Hover preview: muted, looping playback of a video's thumbnail on hover,
        # in both the library gallery and the playlist queue. Both share one VLC
        # instance (cheap: it just hosts two independent players).
        vlc_instance = vlc.Instance(["--no-disable-screensaver"])
        self.videos_hover_preview = HoverPreview(
            self.videos_view, vlc_instance, self._resolve_library_video_path)
        self.playlist_hover_preview = HoverPreview(
            self.playlist_icon_view, vlc_instance, self._resolve_queue_video_path)

        self._load_playlist()
        self._load_config()
        self._update_disable_status_for_buttons()
        
        # set active monitor
        self.monitor_combobox.set_active(0)

    """
        Button Callbacks
    """
    def on_reload_icon_view(self, button: Gtk.Button):
        logger.info(f"[GUI/PlaylistView] Reloading videos")
        self.reload_icon_view()

    def on_add_or_save_playlist(self, button: Gtk.Button):
        # check if playlist name empty
        playlist_name = self.playlist_name_entry.get_text()
        if not playlist_name:
            logger.warning(f"[GUI/PlaylistView] Playlist name is empty")
            button.set_sensitive(False)
            # show translateable error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self.widget.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Playlist name cannot be empty.",
            )
            dialog.format_secondary_text("Please enter a valid playlist name.")
            dialog.run()
            dialog.destroy()
            return
        
        # if all good, add/save playlist to listbox
        # deep-copied so a later "save as" under a different name can't alias (and corrupt)
        # a playlist already stored under another name
        logger.info(f"[GUI/PlaylistView] Adding/Saving playlist: {playlist_name}")
        self.playlists[playlist_name] = copy.deepcopy(self.current_playlist) if self.current_playlist else self._new_playlist_data()

        self._save_playlist(playlist_name)
        self._load_playlist(select_name=playlist_name)

    def on_add_to_playlist(self, button: Gtk.Button):
        monitor_name = self.monitor_combobox.get_active_text()
        if not self._is_all_mode() and not monitor_name:
            logger.warning(f"[GUI/PlaylistView] No monitor selected")
            return

        selected_items = self.videos_view.get_selected_items()
        if not selected_items:
            logger.warning(f"[GUI/PlaylistView] No videos selected to add")
            return

        for item in selected_items:
            video_path = self.video_paths[item.get_indices()[0]]
            self._add_video_to_active_playlist(video_path, monitor_name)

        self._update_playlist_view(monitor_name)
        self._update_disable_status_for_buttons()

    def _add_video_to_active_playlist(self, video_path: str, monitor_name: str = None):
        """
        Add a single video to whichever list is currently being edited: the shared
        'videos' list in ALL mode, or `monitor_name`'s list in PER_MONITOR mode.
        Caller is responsible for refreshing the view afterwards (so batch callers,
        e.g. multi-select add, only redraw once). Returns False if there's nowhere
        to add it (no monitor selected in PER_MONITOR mode).
        """
        if monitor_name is None:
            monitor_name = self.monitor_combobox.get_active_text()
        if not self._is_all_mode() and not monitor_name:
            logger.warning(f"[GUI/PlaylistView] No monitor selected")
            return False

        if self.current_playlist is None:
            self.current_playlist = self._new_playlist_data()

        target_list = self._get_active_list(monitor_name)
        if target_list is None:
            return False

        if video_path not in target_list:
            target_list.append(video_path)
        return True

    def on_remove_from_playlist(self, button: Gtk.Button):
        # check if any item selected on playlist_icon_view
        selected_items = self.playlist_icon_view.get_selected_items()
        if not selected_items:
            logger.warning(f"[GUI/PlaylistView] No videos selected to remove")
            button.set_sensitive(False)
            dialog = Gtk.MessageDialog(
                transient_for=self.widget.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No videos selected to remove from playlist.",
            )
            dialog.format_secondary_text("Please select videos to remove.")
            dialog.run()
            dialog.destroy()
            return

        monitor_name = self.monitor_combobox.get_active_text()
        if not self._is_all_mode() and not monitor_name:
            logger.warning(f"[GUI/PlaylistView] No monitor selected")
            return

        target_list = self._get_active_list(monitor_name)
        if target_list is None:
            logger.warning(f"[GUI/PlaylistView] No current playlist or monitor in playlist")
            return

        for item in selected_items:
            video_path = target_list[item.get_indices()[0]]
            if video_path in target_list:
                target_list.remove(video_path)

        self._update_playlist_view(monitor_name)
        self._update_disable_status_for_buttons()

    def on_move_left(self, button: Gtk.Button):
        # check if any item selected on playlist_icon_view
        selected_items = self.playlist_icon_view.get_selected_items()
        if not selected_items:
            logger.warning(f"[GUI/PlaylistView] No videos selected to move")
            button.set_sensitive(False)
            dialog = Gtk.MessageDialog(
                transient_for=self.widget.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No videos selected to move from playlist.",
            )
            dialog.format_secondary_text("Please select videos to move.")
            dialog.run()
            dialog.destroy()
            return

        monitor_name = self.monitor_combobox.get_active_text()
        if not self._is_all_mode() and not monitor_name:
            logger.warning(f"[GUI/PlaylistView] No monitor selected")
            return

        playlist = self._get_active_list(monitor_name)
        if playlist is None:
            logger.warning(f"[GUI/PlaylistView] No current playlist or monitor in playlist")
            return

        # change order of selected items
        indices = [item.get_indices()[0] for item in selected_items]
        logger.info(f"[GUI/PlaylistView] Selected indices to move left: {indices}")

        # left shift: move from the start to avoid index shifting issues
        for index in sorted(indices):
            if index > 0:
                playlist[index], playlist[index - 1] = playlist[index - 1], playlist[index]

        self._update_playlist_view(monitor_name)
        self._update_disable_status_for_buttons()

    def on_move_right(self, button: Gtk.Button):
        # check if any item selected on playlist_icon_view
        selected_items = self.playlist_icon_view.get_selected_items()
        if not selected_items:
            logger.warning(f"[GUI/PlaylistView] No videos selected to move")
            button.set_sensitive(False)
            dialog = Gtk.MessageDialog(
                transient_for=self.widget.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No videos selected to move from playlist.",
            )
            dialog.format_secondary_text("Please select videos to move.")
            dialog.run()
            dialog.destroy()
            return

        monitor_name = self.monitor_combobox.get_active_text()
        if not self._is_all_mode() and not monitor_name:
            logger.warning(f"[GUI/PlaylistView] No monitor selected")
            return

        playlist = self._get_active_list(monitor_name)
        if playlist is None:
            logger.warning(f"[GUI/PlaylistView] No current playlist or monitor in playlist")
            return

        # change order of selected items
        indices = [item.get_indices()[0] for item in selected_items]
        logger.info(f"[GUI/PlaylistView] Selected indices to move right: {indices}")

        # move from the end to avoid index shifting issues
        for index in sorted(indices, reverse=True):
            if index < len(playlist) - 1:
                playlist[index], playlist[index + 1] = playlist[index + 1], playlist[index]

        self._update_playlist_view(monitor_name)
        self._update_disable_status_for_buttons()

    def on_distribution_mode_changed(self, combo: Gtk.ComboBoxText):
        active_index = combo.get_active()
        if active_index < 0 or self.current_playlist is None:
            return
        mode = self.DISTRIBUTION_MODES[active_index]
        self.monitor_combobox.set_sensitive(mode == PLAYLIST_MODE_PER_MONITOR)
        if self.current_playlist.get(PLAYLIST_KEY_MODE) == mode:
            return
        self.current_playlist[PLAYLIST_KEY_MODE] = mode
        logger.info(f"[GUI/PlaylistView] Distribution mode changed to: {mode}")
        self._update_playlist_view(self.monitor_combobox.get_active_text())
        self._update_disable_status_for_buttons()

    def on_delete_playlist(self, button: Gtk.Button):
        selected_playlist = self.playlist_listbox.get_selected_row()
        if not selected_playlist:
            logger.warning(f"[GUI/PlaylistView] No playlist selected to delete")
            return

        self._delete_playlist(selected_playlist.playlist_name)

    def _delete_playlist(self, playlist_name: str):
        dialog = Gtk.MessageDialog(
            transient_for=self.widget.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete playlist '{playlist_name}'?",
        )
        dialog.format_secondary_text("This cannot be undone.")
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.YES:
            return

        logger.info(f"[GUI/PlaylistView] Deleting playlist: {playlist_name}")
        self.playlists.pop(playlist_name, None)
        self._save_playlist(playlist_name)
        self._load_playlist()

    def on_new_playlist(self, *_):
        if self._is_dirty() and not self._confirm_discard_changes():
            return
        logger.info(f"[GUI/PlaylistView] Starting new playlist draft")
        self.playlist_listbox.unselect_all()
        self._reset_to_new_draft()

    def on_playlist_listbox_button_press(self, listbox: Gtk.ListBox, event: Gdk.EventButton):
        row = listbox.get_row_at_y(int(event.y))
        if row is None:
            if event.button == 3:
                menu = self._build_playlist_context_menu(None)
                menu.popup_at_pointer(event)
                return True
            elif event.button == 1:
                # clicking empty space below the rows: same as "New" - clear the selection/draft
                self.on_new_playlist()
                return True
            return False
        if event.button == 3:
            menu = self._build_playlist_context_menu(row)
            menu.popup_at_pointer(event)
            return True
        return False

    def _build_playlist_context_menu(self, row):
        menu = Gtk.Menu()
        if row is None:
            new_item = Gtk.MenuItem(label="New")
            new_item.connect("activate", lambda _: self.on_new_playlist())
            menu.append(new_item)
        else:
            playlist_name = row.playlist_name

            apply_item = Gtk.MenuItem(label="Apply")
            apply_item.connect("activate", lambda _: self._apply_playlist(playlist_name))
            menu.append(apply_item)

            rename_item = Gtk.MenuItem(label="Rename")
            rename_item.connect("activate", lambda _: self._rename_playlist_via_dialog(playlist_name))
            menu.append(rename_item)

            menu.append(Gtk.SeparatorMenuItem())

            delete_item = Gtk.MenuItem(label="Delete")
            delete_item.connect("activate", lambda _: self._delete_playlist(playlist_name))
            menu.append(delete_item)
        menu.show_all()
        return menu

    def _rename_playlist_via_dialog(self, playlist_name: str):
        dialog = Gtk.MessageDialog(
            transient_for=self.widget.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Rename playlist '{playlist_name}'",
        )
        entry = Gtk.Entry()
        entry.set_text(playlist_name)
        entry.set_activates_default(True)
        dialog.get_content_area().add(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()
        new_name = entry.get_text().strip()
        dialog.destroy()

        if response != Gtk.ResponseType.OK or not new_name or new_name == playlist_name:
            return

        if new_name in self.playlists:
            error_dialog = Gtk.MessageDialog(
                transient_for=self.widget.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"A playlist named '{new_name}' already exists.",
            )
            error_dialog.run()
            error_dialog.destroy()
            return

        logger.info(f"[GUI/PlaylistView] Renaming playlist '{playlist_name}' to '{new_name}'")
        self.playlists[new_name] = self.playlists.pop(playlist_name)
        was_active_playlist = self.config.get(CONFIG_KEY_ACTIVE_PLAYLIST) == playlist_name
        self._save_playlist(None)
        if was_active_playlist:
            self.config[CONFIG_KEY_ACTIVE_PLAYLIST] = new_name
            self._save_config()
            if self.server is not None:
                self.server.playlist(new_name)  # live-reload under the new name
        self._load_playlist(select_name=new_name)

    def on_playlist_apply(self, button: Gtk.Button):
        # get playlist name
        selected_playlist = self.playlist_listbox.get_selected_row()
        if not selected_playlist:
            logger.warning(f"[GUI/PlaylistView] No playlist selected to apply")
            button.set_sensitive(False)
            dialog = Gtk.MessageDialog(
                transient_for=self.widget.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="No playlist selected to apply.",
            )
            dialog.format_secondary_text("Please select a playlist to apply.")
            dialog.run()
            dialog.destroy()
            return

        self._apply_playlist(selected_playlist.playlist_name)

    def _apply_playlist(self, playlist_name: str):
        if playlist_name not in self.playlists:
            logger.warning(f"[GUI/PlaylistView] Playlist {playlist_name} not found in playlists")
            return

        self.config[CONFIG_KEY_MODE] = MODE_PLAYLIST
        self.config[CONFIG_KEY_ACTIVE_PLAYLIST] = playlist_name
        self._save_config()
        logger.info(f"[GUI/PlaylistView] Applying playlist: {playlist_name}")
        if self.server is not None:
            self.server.playlist(playlist_name)

    """
        Other callbacks
    """
    
    def on_playlist_name_changed(self, entry: Gtk.Entry):
        self._update_disable_status_for_buttons()

    def on_playlist_changed(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow):
        playlist_name = row.playlist_name
        if playlist_name == self.current_playlist_name:
            return

        if self._is_dirty() and not self._confirm_discard_changes():
            self._reselect_current_playlist_row()
            return

        logger.info(f"[GUI/PlaylistView] Playlist changed: {playlist_name}")
        self._select_playlist(playlist_name)

    def _select_playlist(self, playlist_name: str):
        """Load `playlist_name` as the current draft. Does not check for unsaved changes."""
        self.playlist_name_entry.set_text(playlist_name)
        self.current_playlist_name = playlist_name
        # Deep-copied so live edits are a draft; nothing is persisted until Add/Save.
        stored = self.playlists.get(playlist_name)
        self.current_playlist = copy.deepcopy(stored) if stored is not None else self._new_playlist_data()
        self.saved_snapshot = copy.deepcopy(self.current_playlist)
        self._sync_distribution_mode_ui()
        self._update_disable_status_for_buttons()
        # set active monitor
        self.monitor_combobox.set_active(0)
        monitor_name = self.monitor_combobox.get_active_text()
        self._update_playlist_view(monitor_name)

    def _is_dirty(self):
        return self.current_playlist is not None and self.current_playlist != self.saved_snapshot

    def _confirm_discard_changes(self):
        dialog = Gtk.MessageDialog(
            transient_for=self.widget.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Discard unsaved changes?",
        )
        dialog.format_secondary_text(
            f"'{self.current_playlist_name or 'Untitled'}' has unsaved changes. "
            f"Switching playlists will discard them.")
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def _reselect_current_playlist_row(self):
        """Undo a listbox row click by re-selecting the row for the still-active draft."""
        index = 0
        row = self.playlist_listbox.get_row_at_index(index)
        while row is not None:
            if row.playlist_name == self.current_playlist_name:
                self.playlist_listbox.select_row(row)
                return
            index += 1
            row = self.playlist_listbox.get_row_at_index(index)

    def on_video_selection_changed(self, icon_view: Gtk.IconView):
        selected_items = []
        for item in icon_view.get_selected_items():
            selected_items.append(item.get_indices()[0])
        logger.info(f"[GUI/PlaylistView] Video selection changed: {selected_items}")
        self._update_disable_status_for_buttons()

    def on_video_selection_changed_in_playlist(self, icon_view: Gtk.IconView):
        selected_items = []
        for item in icon_view.get_selected_items():
            selected_items.append(item.get_indices()[0])
        logger.info(f"[GUI/PlaylistView] Video selection changed in playlist: {selected_items}")
        self._update_disable_status_for_buttons()

    def on_monitor_changed(self, combo: Gtk.ComboBoxText):
        active_monitor = combo.get_active_text()
        logger.info(f"[GUI/PlaylistView] Monitor changed to: {active_monitor}")
        self._update_playlist_view(active_monitor)
        
    def on_video_activated(self, icon_view: Gtk.IconView, path: Gtk.TreePath):
        # Double-click in the library list: quick-add to whatever's currently being edited.
        # (Preview/open lives in the right-click menu instead - see on_video_button_press.)
        index = path.get_indices()[0]
        if not (0 <= index < len(self.video_paths)):
            return
        video_path = self.video_paths[index]
        monitor_name = self.monitor_combobox.get_active_text()
        if self._add_video_to_active_playlist(video_path, monitor_name):
            logger.info(f"[GUI/PlaylistView] Video added via double-click: {video_path}")
            self._update_playlist_view(monitor_name)
            self._update_disable_status_for_buttons()

    def on_playlist_video_activated(self, icon_view: Gtk.IconView, path: Gtk.TreePath):
        model = icon_view.get_model()
        video_path = model[path][2]  # 3rd column holds the full video path
        self._preview_video(video_path)

    def on_video_button_press(self, icon_view: Gtk.IconView, event: Gdk.EventButton):
        if event.button != 3:
            return False
        path = icon_view.get_path_at_pos(int(event.x), int(event.y))
        if path is None:
            return False
        icon_view.unselect_all()
        icon_view.select_path(path)
        index = path.get_indices()[0]
        if not (0 <= index < len(self.video_paths)):
            return False

        menu = self._build_video_context_menu(self.video_paths[index])
        menu.popup_at_pointer(event)
        return True

    def _build_video_context_menu(self, video_path: str):
        menu = Gtk.Menu()

        if self._is_all_mode():
            add_item = Gtk.MenuItem(label="Add to Playlist")
            add_item.connect("activate", lambda _: self._add_video_via_menu(video_path, None))
            menu.append(add_item)
        else:
            for monitor_name in self.monitors.get_monitors():
                add_item = Gtk.MenuItem(label=f"Add to {monitor_name}")
                add_item.connect(
                    "activate", lambda _, m=monitor_name: self._add_video_via_menu(video_path, m))
                menu.append(add_item)

        menu.append(Gtk.SeparatorMenuItem())

        open_item = Gtk.MenuItem(label="Open Video")
        open_item.connect("activate", lambda _: self._preview_video(video_path))
        menu.append(open_item)

        show_item = Gtk.MenuItem(label="Show in Folder")
        show_item.connect("activate", lambda _: self._show_in_folder(video_path))
        menu.append(show_item)

        menu.show_all()
        return menu

    def _add_video_via_menu(self, video_path: str, monitor_name: str):
        if self._add_video_to_active_playlist(video_path, monitor_name):
            logger.info(f"[GUI/PlaylistView] Video added via context menu: {video_path}")
            if monitor_name and monitor_name != self.monitor_combobox.get_active_text():
                # switch the queue view to the monitor the video was just added to
                monitor_names = list(self.monitors.get_monitors())
                if monitor_name in monitor_names:
                    self.monitor_combobox.set_active(monitor_names.index(monitor_name))
            self._update_playlist_view(monitor_name)
            self._update_disable_status_for_buttons()

    def _preview_video(self, video_path: str):
        logger.info(f"[GUI/PlaylistView] Previewing video: {video_path}")
        try:
            Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(video_path).get_uri(), None)
        except GLib.Error as e:
            logger.warning(f"[GUI/PlaylistView] Failed to launch preview for {video_path}: {e}")

    def _show_in_folder(self, video_path: str):
        logger.info(f"[GUI/PlaylistView] Show in folder: {video_path}")
        uri = Gio.File.new_for_path(video_path).get_uri()
        try:
            file_manager = pydbus.SessionBus().get(
                "org.freedesktop.FileManager1", "/org/freedesktop/FileManager1")
            file_manager.ShowItems([uri], "")
            return
        except GLib.Error as e:
            logger.debug(f"[GUI/PlaylistView] FileManager1.ShowItems unavailable, "
                         f"falling back to opening the folder: {e}")
        try:
            folder_uri = Gio.File.new_for_path(os.path.dirname(video_path)).get_uri()
            Gio.AppInfo.launch_default_for_uri(folder_uri, None)
        except GLib.Error as e:
            logger.warning(f"[GUI/PlaylistView] Failed to open folder for {video_path}: {e}")

    def on_video_drag_data_get(self, widget, drag_context, selection_data, info, time):
        selected_items = self.videos_view.get_selected_items()
        if not selected_items:
            return
        index = selected_items[0].get_indices()[0]
        selection_data.set_text(str(index), -1)

    def on_playlist_drag_data_received(self, widget, drag_context, x, y, selection_data, info, time):
        text = selection_data.get_text()
        if not text:
            drag_context.finish(False, False, time)
            return
        try:
            index = int(text)
        except ValueError:
            drag_context.finish(False, False, time)
            return
        if index < 0 or index >= len(self.video_paths):
            drag_context.finish(False, False, time)
            return

        monitor_name = self.monitor_combobox.get_active_text()
        if not self._is_all_mode() and not monitor_name:
            drag_context.finish(False, False, time)
            return

        if self.current_playlist is None:
            self.current_playlist = self._new_playlist_data()
        target_list = self._get_active_list(monitor_name)
        if target_list is None:
            drag_context.finish(False, False, time)
            return

        video_path = self.video_paths[index]
        if video_path not in target_list:
            logger.info(f"[GUI/PlaylistView] Video dropped into playlist: {video_path}")
            target_list.append(video_path)
            self._update_playlist_view(monitor_name)
            self._update_disable_status_for_buttons()
        drag_context.finish(True, False, time)

    def _resolve_library_video_path(self, path: Gtk.TreePath):
        index = path.get_indices()[0]
        video_paths = getattr(self, "video_paths", [])
        if 0 <= index < len(video_paths):
            return video_paths[index]
        return None

    def _resolve_queue_video_path(self, path: Gtk.TreePath):
        model = self.playlist_icon_view.get_model()
        if model is None:
            return None
        try:
            return model[path][2]
        except (IndexError, TypeError):
            return None

    def _ellipsize_item_labels(self, icon_view: Gtk.IconView):
        """
        Force item labels to a single, ellipsized line. The default IconView text
        renderer wraps long filenames onto a second line, which makes items (and
        thus a height-locked, non-scrolling IconView like the playlist queue)
        change height depending on which filenames happen to be showing.
        """
        for cell in icon_view.get_cells():
            if isinstance(cell, Gtk.CellRendererText):
                cell.set_property("wrap-width", -1)
                cell.set_property("ellipsize", Pango.EllipsizeMode.END)
                cell.set_property("alignment", Pango.Alignment.CENTER)

    def reload_icon_view(self, *_):
        self.video_paths = get_video_paths()
        list_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        self.videos_view.set_pixbuf_column(0)
        self.videos_view.set_text_column(1)
        self._ellipsize_item_labels(self.videos_view)
        self.videos_view.set_model(list_store)
        for idx, video_path in enumerate(self.video_paths):
            pixbuf = Gtk.IconTheme().get_default().load_icon("video-x-generic", 96, 0)
            list_store.append([pixbuf, os.path.basename(video_path)])
            thread = threading.Thread(
                target=get_thumbnail, args=(video_path, list_store, idx)
            )
            thread.daemon = True
            thread.start()

    def _update_disable_status_for_buttons(self):
        # if no playlist selected, disable apply/delete buttons
        selected_playlist = self.playlist_listbox.get_selected_row()
        self.apply_button.set_sensitive(selected_playlist is not None)
        self.delete_button.set_sensitive(selected_playlist is not None)

        # if playlist name is empty, disable add/save button
        playlist_name = self.playlist_name_entry.get_text()
        self.add_or_save_button.set_sensitive(playlist_name != "")
            
        # if no video selected, disable add to playlist button
        selected_videos = self.videos_view.get_selected_items()
        self.add_to_playlist_button.set_sensitive(selected_videos)

        # if no video selected in playlist, disable remove, move left, move right buttons
        selected_video = self.playlist_icon_view.get_selected_items()
        self.remove_from_playlist_button.set_sensitive(selected_video)
        self.move_left_button.set_sensitive(selected_video)
        self.move_right_button.set_sensitive(selected_video)

    def _is_all_mode(self):
        return self.current_playlist is not None and \
            self.current_playlist.get(PLAYLIST_KEY_MODE) == PLAYLIST_MODE_ALL

    def _new_playlist_data(self):
        return {
            PLAYLIST_KEY_MODE: PLAYLIST_MODE_PER_MONITOR,
            PLAYLIST_KEY_MONITORS: {monitor: [] for monitor in self.monitors.get_monitors()},
            PLAYLIST_KEY_VIDEOS: [],
        }

    def _get_active_list(self, monitor_name: str):
        """
        Returns a direct reference to the video list currently being edited: the
        shared 'videos' list in ALL mode, or this monitor's list in PER_MONITOR mode.
        """
        if self.current_playlist is None:
            return None
        if self._is_all_mode():
            return self.current_playlist.setdefault(PLAYLIST_KEY_VIDEOS, [])
        if not monitor_name:
            return None
        monitors = self.current_playlist.setdefault(PLAYLIST_KEY_MONITORS, {})
        return monitors.setdefault(monitor_name, [])

    def _sync_distribution_mode_ui(self):
        mode = self.current_playlist.get(PLAYLIST_KEY_MODE, PLAYLIST_MODE_PER_MONITOR)
        index = self.DISTRIBUTION_MODES.index(mode) if mode in self.DISTRIBUTION_MODES else 0
        self.distribution_mode_combobox.set_active(index)
        self.monitor_combobox.set_sensitive(mode == PLAYLIST_MODE_PER_MONITOR)

    def _update_playlist_view(self, monitor_name: str):
        if self.current_playlist is None:
            logger.warning(f"[GUI/PlaylistView] No current playlist to update")
            return

        is_all_mode = self._is_all_mode()
        if not is_all_mode and (not monitor_name or monitor_name not in self.monitors.get_monitors()):
            logger.warning(f"[GUI/PlaylistView] Monitor {monitor_name} not found")
            return

        video_list = self._get_active_list(monitor_name)
        if video_list is None:
            return

        # add icons for playlist videos
        # 3rd column holds the full video path (not displayed) so a drag-reorder
        # can be read back into `self.current_playlist` without relying on the
        # (non-unique) displayed basename.
        list_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        self.playlist_icon_view.set_pixbuf_column(0)
        self.playlist_icon_view.set_text_column(1)
        self._ellipsize_item_labels(self.playlist_icon_view)
        self.playlist_icon_view.set_model(list_store)
        self.playlist_icon_view.set_reorderable(True)
        # Force everything onto a single row: fix column count to (at least) the
        # item count so the icon view never wraps, and lets the ScrolledWindow's
        # horizontal scrollbar take over instead.
        self.playlist_icon_view.set_columns(max(len(video_list), 1))
        list_store.connect("row-deleted", self._on_playlist_reordered)
        for idx, video_path in enumerate(video_list):
            pixbuf = Gtk.IconTheme().get_default().load_icon("video-x-generic", 96, 0)
            list_store.append([pixbuf, os.path.basename(video_path), video_path])
            thread = threading.Thread(
                target=get_thumbnail, args=(video_path, list_store, idx)
            )
            thread.daemon = True
            thread.start()

        logger.info(f"[GUI/PlaylistView] Updating playlist view "
                    f"({'all monitors' if is_all_mode else monitor_name})")

    def _on_playlist_reordered(self, model, path):
        """
        Fires when the user drags an item to a new position in `playlist_icon_view`
        (GTK's built-in reorderable DnD moves a row by inserting the dragged row at
        its new position, then deleting the old one - so "row-deleted" is the point
        at which the model already reflects the final, reordered state).
        Keep `self.current_playlist` in sync so it saves/applies in the new order.
        """
        monitor_name = self.monitor_combobox.get_active_text()
        target_list = self._get_active_list(monitor_name)
        if target_list is None:
            return

        new_order = [row[2] for row in model]
        if new_order == target_list:
            return

        logger.info(f"[GUI/PlaylistView] Playlist reordered "
                    f"({'all monitors' if self._is_all_mode() else monitor_name})")
        target_list[:] = new_order
        self._update_disable_status_for_buttons()

    def _build_playlist_row(self, name: str, playlist_data: dict):
        row = Gtk.ListBoxRow()
        # Identity lives on the row object itself (not the displayed label text) so
        # the label can carry extra decoration (the distribution-mode badge) without
        # breaking every lookup that needs the playlist's real name.
        row.playlist_name = name

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label=name, xalign=0)
        name_label.set_hexpand(True)
        box.add(name_label)
        if playlist_data.get(PLAYLIST_KEY_MODE) == PLAYLIST_MODE_ALL:
            badge = Gtk.Label()
            badge.set_markup("<small><i>All</i></small>")
            badge.get_style_context().add_class("dim-label")
            box.add(badge)
        row.add(box)
        return row

    def _reset_to_new_draft(self):
        """Clear the editor to a blank, unsaved playlist draft (no listbox row selected)."""
        self.current_playlist_name = None
        self.playlist_name_entry.set_text("")
        self.current_playlist = self._new_playlist_data()
        self.saved_snapshot = copy.deepcopy(self.current_playlist)
        self._sync_distribution_mode_ui()
        self._update_disable_status_for_buttons()
        monitor_name = self.monitor_combobox.get_active_text()
        self._update_playlist_view(monitor_name)
        self.playlist_name_entry.grab_focus()

    def _load_playlist(self, select_name=None):
        self.playlists = PlaylistUtil().load()["playlists"]

        if self.playlists:
            # clear listbox then add playlists
            self.playlist_listbox.foreach(lambda row: self.playlist_listbox.remove(row))  # Clear existing rows
            for name, playlist_data in self.playlists.items():
                self.playlist_listbox.add(self._build_playlist_row(name, playlist_data))
            self.playlist_listbox.show_all()

            # prefer re-selecting the playlist just saved/edited; otherwise the first one
            target_row = None
            index = 0
            row = self.playlist_listbox.get_row_at_index(index)
            while row is not None:
                if row.playlist_name == select_name:
                    target_row = row
                    break
                index += 1
                row = self.playlist_listbox.get_row_at_index(index)
            if target_row is None:
                target_row = self.playlist_listbox.get_row_at_index(0)

            if target_row:
                self.playlist_listbox.select_row(target_row)
                self._select_playlist(target_row.playlist_name)
        else:
            self._reset_to_new_draft()

    def _save_playlist(self, playlist_name=None):
        original = PlaylistUtil().load()
        original["playlists"] = self.playlists
        self.playlists = original["playlists"]
        PlaylistUtil().save(original)

        if self.server is not None and playlist_name:
            active_playlist = self.config.get(CONFIG_KEY_ACTIVE_PLAYLIST, None)
            if playlist_name == active_playlist:
                self.server.playlist(playlist_name)  # live-reload the currently applied playlist

    def _load_config(self):
        self.config = ConfigUtil().load()
        
    def _save_config(self):
        ConfigUtil().save(self.config)