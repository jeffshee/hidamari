import gi

gi.require_version("Gtk", "3.0")
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk
from gi.repository import AppIndicator3 as AppIndicator

from hidamari.commons import *


def build_dummy_menu():
    menu = Gtk.Menu()
    item_quit = Gtk.MenuItem(label="Quit")
    item_quit.connect("activate", on_clicked_quit)
    menu.append(item_quit)
    menu.show_all()
    return menu


def on_clicked_quit(*args):
    Gtk.main_quit()


def show_systray_icon(menu: Gtk.Menu = None):
    if not menu:
        menu = build_dummy_menu()
    indicator = AppIndicator.Indicator.new(id=APP_INDICATOR_ID, icon_name=ICON_NAME,
                                           category=AppIndicator.IndicatorCategory.SYSTEM_SERVICES)
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(menu)
    Gtk.main()


if __name__ == "__main__":
    show_systray_icon()
