from datetime import datetime
from gi.repository import Gtk, GLib, GObject
from .conditional_stack import ConditionalStack
from .progress_page import ProgressPage
from .scan_target_selector import ScanTargetSelector
from .scan_result_page import ScanResultPage
from .logbook_entry_dialog import LogbookEntryDialog
from .clamav import get_clamav_version, is_ready_to_scan
from .logbook_store import add_logbook_entry, get_logbook_entries


class Radar(Gtk.Box):
    __gsignals__ = {
        "hostile-contact": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, application, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.application = application
        self.window = window
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.__scan_start_time = None
        self.__last_clamav_version_info = None

        self.stack = ConditionalStack()

        # Create and add views
        self.scan_target_selector = ScanTargetSelector(self.window)
        self.scan_target_selector.connect("scan-start", self.__on_scan_start)
        self.scan_target_selector.connect("scan-finish", self.__on_scan_finish)

        self.progress_page = ProgressPage()

        self.scan_result_page = ScanResultPage()
        self.scan_result_page.connect_scan_another(self.__on_radar_ping)
        self.scan_result_page.connect_identify_threat(
            self.__on_scan_finish_identify_threat
        )
        self.scan_result_page.connect_recheck_readiness(self.__on_recheck_readiness)

        self.stack.add_view("scan_target_selector", self.scan_target_selector)
        self.stack.add_view("progress_page", self.progress_page)
        self.stack.add_view("scan_result_page", self.scan_result_page)

        self.append(self.stack)

        GLib.idle_add(self.__load_clamav_version_info)

    def __on_version_info_ready(self, version_info: dict):
        if is_ready_to_scan(version_info):
            self.__last_clamav_version_info = version_info
            self.stack.set_state("scan_target_selector")
        else:
            self.scan_result_page.set_condition(scan_possible=False)
            self.stack.set_state("scan_result_page")

    def __load_clamav_version_info(self):
        get_clamav_version(self.__on_version_info_ready)
        return False  # only run once

    def __on_recheck_readiness(self, widget):
        # Prevent repeated rapid clicks
        self.stack.set_state("progress_page")
        GLib.timeout_add_seconds(1, self.__load_clamav_version_info)

    def __on_radar_ping(self, widget):
        self.stack.set_state("scan_target_selector")

    def __on_scan_start(self, widget):
        self.__scan_start_time = datetime.now()
        self.stack.set_state("progress_page")

    def __on_scan_finish(
        self, widget, scan_success: bool, is_safe: bool, infections: list
    ):
        if not is_safe:
            duration = None
            if self.__scan_start_time:
                duration = (datetime.now() - self.__scan_start_time).total_seconds()

            add_logbook_entry(
                hostile_count=len(infections),
                hostile_list=infections,
                engine=self.__last_clamav_version_info["engine"],
                db_version=self.__last_clamav_version_info["db_version"],
                db_date=self.__last_clamav_version_info["db_date"],
                duration=duration,
            )

            # Refresh logbook to include fresh entry
            self.emit("hostile-contact")

        self.scan_result_page.set_condition(
            scan_possible=True, scan_success=scan_success, is_safe=is_safe
        )
        self.stack.set_state("scan_result_page")

    def __on_scan_finish_identify_threat(self, widget):
        last_logbook_entry = get_logbook_entries(limit=1)[0]
        dialog = LogbookEntryDialog(
            last_logbook_entry, application=self.application, transient_for=self.window
        )
        dialog.present()
