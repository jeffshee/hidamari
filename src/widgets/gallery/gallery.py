from gi.repository import Gtk, GObject, Pango
from src.widgets.base.conditional_stack import ConditionalStack
from src.widgets.base.base_status_page import BaseStatusPage
from src.messages.messages import UNKNOWN

from src.utils.video import generate_all_video_thumbnails

generate_all_video_thumbnails()



# base mock wallpapers with icon names, no absolute paths
BASE_MOCK_WALLPAPERS = [
    {"title": "Aurora Borealis", "icon_name": "dialog-information-symbolic"},
    {"title": "Nebula", "icon_name": "dialog-warning-symbolic"},
    {"title": "Sunset Glow", "icon_name": "dialog-error-symbolic"},
    {"title": "Mountain Peak", "icon_name": "dialog-question-symbolic"},
    {"title": "Ocean Waves", "icon_name": "folder-pictures-symbolic"},
]

# create a long list by repeating and shuffling base wallpapers
MOCK_GALLERY = []
for i in range(50):  # 50 times repeat to get 250+ items
    for base_item in BASE_MOCK_WALLPAPERS:
        # slightly vary title to distinguish items
        title = f"{base_item['title']} #{i+1}"
        MOCK_GALLERY.append({"title": title, "icon_name": base_item["icon_name"]})



class Gallery(Gtk.Box):
    __gtype_name__ = "Gallery"

    def __init__(self, wallpapers=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)

        # use mock wallpapers if none provided
        self.wallpapers = wallpapers if wallpapers is not None else MOCK_GALLERY

        self.stack = ConditionalStack()
        self.append(self.stack)

        self.__create_gallery_view(self.wallpapers)

    def __create_gallery_view(self, wallpapers: list):
        flowbox = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            column_spacing=12,
            row_spacing=12,
            homogeneous=True
        )
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_halign(Gtk.Align.CENTER)

        for wallpaper in wallpapers:
            item = self.__create_wallpaper_item(wallpaper)
            flowbox.append(item)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(flowbox)

        self.stack.add_named(scroller, "gallery")
        self.stack.set_state("gallery")

    def __create_wallpaper_item(self, wallpaper: dict) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(160, 90)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        preview = Gtk.Image.new_from_file(wallpaper.get("thumbnail", ""))
        preview.set_pixel_size(128)
        preview.set_valign(Gtk.Align.CENTER)
        preview.set_halign(Gtk.Align.CENTER)

        label = Gtk.Label(label=wallpaper.get("title", UNKNOWN))
        label.set_xalign(0.5)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(20)

        box.append(preview)
        box.append(label)

        frame = Gtk.Frame()
        frame.set_child(box)
        return frame

