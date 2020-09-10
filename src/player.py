import os
import signal
import subprocess
import random
from collections import defaultdict
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkClutter', '1.0')
gi.require_version('ClutterGst', '3.0')
from gi.repository import Gtk, Gdk, GtkClutter, Clutter, ClutterGst, GLib

from utils import ConfigHandler, ActiveHandler, WindowHandler, StaticWallpaperHandler
from gui import ControlPanel, create_dir, scan_dir

VIDEO_WALLPAPER_PATH = os.environ['HOME'] + '/Videos/Hidamari'


class Player:
    def __init__(self):
        signal.signal(signal.SIGINT, self._quit)
        signal.signal(signal.SIGTERM, self._quit)
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, self._quit)

        # Initialize
        GtkClutter.init()
        ClutterGst.init()
        create_dir(VIDEO_WALLPAPER_PATH)

        self.config_handler = ConfigHandler(self._on_config_modified)
        self.config = self.config_handler.config
        self.current_video_path = self.config.video_path
        self.user_pause_playback = False
        self.is_any_maximized, self.is_any_fullscreen = False, False

        # Monitor Detect
        self.width, self.height = self.monitor_detect()

        # Actors initialize
        self.embed = GtkClutter.Embed()
        self.main_actor = self.embed.get_stage()
        self.main_actor.set_background_color(Clutter.Color.get_static(Clutter.StaticColor.BLACK))

        # Video initialize
        self.video_playback = ClutterGst.Playback()
        self.video_content = ClutterGst.Content()
        self.video_content.set_player(self.video_playback)

        # Playback settings
        self.video_playback.set_filename(self.config.video_path)
        self.video_playback.set_audio_volume(0.0 if self.config.mute_audio else self.config.audio_volume)
        self.video_playback.set_playing(True)
        self.video_playback.connect('eos', self._on_eos)
        self.main_actor.set_content(self.video_content)

        # Window settings
        self.window = Gtk.Window()
        self.window.add(self.embed)
        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_size_request(self.width, self.height)

        # button event
        self._build_context_menu()
        self.window.connect('button-press-event', self._on_button_press_event)

        self.window.show_all()

        self.active_handler = ActiveHandler(self._on_active_changed)
        self.window_handler = WindowHandler(self._on_window_state_changed)
        self.static_wallpaper_handler = StaticWallpaperHandler()
        self.static_wallpaper_handler.set_static_wallpaper()

        if self.config.video_path == '':
            # First time
            ControlPanel().run()
        elif not os.path.isfile(self.config.video_path):
            self._on_file_not_found(self.config.video_path)

        self.file_list = scan_dir()
        random.shuffle(self.file_list)
        self.current = 0
        if self.config.video_path in self.file_list:
            self.current = self.file_list.index(self.config.video_path)
        Gtk.main()

    def pause_playback(self):
        self.video_playback.set_playing(False)

    def start_playback(self):
        if not self.user_pause_playback:
            self.video_playback.set_playing(True)

    def _quit(self, *args):
        self.static_wallpaper_handler.restore_ori_wallpaper()
        Gtk.main_quit()

    def monitor_detect(self):
        display = Gdk.Display.get_default()
        screen = Gdk.Screen.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        scale_factor = monitor.get_scale_factor()
        width = scale_factor * geometry.width
        height = scale_factor * geometry.height
        screen.connect('size-changed', self._on_size_changed)
        return width, height

    def _on_size_changed(self, *args):
        self.width, self.height = self.monitor_detect()
        self.window.resize(self.width, self.height)
        self.wallpaper_actor.set_size(self.width, self.height)

    def _on_active_changed(self, active):
        if active:
            self.pause_playback()
        else:
            if (self.is_any_maximized and self.config.detect_maximized) or self.is_any_fullscreen:
                self.pause_playback()
            else:
                self.start_playback()

    def _on_window_state_changed(self, state):
        self.is_any_maximized, self.is_any_fullscreen = state['is_any_maximized'], state['is_any_fullscreen']
        if (self.is_any_maximized and self.config.detect_maximized) or self.is_any_fullscreen:
            self.pause_playback()
        else:
            self.start_playback()

    def _on_config_modified(self):
        def _run():
            # Get new config
            self.config = self.config_handler.config
            self.pause_playback()
            if self.current_video_path != self.config.video_path:
                self.video_playback.set_filename(self.config.video_path)
                self.video_playback.set_progress(0.0)
                self.current_video_path = self.config.video_path
            self.video_playback.set_audio_volume(0.0 if self.config.mute_audio else self.config.audio_volume)
            self.start_playback()
            self.menuitem['Mute Audio'].set_active(self.config.mute_audio)

        # To ensure thread safe
        GLib.idle_add(_run)

    def _on_eos(self, *args):
        self.video_playback.set_progress(0.0)
        self.video_playback.set_audio_volume(0.0 if self.config.mute_audio else self.config.audio_volume)
        self.start_playback()

    def _on_menuitem_main_gui(self, *args):
        ControlPanel().run()

    def _on_menuitem_mute_audio(self, item):
        self.config.mute_audio = item.get_active()
        self.config_handler.save()

    def _on_menuitem_pause_playback(self, item):
        self.user_pause_playback = item.get_active()
        self.pause_playback() if self.user_pause_playback else self.start_playback()

    def _on_menuitem_feeling_lucky(self, *args):
        self.current += 1
        if self.current % len(self.file_list) == 0:
            random.shuffle(self.file_list)
        self.config.video_path = self.file_list[self.current % len(self.file_list)]
        self.config_handler.save()

    def _on_menuitem_gnome_settings(self, *args):
        subprocess.Popen('gnome-control-center')

    def _on_menuitem_quit(self, *args):
        self._quit()

    def _build_context_menu(self):
        self.menu = Gtk.Menu()
        items = [('Show Hidamari', self._on_menuitem_main_gui, Gtk.MenuItem),
                 ('Mute Audio', self._on_menuitem_mute_audio, Gtk.CheckMenuItem),
                 ('Pause Playback', self._on_menuitem_pause_playback, Gtk.CheckMenuItem),
                 ('I\'m Feeling Lucky', self._on_menuitem_feeling_lucky, Gtk.MenuItem),
                 ('Quit Hidamari', self._on_menuitem_quit, Gtk.MenuItem)]
        self.menuitem = defaultdict()
        if 'gnome' in os.environ['XDG_CURRENT_DESKTOP'].lower():
            items += [(None, None, Gtk.SeparatorMenuItem),
                      ('GNOME Settings', self._on_menuitem_gnome_settings, Gtk.MenuItem)]

        for item in items:
            label, handler, item_type = item
            if item_type == Gtk.SeparatorMenuItem:
                self.menu.append(Gtk.SeparatorMenuItem())
            else:
                menuitem = item_type.new_with_label(label)
                menuitem.connect('activate', handler)
                menuitem.set_margin_top(4)
                menuitem.set_margin_bottom(4)
                self.menu.append(menuitem)
                self.menuitem[label] = menuitem
        self.menu.show_all()

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer()
        return True

    def _on_not_implemented(self, *args):
        print('Not implemented!')
        message = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK,
                                    message_format='Not implemented!')
        message.connect("response", self._dialog_response)
        message.show()

    def _on_file_not_found(self, path):
        print('File not found!')
        message = Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                                    message_format='File {} not found!'.format(path))
        message.connect("response", self._dialog_response)
        message.show()

    def _dialog_response(self, widget, response_id):
        if response_id == Gtk.ResponseType.OK:
            widget.destroy()


if __name__ == '__main__':
    player = Player()
