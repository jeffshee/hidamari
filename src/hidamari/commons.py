import os
import subprocess

LOGGER_NAME = "Hidamari"

PROJECT = "io.jeffshee.Hidamari"
DBUS_NAME_SERVER = f"{PROJECT}.server"
DBUS_NAME_PLAYER = f"{PROJECT}.player"

HOME = os.environ["HOME"]
try:
    xdg_video_dir = subprocess.run(["xdg-user-dir", "VIDEOS"], stdout=subprocess.PIPE)\
        .stdout.decode('utf-8').replace("\n", "")
    VIDEO_WALLPAPER_DIR = os.path.join(xdg_video_dir, "Hidamari")
except FileNotFoundError:
    # xdg-user-dir not found, use $HOME/Hidamari for Video directory instead
    VIDEO_WALLPAPER_DIR = os.path.join(HOME, "Hidamari")

AUTOSTART_DESKTOP_PATH = os.path.join(HOME, ".config", "autostart", "hidamari.desktop")

CONFIG_DIR = os.path.join(HOME, ".config", "hidamari")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

MODE_VIDEO = "MODE_VIDEO"
MODE_STREAM = "MODE_STREAM"
MODE_WEBPAGE = "MODE_WEBPAGE"

CONFIG_VERSION = 3
CONFIG_KEY_VERSION = "version"
CONFIG_KEY_MODE = "mode"
CONFIG_KEY_DATA_SOURCE = "data_source"
CONFIG_KEY_MUTE = "is_mute"
CONFIG_KEY_VOLUME = "audio_volume"
CONFIG_KEY_STATIC_WALLPAPER = "is_static_wallpaper"
CONFIG_KEY_BLUR_RADIUS = "static_wallpaper_blur_radius"
CONFIG_KEY_DETECT_MAXIMIZED = "is_detect_maximized"
FADE_DURATION_SEC = "fade_duration_sec"
FADE_INTERVAL = "fade_interval"
CONFIG_TEMPLATE = {
    CONFIG_KEY_VERSION: CONFIG_VERSION,
    CONFIG_KEY_MODE: MODE_VIDEO,
    CONFIG_KEY_DATA_SOURCE: "",
    CONFIG_KEY_MUTE: False,
    CONFIG_KEY_VOLUME: 50,
    CONFIG_KEY_STATIC_WALLPAPER: True,
    CONFIG_KEY_BLUR_RADIUS: 5,
    CONFIG_KEY_DETECT_MAXIMIZED: True,
    FADE_DURATION_SEC: 1.5,
    FADE_INTERVAL: 0.1,
}
