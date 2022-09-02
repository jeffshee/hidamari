import os
import sys
import logging
import threading

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


def debounce(wait_time):
    """
    Decorator that will debounce a function so that it is called after wait_time seconds
    If it is called multiple times, will wait for the last call to be debounced and run only this one.
    See the test_debounce.py file for examples
    Reference:
    https://github.com/salesforce/decorator-operations/blob/master/decoratorOperations/debounce_functions/debounce.py
    """
    def decorator(function):
        def debounced(*args, **kwargs):
            def call_function():
                debounced._timer = None
                return function(*args, **kwargs)

            if debounced._timer is not None:
                debounced._timer.cancel()

            debounced._timer = threading.Timer(wait_time, call_function)
            debounced._timer.start()

        debounced._timer = None
        return debounced

    return decorator
