import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    from gui.imports import *
    from utils import ConfigUtil
except ModuleNotFoundError:
    from hidamari.gui.imports import *
    from hidamari.utils import ConfigUtil

class AboutDialog:
    def __init__(self):
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_resource(APP_UI_RESOURCE_PATH + "about_dialog.ui")
        except GLib.Error:
            self.builder.add_from_file(os.path.abspath("./src/hidamari/assets/about_dialog.ui"))

        self.dialog: Gtk.AboutDialog = self.builder.get_object("AboutDialog")
        
