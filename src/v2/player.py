import os
import gi
from collections import defaultdict
import subprocess

gi.require_version("Gtk", "3.0")
gi.require_version("GtkClutter", "1.0")
gi.require_version("ClutterGst", "3.0")

from gi.repository import Gtk, GtkClutter, ClutterGst, Clutter, Gdk
from v2 import constants
from v2.utils import StaticWallpaperHandler

GtkClutter.init()
ClutterGst.init()


class Player(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Config
        self.config = defaultdict()

        # Handlers
        self.static_wallpaper_handler = StaticWallpaperHandler()

        # Actors initialize
        embed = GtkClutter.Embed()
        self.main_actor = embed.get_stage()
        self.main_actor.set_background_color(Clutter.Color.new(0, 0, 0, 0))
        self.add(embed)

        # Video initialize
        self.video_playback = ClutterGst.Playback()
        self.video_playback.connect('eos', self._on_eos)

        # Button event
        self._build_context_menu()
        self.connect("button-press-event", self._on_button_press_event)

        # Window
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_size_request(*self._monitor_detect())
        self.show_all()

        # Set transparency
        self.set_opacity(0.0)

    def _monitor_detect(self):
        display = Gdk.Display.get_default()
        screen = Gdk.Screen.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        scale_factor = monitor.get_scale_factor()
        width = scale_factor * geometry.width
        height = scale_factor * geometry.height
        screen.connect("size-changed", self._on_size_changed)
        return width, height

    def _build_context_menu(self):
        self.menu = Gtk.Menu()
        items = [("Show Hidamari", self._on_menuitem_main_gui, Gtk.MenuItem),
                 ("Mute Audio", self._on_menuitem_mute_audio, Gtk.CheckMenuItem),
                 ("Pause Playback", self._on_menuitem_pause_playback, Gtk.CheckMenuItem),
                 ("I'm Feeling Lucky", self._on_menuitem_feeling_lucky, Gtk.MenuItem),
                 ("Quit Hidamari", self._on_menuitem_quit, Gtk.MenuItem)]
        self.menuitem = defaultdict()
        if "gnome" in os.environ["XDG_CURRENT_DESKTOP"].lower():
            items += [(None, None, Gtk.SeparatorMenuItem),
                      ("GNOME Settings", self._on_menuitem_gnome_settings, Gtk.MenuItem)]

        for item in items:
            label, handler, item_type = item
            if label is None:
                self.menu.append(item_type())
            else:
                menuitem = item_type(label)
                menuitem.connect("activate", handler)
                self.menu.append(menuitem)
                self.menuitem[label] = menuitem
        self.menu.show_all()

    def set_data_source(self, path):
        if os.path.isfile(path):
            video_content = ClutterGst.Content()
            self.video_playback.set_filename(path)
            self.video_playback.set_audio_volume(
                0.0 if self.config.get(constants.CONFIG_KEY_IS_MUTED, False) else self.config.get(
                    constants.CONFIG_KEY_AUDIO_VOLUME, 0.5))
            video_content.set_player(self.video_playback)
            self.main_actor.set_content(video_content)
            # Set static wallpaper
            if self.config.get(constants.CONFIG_KEY_IS_STATIC_WALLPAPER, True):
                self.static_wallpaper_handler.set_static_wallpaper(path, self.config.get(
                    constants.CONFIG_KEY_WALLPAPER_BLUR_R, 5))
            # Show everything and start playback
            self.set_opacity(1.0)
            self.start()

    def pause(self):
        self.video_playback.set_playing(False)

    def start(self):
        self.video_playback.set_playing(True)

    def stop(self):
        # Set original wallpaper
        self.static_wallpaper_handler.set_original_wallpaper()
        # Stop playback and hide everything
        self.video_playback.set_progress(0.0)
        self.pause()
        self.set_opacity(0.0)

    def set_volume(self, volume):
        self.video_playback.set_audio_volume(volume)

    def _on_size_changed(self, *args):
        width, height = self.monitor_detect()
        self.main_actor.set_size(width, height)
        self.resize(width, height)

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer()
        return True

    """
    Event Handlers
    """

    def _on_eos(self, *args):
        self.video_playback.set_progress(0.0)
        self.start()

    def _on_menuitem_main_gui(self, *args):
        pass

    def _on_menuitem_mute_audio(self, item):
        pass

    def _on_menuitem_pause_playback(self, item):
        self.pause() if item.get_active() else self.start()

    def _on_menuitem_feeling_lucky(self, *args):
        pass

    def _on_menuitem_gnome_settings(self, *args):
        subprocess.Popen('gnome-control-center')

    def _on_menuitem_quit(self, *args):
        self.stop()
        self.close()

    def _on_not_implemented(self, *args):
        message = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK,
                                    message_format="Not implemented!")
        message.connect("response", self._on_dialog_response)
        message.show()

    def _on_file_not_found(self, path):
        message = Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                                    message_format="{}\nFile doesn't exist!".format(path))
        message.connect("response", self._on_dialog_response)
        message.show()

    def _on_dialog_response(self, widget, response_id):
        if response_id == Gtk.ResponseType.OK:
            widget.destroy()
