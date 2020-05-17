import os
import subprocess
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkClutter', '1.0')
gi.require_version('ClutterGst', '3.0')
from gi.repository import Gtk, Gdk, GtkClutter, Clutter, ClutterGst
import control_panel

# Initialize
GtkClutter.init()
ClutterGst.init()


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
        self.mute_audio = rc['mute_audio']
        bg_color = Clutter.Color.get_static(Clutter.StaticColor.BLACK)

        # Monitor Detect
        self.width, self.height = monitor_detect()

        # Actors initialize
        self.embed = GtkClutter.Embed()
        self.main_actor = self.embed.get_stage()
        self.wallpaper_actor = Clutter.Actor()
        self.wallpaper_actor.set_size(self.width, self.height)
        self.main_actor.add_child(self.wallpaper_actor)
        self.main_actor.set_background_color(bg_color)

        # Video initialize
        self.video_playback = ClutterGst.Playback()
        self.video_content = ClutterGst.Content()
        self.video_content.set_player(self.video_playback)

        # Playback settings
        self.video_playback.set_filename(self.video_path)
        self.video_playback.set_audio_volume(0.0 if self.mute_audio else self.audio_volume)
        self.video_playback.set_playing(True)
        self.video_playback.connect('eos', self._loop_playback)
        self.wallpaper_actor.set_content(self.video_content)

        # Window settings
        self.window = Gtk.Window()
        self.window.add(self.embed)
        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_size_request(self.width, self.height)

        # button event
        self._build_context_menu()
        self.window.connect('button-press-event', self._on_button_press_event)

        self.window.show_all()

    def main(self):
        Gtk.main()

    def quit(self):
        Gtk.main_quit()

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
            self.video_playback.set_audio_volume(0.0 if self.mute_audio else self.audio_volume)
        if rc['mute_audio'] != self.mute_audio:
            self.mute_audio = rc['mute_audio']
            self.video_playback.set_audio_volume(0.0 if self.mute_audio else self.audio_volume)

    def _loop_playback(self, _):
        self.video_playback.set_progress(0.0)
        self.video_playback.set_audio_volume(0.0 if self.mute_audio else self.audio_volume)
        self.video_playback.set_playing(True)

    def _on_menuitem_main_gui(self, _):
        control_panel.main()

    def _on_menuitem_display_settings(self, _):
        subprocess.Popen(['gnome-control-center', 'display'])

    def _on_menuitem_settings(self, _):
        subprocess.Popen('gnome-control-center')

    def _build_context_menu(self):
        if os.environ['DESKTOP_SESSION'] == 'gnome':
            items = [('Video Wallpaper', self._on_menuitem_main_gui), ('-', None),
                     ('Display Settings', self._on_menuitem_display_settings), ('Settings', self._on_menuitem_settings)]
        else:
            items = [('Video Wallpaper', self._on_menuitem_main_gui)]
        self.menu = Gtk.Menu()
        for item in items:
            label, handler = item
            if label == '-':
                self.menu.append(Gtk.SeparatorMenuItem())
            else:
                menuitem = Gtk.MenuItem.new_with_label(label)
                menuitem.connect('activate', handler)
                menuitem.set_margin_top(8)
                menuitem.set_margin_bottom(8)
                self.menu.append(menuitem)
        self.menu.show_all()

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer()
        return True
