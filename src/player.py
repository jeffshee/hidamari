import os
import signal
import subprocess
import random
from collections import defaultdict
import gi
import ctypes
import vlc

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from utils import ConfigHandler, ActiveHandler, WindowHandler, WindowHandlerGnome, StaticWallpaperHandler
from gui import ControlPanel, create_dir, scan_dir

VIDEO_WALLPAPER_PATH = os.environ['HOME'] + '/Videos/Hidamari'


class VLCWidget(Gtk.DrawingArea):
    """
    Simple VLC widget.
    Its player can be controlled through the 'player' attribute, which
    is a vlc.MediaPlayer() instance.
    """
    __gtype_name__ = 'VLCWidget'

    def __init__(self, width, height):
        # Spawn a VLC instance and create a new media player to embed.
        self.instance = vlc.Instance()
        Gtk.DrawingArea.__init__(self)
        self.player = self.instance.media_player_new()

        def handle_embed(*args):
            self.player.set_xwindow(self.get_window().get_xid())
            return True

        # Embed and set size.
        self.connect("realize", handle_embed)
        self.set_size_request(width, height)


class Player:
    def __init__(self):
        signal.signal(signal.SIGINT, self._quit)
        signal.signal(signal.SIGTERM, self._quit)
        # SIGSEGV as a fail-safe
        signal.signal(signal.SIGSEGV, self._quit)

        # Initialize
        create_dir(VIDEO_WALLPAPER_PATH)

        self.config_handler = ConfigHandler(self._on_config_modified)
        self.config = self.config_handler.config
        self.current_video_path = self.config.video_path
        self.user_pause_playback = False
        self.is_any_maximized, self.is_any_fullscreen = False, False

        # Monitor Detect
        self.width, self.height = self.monitor_detect()

        # We need to initialize X11 threads so we can use hardware decoding.
        x11 = ctypes.cdll.LoadLibrary('libX11.so')
        x11.XInitThreads()

        # Setup a VLC widget given the provided width and height.
        self.video_playback = VLCWidget(self.width, self.height)
        self.media = self.video_playback.instance.media_new(self.config.video_path)

        """
        This loops the media itself. Using -R / --repeat and/or -L / --loop don't seem to work. However,
        based on reading, this probably only repeats 65535 times, which is still a lot of time, but might
        cause the program to stop playback if it's left on for a very long time.
        """
        self.media.add_option("input-repeat=65535")

        self.video_playback.player.set_media(self.media)

        # These are to allow us to right click. VLC can't hijack mouse input, and probably not key inputs either in
        # Case we want to add keyboard shortcuts later on.
        self.video_playback.player.video_set_mouse_input(False)
        self.video_playback.player.video_set_key_input(False)

        # Window settings
        self.window = Gtk.Window()
        self.window.add(self.video_playback)
        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_size_request(self.width, self.height)

        # button event
        self._build_context_menu()
        self.window.connect('button-press-event', self._on_button_press_event)
        self.window.show_all()

        self.active_handler = ActiveHandler(self._on_active_changed)
        if os.environ["DESKTOP_SESSION"] in ["gnome", "gnome-xorg"]:
            self.window_handler = WindowHandlerGnome(self._on_window_state_changed)
        else:
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
        self.video_playback.player.pause()

    def start_playback(self):
        if not self.user_pause_playback:
            self.video_playback.player.play()

    def _quit(self, *args):
        self.static_wallpaper_handler.restore_ori_wallpaper()
        Gtk.main_quit()
        self.video_playback.instance.release()

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
                self.media = self.video_playback.instance.media_new(self.config.video_path)
                self.media.add_option("input-repeat=65535")
                self.video_playback.player.set_media(self.media)
                self.video_playback.player.set_position(0.0)
                self.current_video_path = self.config.video_path
            if self.config.mute_audio:
                self.video_playback.player.audio_set_volume(0)
            else:
                self.video_playback.player.audio_set_volume(int(self.config.audio_volume * 100))
            self.start_playback()

        # To ensure thread safe
        GLib.idle_add(_run)

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
