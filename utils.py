import subprocess
import pathlib
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, Wnck, Gio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageFilter


class WindowHandler:
    def __init__(self, listener):
        self.listener = listener
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()
        self.screen.connect('window-opened', self.window_opened, None)
        self.screen.connect('window-closed', self.window_closed, None)
        self.screen.connect('active-workspace-changed', self.active_workspace_changed, None)
        for window in self.screen.get_windows():
            window.connect('state-changed', self.state_changed, None)

        # Initial check
        self.state_changed(None, None, None, None)

    def main(self):
        Gtk.main()

    def quit(self):
        Gtk.main_quit()

    def window_opened(self, screen, window, _):
        window.connect('state-changed', self.state_changed, None)

    def window_closed(self, screen, window, _):
        self.listener(self.check())

    def state_changed(self, window, changed_mask, new_state, _):
        self.listener(self.check())

    def active_workspace_changed(self, screen, previously_active_space, _):
        self.listener(self.check())

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


class FileModifiedHandler(FileSystemEventHandler):
    def __init__(self, path, file_name, callback):
        self.file_name = file_name
        self.callback = callback

        # set observer to watch for changes in the directory
        self.observer = Observer()
        self.observer.schedule(self, path, recursive=False)
        self.observer.start()

    def on_moved(self, event):
        if not event.is_directory and event.dest_path.endswith(self.file_name):
            self.callback()  # call callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(self.file_name):
            self.callback()  # call callback


class FolderModifiedHandler(FileSystemEventHandler):
    def __init__(self, path, callback):
        self.callback = callback

        # set observer to watch for changes in the directory
        self.observer = Observer()
        self.observer.schedule(self, path, recursive=False)
        self.observer.start()

    def on_any_event(self, event):
        self.callback()  # call callback


class StaticWallpaper:
    def __init__(self, rc=None):
        self.video_path = rc['video_path']
        self.enabled = rc['static_wallpaper']
        self.blur_radius = rc['static_wallpaper_blur_radius']
        self.gso = Gio.Settings.new('org.gnome.desktop.background')
        self.ori_wallpaper_uri = self.gso.get_string('picture-uri')
        self.new_wallpaper_uri = '/tmp/hidamari.png'

    def update_rc(self, rc):
        self.video_path = rc['video_path']
        self.blur_radius = rc['static_wallpaper_blur_radius']
        self.set_static_wallpaper()

    def set_static_wallpaper(self):
        # Extract first frame (use ffmpeg)
        if self.enabled:
            subprocess.call(
                'ffmpeg -y -i "{}" -vframes 1 "{}" -loglevel quiet > /dev/null 2>&1 < /dev/null'.format(
                    self.video_path, self.new_wallpaper_uri), shell=True)
            blur_wallpaper = Image.open(self.new_wallpaper_uri)
            blur_wallpaper = blur_wallpaper.filter(ImageFilter.GaussianBlur(self.blur_radius))
            blur_wallpaper.save(self.new_wallpaper_uri)
            self.gso.set_string('picture-uri', pathlib.Path(self.new_wallpaper_uri).resolve().as_uri())

    def restore_ori_wallpaper(self):
        self.gso.set_string('picture-uri', self.ori_wallpaper_uri)


if __name__ == "__main__":
    lister = WindowHandler(print)
    lister.main()
