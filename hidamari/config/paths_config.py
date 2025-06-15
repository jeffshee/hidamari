import os
from gi.repository import GLib
from hidamari.config.app_config import NAMESPACE

BASE_RESOURCE_PATH = "/" + "/".join(NAMESPACE)
WIDGETS_RESOURCE_PATH = f"{BASE_RESOURCE_PATH}/widgets"
WINDOW_RESOURCE_PATH = f"{WIDGETS_RESOURCE_PATH}/window.ui"

USER_DATA_DIR = GLib.get_user_data_dir()

CLAMAV_EXECUTABLES = ("freshclam", "clamscan")
CLAMAV_DATABASE_DIR = os.path.join(USER_DATA_DIR, "clamav")
CLAMAV_FRESHCLAM_CONFIG_PATH = os.path.join(USER_DATA_DIR, "freshclam.conf")

LOGBOOK_DB_PATH = os.path.join(USER_DATA_DIR, "logbook.db")
PREFERENCES_PATH = os.path.join(USER_DATA_DIR, "preferences.ini")
