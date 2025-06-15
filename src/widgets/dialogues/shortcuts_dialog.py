from gi.repository import Gtk, Gio
from src.config.shortcuts_config import SHORTCUTS, SHORTCUT_TITLES


class ShortcutsDialog(Gtk.ShortcutsWindow):
    def __init__(self, application, **kwargs):
        super().__init__(**kwargs)
        self.set_modal(True)
        self.set_application(application)

        section = Gtk.ShortcutsSection()

        for group_title, actions in SHORTCUTS.items():
            group = Gtk.ShortcutsGroup()
            group.props.title = group_title

            for action_name, accels in actions.items():
                title = SHORTCUT_TITLES.get(action_name, action_name)
                accel = accels[0] if accels else None
                if accel:
                    group.add_shortcut(
                        self.__create_shortcut(title, f"app.{action_name}", accel)
                    )

            section.add_group(group)

        self.add_section(section)
        self.show()

    def __create_shortcut(
        self, title: str, action_name: str, accelerator: str
    ) -> Gtk.ShortcutsShortcut:
        shortcut = Gtk.ShortcutsShortcut()
        shortcut.props.shortcut_type = Gtk.ShortcutType.ACCELERATOR
        shortcut.props.title = title
        shortcut.props.accelerator = accelerator
        shortcut.props.action_name = action_name
        return shortcut
