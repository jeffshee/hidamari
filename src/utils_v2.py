import os

import gi

gi.require_version("GnomeDesktop", "3.0")
from gi.repository import Gio, GnomeDesktop
from gi.repository.GdkPixbuf import Pixbuf

HOME = os.environ["HOME"]
CONFIG_DIR = HOME + "/.config/hidamari"
VIDEO_WALLPAPER_DIR = HOME + "/Videos/Hidamari"


def list_local_video_dir():
    file_list = []
    ext_list = ["3g2", "3gp", "aaf", "asf", "avchd", "avi", "drc", "flv", "m2v", "m4p", "m4v", "mkv", "mng", "mov",
                "mp2", "mp4", "mpe", "mpeg", "mpg", "mpv", "mxf", "nsv", "ogg", "ogv", "qt", "rm", "rmvb", "roq", "svi",
                "vob", "webm", "wmv", "yuv"]
    for filename in os.listdir(VIDEO_WALLPAPER_DIR):
        filepath = os.path.join(VIDEO_WALLPAPER_DIR, filename)
        if os.path.isfile(filepath) and filename.split(".")[-1].lower() in ext_list:
            file_list.append(filepath)
    return sorted(file_list)


def xdg_open_video_dir():
    import subprocess
    subprocess.call(["xdg-open", os.path.realpath(VIDEO_WALLPAPER_DIR)])


def generate_thumbnail_gnome(filename):
    factory = GnomeDesktop.DesktopThumbnailFactory()
    mtime = os.path.getmtime(filename)
    # Use Gio to determine the URI and mime type
    f = Gio.file_new_for_path(filename)
    uri = f.get_uri()
    info = f.query_info(
        "standard::content-type", Gio.FileQueryInfoFlags.NONE, None)
    mime_type = info.get_content_type()

    if factory.lookup(uri, mtime) is not None:
        return False

    if not factory.can_thumbnail(uri, mime_type, mtime):
        return False

    thumbnail = factory.generate_thumbnail(uri, mime_type)
    if thumbnail is None:
        return False

    factory.save_thumbnail(thumbnail, uri, mtime)
    return True


def get_thumbnail_gnome(video_path, list_store, idx):
    file = Gio.File.new_for_path(video_path)
    info = file.query_info("*", 0, None)
    thumbnail = info.get_attribute_byte_string("thumbnail::path")
    if thumbnail is not None:
        new_pixbuf = Pixbuf.new_from_file_at_size(thumbnail, -1, 96)
        list_store[idx][0] = new_pixbuf
    else:
        generate_thumbnail_gnome(video_path)
