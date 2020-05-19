import os
import subprocess
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkClutter', '1.0')
gi.require_version('ClutterGst', '3.0')
from gi.repository import Gtk, Gdk, GtkClutter, Clutter, ClutterGst

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
        self.rc = rc  #TODO at line107
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
            self.check_menu['Mute Audio'].set_active(self.mute_audio)
            self.video_playback.set_audio_volume(0.0 if self.mute_audio else self.audio_volume)

    def _loop_playback(self, _):
        self.video_playback.set_progress(0.0)
        self.video_playback.set_audio_volume(0.0 if self.mute_audio else self.audio_volume)
        self.video_playback.set_playing(True)

    def _on_menuitem_main_gui(self, _):
        import gui
        gui.main()

    def _on_menuitem_mute_audio(self, _):
        self.mute_audio = self.check_menu['Mute Audio'].get_active()
        self.video_playback.set_audio_volume(0.0 if self.mute_audio else self.audio_volume)
        #TODO Reflect the changes in GUI
        # HOME = os.environ['HOME']
        # RC_FILENAME = '.hidamari-rc'
        # RC_PATH = HOME + '/' + RC_FILENAME
        # import json
        # self.rc['mute_audio'] = self.mute_audio
        # print(self.rc)
        # with open(RC_PATH, 'w') as f:
        #     json.dump(self.rc, f)

    def _on_menuitem_pause_playback(self, _):
        self.pause_playback() if self.check_menu['Pause Playback'].get_active() else self.resume_playback()

    def _on_menuitem_settings(self, _):
        subprocess.Popen('gnome-control-center')

    def _on_menuitem_quit(self, _):
        self.quit()

    def _on_not_implemented(self, _):
        print('Not implemented!')
        message = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK,
                                    message_format='Not implemented!')
        message.connect("response", self._dialog_response)
        message.show()

    def _dialog_response(self, widget, response_id):
        if response_id == Gtk.ResponseType.OK:
            widget.destroy()

    def _build_context_menu(self):
        self.menu = Gtk.Menu()
        self.check_menu = {}
        items = [('Show Hidamari', self._on_menuitem_main_gui, False), ('Mute Audio', self._on_menuitem_mute_audio, True),
                 ('Pause Playback', self._on_menuitem_pause_playback, True), ('Next Wallpaper', self._on_not_implemented, False),
                 ('Quit Hidamari', self._on_menuitem_quit, False)]

        if os.environ['DESKTOP_SESSION'] == 'gnome':
            items += [('-', None), ('GNOME Settings', self._on_menuitem_settings)]

        for item in items:
            label, handler, check = item
            if label == '-':
                self.menu.append(Gtk.SeparatorMenuItem())
            else:
                if check:
                    menuitem = Gtk.CheckMenuItem.new_with_label(label)
                    self.check_menu[label] = menuitem
                else:
                    menuitem = Gtk.MenuItem.new_with_label(label)
                menuitem.connect('activate', handler)
                menuitem.set_margin_top(4)
                menuitem.set_margin_bottom(4)
                self.menu.append(menuitem)
        self.menu.show_all()

    def _on_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer()
        return True
