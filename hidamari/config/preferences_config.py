from hidamari.messages.messages import (
    SCAN_DIRECTORIES_RECURSIVELY,
    DETECT_POTENTIALLY_UNWANTED_APPLICATIONS,
    DETECT_SENSITIVE_DATA,
    SOCIAL_SECURITY_NUMBERS_AND_CREDIT_CARD_DETAILS,
    ENABLE_HEURISTIC_ALERTING,
    DELETE_LOGS_AUTOMATICALLY_ON_EXIT,
    UPDATE_MALWARE_DATABASE_AT_LAUNCH,
    RADAR,
    LOGBOOK,
    UPDATE,
)

"""
IMPORTANT:
- If you add, remove, or rename any keys in the schema below,
  make sure to update `DEFAULT_PREFERENCES` inside `stores_config.py` accordingly.
"""

# --- Groups ---

RADAR_SCAN_OPTIONS_GROUP = {
    "rows": [
        {
            "key": "clamscan.recursive",
            "title": SCAN_DIRECTORIES_RECURSIVELY,
            "mode": "switch",
        },
        {
            "key": "clamscan.detect_pua",
            "title": DETECT_POTENTIALLY_UNWANTED_APPLICATIONS,
            "mode": "switch",
        },
        {
            "key": "clamscan.detect_structured",
            "title": DETECT_SENSITIVE_DATA,
            "subtitle": SOCIAL_SECURITY_NUMBERS_AND_CREDIT_CARD_DETAILS,
            "mode": "switch",
        },
        {
            "key": "clamscan.heuristic_alerts",
            "title": ENABLE_HEURISTIC_ALERTING,
            "mode": "switch",
        },
    ],
}

LOGBOOK_SETTINGS_GROUP = {
    "rows": [
        {
            "key": "logbook.delete_on_exit",
            "title": DELETE_LOGS_AUTOMATICALLY_ON_EXIT,
            "mode": "switch",
        }
    ],
}

UPDATE_SETTINGS_GROUP = {
    "rows": [
        {
            "key": "freshclam.auto_update_on_start",
            "title": UPDATE_MALWARE_DATABASE_AT_LAUNCH,
            "mode": "switch",
        },
    ],
}

# --- Pages ---

RADAR_PAGE = {
    "title": RADAR,
    "icon": "find-location-symbolic",
    "groups": [
        RADAR_SCAN_OPTIONS_GROUP,
    ],
}

LOGBOOK_PAGE = {
    "title": LOGBOOK,
    "icon": "x-office-document-symbolic",
    "groups": [
        LOGBOOK_SETTINGS_GROUP,
    ],
}

UPDATE_PAGE = {
    "title": UPDATE,
    "icon": "view-refresh-symbolic",
    "groups": [
        UPDATE_SETTINGS_GROUP,
    ],
}

# --- Combined Structure ---

PREFERENCES_STRUCTURE = [
    RADAR_PAGE,
    LOGBOOK_PAGE,
    UPDATE_PAGE,
]
