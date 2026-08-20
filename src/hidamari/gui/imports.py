import gi
import logging
import sys

try:
    import os

    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    from commons import *
    from monitor import *
    from gui.gui_utils import get_thumbnail, debounce
    from utils import ConfigUtil, setup_autostart, is_gnome, is_wayland, get_video_paths
except ModuleNotFoundError:
    from hidamari.monitor import *
    from hidamari.commons import *
    from hidamari.gui.gui_utils import get_thumbnail, debounce
    from hidamari.utils import (
        ConfigUtil,
        setup_autostart,
        is_gnome,
        is_wayland,
        get_video_paths,
    )

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GdkPixbuf, Gdk

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(LOGGER_NAME)

APP_ID = f"{PROJECT}.gui"
APP_TITLE = "Hidamari"
APP_UI_RESOURCE_PATH = "/io/jeffshee/Hidamari/"