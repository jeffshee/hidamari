import sys
from collections import defaultdict

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = Gtk.Label(label="Player", margin=30)
        self.add(self.label)
        self.label.show()
        self.set_default_size(800, 800)


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="org.example.player",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
            **kwargs
        )
        self.windows = defaultdict()

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        for i in range(2):
            if not self.windows.get(i):
                # Windows are associated with the application
                # when the last one is closed the application shuts down
                self.windows[i] = AppWindow(application=self, title=f"Player{i}")
            self.windows[i].present()
        print(self.windows)

    def on_quit(self, action, param):
        self.quit()


def main():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
