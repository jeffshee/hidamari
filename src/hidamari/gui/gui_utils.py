import logging
import os
import subprocess
import tempfile
import threading

import gi

gi.require_version("GnomeDesktop", "4.0")
from gi.repository import GdkPixbuf, Gio, GLib, GnomeDesktop

from hidamari.commons import LOGGER_NAME
from hidamari.utils import is_flatpak

logger = logging.getLogger(LOGGER_NAME)


def _generate_thumbnail_flatpak(filename):
    # Inside Flatpak, DesktopThumbnailFactory runs the thumbnailer via
    # `flatpak-spawn --sandbox`, where glycin (which writes the PNG on
    # recent GNOME runtimes) can't spawn its own sandboxed loader — nested
    # sandboxes are blocked, so every thumbnail fails. Run the bundled
    # thumbnailer directly instead; glycin's single-level sandbox then
    # works via the org.freedesktop.Flatpak portal.
    with tempfile.TemporaryDirectory() as tmp_dir:
        output = os.path.join(tmp_dir, "thumbnail.png")
        subprocess.run(
            ["totem-video-thumbnailer", "-s", "256", filename, output],
            check=True,
            timeout=60,
        )
        return GdkPixbuf.Pixbuf.new_from_file(output)


def generate_thumbnail(filename):
    """Generate and cache a thumbnail. Returns its path, or None if one can't
    be produced (e.g. no usable thumbnailer, or it failed)."""
    factory = GnomeDesktop.DesktopThumbnailFactory()
    mtime = os.path.getmtime(filename)
    file = Gio.file_new_for_path(filename)
    uri = file.get_uri()
    info = file.query_info("standard::content-type", Gio.FileQueryInfoFlags.NONE, None)
    mime_type = info.get_content_type()

    cached = factory.lookup(uri, mtime)
    if cached is not None:
        return cached

    if not factory.can_thumbnail(uri, mime_type, mtime):
        return None

    if is_flatpak():
        pixbuf = _generate_thumbnail_flatpak(filename)
    else:
        pixbuf = factory.generate_thumbnail(uri, mime_type)
    if pixbuf is None:
        return None

    factory.save_thumbnail(pixbuf, uri, mtime)
    return factory.lookup(uri, mtime)


def get_thumbnail(video_path, list_store, idx):
    # Best-effort: a preview thumbnail must never crash the GUI. On failure the
    # generic video icon set by the caller stays in place. (In the Flatpak the
    # sandboxed thumbnailer can fail; that's fine, we just skip the preview.)
    try:
        info = Gio.File.new_for_path(video_path).query_info(
            "thumbnail::path", Gio.FileQueryInfoFlags.NONE, None
        )
        thumbnail = info.get_attribute_byte_string("thumbnail::path") or generate_thumbnail(
            video_path
        )
        if thumbnail:
            list_store[idx][0] = GdkPixbuf.Pixbuf.new_from_file_at_size(thumbnail, -1, 96)
    except (GLib.Error, OSError, subprocess.SubprocessError) as e:
        logger.debug("[Thumbnail] Skipped %s: %s", os.path.basename(video_path), e)


def debounce(wait_time):
    """
    Decorator that will debounce a function so that it is called after wait_time seconds
    If it is called multiple times, will wait for the last call to be debounced and run only this one.
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
