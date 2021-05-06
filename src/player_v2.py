import ctypes
import os
import pathlib
import subprocess

import gi
import vlc
from PIL import Image, ImageFilter

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio

from base_player import BasePlayer


class VLCWidget(Gtk.DrawingArea):
    """
    Simple VLC widget.
    Its player can be controlled through the 'player' attribute, which
    is a vlc.MediaPlayer() instance.
    """
    __gtype_name__ = "VLCWidget"

    def __init__(self, width, height):
        # Spawn a VLC instance and create a new media player to embed.
        self.instance = vlc.Instance()
        Gtk.DrawingArea.__init__(self)
        self.player = self.instance.media_player_new()

        def handle_embed(*args):
            self.player.set_xwindow(self.get_window().get_xid())
            return True

        # Embed and set size.
        self.connect("realize", handle_embed)
        self.set_size_request(width, height)


class Player(BasePlayer):
    def __init__(self, config):
        super().__init__(config)

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

        # Static wallpaper
        self.gso = Gio.Settings.new("org.gnome.desktop.background")
        self.ori_wallpaper_uri = self.gso.get_string("picture-uri")
        self.new_wallpaper_uri = "/tmp/hidamari.png"

        self._is_playing = False
        self.start_all_monitors()

        # For some weird reason the context menu must be built here but not at the base class.
        # Otherwise it freezes your PC and you will need a reboot ¯\_(ツ)_/¯
        self.menu = self._build_context_menu()
        for child in self.menu.get_children():
            # Remove unsupported action
            if child.get_label() == "Reload":
                self.menu.remove(child)
        self.menu.show_all()

    @property
    def mode(self):
        return self.config["mode"]

    @mode.setter
    def mode(self, mode):
        self.config["mode"] = mode

    @property
    def volume(self):
        return self.config["audio_volume"]

    @volume.setter
    def volume(self, volume):
        self.config["audio_volume"] = volume
        for monitor in self.monitors:
            if monitor.is_primary:
                monitor.vlc_audio_set_volume(volume)

    @property
    def is_playing(self):
        return self._is_playing

    @property
    def data_source(self):
        return self.config["data_source"]

    @data_source.setter
    def data_source(self, data_source):
        self.config["data_source"] = data_source
        if self.mode == "video":
            for monitor in self.monitors:
                media = monitor.vlc_media_new(data_source)
                """
                This loops the media itself. Using -R / --repeat and/or -L / --loop don't seem to work. However,
                based on reading, this probably only repeats 65535 times, which is still a lot of time, but might
                cause the program to stop playback if it's left on for a very long time.
                """
                media.add_option("input-repeat=65535")
                # Prevent awful ear-rape with multiple instances.
                if not monitor.is_primary:
                    media.add_option("no-audio")
                monitor.vlc_set_media(media)
                monitor.vlc_set_position(0.0)
        elif self.mode == "stream":
            from ytl_wrapper import get_formats, get_best_audio, get_optimal_video
            formats = get_formats(data_source)
            max_height = max(self.monitors, key=lambda x: x.height).height
            video_url = get_optimal_video(formats, max_height)
            audio_url = get_best_audio(formats)

            for monitor in self.monitors:
                media = monitor.vlc_media_new(video_url)
                media.add_option("input-repeat=65535")
                monitor.vlc_set_media(media)
                if monitor.is_primary:
                    monitor.vlc_add_audio_track(audio_url)
                monitor.vlc_set_position(0.0)
        else:
            raise ValueError("Invalid mode")

        self.volume = self.config["audio_volume"]
        self.is_mute = self.config["mute_audio"]
        self.start_playback()

        if self.config["static_wallpaper"] and self.mode == "video":
            # TODO currently only support static wallpaper when mode=="video"
            self.set_static_wallpaper()
        else:
            self.restore_original_wallpaper()

    @property
    def is_mute(self):
        return self.config["mute_audio"]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config["mute_audio"] = is_mute
        for monitor in self.monitors:
            if monitor.is_primary:
                monitor.vlc_audio_set_volume(0) if is_mute else monitor.vlc_audio_set_volume(self.volume)

    def pause_playback(self):
        for monitor in self.monitors:
            monitor.vlc_pause()
            self._is_playing = False

    def start_playback(self):
        if not self.user_pause_playback:
            for monitor in self.monitors:
                monitor.vlc_play()
                self._is_playing = True

    def start_all_monitors(self):
        for monitor in self.monitors:
            if monitor.is_vlc_initialized:
                continue
            # Setup a VLC widget given the provided width and height.
            vlc_widget = VLCWidget(monitor.width, monitor.height)

            # These are to allow us to right click. VLC can't hijack mouse input, and probably not key inputs either in
            # Case we want to add keyboard shortcuts later on.
            vlc_widget.player.video_set_mouse_input(False)
            vlc_widget.player.video_set_key_input(False)

            # Window settings
            window = Gtk.Window()
            window.add(vlc_widget)
            window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
            window.set_size_request(monitor.width, monitor.height)
            window.move(monitor.x, monitor.y)

            # Button event
            window.connect("button-press-event", self._on_button_press_event)
            window.show_all()

            monitor.initialize(window, vlc_widget=vlc_widget)

        self.data_source = self.config["data_source"]

    def monitor_sync(self):
        primary = 0
        for i, monitor in enumerate(self.monitors):
            if monitor.is_primary:
                primary = i
                break
        for monitor in self.monitors:
            # `set_position()` method require the playback to be enabled before calling
            monitor.vlc_play()
            monitor.vlc_set_position(self.monitors[primary].vlc_get_position())
            monitor.vlc_play() if self.monitors[primary].vlc_is_playing() else monitor.vlc_pause()

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

    def _on_monitor_added(self, _, gdk_monitor, *args):
        super(Player, self)._on_monitor_added(_, gdk_monitor, *args)
        self.start_all_monitors()
        self.monitor_sync()

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer()
            for child in self.menu.get_children():
                if child.get_label() == "Mute Audio":
                    child.set_active(self.is_mute)
                if child.get_label() == "Pause Playback":
                    child.set_active(not self.is_playing)
        return True

    def release(self):
        self.restore_original_wallpaper()
        super(Player, self).release()
