import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class GUI(Gtk.Application):
    def __init__(self):
        super().__init__()
        self.window = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file("xml/control_panel.glade")
        self.builder.connect_signals(self)

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = self.builder.get_object("window")
            self.window.set_application(self)

        self.window.present()


if __name__ == "__main__":
    app = GUI()
    app.run()
