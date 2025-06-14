from .i18n import _

# config/preferences_config.py
SCAN_DIRECTORIES_RECURSIVELY = _("Scan directories recursively")
DETECT_POTENTIALLY_UNWANTED_APPLICATIONS = _("Detect potentially unwanted applications")
DETECT_SENSITIVE_DATA = _("Detect sensitive data")
SOCIAL_SECURITY_NUMBERS_AND_CREDIT_CARD_DETAILS = _(
    "Social Security Numbers and credit card details"
)
ENABLE_HEURISTIC_ALERTING = _("Enable heuristic alerting")
DELETE_LOGS_AUTOMATICALLY_ON_EXIT = _("Delete logs automatically on exit")
UPDATE_MALWARE_DATABASE_AT_LAUNCH = _("Update malware database at launch")

# config/shortcuts_config.py
QUIT = _("Quit")
PREFERENCES = _("Preferences")
ABOUT = _("About")
SHOW_SHORTCUTS = _("Show Shortcuts")
GENERAL = _("General")

# config/ui_config.py
KAPITANO = _("Kapitano")
STAY_SAFE_FROM_MALWARE = _("Stay safe from malware")
COMMUNITY_CONTRIBUTORS = _("Community Contributors")
MAIN_MENU = _("Main Menu")
KEYBOARD_SHORTCUTS = _("Keyboard Shortcuts")
ABOUT_KAPITANO = _("About Kapitano")

# utils/clamav.py
NO_FILES_AVAILABLE_FOR_SCANNING = _("No files available for scanning.")
UNKNOWN = _("Unknown")

# utils/process.py
ERROR = _("Error")
NO_COMMAND_PROVIDED = _("No command provided.")
ACTION_NOT_PERMITTED = _("This action is not permitted.")
OUTPUT_IS_BINARY = _("The output is binary.")

# utils/ui_helpers.py
HOSTILES = _("Hostiles")
REPORT = _("Report")
DATE = _("Date")
HOSTILES_DETECTED = _("Hostiles Detected")
DURATION = _("Duration")
ENGINE = _("Engine")

# widgets/base/base_list_view.py
NO_ITEMS_FOUND = _("No items found")
NO_ENTRIES_TO_SHOW = _("There are no entries to show.")
DELETE = _("Delete")

# widgets/logbook/logbook.py
ALL_CLEAR = _("All Clear")
NO_HOSTILES_LOGGED_DURING_OPERATION = _("No hostiles logged during operation.")
HOSTILE_COUNT = _("{n} hostile(s)")

# widgets/radar/scan_result_page.py
SCAN_ANOTHER = _("Scan Another")
IDENTIFY_THREAT = _("Identify Threat")
RECHECK_READINESS = _("Recheck Readiness")
CONDITION_GREEN = _("Condition Green")
ALL_SYSTEMS_SECURE = _("All systems secure!")
HOSTILE_CONTACT = _("Hostile Contact")
BATTLE_STATIONS = _("Battle stations, prepare to engage!")
MISSION_ABORT = _("Mission Abort")
DAMAGE_CONTROL = _("Red alert! Damage control teams, report!")
NOT_COMBAT_READY = _("Not Combat-Ready")
UPDATE_MALWARE_DEFINITIONS = _("Update malware definitions before scanning.")

# widgets/radar/scan_target_selector.py
AWAITING_ORDERS = _("Awaiting Orders")
DESIGNATE_TARGETS_TO_INITIATE_SCAN = _("Designate targets to initiate scan.")
SELECT_FILES = _("Select Files")
SELECT_FOLDERS = _("Select Folders")

# widgets/update/update.py
CHECK_FOR_UPDATES = _("Check for Updates")
LOGISTICS_FAILURE = _("Logistics Failure")
UNABLE_TO_REFRESH_DEFINITIONS = _("Unable to refresh malware definitions!")

# widgets/window.py
RADAR = _("Radar")
LOGBOOK = _("Logbook")
UPDATE = _("Update")
