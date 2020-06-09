import os
import json
import subprocess
import pathlib

import gi
import pydbus

gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import GLib, Wnck, Gio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageFilter

from types import SimpleNamespace

HOME = os.environ['HOME']
RC_FILENAME = '.hidamari-rc'
RC_PATH = HOME + '/' + RC_FILENAME
VIDEO_WALLPAPER_PATH = os.environ['HOME'] + '/Videos/Hidamari'


def create_dir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            pass


def scan_dir():
    file_list = []
    ext_list = ['m4v', 'mkv', 'mp4', 'mpg', 'mpeg', 'webm']
    for file in os.listdir(VIDEO_WALLPAPER_PATH):
        path = VIDEO_WALLPAPER_PATH + '/' + file
        if os.path.isfile(path) and path.split('.')[-1].lower() in ext_list:
            file_list.append(path)
    return file_list


class ActiveHandler:
    """
    Handler for monitoring screen lock
    """

    def __init__(self, on_active_changed: callable):
        session_bus = pydbus.SessionBus()
        screensaver_list = ['org.gnome.ScreenSaver',
                            'org.cinnamon.ScreenSaver',
                            'org.kde.screensaver',
                            'org.freedesktop.ScreenSaver']
        for s in screensaver_list:
            try:
                proxy = session_bus.get(s)
                proxy.ActiveChanged.connect(on_active_changed)
            except GLib.Error:
                pass


class WindowHandler:
    """
    Handler for monitoring window events (maximized and fullscreen mode)
    """

    def __init__(self, on_window_state_changed: callable):
        self.on_window_state_changed = on_window_state_changed
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()
        self.screen.connect('window-opened', self.window_opened, None)
        self.screen.connect('window-closed', self.window_closed, None)
        self.screen.connect('active-workspace-changed', self.active_workspace_changed, None)
        for window in self.screen.get_windows():
            window.connect('state-changed', self.state_changed, None)

        # Initial check
        self.state_changed(None, None, None, None)

    def window_opened(self, screen, window, _):
        window.connect('state-changed', self.state_changed, None)

    def window_closed(self, screen, window, _):
        self.on_window_state_changed(self.check())

    def state_changed(self, window, changed_mask, new_state, _):
        self.on_window_state_changed(self.check())

    def active_workspace_changed(self, screen, previously_active_space, _):
        self.on_window_state_changed(self.check())

    def check(self):
        is_any_maximized, is_any_fullscreen = False, False
        for window in self.screen.get_windows():
            base_state = not Wnck.Window.is_minimized(window) and \
                         Wnck.Window.is_on_workspace(window, self.screen.get_active_workspace())
            window_name, is_maximized, is_fullscreen = window.get_name(), \
                                                       Wnck.Window.is_maximized(window) and base_state, \
                                                       Wnck.Window.is_fullscreen(window) and base_state
            if is_maximized is True:
                is_any_maximized = True
            if is_fullscreen is True:
                is_any_fullscreen = True
        return {'is_any_maximized': is_any_maximized, 'is_any_fullscreen': is_any_fullscreen}


class StaticWallpaperHandler:
    """
    Handler for setting the static wallpaper
    """

    def __init__(self):
        self.rc_handler = RCHandler(self._on_rc_modified)
        self.rc = self.rc_handler.rc
        self.current_video_path = self.rc.video_path
        self.current_static_wallpaper = self.rc.static_wallpaper
        self.current_static_wallpaper_blur_radius = self.rc.static_wallpaper_blur_radius
        self.gso = Gio.Settings.new('org.gnome.desktop.background')
        self.ori_wallpaper_uri = self.gso.get_string('picture-uri')
        self.new_wallpaper_uri = '/tmp/hidamari.png'

    def _on_rc_modified(self):
        # Get new rc
        self.rc = self.rc_handler.rc
        if self.current_static_wallpaper != self.rc.static_wallpaper:
            if self.rc.static_wallpaper:
                self.set_static_wallpaper()
            else:
                self.restore_ori_wallpaper()
        elif ((self.current_video_path != self.rc.video_path or
               self.current_static_wallpaper_blur_radius != self.rc.static_wallpaper_blur_radius) and
              self.rc.static_wallpaper):
            self.set_static_wallpaper()
        self.current_video_path = self.rc.video_path
        self.current_static_wallpaper = self.rc.static_wallpaper
        self.current_static_wallpaper_blur_radius = self.rc.static_wallpaper_blur_radius

    def set_static_wallpaper(self):
        # Extract first frame (use ffmpeg)
        if self.rc.static_wallpaper:
            subprocess.call(
                'ffmpeg -y -i "{}" -vframes 1 "{}" -loglevel quiet > /dev/null 2>&1 < /dev/null'.format(
                    self.rc.video_path, self.new_wallpaper_uri), shell=True)
            if os.path.isfile(self.new_wallpaper_uri):
                blur_wallpaper = Image.open(self.new_wallpaper_uri)
                blur_wallpaper = blur_wallpaper.filter(ImageFilter.GaussianBlur(self.rc.static_wallpaper_blur_radius))
                blur_wallpaper.save(self.new_wallpaper_uri)
                self.gso.set_string('picture-uri', pathlib.Path(self.new_wallpaper_uri).resolve().as_uri())

    def restore_ori_wallpaper(self):
        self.gso.set_string('picture-uri', self.ori_wallpaper_uri)
        if os.path.isfile(self.new_wallpaper_uri):
            os.remove(self.new_wallpaper_uri)


class FileWatchdog(FileSystemEventHandler):
    def __init__(self, path, file_name, callback: callable):
        self.file_name = file_name
        self.callback = callback
        # Set observer to watch for changes in the directory
        self.observer = Observer()
        self.observer.schedule(self, path, recursive=False)
        self.observer.start()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_name):
            self.callback()  # call callback

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_name):
            self.callback()  # call callback

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.endswith(self.file_name):
            self.callback()  # call callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_name):
            self.callback()  # call callback


class RCHandler:
    """
    Handler for monitoring changes on configuration file (.hidamari-rc at home directory)
    """

    def __init__(self, on_rc_modified: callable):
        self.on_rc_modified = on_rc_modified
        self.template_rc = {
            'video_path': '',
            'mute_audio': False,
            'audio_volume': 0.5,
            'static_wallpaper': True,
            'static_wallpaper_blur_radius': 5,
            'detect_maximized': True,
        }
        self._update()
        FileWatchdog(path=HOME, file_name=RC_FILENAME, callback=self._rc_modified)

    def _generate_template_rc(self):
        with open(RC_PATH, 'w') as f:
            json.dump(self.template_rc, f)
        return self.template_rc

    def _update(self):
        self.rc = SimpleNamespace(**self._load())

    def _rc_modified(self):
        self._update()
        # print(vars(self.rc))
        self.on_rc_modified()

    def _check(self, rc: dict):
        return all(key in rc for key in self.template_rc)

    def _load(self):
        if os.path.isfile(RC_PATH):
            with open(RC_PATH, 'r') as f:
                rc = json.load(f)
                if self._check(rc):
                    return rc
        return self._generate_template_rc()

    def save(self):
        with open(RC_PATH, 'w') as f:
            json.dump(vars(self.rc), f)
