import sys
import yt_dlp

try:
    import os
    sys.path.insert(1, os.path.join(sys.path[0], ".."))
    from gui.imports import *
    from utils import ConfigUtil
except ModuleNotFoundError:
    from hidamari.gui.imports import *
    from hidamari.utils import ConfigUtil

class StreamingView:
    def __init__(self, config: ConfigUtil, server):
        self.config = config
        self.server = server
        self.builder = Gtk.Builder()
        try:
            self.builder.add_from_resource(APP_UI_RESOURCE_PATH + "streaming_view.ui")
        except GLib.Error:
            self.builder.add_from_file(os.path.abspath("./src/hidamari/assets/streaming_view.ui"))

        self.widget = self.builder.get_object("StreamingView")

        signals = {
            "on_streaming_activate": self.on_streaming_activate
        }

        self.builder.connect_signals(signals)
        
    def _check_yt_dlp(self, raw_url):
        # Check if the url is valid (yt_dlp)
        try:
            with yt_dlp.YoutubeDL({"noplaylist": True}) as ydl:
                ydl.extract_info(raw_url, download=False)
        except yt_dlp.utils.DownloadError as e:
            s = " ".join(str(e).split(" ")[1:])
            logger.error(f"[GUI/StreamingView] Failed to stream {raw_url}. Error:\n{s}")
            self._show_error(f"Failed to stream {raw_url}. Error:\n{s}")
            return False
        return True

    def on_streaming_activate(self, entry: Gtk.Entry, *_):
        url = entry.get_text()
        if not self._check_yt_dlp(url):
            return
        logger.info(f"[GUI/StreamingView] Streaming: {url}")
        self.config[CONFIG_KEY_MODE] = MODE_STREAM
        self.config[CONFIG_KEY_DATA_SOURCE]['Default'] = url #! we dont want to break the config, webpage and stream modes will kept in Default source
        self._save_config()
        if self.server is not None:
            self.server.stream(url)

    def _load_config(self):
        self.config = ConfigUtil().load()
        
    def _save_config(self):
        ConfigUtil().save(self.config)