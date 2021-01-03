import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio
from src.v2.player import Player
from src.v2.webview import WebView


class Application(Gtk.Application):
    def __init__(self):
        super().__init__()
        self.window = None

        # Read Dbus XML
        with open("xml/dbus.xml") as f:
            self.xml = f.read()

        self.node = Gio.DBusNodeInfo.new_for_xml(self.xml)  # We make a node for the xml

        self.owner_id = Gio.bus_own_name(
            Gio.BusType.SESSION,  # What kinda bus is it?
            "io.github.jeffshee.hidamari",  # It's name ?
            Gio.BusNameOwnerFlags.NONE,  # If other has same name, what to do?
            self.on_bus_acquired,
            self.on_name_acquired,
            self.on_name_lost,
        )

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            # Windows are associated with the application
            # when the last one is closed the application shuts down
            self.window = Player(application=self, title="Main Window")
            # self.window = WebView(application=self, title="Main Window")

        self.window.present()

    def on_quit(self, action, param):
        self.quit()

    def handle_method_call(self, connection, sender, object_path, interface_name, method_name, params, invocation):
        print("called")
        if method_name == "start":
            self.window.start()
            invocation.return_value(None)  # Nothing to say, so just return None.
        elif method_name == "pause":
            self.window.pause()
            invocation.return_value(None)
        elif method_name == "setVolume":
            self.window.set_volume(params.unpack()[0])
            invocation.return_value(None)
        elif method_name == "setDataSource":
            self.window.set_data_source(params.unpack()[0])
            invocation.return_value(None)

    def on_bus_acquired(self, connection, name):
        """
        The function that introduces our server to the world. It is called automatically
        when we get the bus we asked.
        """
        # Remember the node we made earlier? That has a list as interfaces attribute.
        # From that get our interface. We made only one interface, so we get the first
        # interface.
        print("Bus acquired for name, ", name)
        reg_id = connection.register_object(
            "/io/github/jeffshee/hidamari", self.node.interfaces[0], self.handle_method_call, None, None
        )

    def on_name_acquired(self, connection, name):
        """
        What to do after name acquired?
        """
        print("Name acquired :", name)

    def on_name_lost(self, connection, name):
        """
        What to do after our name is lost? May be just exit.
        """
        print("Name lost :", name)
        self.quit()


if __name__ == "__main__":
    app = Application()
    app.run()
