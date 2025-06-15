from gi.repository import Gtk, GObject, Adw
from src.widgets.base.base_status_page import BaseStatusPage
from src.widgets.base.conditional_stack import ConditionalStack
from src.messages.messages import (
    NO_ITEMS_FOUND,
    NO_ENTRIES_TO_SHOW,
    DELETE,
)


class BaseListView(Gtk.Box):
    __gtype_name__ = "BaseListView"
    __gsignals__ = {
        "row-activated": (GObject.SignalFlags.RUN_FIRST, None, (Gtk.ListBoxRow,))
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.stack = ConditionalStack()
        self.append(self.stack)

        self.__create_list_container()
        self.__create_default_empty_status()

        self.stack.add_view("list", self.scroll)
        self.stack.add_view("empty", self.empty_status)

    def __create_list_container(self):
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.container.set_margin_top(12)
        self.container.set_margin_bottom(12)
        self.container.set_margin_start(30)
        self.container.set_margin_end(30)

        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.connect("row-activated", self.__on_row_activated)

        self.container.append(self.listbox)
        self.scroll.set_child(self.container)

    def __create_default_empty_status(self):
        self.empty_status = BaseStatusPage()
        self.empty_status.set_status(
            NO_ITEMS_FOUND,
            NO_ENTRIES_TO_SHOW,
            "dialog-warning-symbolic",
        )

    def set_empty_status(self, title: str, subtitle: str, icon_name: str):
        self.empty_status.set_status(title, subtitle, icon_name)

    def __on_row_activated(self, listbox, row):
        self.emit("row-activated", row)

    def show_empty(self):
        self.stack.set_state("empty")

    def show_list(self):
        self.stack.set_state("list")

    def clear(self):
        self.listbox.remove_all()

    def set_filter_func(self, func):
        self.listbox.set_filter_func(func)

    def set_sort_func(self, func):
        self.listbox.set_sort_func(func)

    def create_button(
        self,
        icon_name: str,
        tooltip: str = "",
        on_click: callable = None,
        data: object = None,
        halign: Gtk.Align = Gtk.Align.END,
        css_classes: list[str] = ["flat"],
    ) -> Gtk.Button:
        button = Gtk.Button.new_from_icon_name(icon_name)
        button.set_tooltip_text(tooltip)
        button.set_halign(halign)

        for cls in css_classes:
            button.add_css_class(cls)

        if on_click and data:
            button.connect("clicked", on_click, data)

        return button

    def add_row(
        self,
        title: str,
        subtitle: str = "",
        entry: object = None,
        activatable: bool = True,
        selectable: bool = True,
        suffix_icon_name: str = "window-close-symbolic",
        suffix_tooltip: str = DELETE,
        on_suffix_button_click: callable = None,
    ):
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        row.set_activatable(activatable)
        row.set_selectable(selectable)

        if entry:
            row.entry = entry

        if suffix_icon_name and suffix_tooltip and on_suffix_button_click:
            button = self.create_button(
                icon_name=suffix_icon_name,
                tooltip=suffix_tooltip,
                on_click=on_suffix_button_click,
                data=row,
            )
            row.add_suffix(button)

        self.listbox.append(row)
