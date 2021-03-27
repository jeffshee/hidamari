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
from time import sleep
from types import SimpleNamespace

HOME = os.environ['HOME']
CONFIG_DIR = HOME + '/.config/hidamari'
CONFIG_PATH = CONFIG_DIR + '/hidamari.config'
VIDEO_WALLPAPER_DIR = HOME + '/Videos/Hidamari'
SESSION_TYPE = os.environ.get("XDG_SESSION_TYPE")


def create_dir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            pass


def scan_dir():
    file_list = []
    ext_list = ['m4v', 'mkv', 'mp4', 'mpg', 'mpeg', 'webm']
    for file in os.listdir(VIDEO_WALLPAPER_DIR):
        path = VIDEO_WALLPAPER_DIR + '/' + file
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

        workspace = None

        if SESSION_TYPE == "wayland":
            try:
                workspace = self.screen.get_workspace(
                    int(subprocess.getoutput("xprop -root -notype _NET_CURRENT_DESKTOP").split(" = ")[-1])
                )
            except ValueError:
                """
                _NET_CURRENT_DESKTOP is not defined until the user actually switches to another workspace. So we can
                assume that if the value isn't defined, we are on the first. I'm not sure if this is accurate, does
                the value become undefined after resuming from hibernation on another workspace?
                """
                workspace = self.screen.get_workspace(0)

        else:
            workspace = self.screen.get_active_workspace()

        is_any_maximized, is_any_fullscreen = False, False
        for window in self.screen.get_windows():
            base_state = not Wnck.Window.is_minimized(window) and Wnck.Window.is_on_workspace(window, workspace)
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
        self.config_handler = ConfigHandler(self._on_config_modified)
        self.config = self.config_handler.config
        self.current_video_path = self.config.video_path
        self.current_static_wallpaper = self.config.static_wallpaper
        self.current_static_wallpaper_blur_radius = self.config.static_wallpaper_blur_radius
        self.gso = Gio.Settings.new('org.gnome.desktop.background')
        self.ori_wallpaper_uri = self.gso.get_string('picture-uri')
        self.new_wallpaper_uri = '/tmp/hidamari.png'

    def _on_config_modified(self):
        # Get new config
        self.config = self.config_handler.config
        if self.current_static_wallpaper != self.config.static_wallpaper:
            if self.config.static_wallpaper:
                self.set_static_wallpaper()
            else:
                self.restore_ori_wallpaper()
        elif ((self.current_video_path != self.config.video_path or
               self.current_static_wallpaper_blur_radius != self.config.static_wallpaper_blur_radius) and
              self.config.static_wallpaper):
            self.set_static_wallpaper()
        self.current_video_path = self.config.video_path
        self.current_static_wallpaper = self.config.static_wallpaper
        self.current_static_wallpaper_blur_radius = self.config.static_wallpaper_blur_radius

    def set_static_wallpaper(self):
        # Extract first frame (use ffmpeg)
        if self.config.static_wallpaper:
            subprocess.call(
                'ffmpeg -y -i "{}" -vframes 1 "{}" -loglevel quiet > /dev/null 2>&1 < /dev/null'.format(
                    self.config.video_path, self.new_wallpaper_uri), shell=True)
            if os.path.isfile(self.new_wallpaper_uri):
                blur_wallpaper = Image.open(self.new_wallpaper_uri)
                blur_wallpaper = blur_wallpaper.filter(
                    ImageFilter.GaussianBlur(self.config.static_wallpaper_blur_radius))
                blur_wallpaper.save(self.new_wallpaper_uri)
                self.gso.set_string('picture-uri', pathlib.Path(self.new_wallpaper_uri).resolve().as_uri())

    def restore_ori_wallpaper(self):
        self.gso.set_string('picture-uri', self.ori_wallpaper_uri)
        if os.path.isfile(self.new_wallpaper_uri):
            os.remove(self.new_wallpaper_uri)


class FileWatchdog(FileSystemEventHandler):
    def __init__(self, filepath, callback: callable):
        self.file_name = os.path.basename(filepath)
        self.callback = callback
        self.observer = Observer()
        self.observer.schedule(self, os.path.dirname(filepath), recursive=False)
        self.observer.start()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_name):
            print('Watchdog:', event)
            self.callback()  # call callback

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_name):
            print('Watchdog:', event)
            self.callback()  # call callback

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.endswith(self.file_name):
            print('Watchdog:', event)
            self.callback()  # call callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_name):
            print('Watchdog:', event)
            self.callback()  # call callback


# class FileWatchdog:
#     # NOTE: Pyinotify didn't quit well
#     def __init__(self, filepath, callback: callable):
#         import pyinotify
#         self.filepath = filepath
#         self.callback = callback
#         wm = pyinotify.WatchManager()
#         wm.add_watch(os.path.dirname(filepath), pyinotify.IN_MOVED_TO | pyinotify.IN_MODIFY, self.on_modified)
#         self.notifier = pyinotify.ThreadedNotifier(wm)
#
#     def on_modified(self, event):
#         if event.pathname == self.filepath:
#             print('Pyinotify:', event)
#             self.callback()
#
#     def start(self):
#         self.notifier.start()
#
#     def stop(self):
#         self.notifier.stop()


class ConfigHandler:
    """
    Handler for monitoring changes on configuration file
    """

    def __init__(self, on_config_modified: callable):
        self.on_config_modified = on_config_modified
        self.template_config = {
            'video_path': '',
            'mute_audio': False,
            'audio_volume': 0.5,
            'static_wallpaper': True,
            'static_wallpaper_blur_radius': 5,
            'detect_maximized': True,
        }
        self._update()
        FileWatchdog(filepath=CONFIG_PATH, callback=self._config_modified)

    def _generate_template_config(self):
        create_dir(CONFIG_DIR)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.template_config, f)
        return self.template_config

    def _update(self):
        status, config = self._load()
        if status:
            self.config = SimpleNamespace(**config)

    def _config_modified(self):
        self._update()
        self.on_config_modified()

    def _check(self, config: dict):
        return all(key in config for key in self.template_config)

    def _load(self):
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                json_str = f.read()
                try:
                    config = json.loads(json_str)
                    print('JSON:', json_str)
                    return self._check(config), config
                except json.decoder.JSONDecodeError:
                    print('JSONDecodeError:', json_str)
                    return False, None
        return True, self._generate_template_config()

    def save(self):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(vars(self.config), f)
