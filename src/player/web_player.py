import logging
import pathlib

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, WebKit2
from pydbus import SessionBus
from commons import *
from player.base_player import BasePlayer

logger = logging.getLogger(LOGGER_NAME)


class WebWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super(WebWindow, self).__init__(*args, **kwargs)
        self.__webview = WebKit2.WebView()
        self.add(self.__webview)
        self.__webview.show()

    def load_uri(self, uri):
        self.__webview.load_uri(uri)

    def set_is_mute(self, is_mute):
        self.__webview.set_is_muted(is_mute)

    def reload(self):
        self.__webview.reload()


class WebPlayer(BasePlayer):
    """
    <node>
    <interface name='io.github.jeffshee.hidamari.player'>
        <property name="mode" type="s" access="read"/>
        <property name="data_source" type="s" access="readwrite"/>
        <property name="volume" type="i" access="readwrite"/>
        <property name="is_mute" type="b" access="readwrite"/>
        <property name="is_playing" type="b" access="read"/>
        <method name='reload_config'/>
        <method name='pause_playback'/>
        <method name='start_playback'/>
        <method name='quit_player'/>
    </interface>
    </node>
    """

    def __init__(self, *args, **kwargs):
        super(WebPlayer, self).__init__(*args, **kwargs)
        self.config = None
        self.reload_config()

    def new_window(self, gdk_monitor):
        return WebWindow(application=self)

    def do_activate(self):
        super().do_activate()
        self.data_source = self.config[CONFIG_KEY_DATA_SOURCE]

    @property
    def mode(self):
        return self.config[CONFIG_KEY_MODE]

    @property
    def data_source(self):
        return self.config[CONFIG_KEY_DATA_SOURCE]

    @data_source.setter
    def data_source(self, data_source: str):
        self.config[CONFIG_KEY_DATA_SOURCE] = data_source
        if self.mode != MODE_WEBPAGE:
            raise ValueError("Invalid mode")

        # Convert to uri if necessary
        if not data_source.startswith("http://") and \
                not data_source.startswith("https://") and not data_source.startswith("file://"):
            data_source = pathlib.Path(data_source).resolve().as_uri()

        for monitor, window in self.windows.items():
            window.load_uri(data_source)
            if not monitor.is_primary():
                # TODO not sure if this is desirable
                monitor.set_is_mute(True)
        self.volume = self.config[CONFIG_KEY_VOLUME]
        self.is_mute = self.config[CONFIG_KEY_MUTE]

    @property
    def volume(self):
        return self.config[CONFIG_KEY_VOLUME]

    @volume.setter
    def volume(self, volume):
        # TODO can we set volume of webview?
        self.config[CONFIG_KEY_VOLUME] = volume

    @property
    def is_mute(self):
        return self.config[CONFIG_KEY_MUTE]

    @is_mute.setter
    def is_mute(self, is_mute):
        self.config[CONFIG_KEY_MUTE] = is_mute
        for monitor, window in self.windows.items():
            if monitor.is_primary():
                window.set_is_mute(is_mute)

    @property
    def is_playing(self):
        return True

    def pause_playback(self):
        pass

    def start_playback(self):
        pass

    def reload_config(self):
        from utils import ConfigUtil
        self.config = ConfigUtil().load()


def main():
    bus = SessionBus()
    app = WebPlayer()
    try:
        bus.publish(DBUS_NAME_PLAYER, app)
    except RuntimeError as e:
        logger.error(e)
    app.run(sys.argv)


if __name__ == "__main__":
    main()
