import os
import sys
import logging
from pprint import pformat

import gi
gi.require_version("GnomeDesktop", "4.0")
from gi.repository import Gio, GnomeDesktop, GdkPixbuf

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], '..'))
    from commons import *
except ModuleNotFoundError:
    from hidamari.commons import *

logger = logging.getLogger(LOGGER_NAME)


def get_video_paths():
    file_list = []
    for filename in os.listdir(VIDEO_WALLPAPER_DIR):
        filepath = os.path.join(VIDEO_WALLPAPER_DIR, filename)
        file = Gio.file_new_for_path(filepath)
        info = file.query_info('standard::content-type',
                               Gio.FileQueryInfoFlags.NONE, None)
        mime_type = info.get_content_type()
        if "video" in mime_type:
            file_list.append(filepath)
    return sorted(file_list)


def generate_thumbnail(filename):
    factory = GnomeDesktop.DesktopThumbnailFactory()
    mtime = os.path.getmtime(filename)
    file = Gio.file_new_for_path(filename)
    uri = file.get_uri()
    info = file.query_info("standard::content-type",
                           Gio.FileQueryInfoFlags.NONE, None)
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


def get_thumbnail(video_path, list_store, idx):
    file = Gio.File.new_for_path(video_path)
    info = file.query_info("*", Gio.FileQueryInfoFlags.NONE, None)
    thumbnail = info.get_attribute_byte_string("thumbnail::path")
    if thumbnail is not None or generate_thumbnail(video_path):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(thumbnail, -1, 96)
        list_store[idx][0] = pixbuf
