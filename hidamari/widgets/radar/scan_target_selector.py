from gi.repository import Gtk, Gdk, Gio, GLib, GObject
from hidamari.widgets.base.base_status_page import BaseStatusPage
from hidamari.utils.clamav import scan_for_malware, extract_infections_from_scan_result
from hidamari.messages.messages import (
    AWAITING_ORDERS,
    DESIGNATE_TARGETS_TO_INITIATE_SCAN,
    SELECT_FILES,
    SELECT_FOLDERS,
)


class ScanTargetSelector(BaseStatusPage):
    __gsignals__ = {
        "scan-start": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "scan-finish": (GObject.SIGNAL_RUN_FIRST, None, (bool, bool, object)),
    }

    def __init__(self, window):
        super().__init__()
        self.window = window

        self.set_status(
            AWAITING_ORDERS,
            DESIGNATE_TARGETS_TO_INITIATE_SCAN,
            "folder-new-symbolic",
        )

        self.select_files_button = Gtk.Button(label=SELECT_FILES)
        self.select_folders_button = Gtk.Button(label=SELECT_FOLDERS)

        self.select_files_button.connect(
            "clicked", lambda btn: self.open_selector(target_type="files")
        )
        self.select_folders_button.connect(
            "clicked", lambda btn: self.open_selector(target_type="folders")
        )

        self.add_button(self.select_files_button)
        self.add_button(self.select_folders_button)

    def assess_infection_risk(self, scan_success: bool, message: str):
        infections = []

        if scan_success:
            infections = extract_infections_from_scan_result(message)

        is_safe = not bool(infections)
        self.emit("scan-finish", scan_success, is_safe, infections)

    def open_selector(self, target_type: str):
        def on_selection_complete(dialog, result):
            try:
                if target_type == "files":
                    targets = dialog.open_multiple_finish(result)
                elif target_type == "folders":
                    targets = dialog.select_multiple_folders_finish(result)
                else:
                    targets = []

                if targets:
                    self.emit("scan-start")

                    scan_paths = [target.get_path() for target in targets]
                    scan_for_malware(
                        scan_paths,
                        lambda scan_success, message: self.assess_infection_risk(
                            scan_success, message
                        ),
                    )
            except GLib.Error as e:
                pass

        dialog = Gtk.FileDialog()

        if target_type == "files":
            dialog.open_multiple(self.window, None, on_selection_complete)
        elif target_type == "folders":
            dialog.select_multiple_folders(self.window, None, on_selection_complete)
