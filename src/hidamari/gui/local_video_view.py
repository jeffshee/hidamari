import sys
import threading

import gi
import vlc

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf, Gdk

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    from gui.imports import *
    from gui.gui_utils import get_thumbnail, HoverPreview
    from utils import ConfigUtil
except ModuleNotFoundError:
    from hidamari.gui.imports import *
    from hidamari.gui.gui_utils import get_thumbnail, HoverPreview
    from hidamari.utils import ConfigUtil

class LocalVideoView:
    def __init__(self, config: ConfigUtil, server):
        self.config = config
        self.server = server
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_resource(APP_UI_RESOURCE_PATH + "local_video_view.ui")
        except GLib.Error:
            self.builder.add_from_file(os.path.abspath("./src/hidamari/assets/local_video_view.ui"))

        self.widget = self.builder.get_object("LocalVideoView")

        self.builder.connect_signals({
        })
        
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
                
        self.all_key = "all"
        self.video_paths = []

        self.icon_view: Gtk.IconView = self.builder.get_object("IconView")
        self.icon_view.connect("button-press-event", self.on_icon_view_button_press)
        self.hover_preview = HoverPreview(
            self.icon_view, vlc.Instance(["--no-disable-screensaver"]), self._resolve_video_path)

        self._setup_context_menu() # setup context menu for selecting monitors

    def _resolve_video_path(self, path: Gtk.TreePath):
        index = path.get_indices()[0]
        if 0 <= index < len(self.video_paths):
            return self.video_paths[index]
        return None

    def reload_icon_view(self, *_):
        self.video_paths = get_video_paths()
        list_store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        self.icon_view.set_pixbuf_column(0)
        self.icon_view.set_text_column(1)
        self.icon_view.set_model(list_store)
        for idx, video_path in enumerate(self.video_paths):
            pixbuf = Gtk.IconTheme().get_default().load_icon("video-x-generic", 96, 0)
            list_store.append([pixbuf, os.path.basename(video_path)])
            thread = threading.Thread(
                target=get_thumbnail, args=(video_path, list_store, idx)
            )
            thread.daemon = True
            thread.start()
        
    def _setup_context_menu(self):
        self.contextMenu_monitors = Gtk.Menu()
        self.contextMenu_monitors.show_all()
        
        for monitor_name,monitor in self.monitors.get_monitors().items():
            item = Gtk.MenuItem(label=f"Set For {monitor_name}")
            item.connect("activate", self.on_set_as, monitor)
            self.contextMenu_monitors.append(item)

        # add all option
        item = Gtk.MenuItem(label=f"Set For All")
        item.connect("activate", self.on_set_as, self.all_key)
        self.contextMenu_monitors.append(item)
        
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
        logger.info(f"[GUI/LocalVideoView] Local Video Set To {video_path} For Monitor {monitor}")
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
            
    def _load_config(self):
        self.config = ConfigUtil().load()
        
    def _save_config(self):
        ConfigUtil().save(self.config)