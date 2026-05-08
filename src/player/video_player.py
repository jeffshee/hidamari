import gc
import sys
import glob
import time
import random
import ctypes
import logging
import pathlib
import subprocess
import threading
from collections import deque
from threading import Timer

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, Gdk, GLib

import vlc
from pydbus import SessionBus
from PIL import Image, ImageFilter

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], '..'))
    from player.base_player import BasePlayer
    from menu import build_menu
    from commons import *
    from utils import (
        ActiveHandler,
        ConfigUtil,
        build_playlist_media_info,
        is_flatpak,
        is_gnome,
        is_nvidia_proprietary,
        is_vdpau_ok,
        is_wayland,
        mark_playlist_media_info_stalled,
        normalize_playlist_media_info,
    )
    from yt_utils import get_formats, get_best_audio, get_optimal_video
except ModuleNotFoundError:
    from hidamari.player.base_player import BasePlayer
    from hidamari.menu import build_menu
    from hidamari.commons import *
    from hidamari.utils import (
        ActiveHandler,
        ConfigUtil,
        build_playlist_media_info,
        is_flatpak,
        is_gnome,
        is_nvidia_proprietary,
        is_vdpau_ok,
        is_wayland,
        mark_playlist_media_info_stalled,
        normalize_playlist_media_info,
    )
    from hidamari.yt_utils import get_formats, get_best_audio, get_optimal_video

logger = logging.getLogger(LOGGER_NAME)

# Proactive soft-restart: every N playlist transitions we recreate the libVLC
# Instance (instead of just swapping the media). Keeps the decoder "breathing"
# during long sessions and avoids silent state accumulation.
PLAYLIST_SOFT_RESTART_EVERY = 25

# Circuit breaker for the recovery path: if within a window of N seconds the
# player performs M or more recoveries, the current video is marked as
# problematic and the playlist advances instead of trying to recover again.
PLAYLIST_RECOVERY_WINDOW_SEC = 60.0
PLAYLIST_RECOVERY_MAX_IN_WINDOW = 3

# Brief synchronous pause (in seconds) between releasing the old Instance and
# creating the new one in recover_vlc_widget. Gives libVLC time to free the
# decoder before bringing up a new Instance on the same widget.
PLAYLIST_RECOVERY_SLEEP_SEC = 0.25

if is_wayland():
    # TODO: Window event monitoring for GNOME Wayland is broken
    class WindowHandler:
        def __init__(self, _: callable):
            pass
else:
    try:
        from utils import WindowHandler
    except ModuleNotFoundError:
        from hidamari.utils import WindowHandler


class Fade:
    def __init__(self):
        self.timer = None
        self.is_active = False
        self._cycle_id = 0

    def start(self, cur, target, step, fade_interval, update_callback: callable = None,
              complete_callback: callable = None):
        self.cancel()
        self._cycle_id += 1
        cycle = self._cycle_id
        self.is_active = True
        self._fade_step(cycle, cur, target, step, fade_interval, update_callback, complete_callback)

    def _fade_step(self, cycle, cur, target, step, fade_interval, update_callback, complete_callback):
        if not self.is_active or cycle != self._cycle_id:
            if cycle != self._cycle_id:
                logger.debug(f"[Fade] Stale cycle {cycle} ignored (current={self._cycle_id})")
            return
            
        new_cur = cur + step
        if (step < 0 and new_cur <= target) or (step > 0 and new_cur >= target):
            new_cur = target
            if update_callback:
                update_callback(int(new_cur))
            if complete_callback:
                complete_callback()
            self.is_active = False
        else:
            if update_callback:
                update_callback(int(new_cur))
            self.timer = Timer(fade_interval, self._fade_step,
                               args=[cycle, new_cur, target, step, fade_interval, update_callback, complete_callback])
            self.timer.daemon = True
            self.timer.start()

    def cancel(self):
        self.is_active = False
        if self.timer:
            self.timer.cancel()
            self.timer = None


class VLCWidget(Gtk.DrawingArea):
    """
    Simple VLC widget.
    Its player can be controlled through the 'player' attribute, which
    is a vlc.MediaPlayer() instance.
    """
    __gtype_name__ = "VLCWidget"

    def __init__(self, width, height, disable_audio: bool = False):
        Gtk.DrawingArea.__init__(self)

        # Spawn a VLC instance and create a new media player to embed.
        # Some options need to be specified when instantiating VLC.
        # --no-disable-screensaver: Allow screensaver.
        vlc_options = ["--no-disable-screensaver"]
        if disable_audio:
            # Fully disable libVLC's audio subsystem, preventing the
            # PipeWire/PulseAudio module from being loaded. Used in playlist
            # mode to avoid PipeWire crashes during transitions.
            vlc_options += ["--no-audio", "--aout=none"]
        self.instance = vlc.Instance(vlc_options)
        self.player = self.instance.media_player_new()

        def handle_embed(*args):
            self.player.set_xwindow(self.get_window().get_xid())
            return True

        # Embed and set size.
        self.connect("realize", handle_embed)
        self.set_size_request(width, height)

    def cleanup(self):
        """Cleanup VLC resources to prevent memory leaks"""
        player = self.player
        instance = self.instance
        self.player = None
        self.instance = None

        try:
            if player:
                media = player.get_media()
                if media is not None:
                    media.release()
                player.release()
            if instance:
                instance.release()
        except Exception as e:
            logger.warning(f"[VLCWidget] Cleanup error: {e}")


