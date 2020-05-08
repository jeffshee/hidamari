import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkClutter', '1.0')
gi.require_version('ClutterGst', '3.0')
from gi.repository import Gtk, Gdk, GtkClutter, Clutter, ClutterGst


def monitor_detect():
    display = Gdk.Display.get_default()
    monitor = display.get_primary_monitor()
    geometry = monitor.get_geometry()
    scale_factor = monitor.get_scale_factor()
    width = scale_factor * geometry.width
    height = scale_factor * geometry.height
    return width, height


class Player:
    def __init__(self, rc=None):
        # Settings
        self.video_path = rc['video_path']
        self.audio_volume = rc['audio_volume']
        bg_color = Clutter.Color.get_static(Clutter.StaticColor.BLACK)

        # Monitor Detect
        self.width, self.height = monitor_detect()

        # Actors initialize
        GtkClutter.init()
        self.embed = GtkClutter.Embed()
        self.main_actor = self.embed.get_stage()
        self.wallpaper_actor = Clutter.Actor()
        self.wallpaper_actor.set_size(self.width, self.height)
        self.main_actor.add_child(self.wallpaper_actor)
        self.main_actor.set_background_color(bg_color)

        # Video initialize
        ClutterGst.init()
        self.video_playback = ClutterGst.Playback()
        self.video_content = ClutterGst.Content()
        self.video_content.set_player(self.video_playback)

        # Playback settings
        self.video_playback.set_filename(self.video_path)
        self.video_playback.set_audio_volume(self.audio_volume)
        self.video_playback.set_playing(True)
        self.video_playback.connect('eos', self.loop_playback)
        self.wallpaper_actor.set_content(self.video_content)

        # Window settings
        self.window = Gtk.Window()
        self.window.add(self.embed)
        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_size_request(self.width, self.height)
        self.window.show_all()

    def main(self):
        Gtk.main()

    def quit(self):
        Gtk.main_quit()

    def loop_playback(self, _):
        self.video_playback.set_progress(0.0)
        self.video_playback.set_audio_volume(self.audio_volume)
        self.video_playback.set_playing(True)

    def pause_playback(self):
        self.video_playback.set_playing(False)

    def resume_playback(self):
        self.video_playback.set_playing(True)

    def update_rc(self, rc):
        if rc['video_path'] != self.video_path:
            self.video_path = rc['video_path']
            self.video_playback.set_playing(False)
            self.video_playback.set_filename(self.video_path)
            self.video_playback.set_progress(0.0)
            self.video_playback.set_playing(True)
        if rc['audio_volume'] != self.audio_volume:
            self.audio_volume = rc['audio_volume']
            self.video_playback.set_audio_volume(self.audio_volume)
