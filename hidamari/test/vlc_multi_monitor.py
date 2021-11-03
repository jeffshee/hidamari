import ctypes
import gi
import copy
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import vlc

"""
Resource:
https://www.codementor.io/@princerapa/python-media-player-vlc-gtk-favehuy2b
"""


class VLCWidget(Gtk.DrawingArea):
    """
    Simple VLC widget.
    Its player can be controlled through the 'player' attribute, which
    is a vlc.MediaPlayer() instance.
    """
    __gtype_name__ = "VLCWidget"

    def __init__(self, width, height):
        # Spawn a VLC instance and create a new media player to embed.
        self.instance = vlc.Instance()
        # Working

        # self.instance = vlc.Instance("--sout '#duplicate{dst=display,dst=display}'")
        # self.instance = vlc.Instance("--video-splitter=clone --clone-count=2")
        Gtk.DrawingArea.__init__(self)
        self.player = self.instance.media_player_new()

        def handle_embed(*args):
            ## Bad news
            # No more than one window handle per media player instance can be specified. If the media has multiple simultaneously active video tracks, extra tracks will be rendered into external windows beyond the control of the application.
            self.player.set_xwindow(self.get_window().get_xid())
            # print(self.player.get_xwindow())
            # print(self.player.has_vout())
            return True

        # Embed and set size.
        self.connect("realize", handle_embed)
        self.set_size_request(width, height)


def main():
    # We need to initialize X11 threads so we can use hardware decoding.
    # `libX11.so.6` fix for Fedora 33
    x11 = None
    for lib in ["libX11.so", "libX11.so.6"]:
        try:
            x11 = ctypes.cdll.LoadLibrary(lib)
        except OSError:
            pass
        if x11 is not None:
            x11.XInitThreads()
            break

    dummy_video_path = "/home/jeffshee/Videos/Hidamari/Rem.mp4"
    width, height = 1920 * 0.5, 1080 * 0.5
    vlc_widget = VLCWidget(width, height)

    window = Gtk.Window()
    window.add(vlc_widget)
    window.set_size_request(width, height)
    window.show_all()

    media = vlc_widget.instance.media_new(dummy_video_path)
    # Working
    # media.add_option(":sout=#duplicate{dst=display,dst=display}")

    # Not working
    # media.add_option(":video-splitter=clone")
    # media.add_option(":clone-count=2")

    # media.add_option(":video-filter=invert")
    vlc_widget.player.set_media(media)
    vlc_widget.player.play()

    Gtk.main()


if __name__ == "__main__":
    main()
