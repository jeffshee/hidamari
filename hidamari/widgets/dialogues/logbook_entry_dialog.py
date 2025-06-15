from hidamari.utils.ui_helpers import get_logbook_structure
from hidamari.widgets.base.preferences_window import PreferencesWindow


class LogbookEntryDialog(PreferencesWindow):
    __gtype_name__ = "LogbookEntryDialog"

    def __init__(self, log_entry, **kwargs):
        structure = get_logbook_structure(log_entry)
        super().__init__(structure=structure, **kwargs)
