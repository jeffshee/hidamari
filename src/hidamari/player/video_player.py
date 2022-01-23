import ctypes
import logging
import pathlib
import subprocess
import sys
import tempfile
from threading import Timer

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, Gdk

from pydbus import SessionBus
import vlc
from PIL import Image, ImageFilter

from hidamari.player.base_player import BasePlayer
from hidamari.ui.menu import build_menu
from hidamari.commons import *
from hidamari.utils import ActiveHandler, is_gnome, is_wayland

logger = logging.getLogger(LOGGER_NAME)
if is_wayland():
    if is_gnome():
        from hidamari.utils import WindowHandlerGnome as WindowHandler
    else:
        # Dummy class as not currently supported.
        class WindowHandler:
            def __init__(self, _: callable):
                pass
elif is_gnome():
    from hidamari.utils import WindowHandlerGnome as WindowHandler
else:
    from hidamari.utils import WindowHandler


class Fade:
    def __init__(self):
        self.timer = None

    def start(self, cur, target, step, fade_interval, update_callback: callable = None,
              complete_callback: callable = None):
        new_cur = cur + step
        if (step < 0 and new_cur <= target) or (step > 0 and new_cur >= target):
            new_cur = target
            if update_callback:
                update_callback(int(new_cur))
            if complete_callback:
                complete_callback()
        else:
            if update_callback:
                update_callback(int(new_cur))
            self.timer = Timer(fade_interval, self.start,
                               args=[new_cur, target, step, fade_interval, update_callback, complete_callback])
            self.timer.start()

    def cancel(self):
        if self.timer:
            self.timer.cancel()


class VLCWidget(Gtk.DrawingArea):
    """
    Simple VLC widget.
    Its player can be controlled through the 'player' attribute, which
    is a vlc.MediaPlayer() instance.
    """
    __gtype_name__ = "VLCWidget"

    def __init__(self, width, height):
        Gtk.DrawingArea.__init__(self)

        # Spawn a VLC instance and create a new media player to embed.
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        def handle_embed(*args):
            self.player.set_xwindow(self.get_window().get_xid())
            return True

        # Embed and set size.
        self.connect("realize", handle_embed)
        self.set_size_request(width, height)


def build_dummy_menu():
    menu = Gtk.Menu()
    menu.append(Gtk.MenuItem(label="Hello"))
    menu.show_all()
    return menu


class PlayerWindow(Gtk.ApplicationWindow):
    def __init__(self, width, height, *args, **kwargs):
        super(PlayerWindow, self).__init__(*args, **kwargs)
        # Setup a VLC widget given the provided width and height.
        self.__vlc_widget = VLCWidget(width, height)
        self.add(self.__vlc_widget)
        self.__vlc_widget.show()

        # These are to allow us to right click. VLC can't hijack mouse input, and probably not key inputs either in
        # Case we want to add keyboard shortcuts later on.
        self.__vlc_widget.player.video_set_mouse_input(False)
        self.__vlc_widget.player.video_set_key_input(False)

        # A timer that handling fade-in/out
        self.fade = Fade()

        self.menu = None
        self.connect("button-press-event", self._on_button_press_event)

    def play(self):
        self.__vlc_widget.player.play()

    def play_fade(self, target, fade_duration_sec, fade_interval):
        self.play()
        cur = 0
        step = (target - cur) / (fade_duration_sec / fade_interval)
        self.fade.cancel()
        self.fade.start(cur=cur, target=target, step=step, fade_interval=fade_interval, update_callback=self.set_volume)

    def is_playing(self):
        return self.__vlc_widget.player.is_playing()

    def pause(self):
        if self.is_playing():
            self.__vlc_widget.player.pause()

    def pause_fade(self, fade_duration_sec, fade_interval):
        cur = self.get_volume()
        target = 0
        step = (target - cur) / (fade_duration_sec / fade_interval)
        self.fade.cancel()
        self.fade.start(cur=cur, target=target, step=step, fade_interval=fade_interval, update_callback=self.set_volume,
                        complete_callback=self.pause)

    def media_new(self, *args):
        return self.__vlc_widget.instance.media_new(*args)

    def set_media(self, *args):
        self.__vlc_widget.player.set_media(*args)

    def set_volume(self, *args):
        self.__vlc_widget.player.audio_set_volume(*args)

    def get_volume(self):
        return self.__vlc_widget.player.audio_get_volume()

    def set_mute(self, is_mute):
        return self.__vlc_widget.player.audio_set_mute(is_mute)

    def get_position(self):
        return self.__vlc_widget.player.get_position()

    def set_position(self, *args):
        self.__vlc_widget.player.set_position(*args)

    def snapshot(self, *args):
        return self.__vlc_widget.player.video_take_snapshot(*args)

    def add_audio_track(self, audio):
        self.__vlc_widget.player.add_slave(vlc.MediaSlaveType(1), audio, True)

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if not self.menu:
                self.menu = build_menu(MODE_VIDEO)
            self.menu.popup_at_pointer()
            return True
        return False


