import sys
import os
import gi
import subprocess

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from utils_v2 import ActiveHandler

if os.environ["DESKTOP_SESSION"] in ["gnome", "gnome-xorg"]:
    from utils_v2 import WindowHandlerGnome as WindowHandler
else:
    from utils_v2 import WindowHandler

from monitor_v2 import Monitor
from utils_v2 import ConfigUtil


class BasePlayer:
    """
    Base class for player
    """

    def __init__(self, config):
        self.config = config
        self.user_pause_playback = False
        self.is_any_maximized, self.is_any_fullscreen = False, False

        self.monitors = []
        self._monitor_detect()

        self.active_handler = ActiveHandler(self._on_active_changed)
        self.window_handler = WindowHandler(self._on_window_state_changed)

    @property
    def mode(self):
        raise NotImplementedError

    @property
    def data_source(self):
        raise NotImplementedError

    @property
    def volume(self):
        raise NotImplementedError

    @property
    def is_mute(self):
        raise NotImplementedError

    @is_mute.setter
    def is_mute(self, is_mute: bool):
        raise NotImplementedError

    @property
    def is_playing(self):
        raise NotImplementedError

    def pause_playback(self):
        raise NotImplementedError

    def start_playback(self):
        raise NotImplementedError

    def _build_context_menu(self):
        # TODO will use Gtk.Popover instead with Gtk4 (aesthetic!)
        self.menu = Gtk.Menu()
        # Idk, if I don't use Popen to launch GUI, the pydbus just don't work (it freeze)... ¯\_(ツ)_/¯
        items = [('Show Hidamari', lambda *_: subprocess.Popen([sys.executable, "gui_v2.py"]), Gtk.MenuItem),
                 ('Mute Audio', self._on_menuitem_mute_audio, Gtk.CheckMenuItem),
                 ('Pause Playback', self._on_menuitem_pause_playback, Gtk.CheckMenuItem),
                 ('Reload', self._on_menuitem_reload, Gtk.MenuItem),
                 ('I\'m Feeling Lucky', self._on_menuitem_feeling_lucky, Gtk.MenuItem),
                 ('Quit Hidamari', self.quit, Gtk.MenuItem)]
        if 'gnome' in os.environ['XDG_CURRENT_DESKTOP'].lower():
            items += [(None, None, Gtk.SeparatorMenuItem),
                      ('GNOME Settings', lambda *_: subprocess.Popen("gnome-control-center"), Gtk.MenuItem)]

        for item in items:
            label, handler, item_type = item
            if item_type == Gtk.SeparatorMenuItem:
                self.menu.append(Gtk.SeparatorMenuItem())
            else:
                menuitem = item_type.new_with_label(label)
                menuitem.connect('activate', handler)
                self.menu.append(menuitem)
        return self.menu

    def _monitor_detect(self):
        display = Gdk.Display.get_default()
        screen = display.get_default_screen()

        for i in range(display.get_n_monitors()):
            monitor = Monitor(display.get_monitor(i))
            if monitor not in self.monitors:
                self.monitors.append(monitor)

        screen.connect("size-changed", self._on_size_changed)
        display.connect("monitor-added", self._on_monitor_added)
        display.connect("monitor-removed", self._on_monitor_removed)

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

    def _on_monitor_removed(self, _, gdk_monitor, *args):
        print("monitor-removed")
        self.monitors.remove(Monitor(gdk_monitor))

    def _on_active_changed(self, active):
        if active:
            self.pause_playback()
        else:
            if (self.is_any_maximized and self.config["detect_maximized"]) or self.is_any_fullscreen:
                self.pause_playback()
            else:
                self.start_playback()

    def _on_window_state_changed(self, state):
        self.is_any_maximized, self.is_any_fullscreen = state["is_any_maximized"], state["is_any_fullscreen"]
        if (self.is_any_maximized and self.config["detect_maximized"]) or self.is_any_fullscreen:
            self.pause_playback()
        else:
            self.start_playback()

    def _on_menuitem_mute_audio(self, item):
        self.config["mute_audio"] = item.get_active()
        self.is_mute = self.config["mute_audio"]

    def _on_menuitem_pause_playback(self, item):
        self.user_pause_playback = item.get_active()
        self.pause_playback() if self.user_pause_playback else self.start_playback()

    def _on_menuitem_feeling_lucky(self, *args):
        pass

    def _on_menuitem_reload(self, *args):
        pass

    def release(self):
        """Release the player"""
        print("release")
        del self.monitors

    def quit(self, *args):
        """Quit everything"""
        print("quit")
        ConfigUtil.save(self.config)
        self.release()
        exit(0)
