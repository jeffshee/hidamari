from src.widgets.dialogues.about_dialog import show_about_dialog
from src.widgets.base.preferences_window import PreferencesWindow
from src.widgets.dialogues.shortcuts_dialog import ShortcutsDialog
from src.config.preferences_config import PREFERENCES_STRUCTURE


def on_quit_action(app, *args):
    app.quit()


def on_about_action(app, *args):
    win = app.props.active_window
    show_about_dialog(win)


def on_shortcuts_action(app, *args):
    win = app.props.active_window
    shortcuts = ShortcutsDialog(application=app, transient_for=win)
    shortcuts.present()


def on_preferences_action(app, *args):
    win = app.props.active_window
    preferences = PreferencesWindow(
        structure=PREFERENCES_STRUCTURE, application=app, transient_for=win
    )
    preferences.present()


ALL_APP_ACTIONS = {
    "quit": on_quit_action,
    "about": on_about_action,
    "shortcuts": on_shortcuts_action,
    "preferences": on_preferences_action,
}
