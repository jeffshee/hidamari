from src.widgets.base.base_list_view import BaseListView
from src.widgets.dialogues.logbook_entry_dialog import LogbookEntryDialog
from src.stores.logbook_store import get_logbook_entries, delete_logbook_entry
from src.messages.messages import (
    ALL_CLEAR,
    NO_HOSTILES_LOGGED_DURING_OPERATION,
    HOSTILE_COUNT,
)


class Logbook(BaseListView):
    def __init__(self, application, window):
        super().__init__()
        self.application = application
        self.window = window
        self.set_empty_status(
            ALL_CLEAR,
            NO_HOSTILES_LOGGED_DURING_OPERATION,
            "weather-clear-symbolic",
        )
        self.connect("row-activated", self.__on_row_activated)
        self.__load_entries()

    def __load_entries(self):
        self.clear()
        entries = get_logbook_entries()

        if not entries:
            self.show_empty()
            return

        for entry in entries:
            title = entry["timestamp"]
            subtitle = HOSTILE_COUNT.format(n=entry["hostile_count"])
            self.add_row(
                title=title,
                subtitle=subtitle,
                entry=entry,
                on_suffix_button_click=self.__on_delete_row,
            )

        self.show_list()

    def reload(self):
        """Clear existing rows and reload fresh data."""
        self.clear()
        self.__load_entries()

    def __on_row_activated(self, widget, row):
        entry = getattr(row, "entry", None)
        if entry:
            dialog = LogbookEntryDialog(
                entry, application=self.application, transient_for=self.window
            )
            dialog.present()

    def __on_delete_row(self, widget, row):
        entry = getattr(row, "entry", None)
        if entry:
            delete_logbook_entry(entry["id"])
            self.reload()
