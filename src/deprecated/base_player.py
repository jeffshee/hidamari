import subprocess

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from utils import ActiveHandler, is_gnome, is_wayland

if is_wayland():
    if is_gnome():
        from utils import WindowHandlerGnome as WindowHandler
    else:
        # Dummy class as not currently supported.
        class WindowHandler:
            def __init__(self, _: callable):
                pass
else:
    from utils import WindowHandler

from monitor import Monitor
from commons import *


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
        items = [('Show Hidamari', lambda *_: subprocess.Popen([sys.executable, GUI_SCRIPT_PATH]), Gtk.MenuItem),
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
        print("Player: size-changed")
        for monitor in self.monitors:
            monitor.win_resize(monitor.width, monitor.height)
            monitor.win_move(monitor.x, monitor.y)
            print(monitor.x, monitor.y, monitor.width, monitor.height)

    def _on_monitor_added(self, _, gdk_monitor, *args):
        print("Player: monitor-added")
        new_monitor = Monitor(gdk_monitor)
        self.monitors.append(new_monitor)

    def _on_monitor_removed(self, _, gdk_monitor, *args):
        print("Player: monitor-removed")
        self.monitors.remove(Monitor(gdk_monitor))

    def _on_active_changed(self, active):
        if active:
            self.pause_playback()
        else:
            if (self.is_any_maximized and self.config[CONFIG_KEY_DETECT_MAXIMIZED]) or self.is_any_fullscreen:
                self.pause_playback()
            else:
                self.start_playback()

    def _on_window_state_changed(self, state):
        self.is_any_maximized, self.is_any_fullscreen = state["is_any_maximized"], state["is_any_fullscreen"]
        # Ignore a weird error (everything is actually working fine...)
        try:
            if (self.is_any_maximized and self.config[CONFIG_KEY_DETECT_MAXIMIZED]) or self.is_any_fullscreen:
                self.pause_playback()
            else:
                self.start_playback()
        except AttributeError:
            pass

    def _on_menuitem_mute_audio(self, item):
        self.config[CONFIG_KEY_MUTE] = item.get_active()
        self.is_mute = self.config[CONFIG_KEY_MUTE]

    def _on_menuitem_pause_playback(self, item):
        self.user_pause_playback = item.get_active()
        self.pause_playback() if self.user_pause_playback else self.start_playback()

    def _on_menuitem_feeling_lucky(self, *args):
        pass

    def _on_menuitem_reload(self, *args):
        pass

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            for child in self.menu.get_children():
                if child.get_label() == "Mute Audio":
                    child.handler_block_by_func(self._on_menuitem_mute_audio)
                    child.set_active(self.is_mute)
                    child.handler_unblock_by_func(self._on_menuitem_mute_audio)
                if child.get_label() == "Pause Playback":
                    child.handler_block_by_func(self._on_menuitem_pause_playback)
                    child.set_active(not self.is_playing)
                    child.handler_unblock_by_func(self._on_menuitem_pause_playback)
            self.menu.popup_at_pointer()
            return True
        return False

    def release(self):
        """Release the player"""
        print("Player: Release")
        del self.monitors

    def quit(self, *args):
        """Quit everything"""
        print("Player: Quit")
        self.release()
        # exit(0)
