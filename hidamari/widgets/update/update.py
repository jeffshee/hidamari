from gi.repository import Gtk, GLib, GObject
from hidamari.widgets.base.conditional_stack import ConditionalStack
from hidamari.widgets.base.base_status_page import BaseStatusPage
from hidamari.widgets.base.progress_page import ProgressPage
from hidamari.utils.clamav import get_clamav_version, update_malware_definitions
from hidamari.messages.messages import (
    CHECK_FOR_UPDATES,
    UNKNOWN,
    LOGISTICS_FAILURE,
    UNABLE_TO_REFRESH_DEFINITIONS,
)


class Update(Gtk.Box):
    __gtype_name__ = "Update"
    __gsignals__ = {
        "auto-update-success": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, auto_update_mode):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.__auto_update_mode = auto_update_mode

        self.stack = ConditionalStack()
        self.append(self.stack)

        self.__create_status_view()
        self.__create_progress_view()

        if self.__auto_update_mode:
            self.__start_update()
        else:
            self.stack.set_state("status")
            GLib.idle_add(self.__load_clamav_version_info)

    def __create_status_view(self):
        self.status_page = BaseStatusPage()

        self.update_button = Gtk.Button(label=CHECK_FOR_UPDATES)
        self.update_button.connect("clicked", self.__on_update_button_clicked)
        self.status_page.add_button(self.update_button, suggested=True)

        self.stack.add_view("status", self.status_page)

    def __create_progress_view(self):
        self.progress_page = ProgressPage()
        self.stack.add_view("progress", self.progress_page)

    def __on_version_info_ready(self, version_info: dict):
        db_date = version_info["db_date"]
        is_db_ready = db_date != UNKNOWN

        self.status_page.set_status(
            version_info["engine"],
            db_date if is_db_ready else "",
            "security-high-symbolic" if is_db_ready else "security-low-symbolic",
        )

    def __load_clamav_version_info(self):
        get_clamav_version(self.__on_version_info_ready)
        return False  # only run once

    def __start_update(self):
        self.stack.set_state("progress")
        update_malware_definitions(self.__on_update_finished)

    def __on_update_button_clicked(self, button):
        self.__start_update()

    def __on_update_finished(self, success: bool, message: str):
        self.stack.set_state("status")

        if success:
            self.__load_clamav_version_info()
            if self.__auto_update_mode:
                self.emit("auto-update-success")
        else:
            self.status_page.set_status(
                LOGISTICS_FAILURE,
                UNABLE_TO_REFRESH_DEFINITIONS,
                "face-sick-symbolic",
            )
