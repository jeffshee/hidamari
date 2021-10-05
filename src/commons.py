import os
import sys

DBUS_NAME = "io.github.jeffshee.hidamari"
APP_INDICATOR_ID = "io.github.jeffshee.hidamari"
ICON_NAME = "hidamari"
LOGGER_NAME = "hidamari"
HOME = os.environ["HOME"]
VIDEO_WALLPAPER_DIR = os.path.join(HOME, "Videos", "Hidamari")
CONFIG_DIR = os.path.join(HOME, ".config", "hidamari")
CONFIG_PATH = os.path.join(CONFIG_DIR, "hidamari.config")
AUTOSTART_DESKTOP_PATH = os.path.join(os.environ["HOME"], ".config", "autostart", "hidamari.desktop")
AUTOSTART_DESKTOP_CONTENT = \
    """
    [Desktop Entry]
    Type=Application
    Name=Hidamari
    Exec=hidamari --p 5
    StartupNotify=false
    Terminal=false
    Icon=hidamari
    Categories=System;Monitor;
    """
GUI_SCRIPT_PATH = os.path.join(sys.path[0], "gui.py")
GUI_GLADE_PATH = os.path.join(sys.path[0], "gui_v2.glade")
APPLICATION_ID = "io.github.jeffshee.hidamari.gui"

MODE_NULL = "MODE_NULL"
MODE_VIDEO = "MODE_VIDEO"
MODE_STREAM = "MODE_STREAM"
MODE_WEBPAGE = "MODE_WEBPAGE"

CONFIG_VERSION = 2
CONFIG_KEY_VERSION = "version"
CONFIG_KEY_MODE = "mode"
CONFIG_KEY_DATA_SOURCE = "data_source"
CONFIG_KEY_MUTE = "is_mute"
CONFIG_KEY_VOLUME = "audio_volume"
CONFIG_KEY_STATIC_WALLPAPER = "is_static_wallpaper"
CONFIG_KEY_BLUR_RADIUS = "static_wallpaper_blur_radius"
CONFIG_KEY_DETECT_MAXIMIZED = "is_detect_maximized"
CONFIG_TEMPLATE = {
    CONFIG_KEY_VERSION: CONFIG_VERSION,
    CONFIG_KEY_MODE: None,
    CONFIG_KEY_DATA_SOURCE: None,
    CONFIG_KEY_MUTE: False,
    CONFIG_KEY_VOLUME: 50,
    CONFIG_KEY_STATIC_WALLPAPER: True,
    CONFIG_KEY_BLUR_RADIUS: 5,
    CONFIG_KEY_DETECT_MAXIMIZED: True
}
