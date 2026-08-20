import sys
import requests

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    from gui.imports import *
    from utils import ConfigUtil
except ModuleNotFoundError:
    from hidamari.gui.imports import *
    from hidamari.utils import ConfigUtil

class WebView:
    def __init__(self, config: ConfigUtil, server):
        self.config = config
        self.server = server
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_resource(APP_UI_RESOURCE_PATH + "web_view.ui")
        except GLib.Error:
            self.builder.add_from_file(os.path.abspath("./src/hidamari/assets/web_view.ui"))

        self.widget = self.builder.get_object("WebView")

        signals = {
            "on_web_page_activate": self.on_web_page_activate
        }

        self.builder.connect_signals(signals)
        
    def _check_url(self, url):
        # Check if the url is valid
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            logger.error(f"[GUI/WebView] Failed to access {url}. Error:\n{e}")
            self._show_error(f"Failed to access {url}. Error:\n{e}")
            return False
        if response.status_code >= 400:
            logger.error(
                f"[GUI/WebView] Failed to access {url}. Error code: {response.status_code}"
            )
            self._show_error(
                f"Failed to access {url}. Error code: {response.status_code}"
            )
            return False
        return True

    def on_web_page_activate(self, entry: Gtk.Entry, *_):
        url = entry.get_text()
        if not self._check_url(url):
            return
        logger.info(f"[GUI/WebView] Webpage: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_WEBPAGE
        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = url #! we dont want to break the config, webpage and stream modes will kept in Default source
        self._save_config()
        if self.server is not None:
            self.server.webpage(url)
            
    def on_local_web_page_apply(self, *_):
        file_chooser: Gtk.FileChooserButton = self.builder.get_object("FileChooser")
        choose: Gio.File = file_chooser.get_file()
        if choose is None:
            self._show_error("Please choose a HTML file")
            return
        file_path = choose.get_path()
        logger.info(f"[GUI/WebView] Local Webpage: {file_path}")
        self.config[CONFIG_KEY_MODE] = MODE_WEBPAGE
        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = file_path #! we dont want to break the config, webpage and stream modes will kept in Default source
        self._save_config()
        if self.server is not None:
            self.server.webpage(choose.get_path())
            
    def _load_config(self):
        self.config = ConfigUtil().load()
        
    def _save_config(self):
        ConfigUtil().save(self.config)