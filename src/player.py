import os
import signal
import subprocess
import random
from collections import defaultdict
import gi
import ctypes
import vlc

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from utils import ConfigHandler, ActiveHandler, WindowHandler, WindowHandlerGnome, StaticWallpaperHandler
from gui import ControlPanel, create_dir, scan_dir

VIDEO_WALLPAPER_PATH = os.environ["HOME"] + "/Videos/Hidamari"


class VLCWidget(Gtk.DrawingArea):
    """
    Simple VLC widget.
    Its player can be controlled through the 'player' attribute, which
    is a vlc.MediaPlayer() instance.
    """
    __gtype_name__ = "VLCWidget"

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


class Monitor:
    """
    A wrapper of Gdk.Monitor
    """

    def __init__(self, gdk_monitor: Gdk.Monitor):
        self.gdk_monitor = gdk_monitor
        # Window and VLC widget dedicated for each monitor
        self.__window = None
        self.__vlc_widget = None

    def initialize(self, window: Gtk.Window, vlc_widget: VLCWidget):
        self.__window = window
        self.__vlc_widget = vlc_widget

    @property
    def is_initialized(self):
        return self.__window is not None and self.__vlc_widget is not None

    @property
    def x(self):
        return self.gdk_monitor.get_geometry().x

    @property
    def y(self):
        return self.gdk_monitor.get_geometry().y

    @property
    def width(self):
        return self.gdk_monitor.get_geometry().width * self.gdk_monitor.get_scale_factor()

    @property
    def height(self):
        return self.gdk_monitor.get_geometry().height * self.gdk_monitor.get_scale_factor()

    @property
    def is_primary(self):
        return self.gdk_monitor.is_primary()

    # Expose frequently used functions
    def vlc_play(self):
        if self.is_initialized:
            self.__vlc_widget.player.play()

    def vlc_is_playing(self):
        if self.is_initialized:
            return self.__vlc_widget.player.is_playing()

    def vlc_pause(self):
        if self.is_initialized:
            self.__vlc_widget.player.pause_playback()

    def vlc_media_new(self, *args):
        if self.is_initialized:
            return self.__vlc_widget.instance.media_new(*args)

    def vlc_set_media(self, *args):
        if self.is_initialized:
            self.__vlc_widget.player.set_media(*args)

    def vlc_audio_set_volume(self, *args):
        if self.is_initialized:
            self.__vlc_widget.player.audio_set_volume(*args)

    def vlc_get_position(self, *args):
        if self.is_initialized:
            return self.__vlc_widget.player.get_position()

    def vlc_set_position(self, *args):
        if self.is_initialized:
            self.__vlc_widget.player.set_position(*args)

    def win_move(self, *args):
        if self.is_initialized:
            self.__window.move(*args)

    def win_resize(self, *args):
        if self.is_initialized:
            self.__window.resize(*args)

    def __eq__(self, other):
        if isinstance(other, Monitor):
            return self.gdk_monitor == other.gdk_monitor
        return False

    def __del__(self):
        if self.is_initialized:
            self.__vlc_widget.player.release()
            self.__window.close()


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

        # We need to initialize X11 threads so we can use hardware decoding.
        # `libX11.so.6` fix for Fedora 33
        x11 = None
        for lib in ["libX11.so", "libX11.so.6"]:
            try:
                x11 = ctypes.cdll.LoadLibrary(lib)
            except OSError:
                pass
            if x11 is not None:
                x11.XInitThreads()
                break

        self._build_context_menu()

        # Monitor Detect
        self.monitors = []
        self.monitor_detect()
        self.start_all_monitors()

        self.active_handler = ActiveHandler(self._on_active_changed)
        if os.environ["DESKTOP_SESSION"] in ["gnome", "gnome-xorg"]:
            self.window_handler = WindowHandlerGnome(self._on_window_state_changed)
        else:
            self.window_handler = WindowHandler(self._on_window_state_changed)
        self.static_wallpaper_handler = StaticWallpaperHandler()
        self.static_wallpaper_handler.set_static_wallpaper()

        if self.config.video_path == "":
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

    def start_all_monitors(self):
        for monitor in self.monitors:
            if monitor.is_vlc_initialized:
                continue
            # Setup a VLC widget given the provided width and height.
            vlc_widget = VLCWidget(monitor.width, monitor.height)
            media = vlc_widget.instance.media_new(self.config.video_path)
            """
            This loops the media itself. Using -R / --repeat and/or -L / --loop don't seem to work. However,
            based on reading, this probably only repeats 65535 times, which is still a lot of time, but might
            cause the program to stop playback if it's left on for a very long time.
            """
            media.add_option("input-repeat=65535")

            # Prevent awful ear-rape with multiple instances.
            if not monitor.is_primary:
                media.add_option("no-audio")

            vlc_widget.player.set_media(media)

            # These are to allow us to right click. VLC can't hijack mouse input, and probably not key inputs either in
            # Case we want to add keyboard shortcuts later on.
            vlc_widget.player.video_set_mouse_input(False)
            vlc_widget.player.video_set_key_input(False)

            # Window settings
            window = Gtk.Window()
            window.add(vlc_widget)
            window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
            window.set_size_request(monitor.width, monitor.height)
            window.move(monitor.x, monitor.y)

            # Button event
            window.connect("button-press-event", self._on_button_press_event)
            window.show_all()

            monitor.initialize(window, vlc_widget)

    def set_volume(self, volume):
        for monitor in self.monitors:
            if monitor.is_primary:
                monitor.vlc_audio_set_volume(volume)

    def pause_playback(self):
        for monitor in self.monitors:
            monitor.vlc_pause()

    def start_playback(self):
        if not self.user_pause_playback:
            for monitor in self.monitors:
                monitor.vlc_play()

    def _quit(self, *args):
        self.static_wallpaper_handler.restore_ori_wallpaper()
        del self.monitors
        Gtk.main_quit()

    def monitor_detect(self):
        display = Gdk.Display.get_default()
        screen = display.get_default_screen()

        for i in range(display.get_n_monitors()):
            monitor = Monitor(display.get_monitor(i))
            if monitor not in self.monitors:
                self.monitors.append(monitor)

        screen.connect("size-changed", self._on_size_changed)
        display.connect("monitor-added", self._on_monitor_added)
        display.connect("monitor-removed", self._on_monitor_removed)

    def monitor_sync(self):
        primary = 0
        for i, monitor in enumerate(self.monitors):
            if monitor.is_primary:
                primary = i
                break
        for monitor in self.monitors:
            # `set_position()` method require the playback to be enabled before calling
            monitor.vlc_play()
            monitor.vlc_set_position(self.monitors[primary].vlc_get_position())
            monitor.vlc_play() if self.monitors[primary].vlc_is_playing() else monitor.vlc_pause()

    def _on_size_changed(self, *args):
        print("size-changed")
        for monitor in self.monitors:
            monitor.win_resize(monitor.width, monitor.height)
            monitor.win_move(monitor.x, monitor.y)
            print(monitor.x, monitor.y, monitor.width, monitor.height)

    def _on_monitor_added(self, _, gdk_monitor, *args):
        print("monitor-added")
        new_monitor = Monitor(gdk_monitor)
        self.monitors.append(new_monitor)
        self.start_all_monitors()
        self.monitor_sync()

    def _on_monitor_removed(self, _, gdk_monitor, *args):
        print("monitor-removed")
        self.monitors.remove(Monitor(gdk_monitor))

    def _on_active_changed(self, active):
        if active:
            self.pause_playback()
        else:
            if (self.is_any_maximized and self.config.detect_maximized) or self.is_any_fullscreen:
                self.pause_playback()
            else:
                self.start_playback()

    def _on_window_state_changed(self, state):
        self.is_any_maximized, self.is_any_fullscreen = state["is_any_maximized"], state["is_any_fullscreen"]
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
                for monitor in self.monitors:
                    media = monitor.vlc_media_new(self.config.video_path)
                    media.add_option("input-repeat=65535")
                    if not monitor.is_primary:
                        media.add_option("no-audio")
                    monitor.vlc_set_media(media)
                    monitor.vlc_set_position(0.0)
                self.current_video_path = self.config.video_path
            if self.config.mute_audio:
                self.set_volume(0)
            else:
                self.set_volume(int(self.config.audio_volume * 100))
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
        print("Not implemented!")
        message = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK,
                                    message_format='Not implemented!')
        message.connect("response", self._dialog_response)
        message.show()

    def _on_file_not_found(self, path):
        print("File not found!")
        message = Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                                    message_format='File {} not found!'.format(path))
        message.connect("response", self._dialog_response)
        message.show()

    def _dialog_response(self, widget, response_id):
        if response_id == Gtk.ResponseType.OK:
            widget.destroy()


if __name__ == '__main__':
    player = Player()
