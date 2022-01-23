import logging
import sys

import gi
from pydbus import SessionBus

from hidamari.player.base_player import BasePlayer
from hidamari.ui.menu import build_menu

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from hidamari.commons import *

logger = logging.getLogger(LOGGER_NAME)


class NullWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super(NullWindow, self).__init__(*args, **kwargs)
        self.show_all()
        self.set_opacity(0.0)
        self.connect("button-press-event", self._on_button_press_event)

        self.menu = None
        # Welcome dialog
        dialog = Gtk.MessageDialog(text="Welcome to Hidamari 🤗", message_type=Gtk.MessageType.INFO,
                                   secondary_text="You can bring up the Menu by <b>Right click</b> on the desktop",
                                   secondary_use_markup=True,
                                   buttons=Gtk.ButtonsType.OK)
        dialog.run()
        dialog.destroy()

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if not self.menu:
                self.menu = build_menu(MODE_NULL)
            self.menu.popup_at_pointer()
            return True
        return False


class NullPlayer(BasePlayer):
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

    @property
    def mode(self):
        return MODE_NULL

    @property
    def data_source(self):
        return ""

    @property
    def volume(self):
        return 0

    @property
    def is_mute(self):
        return False

    @property
    def is_playing(self):
        return False

    def pause_playback(self):
        pass

    def start_playback(self):
        pass

    def new_window(self, gdk_monitor):
        return NullWindow(application=self)


def main():
    bus = SessionBus()
    app = NullPlayer()
    try:
        bus.publish(DBUS_NAME_PLAYER, app)
    except RuntimeError as e:
        logger.error(e)
    app.run(sys.argv)