class PlayerWindow(Gtk.ApplicationWindow):
    def __init__(self, name, width, height, *args, disable_audio: bool = False, **kwargs):
        super(PlayerWindow, self).__init__(*args, **kwargs)
        # Setup a VLC widget given the provided width and height.
        self.width = width
        self.height = height
        self.name = name
        self._disable_audio = disable_audio
        self.__vlc_widget = None
        self._create_vlc_widget()

        # A timer that handling fade-in/out
        self.fade = Fade()
        self.fade_opacity = Fade()

        self._pending_crop = None
        self._crop_retries = 0
        self._crop_max_retries = 10

        self.menu = None
        self.connect("button-press-event", self._on_button_press_event)

    def _create_vlc_widget(self):
        self.__vlc_widget = VLCWidget(self.width, self.height, disable_audio=self._disable_audio)
        self.add(self.__vlc_widget)
        self.__vlc_widget.show()

        # These are to allow us to right click. VLC can't hijack mouse input, and probably not key inputs either in
        # Case we want to add keyboard shortcuts later on.
        self.__vlc_widget.player.video_set_mouse_input(False)
        self.__vlc_widget.player.video_set_key_input(False)

    def play(self):
        self.__vlc_widget.player.play()

    def play_fade(self, target, fade_duration_sec, fade_interval):
        self.play()
        cur = 0
        step = (target - cur) / (fade_duration_sec / fade_interval)
        self.fade.cancel()
        self.fade.start(cur=cur, target=target, step=step,
                        fade_interval=fade_interval, update_callback=self.set_volume)

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

    def volume_fade(self, target, fade_duration_sec, fade_interval):
        cur = self.get_volume()
        step = (target - cur) / (fade_duration_sec / fade_interval)
        self.fade.cancel()
        self.fade.start(cur=cur, target=target, step=step, fade_interval=fade_interval, update_callback=self.set_volume)

    def media_new(self, *args):
        return self.__vlc_widget.instance.media_new(*args)

    def set_media(self, *args):
        self._cancel_pending_crop()
        old_media = self.__vlc_widget.player.get_media()
        self.__vlc_widget.player.set_media(*args)
        if old_media is not None:
            old_media.release()

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

    def centercrop(self, video_width=None, video_height=None):
        # Getting dimension from libvlc is not reliable enough (need to consider timing)
        if (video_width, video_height) == (None, None):
            video_width, video_height = self.__vlc_widget.player.video_get_size()
            if video_width == 0 or video_height == 0:
                logger.warning("[CenterCrop] video_get_size is not ready yet")
                return
        logger.debug(f"[CenterCrop] Dimension {video_width}x{video_height}")
        window_ratio = self.width / self.height
        video_ratio = video_width / video_height
        if window_ratio == video_ratio:
            return
        elif video_ratio < window_ratio:
            # If window is wider than video
            # For example video ratio (4:3)=1.33..., window ratio (16:9)=1.77...
            crop_height = video_width / window_ratio
            top_offset = (video_height - crop_height) / 2
            crop_geometry = f"{int(video_width)}x{int(crop_height+top_offset)}+0+{int(top_offset)}"

        else:
            # If video is wider than window
            crop_width = video_height * window_ratio
            left_offset = (video_width - crop_width) / 2
            crop_geometry = f"{int(crop_width+left_offset)}x{int(video_height)}+{int(left_offset)}+0"

        # Crop geometry WxH+L+T: Width x Height + Left Offset + top Offset
        logger.debug(f"[CenterCrop] Crop geometry: {crop_geometry}")
        self.__vlc_widget.player.video_set_crop_geometry(crop_geometry)

    def schedule_centercrop(self, video_width, video_height, max_retries=10, interval_ms=150):
        """Schedule centercrop to be applied once VLC's video output is ready."""
        self._pending_crop = (video_width, video_height)
        self._crop_retries = 0
        self._crop_max_retries = max_retries

        try:
            em = self.__vlc_widget.player.event_manager()
            em.event_detach(vlc.EventType.MediaPlayerVout)
        except Exception:
            pass
        try:
            em = self.__vlc_widget.player.event_manager()
            em.event_attach(vlc.EventType.MediaPlayerVout, self._on_vout_ready)
        except Exception as e:
            logger.debug(f"[CenterCrop] Could not attach Vout event: {e}")

        GLib.timeout_add(interval_ms, self._retry_centercrop)

    def _on_vout_ready(self, event):
        """Called by VLC when video output is created -- apply pending centercrop."""
        if self._pending_crop:
            w, h = self._pending_crop
            self._pending_crop = None
            logger.debug(f"[CenterCrop] Vout ready, applying crop {w}x{h}")
            GLib.idle_add(self.centercrop, w, h)

    def _retry_centercrop(self):
        """Fallback timer: retry centercrop until VLC reports a valid video size."""
        if not self._pending_crop:
            return False
        if self._crop_retries >= self._crop_max_retries:
            w, h = self._pending_crop
            self._pending_crop = None
            logger.debug(f"[CenterCrop] Max retries reached, forcing crop {w}x{h}")
            self.centercrop(w, h)
            return False
        self._crop_retries += 1
        w, h = self._pending_crop
        self.centercrop(w, h)
        size = self.__vlc_widget.player.video_get_size()
        if size[0] > 0 and size[1] > 0:
            logger.debug(f"[CenterCrop] Retry #{self._crop_retries} succeeded (vout size {size[0]}x{size[1]})")
            self._pending_crop = None
            return False
        return True

    def _cancel_pending_crop(self):
        """Cancel any pending centercrop schedule."""
        self._pending_crop = None
        try:
            em = self.__vlc_widget.player.event_manager()
            em.event_detach(vlc.EventType.MediaPlayerVout)
        except Exception:
            pass

    def add_audio_track(self, audio):
        self.__vlc_widget.player.add_slave(vlc.MediaSlaveType(1), audio, True)

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if not self.menu:
                self.menu = build_menu(MODE_VIDEO)
            self.menu.popup_at_pointer()
            return True
        return False

    def get_name(self):
        return self.name

    def get_event_manager(self):
        return self.__vlc_widget.player.event_manager()

    def stop(self):
        self.__vlc_widget.player.stop()

    def fade_out_opacity(self, duration=0.5, interval=0.05, callback=None):
        cur = int(self.get_opacity() * 100)
        target = 0
        step = (target - cur) / max(duration / interval, 1)
        self.fade_opacity.cancel()
        self.fade_opacity.start(
            cur=cur, target=target, step=step, fade_interval=interval,
            update_callback=lambda v: GLib.idle_add(self.set_opacity, max(v / 100.0, 0.0)),
            complete_callback=callback)

    def fade_in_opacity(self, duration=0.5, interval=0.05, callback=None):
        cur = int(self.get_opacity() * 100)
        target = 100
        step = (target - cur) / max(duration / interval, 1)
        self.fade_opacity.cancel()
        self.fade_opacity.start(
            cur=cur, target=target, step=step, fade_interval=interval,
            update_callback=lambda v: GLib.idle_add(self.set_opacity, min(v / 100.0, 1.0)),
            complete_callback=callback)

    def cleanup(self):
        """Cleanup resources to prevent memory leaks"""
        self._cancel_pending_crop()
        self.fade.cancel()
        self.fade_opacity.cancel()
        if self.__vlc_widget:
            self.__vlc_widget.cleanup()
            self.__vlc_widget = None

    def recover_vlc_widget(self):
        """Replace the VLC widget with a fresh instance after a playback failure."""
        old_widget = self.__vlc_widget

        self._cancel_pending_crop()
        self.fade.cancel()
        self.fade_opacity.cancel()

        try:
            old_widget.cleanup()
        except Exception as e:
            logger.warning(f"[PlayerWindow] Old widget cleanup error: {e}")

        self.remove(old_widget)
        del old_widget
        gc.collect()

        # Brief synchronous block (~250 ms) so libVLC finishes freeing the
        # decoder before creating the next Instance. Blocking the main thread
        # for less than half a frame is acceptable and keeps the logic linear.
        time.sleep(PLAYLIST_RECOVERY_SLEEP_SEC)

        self._create_vlc_widget()


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
        if is_wayland() and is_nvidia_proprietary() and not is_vdpau_ok():
            logger.warning(
                "Proprietary Nvidia driver detected! HW Acceleration is not yet working in Wayland.")
        else:
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

        # Static wallpaper (currently for GNOME only)
        if is_gnome():
            self.original_wallpaper_uri = None
            self.original_wallpaper_uri_dark = None
            if is_flatpak():
                try:
                    self.original_wallpaper_uri = subprocess.check_output(
                        "flatpak-spawn --host gsettings get org.gnome.desktop.background picture-uri", shell=True, encoding='UTF-8')
                    self.original_wallpaper_uri_dark = subprocess.check_output(
                        "flatpak-spawn --host gsettings get org.gnome.desktop.background picture-uri-dark", shell=True, encoding='UTF-8')
                except subprocess.CalledProcessError as e:
                    logger.error(f"[StaticWallpaper] {e}")
            else:
                gso = Gio.Settings.new("org.gnome.desktop.background")
                self.original_wallpaper_uri = gso.get_string("picture-uri")
                self.original_wallpaper_uri_dark = gso.get_string(
                    "picture-uri-dark")

        # Handler should be created after everything initialized
        self.active_handler, self.window_handler = None, None
        self.is_any_maximized, self.is_any_fullscreen = False, False
        self.is_paused_by_user = False

        # Playlist state
        self._playlist_index = 0
        self._playlist_event_attached = False
        self._is_transitioning = False
        self._playlist_wallpaper_set = False
        self._playlist_dimensions_cache = {}
        self._last_watchdog_position = -1.0
        self._playlist_stall_count = 0
        self._media_end_count = 0
        self._transition_count = 0
        self._playlist_recovery_count = 0
        self._playlist_recovering = False
        self._playlist_info_lock = threading.Lock()
        self._playlist_preload_generation = 0
        self._playlist_preload_thread = None
        self._current_recovery_attempts = 0
        self._timers_active = False
        # Sliding window of recovery timestamps for the circuit breaker.
        # If too many recoveries happen within PLAYLIST_RECOVERY_WINDOW_SEC,
        # mark the current video as problematic and advance instead of retrying.
        self._recovery_timestamps = deque(maxlen=PLAYLIST_RECOVERY_MAX_IN_WINDOW + 5)

    def new_window(self, gdk_monitor):
        rect = gdk_monitor.get_geometry()
        # In playlist mode, create the libVLC Instance without any audio
        # module (see VLCWidget.__init__) to avoid contact with PipeWire.
        disable_audio = self.mode == MODE_PLAYLIST
        return PlayerWindow(
            gdk_monitor.get_model(),
            rect.width,
            rect.height,
            application=self,
            disable_audio=disable_audio,
        )

    def do_activate(self):
        super().do_activate()
        if self.mode == MODE_PLAYLIST:
            self._setup_playlist()
        else:
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
        logger.info(f"is_any_maximized: {self.is_any_maximized}, is_any_fullscreen: {self.is_any_fullscreen}")

        if self.config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED]:
            if self._should_playback_start():
                self.start_playback()
            else:
                self.pause_playback()
        elif self.config[CONFIG_KEY_MUTE_WHEN_MAXIMIZED]:
            for monitor, window in self.windows.items():
                if not monitor.is_primary():
                    continue
                if self.is_any_fullscreen or self.is_any_maximized:
                    window.volume_fade(target=0, fade_duration_sec=self.config[CONFIG_KEY_FADE_DURATION_SEC],
                                fade_interval=self.config[CONFIG_KEY_FADE_INTERVAL])
                else:
                    window.volume_fade(target=self.volume, fade_duration_sec=self.config[CONFIG_KEY_FADE_DURATION_SEC],
                                fade_interval=self.config[CONFIG_KEY_FADE_INTERVAL])
        
    def _should_playback_start(self):
        if self.config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED] and (self.is_any_maximized or self.is_any_fullscreen):
            return False
        if self.is_paused_by_user:
            return False
        return True

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
            # Get the dimension of the video
            video_width, video_height = {}, {}
            try:
                for monitor,video in data_source.items():
                    # fallback to Default video
                    if len(video) == 0:
                        video = data_source['Default']
                    dimension = subprocess.check_output([
                        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=width,height', '-of',
                        'csv=s=x:p=0', video
                        ], shell=False, encoding='UTF-8').replace('\n', '')
                    dimension = dimension.split("x")
                    video_width[monitor] = int(dimension[0])
                    video_height[monitor] = int(dimension[1])
            except subprocess.CalledProcessError:
                for monitor, video in data_source.items():
                    video_width.setdefault(monitor, None)
                    video_height.setdefault(monitor, None)
                    
            for (monitor, window) in self.windows.items():
                source = data_source[monitor.get_model()] if monitor.get_model() in data_source and len(data_source[monitor.get_model()]) != 0 else data_source['Default']
                logger.info(f"Setting source {source} to {monitor.get_model()}")
                media = window.media_new(source)
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
                if monitor.get_model() not in data_source or len(data_source[monitor.get_model()]) == 0:
                    window.centercrop(video_width['Default'], video_height['Default'])
                else:                
                    window.centercrop(video_width[monitor.get_model()], video_height[monitor.get_model()])

        elif self.mode == MODE_STREAM:
            source = data_source['Default']
            formats = get_formats(source)
            max_height = max(
                self.windows, key=lambda m: m.get_geometry().height).get_geometry().height
            video_url, video_width, video_height = get_optimal_video(
                formats, max_height)
            audio_url = get_best_audio(formats)

            for monitor, window in self.windows.items():
                media = window.media_new(video_url)
                media.add_option("input-repeat=65535")
                window.set_media(media)
                if monitor.is_primary():
                    window.add_audio_track(audio_url)
                else:
                    # `get_optimal_video` now might return video with audio.
                    media.add_option("no-audio")
                window.set_position(0.0)
                window.centercrop(video_width, video_height)
        else:
            raise ValueError("Invalid mode")

        self.volume = self.config[CONFIG_KEY_VOLUME]
        self.is_mute = self.config[CONFIG_KEY_MUTE]
        self.start_playback()

        # Everything is initialized. Create handlers if haven't (singleton pattern).
        if not self.active_handler:
            self.active_handler = ActiveHandler(self._on_active_changed)
        if not self.window_handler and not is_wayland():
            # Only create WindowHandler on X11, not Wayland
            self.window_handler = WindowHandler(self._on_window_state_changed)

        if self.config[CONFIG_KEY_STATIC_WALLPAPER] and self.mode in (MODE_VIDEO, MODE_PLAYLIST):
            self.set_static_wallpaper()
        else:
            self.set_original_wallpaper()

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
            window.pause_fade(fade_duration_sec=self.config[CONFIG_KEY_FADE_DURATION_SEC],
                              fade_interval=self.config[CONFIG_KEY_FADE_INTERVAL])

    def start_playback(self):
        if self._should_playback_start():
            for monitor, window in self.windows.items():
                window.play_fade(target=self.volume, fade_duration_sec=self.config[CONFIG_KEY_FADE_DURATION_SEC],
                            fade_interval=self.config[CONFIG_KEY_FADE_INTERVAL])

    def _probe_video_dimensions(self, video_path):
        """Get video dimensions via ffprobe, returns (width, height) or (None, None)."""
        try:
            dimension = subprocess.check_output([
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height', '-of',
                'csv=s=x:p=0', video_path
            ], shell=False, encoding='UTF-8').replace('\n', '')
            parts = dimension.split("x")
            return int(parts[0]), int(parts[1])
        except (subprocess.CalledProcessError, IndexError, ValueError):
            return None, None

    def _get_playlist_media_info_map(self):
        media_info = self.config.get(CONFIG_KEY_PLAYLIST_MEDIA_INFO)
        if not isinstance(media_info, dict):
            media_info = {}
            self.config[CONFIG_KEY_PLAYLIST_MEDIA_INFO] = media_info
        return media_info

    def _get_playlist_media_info(self, video_path):
        return normalize_playlist_media_info(self._get_playlist_media_info_map().get(video_path, {}))

    def _set_playlist_media_info(self, video_path, media_info, save=False):
        normalized = normalize_playlist_media_info(media_info)
        should_save = False
        with self._playlist_info_lock:
            current = self._get_playlist_media_info_map().get(video_path)
            if current != normalized:
                self._get_playlist_media_info_map()[video_path] = normalized
                should_save = True
        if should_save and save:
            ConfigUtil().save(self.config)
        return should_save

    def _prune_playlist_media_info(self, playlist):
        pruned = {
            path: normalize_playlist_media_info(info)
            for path, info in self._get_playlist_media_info_map().items()
            if path in playlist
        }
        with self._playlist_info_lock:
            if pruned == self._get_playlist_media_info_map():
                return False
            self.config[CONFIG_KEY_PLAYLIST_MEDIA_INFO] = pruned
        ConfigUtil().save(self.config)
        return True

    def _apply_centercrop_if_current(self, video_path, video_width, video_height):
        if video_path != self._get_playlist_video_path():
            return False
        self._apply_centercrop(video_width, video_height)
        return False

    def _start_playlist_metadata_preload(self, playlist):
        self._playlist_preload_generation += 1
        generation = self._playlist_preload_generation

        def _worker():
            changed = False
            for video_path in playlist:
                if generation != self._playlist_preload_generation or not self._timers_active:
                    return
                media_info = build_playlist_media_info(video_path, timeout_sec=5)
                if media_info.get("width") and media_info.get("height"):
                    self._playlist_dimensions_cache[video_path] = (
                        media_info["width"],
                        media_info["height"],
                    )
                    GLib.idle_add(
                        self._apply_centercrop_if_current,
                        video_path,
                        media_info["width"],
                        media_info["height"],
                    )
                if self._set_playlist_media_info(video_path, media_info, save=False):
                    changed = True
            if changed:
                ConfigUtil().save(self.config)

        self._playlist_preload_thread = threading.Thread(target=_worker, daemon=True)
        self._playlist_preload_thread.start()

    def _playlist_health_check(self):
        """Periodic health check logging for playlist diagnostics."""
        if not self._timers_active:
            return False
        try:
            thread_count = threading.active_count()
            mem_mb = 0.0
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            mem_mb = int(line.split()[1]) / 1024
                            break
            except (OSError, ValueError):
                import resource
                mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            logger.info(
                f"[Playlist Health] threads={thread_count} rss={mem_mb:.1f}MB "
                f"index={self._playlist_index} transitioning={self._is_transitioning} "
                f"media_ends={self._media_end_count} transitions={self._transition_count}"
            )
            video_path = self._get_playlist_video_path()
            if video_path:
                media_info = self._get_playlist_media_info(video_path)
                logger.info(
                    f"[Playlist Health] codec={media_info.get('codec_name') or 'unknown'} "
                    f"problematic={media_info.get('is_problematic')} "
                    f"sw_decode={media_info.get('force_software_decode')}"
                )
        except Exception as e:
            logger.debug(f"[Playlist Health] Error collecting stats: {e}")
        return self._timers_active

    def _setup_playlist(self):
        """Initialize and start playlist playback."""
        playlist = self.config.get(CONFIG_KEY_PLAYLIST, [])
        if not playlist:
            logger.warning("[Playlist] Empty playlist, falling back to normal video mode")
            self.data_source = self.config[CONFIG_KEY_DATA_SOURCE]
            return

        self._playlist_index = 0
        self._playlist_wallpaper_set = False
        self._media_end_count = 0
        self._transition_count = 0
        self._playlist_dimensions_cache.clear()
        self._current_recovery_attempts = 0
        self._prune_playlist_media_info(playlist)
        for video_path in playlist:
            media_info = self._get_playlist_media_info(video_path)
            if media_info.get("width") and media_info.get("height"):
                self._playlist_dimensions_cache[video_path] = (
                    media_info["width"],
                    media_info["height"],
                )

        logger.info(f"[Playlist] Starting playlist with {len(playlist)} videos")

        if not self._timers_active:
            self._timers_active = True
            GLib.timeout_add_seconds(60, self._playlist_health_check)
            # Watchdog every 45 s (was 30 s) to reduce false positives on
            # long videos with variable bitrate.
            GLib.timeout_add_seconds(45, self._playlist_watchdog)

        self._start_playlist_metadata_preload(playlist)
        self._playlist_play_current()

    def _get_playlist_video_path(self):
        playlist = self.config.get(CONFIG_KEY_PLAYLIST, [])
        if not playlist:
            return None
        return playlist[self._playlist_index]

    def _set_playlist_media(self, monitor, window, video_path, repeat_count):
        media_info = self._get_playlist_media_info(video_path)
        media = window.media_new(video_path)
        if repeat_count > 1:
            media.add_option(f":input-repeat={repeat_count - 1}")
        # Defense in depth: the libVLC Instance was already created with
        # --no-audio --aout=none in playlist mode (see VLCWidget), but we
        # still set :no-audio per media to guarantee that, even on an
        # unexpected code path, no audio track is decoded.
        media.add_option("no-audio")
        if media_info.get("force_software_decode"):
            media.add_option(":avcodec-hw=none")
        # Release the previous stream synchronously before switching media.
        # On a freshly created widget after recovery this is a cheap no-op;
        # on a normal transition it prevents the player from being left in
        # an inconsistent state.
        try:
            window.stop()
        except Exception as e:
            logger.debug(f"[Playlist] stop() before set_media: {e}")
        window.set_media(media)

    def _advance_problematic_video(self, reason):
        video_path = self._get_playlist_video_path()
        if not video_path:
            return False
        media_info = self._get_playlist_media_info(video_path)
        if not media_info.get("is_problematic") or self._current_recovery_attempts < 1:
            return False
        logger.warning(
            f"[Playlist] Problematic video stalled again after recovery; advancing "
            f"(reason={reason}, index={self._playlist_index})"
        )
        self._set_playlist_media_info(
            video_path,
            mark_playlist_media_info_stalled(media_info),
            save=True,
        )
        self._playlist_stall_count = 0
        self._last_watchdog_position = -1.0
        self._on_playlist_media_end(None)
        return True

    def _attach_playlist_events(self):
        for monitor, window in self.windows.items():
            if not monitor.is_primary():
                continue
            try:
                em = window.get_event_manager()
                em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_playlist_media_end)
                em.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_playlist_media_error)
                self._playlist_event_attached = True
            except Exception as e:
                logger.warning(f"[Playlist] event_attach error: {e}")
            break

    def _playlist_watchdog(self):
        """Detect stuck VLC player by checking if playback position progresses."""
        if not self._timers_active:
            return False
        try:
            primary_window = None
            for monitor, window in self.windows.items():
                if monitor.is_primary():
                    primary_window = window
                    break
            if not primary_window:
                primary_window = next(iter(self.windows.values()), None)
            if not primary_window:
                return self._timers_active

            if self._is_transitioning or self._playlist_recovering or not self._should_playback_start():
                self._last_watchdog_position = -1.0
                self._playlist_stall_count = 0
                return self._timers_active

            current_pos = primary_window.get_position()
            if current_pos == -1.0:
                self._last_watchdog_position = current_pos
                self._playlist_stall_count = 0
                return self._timers_active

            if current_pos == self._last_watchdog_position:
                self._playlist_stall_count += 1
                video_path = self._get_playlist_video_path()
                media_info = self._get_playlist_media_info(video_path) if video_path else {}
                av1_sw = (
                    media_info.get("codec_name") == "av1"
                    and media_info.get("force_software_decode")
                )
                # AV1 in SW is known to be more prone to intermittent stalls;
                # allow one extra stall of tolerance before triggering recovery.
                recovery_threshold = 3 if av1_sw else 2
                logger.warning(
                    f"[Playlist Watchdog] Player stuck at position {current_pos:.4f} "
                    f"index={self._playlist_index}, stalls={self._playlist_stall_count}, "
                    f"av1_sw={av1_sw}, threshold={recovery_threshold}"
                )
                if self._advance_problematic_video("watchdog"):
                    return self._timers_active
                if self._playlist_stall_count < recovery_threshold:
                    # Just log and wait for the next watchdog pass.
                    pass
                elif self._playlist_stall_count == recovery_threshold:
                    # First recovery attempt (subject to the circuit breaker).
                    # Direct synchronous call - we are already on the main thread.
                    self._playlist_recover_current("watchdog")
                else:
                    # Previous recovery did not help; skip to the next video.
                    self._playlist_stall_count = 0
                    self._last_watchdog_position = -1.0
                    self._playlist_advance()
            else:
                self._last_watchdog_position = current_pos
                self._playlist_stall_count = 0
        except Exception as e:
            logger.debug(f"[Playlist Watchdog] Error: {e}")
        return self._timers_active

    def _detach_playlist_event(self):
        """Detach MediaPlayerEndReached from the current primary player's event manager."""
        if not self._playlist_event_attached:
            return
        for monitor, window in self.windows.items():
            if monitor.is_primary():
                try:
                    em = window.get_event_manager()
                    em.event_detach(vlc.EventType.MediaPlayerEndReached)
                    em.event_detach(vlc.EventType.MediaPlayerEncounteredError)
                except Exception as e:
                    logger.debug(f"[Playlist] event_detach error (expected during cleanup): {e}")
                break
        self._playlist_event_attached = False

    def _playlist_play_current(self, recover_players=False, reset_recovery_attempts=True):
        """Play the current video in the playlist on all monitors."""
        video_path = self._get_playlist_video_path()
        if not video_path:
            return

        playlist = self.config.get(CONFIG_KEY_PLAYLIST, [])
        repeat_count = self.config.get(CONFIG_KEY_PLAYLIST_REPEAT_COUNT, 1)
        media_info = self._get_playlist_media_info(video_path)
        logger.info(
            f"[Playlist] Playing video {self._playlist_index + 1}/{len(playlist)} "
            f"(repeat={repeat_count}x, codec={media_info.get('codec_name') or 'unknown'}, "
            f"problematic={media_info.get('is_problematic')}, "
            f"sw_decode={media_info.get('force_software_decode')}): {video_path}"
        )

        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = video_path

        self._detach_playlist_event()

        if recover_players:
            # Deterministic cleanup before destroying/recreating the VLCWidget:
            # - bump the preload generation so in-flight workers stop trying
            #   to schedule centercrop on widgets that will be swapped out;
            # - cancel pending fades on every window to avoid calling
            #   set_volume/set_opacity on players that are already released.
            self._playlist_preload_generation += 1
            for window in self.windows.values():
                if window is None:
                    continue
                window.fade.cancel()
                window.fade_opacity.cancel()
            for monitor, window in self.windows.items():
                logger.warning(f"[Playlist] Recovering player for {monitor.get_model()}")
                window.recover_vlc_widget()

        for monitor, window in self.windows.items():
            self._set_playlist_media(monitor, window, video_path, repeat_count)

        self._attach_playlist_events()

        self.volume = self.config[CONFIG_KEY_VOLUME]
        self.is_mute = self.config[CONFIG_KEY_MUTE]
        self._last_watchdog_position = -1.0
        self._playlist_stall_count = 0
        if reset_recovery_attempts:
            self._current_recovery_attempts = 0
        self.start_playback()

        cached = self._playlist_dimensions_cache.get(video_path)
        if cached:
            video_width, video_height = cached
            if video_width and video_height:
                for monitor, window in self.windows.items():
                    window.schedule_centercrop(video_width, video_height)

        if not self.active_handler:
            self.active_handler = ActiveHandler(self._on_active_changed)
        if not self.window_handler and not is_wayland():
            self.window_handler = WindowHandler(self._on_window_state_changed)

        if self.config[CONFIG_KEY_STATIC_WALLPAPER] and not self._playlist_wallpaper_set:
            self._playlist_wallpaper_set = True
            t = threading.Thread(target=self.set_static_wallpaper, daemon=True)
            t.start()
        elif not self.config[CONFIG_KEY_STATIC_WALLPAPER] and not self._playlist_wallpaper_set:
            self.set_original_wallpaper()

    def _apply_centercrop(self, video_width, video_height):
        """Apply centercrop to all windows (must be called from GTK main thread)."""
        for monitor, window in self.windows.items():
            window.schedule_centercrop(video_width, video_height)
        return False

    def _on_playlist_media_end(self, event):
        """VLC callback when a video finishes. Runs in VLC thread, dispatches to GTK main thread."""
        self._media_end_count += 1
        logger.info(f"[Playlist] MediaEnd #{self._media_end_count} (transitioning={self._is_transitioning})")
        GLib.idle_add(self._playlist_advance)

    def _on_playlist_media_error(self, event):
        """VLC callback when playback fails. Runs in VLC thread, dispatches recovery to GTK main thread."""
        logger.warning(f"[Playlist] Media error received (transitioning={self._is_transitioning})")
        GLib.idle_add(self._handle_playlist_media_error, "vlc-error")

    def _handle_playlist_media_error(self, reason):
        if self._advance_problematic_video(reason):
            return False
        return self._playlist_recover_current(reason)

    def _playlist_advance(self):
        """Advance the playlist to the next video (VLC handles repeats via input-repeat)."""
        playlist = self.config.get(CONFIG_KEY_PLAYLIST, [])
        if not playlist:
            return False

        if self._playlist_recovering:
            return False

        self._playlist_index = (self._playlist_index + 1) % len(playlist)
        logger.info(
            f"[Playlist] Advance: index={self._playlist_index}/{len(playlist)} "
            f"transitioning={self._is_transitioning} threads={threading.active_count()}"
        )
        self._playlist_transition_to_next()

        return False

    def _playlist_transition_to_next(self):
        """Switch to the next video instantly (no fade effect)."""
        if self._is_transitioning or self._playlist_recovering:
            logger.warning("[Playlist] Transition skipped: already transitioning")
            return
        self._transition_count += 1
        self._is_transitioning = True
        soft_restart = (
            PLAYLIST_SOFT_RESTART_EVERY > 0
            and self._transition_count % PLAYLIST_SOFT_RESTART_EVERY == 0
        )
        if soft_restart:
            logger.info(
                f"[Playlist] Soft-restart at transition #{self._transition_count} "
                f"(every {PLAYLIST_SOFT_RESTART_EVERY})"
            )
        else:
            logger.info(f"[Playlist] Transition #{self._transition_count} starting (index={self._playlist_index})")

        try:
            self._playlist_play_current(recover_players=soft_restart)
            logger.info(f"[Playlist] Transition #{self._transition_count} complete (index={self._playlist_index})")
        except Exception as e:
            logger.error(f"[Playlist] Transition error: {e}", exc_info=True)
        finally:
            self._is_transitioning = False

    def _circuit_breaker_tripped(self) -> bool:
        """Record a recovery and report whether the recent limit was reached."""
        now = time.monotonic()
        self._recovery_timestamps.append(now)
        recent = sum(
            1 for t in self._recovery_timestamps
            if now - t <= PLAYLIST_RECOVERY_WINDOW_SEC
        )
        return recent >= PLAYLIST_RECOVERY_MAX_IN_WINDOW

    def _playlist_recover_current(self, reason):
        """Recover the current playlist item after VLC stalls or reports an error."""
        if self._playlist_recovering:
            logger.warning(f"[Playlist] Recovery skipped: already recovering ({reason})")
            return False

        # Circuit breaker: too many recoveries in a short window -> mark as
        # problematic and advance, instead of looping. Fully synchronous
        # path: call _playlist_advance() directly (we are already on the
        # main thread), avoiding the GLib.idle_add that
        # _on_playlist_media_end would use.
        if self._circuit_breaker_tripped():
            video_path = self._get_playlist_video_path()
            if video_path:
                logger.warning(
                    f"[Playlist] Circuit breaker tripped (reason={reason}, "
                    f"index={self._playlist_index}); marking {video_path} "
                    f"problematic and advancing"
                )
                self._set_playlist_media_info(
                    video_path,
                    mark_playlist_media_info_stalled(self._get_playlist_media_info(video_path)),
                    save=True,
                )
            self._playlist_stall_count = 0
            self._last_watchdog_position = -1.0
            self._playlist_advance()
            return False

        self._playlist_recovering = True
        self._playlist_recovery_count += 1
        self._current_recovery_attempts += 1
        logger.warning(
            f"[Playlist] Recovery #{self._playlist_recovery_count} starting "
            f"(reason={reason}, index={self._playlist_index})"
        )

        try:
            self._playlist_play_current(recover_players=True, reset_recovery_attempts=False)
            logger.info(
                f"[Playlist] Recovery #{self._playlist_recovery_count} complete "
                f"(index={self._playlist_index})"
            )
        except Exception as e:
            logger.error(f"[Playlist] Recovery error: {e}", exc_info=True)
        finally:
            self._playlist_recovering = False

        return False


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
                window.set_position(
                    self.windows[primary_monitor].get_position())
                window.play() if self.windows[primary_monitor].is_playing(
                ) else window.pause()

    def set_static_wallpaper(self):
        # Currently for GNOME only
        if not is_gnome():
            return
        # Get the duration of the video
        try:
            duration = float(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', self.data_source['Default']
            ], shell = False))
        except subprocess.CalledProcessError:
            duration = 0
        # Find the golden ratio
        ss = time.strftime('%H:%M:%S', time.gmtime(duration / 3.14))
        # Extract the frame
        static_wallpaper_path = os.path.join(
            CONFIG_DIR, "static-{:06d}.png".format(random.randint(0, 999999)))
        ret = subprocess.run([
            'ffmpeg', '-y', '-ss', ss, '-i', self.data_source['Default'],
            '-vframes', '1', static_wallpaper_path
        ], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        if ret.returncode == 0 and os.path.isfile(static_wallpaper_path):
            with Image.open(static_wallpaper_path) as img:
                blurred = img.filter(
                    ImageFilter.GaussianBlur(self.config["static_wallpaper_blur_radius"]))
                blurred.save(static_wallpaper_path)
            static_wallpaper_uri = pathlib.Path(
                static_wallpaper_path).resolve().as_uri()
            if is_flatpak():
                try:
                    subprocess.run(
                        ['flatpak-spawn', '--host', 'gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', static_wallpaper_uri], shell=False)
                    subprocess.run(
                        ['flatpak-spawn', '--host', 'gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri-dark', static_wallpaper_uri], shell=False)
                except subprocess.CalledProcessError as e:
                    logger.error(f"[StaticWallpaper] {e}")
            else:
                gso = Gio.Settings.new("org.gnome.desktop.background")
                gso.set_string("picture-uri", static_wallpaper_uri)
                gso.set_string("picture-uri-dark", static_wallpaper_uri)

    def set_original_wallpaper(self):
        # Currently for GNOME only
        if not is_gnome():
            return
        if is_flatpak():
            try:
                if self.original_wallpaper_uri is not None:
                    subprocess.run(
                        ['flatpak-spawn', '--host', 'gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', self.original_wallpaper_uri], shell=False)
                if self.original_wallpaper_uri_dark is not None:
                    subprocess.run(
                        ['flatpak-spawn', '--host', 'gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri-dark', self.original_wallpaper_uri], shell=False)
            except subprocess.CalledProcessError as e:
                logger.error(f"[StaticWallpaper] {e}")
        else:
            gso = Gio.Settings.new("org.gnome.desktop.background")
            gso.set_string("picture-uri", self.original_wallpaper_uri)
            gso.set_string("picture-uri-dark",
                           self.original_wallpaper_uri_dark)
        # Purge the generated static wallpaper (and leftover if any)
        for f in glob.glob(os.path.join(CONFIG_DIR, "static-*.png")):
            os.remove(f)

    def reload_config(self):
        self.config = ConfigUtil().load()
        self.config.setdefault(CONFIG_KEY_PLAYLIST_MEDIA_INFO, {})

    def quit_player(self):
        self._timers_active = False
        self._detach_playlist_event()
        self.set_original_wallpaper()
        
        if self.active_handler:
            self.active_handler.cleanup()
            self.active_handler = None
            
        if self.window_handler:
            self.window_handler.cleanup()
            self.window_handler = None
        
        for monitor, window in self.windows.items():
            if window:
                window.cleanup()

        gc.collect()
        
        super().quit_player()


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    logger.info("[Player] Process starting")

    bus = SessionBus()
    app = VideoPlayer()
    try:
        bus.publish(DBUS_NAME_PLAYER, app)
    except RuntimeError as e:
        logger.error(e)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
