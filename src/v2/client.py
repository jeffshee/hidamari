from gi.repository import Gio, GLib

"""
Special Thanks ^^
https://discourse.gnome.org/t/minimal-example-of-gdbus-in-python/3165/25
"""


class Client:
    def __init__(self):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)  # What is the bus type?

    def _connect(self):
        # Below we are doing something like, 'Hey Gio, heard there is a DBus server
        # with name org.examples.gdbus and type SESSION, get me a connection to it'
        proxy = Gio.DBusProxy.new_sync(
            self.bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "io.github.jeffshee.hidamari",
            "/io/github/jeffshee/hidamari",
            "io.github.jeffshee.hidamari",
            None,
        )
        return proxy

    # proxy.call_sync is the way to call the method names of server.
    def _proxy_call_sync(self, method_name, param=None, type_code=None):
        if param is not None:
            param = GLib.Variant(type_code, (param,))
        return self._connect().call_sync(
            method_name,  # Method name
            param,  # Parameters for method
            Gio.DBusCallFlags.NO_AUTO_START,  # Flags for call APIs
            1000,  # How long to wait for reply? (in milliseconds)
            None,  # Cancellable, to cancel the call if you changed mind in middle)
        )

    def start(self):
        self._proxy_call_sync("start")

    def pause(self):
        self._proxy_call_sync("pause")

    def set_volume(self, volume):
        self._proxy_call_sync("setVolume", volume, "(d)")

    def set_data_source(self, path):
        self._proxy_call_sync("setDataSource", path, "(s)")


if __name__ == "__main__":
    """
    For debug
    """
    client = Client()
    client.set_data_source("/home/jeffshee/Developers/video-wallpaper-linux/src/v2/Rem.mp4")