from collections import defaultdict

import gi

gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, Gdk, WebKit2


class WebView(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Config
        self.config = defaultdict()

        # WebView initialize
        self.webview = WebKit2.WebView()
        self.webview.load_uri("https://alteredqualia.com/three/examples/webgl_pasta.html")
        self.add(self.webview)

        # Window
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_size_request(*self._monitor_detect())
        self.show_all()

    def _monitor_detect(self):
        display = Gdk.Display.get_default()
        screen = Gdk.Screen.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        scale_factor = monitor.get_scale_factor()
        width = scale_factor * geometry.width
        height = scale_factor * geometry.height
        screen.connect("size-changed", self._on_size_changed)
        return width, height

    def _on_size_changed(self, *args):
        width, height = self.monitor_detect()
        self.resize(width, height)
