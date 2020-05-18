import sys
import os
import json
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, Gdk, GLib
from gi.repository.GdkPixbuf import Pixbuf
from utils import FolderModifiedHandler

HOME = os.environ['HOME']
RC_FILENAME = '.hidamari-rc'
RC_PATH = HOME + '/' + RC_FILENAME
VIDEO_WALLPAPER_PATH = HOME + '/Videos/Hidamari'
GUI_GLADE_FILENAME = 'gui.glade'

volume_adjustment, blur_adjustment = None, None
mute_audio, static_wallpaper, detect_maximized = None, None, None
volume, blur_radius = None, None
icon_view = None
btn_apply = None


def create_dir():
    if not os.path.exists(VIDEO_WALLPAPER_PATH):
        try:
            os.makedirs(VIDEO_WALLPAPER_PATH)
        except OSError:
            pass


def scan_dir():
    file_list = []
    for file in os.listdir(VIDEO_WALLPAPER_PATH):
        # TODO file format checking (supported video?)
        # TODO there is a case that isfile return False even it's a file, need investigate
        # if os.path.isfile(file):
        file_list.append(VIDEO_WALLPAPER_PATH + '/' + file)
    return file_list


with open(RC_PATH, 'r') as f:
    rc = json.load(f)
create_dir()
file_list = scan_dir()


def get_thumbnail(filename):
    # TODO get thumbnail from nautilus is working but not reliable at all.
    if os.path.exists(filename):
        file = Gio.File.new_for_path(filename)
        info = file.query_info('*', 0, None)
        return info.get_attribute_byte_string('thumbnail::path')
    return None


class Handler:
    def on_apply_clicked(self, *args):
        # TODO it's not a good idea to hard-coding the key of dict rc['...']
        selected = icon_view.get_selected_items()
        if len(selected) != 0:
            icon_view_selection = selected[0].get_indices()[0]
            rc['video_path'] = file_list[icon_view_selection]
        #
        rc['static_wallpaper'] = static_wallpaper.get_active()
        rc['detect_maximized'] = detect_maximized.get_active()
        rc['mute_audio'] = mute_audio.get_active()
        #
        rc['static_wallpaper_blur_radius'] = blur_adjustment.get_value()
        rc['audio_volume'] = volume_adjustment.get_value() / 100
        with open(RC_PATH, 'w') as f:
            json.dump(rc, f)
        btn_apply.set_sensitive(False)

    def on_cancel_clicked(self, *args):
        #
        static_wallpaper.set_active(rc['static_wallpaper'])
        detect_maximized.set_active(rc['detect_maximized'])
        mute_audio.set_active(rc['mute_audio'])
        #
        volume_adjustment.set_value(rc['audio_volume'] * 100)
        blur_adjustment.set_value(rc['static_wallpaper_blur_radius'])
        #
        icon_view.unselect_all()
        #
        volume.set_sensitive(not mute_audio.get_active())
        blur_radius.set_sensitive(static_wallpaper.get_active())
        btn_apply.set_sensitive(False)

    def on_value_changed(self, *args):
        volume.set_sensitive(not mute_audio.get_active())
        blur_radius.set_sensitive(static_wallpaper.get_active())
        btn_apply.set_sensitive(True)


class ControlPanel():
    def __init__(self):
        global volume, blur_radius
        global volume_adjustment, blur_adjustment, icon_view, btn_apply
        global mute_audio, static_wallpaper, detect_maximized

        # Builder Initialization
        builder = Gtk.Builder()
        builder.add_from_file(sys.path[0] + '/' + GUI_GLADE_FILENAME)
        window = builder.get_object('window')
        icon_view = builder.get_object('icon_view')
        volume = builder.get_object('volume')
        volume_adjustment = builder.get_object('volume_adjustment')
        mute_audio = builder.get_object('mute_audio')
        detect_maximized = builder.get_object('detect_maximized')
        static_wallpaper = builder.get_object('static_wallpaper')
        blur_adjustment = builder.get_object('blur_adjustment')
        blur_radius = builder.get_object('blur_radius')
        btn_apply = builder.get_object('apply')
        builder.connect_signals(Handler())

        # Icon View
        self.refresh()

        # Setting Initialization
        volume_adjustment.set_value(rc['audio_volume'] * 100)
        blur_adjustment.set_value(rc['static_wallpaper_blur_radius'])
        mute_audio.set_active(rc['mute_audio'])
        static_wallpaper.set_active(rc['static_wallpaper'])
        detect_maximized.set_active(rc['detect_maximized'])

        btn_apply.set_sensitive(False)

        window.connect("destroy", Gtk.main_quit)
        window.show_all()

    def main(self):
        FolderModifiedHandler(VIDEO_WALLPAPER_PATH, self.refresh)
        Gtk.main()

    def refresh(self):
        global file_list
        file_list = scan_dir()
        list_store = Gtk.ListStore(Pixbuf, str)
        icon_view.set_model(list_store)
        icon_view.set_pixbuf_column(0)
        icon_view.set_text_column(1)
        for video in file_list:
            thumbnail = get_thumbnail(video)
            if thumbnail is not None:
                pixbuf = Pixbuf.new_from_file_at_size(thumbnail, 128, 128)
            else:
                pixbuf = None
            list_store.append([pixbuf, os.path.basename(video)])


def main():
    control = ControlPanel()
    control.main()


if __name__ == '__main__':
    main()