class VideoPlayer(BasePlayer):
    """
    <node>
    <interface name='io.github.jeffshee.hidamari.player'>
        <property name="mode" type="s" access="read"/>
        <property name="data_source" type="s" access="readwrite"/>
        <property name="volume" type="i" access="readwrite"/>
        <property name="is_mute" type="b" access="readwrite"/>
        <property name="is_playing" type="b" access="read"/>
        <property name="is_paused_by_user" type="b" access="readwrite"/>
        <method name='reload_config'/>
        <method name='pause_playback'/>
        <method name='start_playback'/>
        <method name='quit_player'/>
    </interface>
    </node>
    """

    def __init__(self, *args, **kwargs):
        super(VideoPlayer, self).__init__(*args, **kwargs)

        # We need to initialize X11 threads so we can use hardware decoding.
        # `libX11.so.6` fix for Fedora 33
        x11 = None
        for lib in ["libX11.so", "libX11.so.6"]:
            try:
                x11 = ctypes.cdll.LoadLibrary(lib)
            except OSError:
                pass
            if x11 is not None:
                x11.XInitThreads()
                break

        self.config = None
        self.reload_config()

        # Static wallpaper
        self.gso = Gio.Settings.new("org.gnome.desktop.background")
        self.ori_wallpaper_uri = self.gso.get_string("picture-uri")
        self.new_wallpaper_uri = os.path.join(tempfile.gettempdir(), "hidamari.png")

        # Handler should be created after everything initialized
        self.active_handler, self.window_handler = None, None
        self.is_any_maximized, self.is_any_fullscreen = False, False
        self.is_paused_by_user = False

    def new_window(self, gdk_monitor):
        rect = gdk_monitor.get_geometry()
        return PlayerWindow(rect.width, rect.height, application=self)

    def do_activate(self):
        super().do_activate()
        self.data_source = self.config[CONFIG_KEY_DATA_SOURCE]

    def _on_monitor_added(self, _, gdk_monitor, *args):
        super()._on_monitor_added(_, gdk_monitor, *args)
        self.monitor_sync()

    def _on_active_changed(self, active):
        if active:
            self.pause_playback()
        else:
            if self._should_playback_start():
                self.start_playback()
            else:
                self.pause_playback()

    def _on_window_state_changed(self, state):
        self.is_any_maximized, self.is_any_fullscreen = state["is_any_maximized"], state["is_any_fullscreen"]
        if self._should_playback_start():
            self.start_playback()
        else:
            self.pause_playback()

    def _should_playback_start(self):
        result = True
        if self.config[CONFIG_KEY_DETECT_MAXIMIZED] and self.is_any_maximized:
            result = False
        if self.is_any_fullscreen:
            result = False
        if self.is_paused_by_user:
            result = False
        return result

    @property
    def mode(self):
        return self.config[CONFIG_KEY_MODE]

    @property
    def data_source(self):
        return self.config[CONFIG_KEY_DATA_SOURCE]

    @data_source.setter
    def data_source(self, data_source):
        self.config[CONFIG_KEY_DATA_SOURCE] = data_source

        if self.mode == MODE_VIDEO:
            for monitor, window in self.windows.items():
                media = window.media_new(data_source)
                """
                This loops the media itself. Using -R / --repeat and/or -L / --loop don't seem to work. However,
                based on reading, this probably only repeats 65535 times, which is still a lot of time, but might
                cause the program to stop playback if it's left on for a very long time.
                """
                media.add_option("input-repeat=65535")
                # Prevent awful ear-rape with multiple instances.
                if not monitor.is_primary():
                    media.add_option("no-audio")
                window.set_media(media)
                window.set_position(0.0)

        elif self.mode == MODE_STREAM:
            from hidamari.ytl_wrapper import get_formats, get_best_audio, get_optimal_video
            formats = get_formats(data_source)
            max_height = max(self.windows, key=lambda m: m.get_geometry().height).get_geometry().height
            video_url = get_optimal_video(formats, max_height)
            audio_url = get_best_audio(formats)

            for monitor, window in self.windows.items():
                media = window.media_new(video_url)
                media.add_option("input-repeat=65535")
                window.set_media(media)
                if monitor.is_primary():
                    window.add_audio_track(audio_url)
                window.set_position(0.0)
        else:
            raise ValueError("Invalid mode")

        self.volume = self.config[CONFIG_KEY_VOLUME]
        self.is_mute = self.config[CONFIG_KEY_MUTE]
        self.start_playback()

        # Everything is initialized. Create handlers if haven't.
        if not self.active_handler:
            self.active_handler = ActiveHandler(self._on_active_changed)
        if not self.window_handler:
            self.window_handler = WindowHandler(self._on_window_state_changed)

        # TODO currently only support static wallpaper when mode==MODE_VIDEO
        if self.config[CONFIG_KEY_STATIC_WALLPAPER] and self.mode == MODE_VIDEO:
            self.set_static_wallpaper()
        else:
            self.restore_original_wallpaper()

    @property
    def volume(self):
        return self.config[CONFIG_KEY_VOLUME]

    @volume.setter
    def volume(self, volume):
        self.config[CONFIG_KEY_VOLUME] = volume
        for monitor in self.windows:
            if monitor.is_primary():
                self.windows[monitor].set_volume(volume)

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config[CONFIG_KEY_MUTE] = is_mute
        for monitor, window in self.windows.items():
            if monitor.is_primary():
                window.set_mute(is_mute)

    @property
    def is_playing(self):
        return not self.is_paused_by_user

    def pause_playback(self):
        for monitor, window in self.windows.items():
            window.pause_fade(fade_duration_sec=self.config[FADE_DURATION_SEC],
                              fade_interval=self.config[FADE_INTERVAL])

    def start_playback(self):
        # if not self.is_paused_by_user:
        if self._should_playback_start():
            for monitor, window in self.windows.items():
                window.play_fade(target=self.volume, fade_duration_sec=self.config[FADE_DURATION_SEC],
                                 fade_interval=self.config[FADE_INTERVAL])

    def monitor_sync(self):
        primary_monitor = None
        for monitor, window in self.windows.items():
            if monitor.is_primary:
                primary_monitor = monitor
                break
        if primary_monitor:
            for monitor, window in self.windows.items():
                if monitor == primary_monitor:
                    continue
                # `set_position()` method require the playback to be enabled before calling
                window.play()
                window.set_position(self.windows[primary_monitor].get_position())
                window.play() if self.windows[primary_monitor].is_playing() else window.pause()

    def set_static_wallpaper(self):
        subprocess.call(
            'ffmpeg -y -i "{}" -vframes 1 "{}" -loglevel quiet > /dev/null 2>&1 < /dev/null'.format(
                self.data_source, self.new_wallpaper_uri), shell=True)
        if os.path.isfile(self.new_wallpaper_uri):
            blur_wallpaper = Image.open(self.new_wallpaper_uri)
            blur_wallpaper = blur_wallpaper.filter(
                ImageFilter.GaussianBlur(self.config["static_wallpaper_blur_radius"]))
            blur_wallpaper.save(self.new_wallpaper_uri)
            self.gso.set_string("picture-uri", pathlib.Path(self.new_wallpaper_uri).resolve().as_uri())

    def restore_original_wallpaper(self):
        self.gso.set_string("picture-uri", self.ori_wallpaper_uri)
        if os.path.isfile(self.new_wallpaper_uri):
            os.remove(self.new_wallpaper_uri)

    def reload_config(self):
        from hidamari.utils import ConfigUtil
        self.config = ConfigUtil().load()

    def quit_player(self):
        self.restore_original_wallpaper()
        super().quit_player()


def main():
    bus = SessionBus()
    app = VideoPlayer()
    try:
        bus.publish(DBUS_NAME_PLAYER, app)
    except RuntimeError as e:
        logger.error(e)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
