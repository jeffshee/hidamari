import logging
from abc import abstractmethod

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, Gdk
from pydbus import SessionBus
from commons import *

logger = logging.getLogger(LOGGER_NAME)


class RikaWindow(Gtk.ApplicationWindow):
    # A cute dummy window ;)
    def __init__(self, *args, **kwargs):
        super(RikaWindow, self).__init__(*args, **kwargs)
        self.image = Gtk.Image.new_from_file("rika.gif")
        self.add(self.image)
        self.image.show()


class BasePlayer(Gtk.Application):
    """
    <node>
    <interface name='io.github.jeffshee.hidamari.player'>
        <property name="mode" type="s" access="read"/>
        <property name="data_source" type="s" access="readwrite"/>
        <property name="volume" type="i" access="readwrite"/>
        <property name="is_mute" type="b" access="readwrite"/>
        <property name="is_playing" type="b" access="read"/>
        <method name='pause_playback'/>
        <method name='start_playback'/>
        <method name='quit_player'/>
    </interface>
    </node>
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id=APPLICATION_ID_PLAYER,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
            **kwargs
        )
        self.windows = dict()
        self._monitor_detect()

    def _monitor_detect(self):
        display = Gdk.Display.get_default()
        screen = display.get_default_screen()

        for i in range(display.get_n_monitors()):
            monitor = display.get_monitor(i)
            if monitor not in self.windows:
                self.windows[monitor] = None

        screen.connect("size-changed", self._on_size_changed)
        display.connect("monitor-added", self._on_monitor_added)
        display.connect("monitor-removed", self._on_monitor_removed)

    def new_window(self, gdk_monitor):
        # Override here for different window
        # NOTE: Don't forget to set the application=self, otherwise the application will quit immediately lol
        return RikaWindow(application=self)

    def _on_size_changed(self, *args):
        logger.info("[Player] size-changed")
        for monitor in self.windows:
            rect = monitor.get_geometry()
            x, y, width, height = rect.x, rect.y, rect.width, rect.height
            monitor.win_resize(width, height)
            monitor.win_move(x, y)

    def _on_monitor_added(self, _, gdk_monitor, *args):
        logger.info("[Player] monitor-added")
        self.windows[gdk_monitor] = None
        self.do_activate()

    def _on_monitor_removed(self, _, gdk_monitor, *args):
        logger.info("[Player] monitor-removed")
        del self.windows[gdk_monitor]

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        for monitor in self.windows:
            if not self.windows[monitor]:
                window = self.new_window(monitor)
                window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
                rect = monitor.get_geometry()
                x, y, width, height = rect.x, rect.y, rect.width, rect.height
                window.set_size_request(width, height)
                window.move(x, y)
                self.windows[monitor] = window
            self.windows[monitor].present()

    @property
    @abstractmethod
    def mode(self):
        pass

    @property
    @abstractmethod
    def data_source(self):
        pass

    @data_source.setter
    def data_source(self, data_source):
        pass

    @property
    @abstractmethod
    def volume(self):
        pass

    @volume.setter
    def volume(self, volume):
        pass

    @property
    @abstractmethod
    def is_mute(self):
        pass

    @is_mute.setter
    def is_mute(self, is_mute):
        pass

    @property
    @abstractmethod
    def is_playing(self):
        pass

    @abstractmethod
    def pause_playback(self):
        pass

    @abstractmethod
    def start_playback(self):
        pass

    def quit_player(self):
        self.quit()


def main():
    bus = SessionBus()
    app = BasePlayer()
    try:
        bus.publish(DBUS_NAME_PLAYER, app)
    except RuntimeError as e:
        logger.error(e)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
