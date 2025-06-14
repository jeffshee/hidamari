import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, Adw, GLib, Gdk
from .window import Window
from .app_actions import ALL_APP_ACTIONS
from .app_config import APP_ID
from .paths_config import BASE_RESOURCE_PATH
from .shortcuts_config import SHORTCUTS

from .logbook_store import clear_all_log_entries
from .preferences_store import get_preference_bool


class MainApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path=BASE_RESOURCE_PATH,
        )
        self.__register_app_actions()
        self.connect("shutdown", self.__on_shutdown)

    def __create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def __register_app_actions(self):
        flat_shortcuts = {}
        for group_shortcuts in SHORTCUTS.values():
            flat_shortcuts.update(group_shortcuts)

        for name, handler in ALL_APP_ACTIONS.items():
            shortcuts = flat_shortcuts.get(name, [])
            self.__create_action(
                name,
                lambda action, param=None, h=handler: h(self),
                shortcuts=shortcuts,
            )

    def __on_shutdown(self, app):
        if get_preference_bool("logbook", "delete_on_exit"):
            clear_all_log_entries()

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = Window(application=self)
        win.present()


def main(version):
    app = MainApplication()
    return app.run(sys.argv)
