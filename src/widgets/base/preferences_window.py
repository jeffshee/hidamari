from typing import Optional
from gi.repository import Adw, Gtk
from .preferences_store import get_preference_bool, set_preference_bool


def create_switch_suffix_widget(row_def):
    switch = Gtk.Switch()
    switch.set_valign(Gtk.Align.CENTER)

    key = row_def.get("key")
    if key and "." in key:
        section, pref_key = key.split(".", 1)
        current_value = get_preference_bool(section, pref_key)
        switch.set_active(current_value)

        def on_switch_notify(switch, gparam):
            set_preference_bool(section, pref_key, switch.get_active())

        switch.connect("notify::active", on_switch_notify)
    else:
        switch.set_active(False)

    if row_def.get("suffix_disabled", False):
        switch.set_sensitive(False)

    return switch


def create_suffix_widget(row_def):
    mode = row_def.get("mode")
    if mode == "switch":
        return create_switch_suffix_widget(row_def)

    # Add other suffix types here if needed

    return None


def create_action_row(
    group,
    title: str,
    subtitle: Optional[str] = None,
    suffix_widget: Optional[Gtk.Widget] = None,
    on_activate: Optional[callable] = None,
):
    row = Adw.ActionRow()
    row.set_title(title)

    if subtitle:
        row.set_subtitle(subtitle)

    if suffix_widget:
        row.add_suffix(suffix_widget)
        row.set_activatable_widget(suffix_widget)

    if on_activate:
        row.set_activatable(True)
        row.connect("activated", lambda r: on_activate())

    group.add(row)


class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    def __init__(self, structure, search_enabled=True, **kwargs):
        super().__init__(**kwargs)
        self.set_search_enabled(search_enabled)

        for page_def in structure:
            page = Adw.PreferencesPage()

            if "title" in page_def:
                page.set_title(page_def["title"])
            if "icon" in page_def:
                page.set_icon_name(page_def["icon"])

            for group_def in page_def.get("groups", []):
                group = Adw.PreferencesGroup()
                if "title" in group_def:
                    group.set_title(group_def["title"])

                for row_def in group_def.get("rows", []):
                    title = row_def.get("title")
                    subtitle = row_def.get("subtitle")
                    mode = row_def.get("mode")
                    suffix_widget = create_suffix_widget(row_def)
                    on_activate = (
                        row_def.get("on_activate") if mode == "action" else None
                    )

                    if title:
                        create_action_row(
                            group, title, subtitle, suffix_widget, on_activate
                        )

                page.add(group)

            self.add(page)
