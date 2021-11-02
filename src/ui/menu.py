import gi

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')

from gi.repository import GLib, Gtk
from gi.repository import AppIndicator3 as AppIndicator

from pydbus import SessionBus
from commons import *


def on_item_mute(server, item):
    server.is_mute = item.get_active()


def on_item_pause(server, item):
    prev_state = server.is_paused_by_user
    server.is_paused_by_user = item.get_active()
    if not prev_state:
        server.pause_playback()
    else:
        server.start_playback()


def build_menu():
    # Connect to server
    bus = SessionBus()
    try:
        server = bus.get(DBUS_NAME_SERVER)
    except GLib.Error:
        print("Error: Couldn't connect to server")
        return
    menu = Gtk.Menu()
    mode = server.mode
    #
    item_show = Gtk.MenuItem(label="Show Hidamari")
    item_show.connect("activate", lambda *_: server.show_gui())
    #
    item_mute = Gtk.CheckMenuItem(label="Mute Audio")
    item_mute.connect("activate", lambda item: on_item_mute(server, item))
    item_mute.set_active(server.is_mute)
    #
    item_pause = Gtk.CheckMenuItem(label="Pause Playback")
    item_pause.connect("activate", lambda item: on_item_pause(server, item))
    item_pause.set_active(server.is_paused_by_user)
    #
    item_reload = Gtk.MenuItem(label="Reload")
    item_reload.connect("activate", lambda *_: server.reload())
    #
    item_lucky = Gtk.MenuItem(label="I'm Feeling Lucky")
    item_lucky.connect("activate", lambda *_: server.feeling_lucky())
    #
    item_quit = Gtk.MenuItem(label="Quit Hidamari")
    item_quit.connect("activate", lambda *_: server.quit())
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


def show_systray_icon():
    menu = build_menu()
    indicator = AppIndicator.Indicator.new(id=APP_INDICATOR_ID, icon_name=ICON_NAME,
                                           category=AppIndicator.IndicatorCategory.SYSTEM_SERVICES)
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(menu)
    print("Systray icon is ready")
    Gtk.main()


if __name__ == "__main__":
    show_systray_icon()
