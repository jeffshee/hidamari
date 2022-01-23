import logging
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')

from gi.repository import GLib, Gtk
from gi.repository import AppIndicator3 as AppIndicator

from pydbus import SessionBus
from hidamari.commons import *

logger = logging.getLogger(LOGGER_NAME)


def connect():
    # Connect to server
    bus = SessionBus()
    try:
        server = bus.get(DBUS_NAME_SERVER)
        return server
    except GLib.Error:
        logger.error("Couldn't connect to server")
    return


def on_item_show():
    server = connect()
    if server:
        server.show_gui()


def on_item_mute():
    server = connect()
    if server:
        prev_state = server.is_mute
        server.is_mute = not prev_state


def on_item_pause():
    server = connect()
    if server:
        prev_state = server.is_paused_by_user
        server.is_paused_by_user = not prev_state
        if not prev_state:
            server.pause_playback()
        else:
            server.start_playback()


def on_item_reload():
    server = connect()
    if server:
        server.reload()


def on_item_lucky():
    server = connect()
    if server:
        server.feeling_lucky()


def on_item_quit():
    server = connect()
    if server:
        server.quit()


def start_action(f: callable):
    """Use this function to execute callback (for not blocking the UI)"""
    t = threading.Thread(target=f)
    t.start()


def build_menu(mode):
    menu = Gtk.Menu()
    #
    item_show = Gtk.MenuItem(label="Show Hidamari")
    item_show.connect("activate", lambda *_: start_action(on_item_show))
    #
    item_mute = Gtk.MenuItem(label="Toggle Mute Audio")
    item_mute.connect("activate", lambda *_: start_action(on_item_mute))
    #
    item_pause = Gtk.MenuItem(label="Toggle Play/Pause")
    item_pause.connect("activate", lambda *_: start_action(on_item_pause))
    #
    item_reload = Gtk.MenuItem(label="Reload")
    item_reload.connect("activate", lambda *_: start_action(on_item_reload))
    #
    item_lucky = Gtk.MenuItem(label="I'm Feeling Lucky")
    item_lucky.connect("activate", lambda *_: start_action(on_item_lucky))
    #
    item_quit = Gtk.MenuItem(label="Quit Hidamari")
    item_quit.connect("activate", lambda *_: start_action(on_item_quit))
    #
    # Filter out unsupported action in current mode
    if mode == MODE_NULL:
        item_list = [item_show, item_reload, item_quit]
    elif mode == MODE_WEBPAGE:
        item_list = [item_show, item_mute, item_reload, item_lucky, item_quit]
    else:
        item_list = [item_show, item_mute, item_pause, item_reload, item_lucky, item_quit]
    for item in item_list:
        menu.append(item)
    menu.show_all()
    return menu


def show_systray_icon(mode):
    menu = build_menu(mode)
    indicator = AppIndicator.Indicator.new(id=APP_INDICATOR_ID, icon_name=ICON_NAME,
                                           category=AppIndicator.IndicatorCategory.SYSTEM_SERVICES)
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(menu)
    logger.info("[Systray] Ready")
    Gtk.main()


if __name__ == "__main__":
    show_systray_icon(MODE_VIDEO)
