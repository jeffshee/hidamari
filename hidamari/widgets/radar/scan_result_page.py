from gi.repository import Gtk
from hidamari.widgets.base.base_status_page import BaseStatusPage
from hidamari.messages.messages import (
    SCAN_ANOTHER,
    IDENTIFY_THREAT,
    RECHECK_READINESS,
    CONDITION_GREEN,
    ALL_SYSTEMS_SECURE,
    HOSTILE_CONTACT,
    BATTLE_STATIONS,
    MISSION_ABORT,
    DAMAGE_CONTROL,
    NOT_COMBAT_READY,
    UPDATE_MALWARE_DEFINITIONS,
)


class ScanResultPage(BaseStatusPage):
    def __init__(self):
        super().__init__()

        self.scan_another_button = Gtk.Button(label=SCAN_ANOTHER)
        self.identify_threat_button = Gtk.Button(label=IDENTIFY_THREAT)
        self.recheck_readiness_button = Gtk.Button(label=RECHECK_READINESS)

    def set_condition(
        self,
        scan_possible: bool = False,
        scan_success: bool = False,
        is_safe: bool = False,
    ) -> None:
        self.clear_buttons()
        if scan_possible:
            self.add_button(self.scan_another_button, suggested=True)

            if scan_success:
                if is_safe:
                    self.set_status(
                        CONDITION_GREEN,
                        ALL_SYSTEMS_SECURE,
                        "face-cool-symbolic",
                    )
                else:
                    self.add_button(self.identify_threat_button, destructive=True)
                    self.set_status(
                        HOSTILE_CONTACT,
                        BATTLE_STATIONS,
                        "dialog-warning-symbolic",
                    )
            else:
                self.set_status(
                    MISSION_ABORT,
                    DAMAGE_CONTROL,
                    "computer-fail-symbolic",
                )
        else:
            self.add_button(self.recheck_readiness_button, suggested=True)
            self.set_status(
                NOT_COMBAT_READY,
                UPDATE_MALWARE_DEFINITIONS,
                "face-uncertain-symbolic",
            )

    def connect_scan_another(self, callback):
        self.scan_another_button.connect("clicked", callback)

    def connect_identify_threat(self, callback):
        self.identify_threat_button.connect("clicked", callback)

    def connect_recheck_readiness(self, callback):
        self.recheck_readiness_button.connect("clicked", callback)
