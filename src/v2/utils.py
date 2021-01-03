import os
import pathlib
import subprocess

import gi
import pydbus

gi.require_version("Gtk", "3.0")
gi.require_version("Wnck", "3.0")
from gi.repository import GLib, Wnck, Gio
from PIL import Image, ImageFilter

HOME = os.environ["HOME"]
CONFIG_DIR = HOME + "/.config/hidamari"
CONFIG_PATH = CONFIG_DIR + "/hidamari.config"
VIDEO_WALLPAPER_DIR = HOME + "/Videos/Hidamari"


# class ActiveHandler:
#     """
#     Handler for monitoring screen lock
#     """
#
#     def __init__(self, on_active_changed: callable):
#         session_bus = pydbus.SessionBus()
#         screensaver_list = ["org.gnome.ScreenSaver",
#                             "org.cinnamon.ScreenSaver",
#                             "org.kde.screensaver",
#                             "org.freedesktop.ScreenSaver"]
#         for s in screensaver_list:
#             try:
#                 proxy = session_bus.get(s)
#                 proxy.ActiveChanged.connect(on_active_changed)
#             except GLib.Error:
#                 pass
#
#
# class WindowHandler:
#     """
#     Handler for monitoring window events (maximized and fullscreen mode)
#     """
#
#     def __init__(self, on_window_state_changed: callable):
#         self.on_window_state_changed = on_window_state_changed
#         self.screen = Wnck.Screen.get_default()
#         self.screen.force_update()
#         self.screen.connect("window-opened", self.window_opened, None)
#         self.screen.connect("window-closed", self.window_closed, None)
#         self.screen.connect("active-workspace-changed", self.active_workspace_changed, None)
#         for window in self.screen.get_windows():
#             window.connect("state-changed", self.state_changed, None)
#
#         # Initial check
#         self.state_changed(None, None, None, None)
#
#     def window_opened(self, screen, window, _):
#         window.connect("state-changed", self.state_changed, None)
#
#     def window_closed(self, screen, window, _):
#         self.on_window_state_changed(self.check())
#
#     def state_changed(self, window, changed_mask, new_state, _):
#         self.on_window_state_changed(self.check())
#
#     def active_workspace_changed(self, screen, previously_active_space, _):
#         self.on_window_state_changed(self.check())
#
#     def check(self):
#         is_any_maximized, is_any_fullscreen = False, False
#         for window in self.screen.get_windows():
#             base_state = not Wnck.Window.is_minimized(window) and \
#                          Wnck.Window.is_on_workspace(window, self.screen.get_active_workspace())
#             window_name, is_maximized, is_fullscreen = window.get_name(), \
#                                                        Wnck.Window.is_maximized(window) and base_state, \
#                                                        Wnck.Window.is_fullscreen(window) and base_state
#             if is_maximized is True:
#                 is_any_maximized = True
#             if is_fullscreen is True:
#                 is_any_fullscreen = True
#         return {"is_any_maximized": is_any_maximized, "is_any_fullscreen": is_any_fullscreen}


class StaticWallpaperHandler:
    """
    Handler for setting the static wallpaper
    """

    def __init__(self):
        self.gso = Gio.Settings.new("org.gnome.desktop.background")
        self.original_wallpaper_uri = self.gso.get_string("picture-uri")
        self.static_wallpaper_uri = "/tmp/hidamari.png"

    def set_static_wallpaper(self, video_path, blur_radius):
        # Extract first frame (use ffmpeg)
        subprocess.call(
            "ffmpeg -y -i '{}' -vframes 1 '{}' -loglevel quiet > /dev/null 2>&1 < /dev/null".format(
                video_path, self.static_wallpaper_uri), shell=True)
        if os.path.isfile(self.static_wallpaper_uri):
            blur_wallpaper = Image.open(self.static_wallpaper_uri)
            blur_wallpaper = blur_wallpaper.filter(
                ImageFilter.GaussianBlur(blur_radius))
            blur_wallpaper.save(self.static_wallpaper_uri)
            self.gso.set_string("picture-uri", pathlib.Path(self.static_wallpaper_uri).resolve().as_uri())

    def set_original_wallpaper(self):
        self.gso.set_string("picture-uri", self.original_wallpaper_uri)
        if os.path.isfile(self.static_wallpaper_uri):
            os.remove(self.static_wallpaper_uri)
