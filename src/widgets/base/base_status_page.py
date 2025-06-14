from gi.repository import Gtk, Adw


class BaseStatusPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.page = Adw.StatusPage()
        self.page.set_valign(Gtk.Align.FILL)
        self.page.set_halign(Gtk.Align.FILL)
        self.page.set_hexpand(True)
        self.page.set_vexpand(True)
        self.append(self.page)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.button_box.set_halign(Gtk.Align.CENTER)
        self.page.set_child(self.button_box)

        self._buttons = []

    def set_status(self, title: str, description: str, icon_name: str):
        self.page.set_title(title)
        self.page.set_description(description)
        self.page.set_icon_name(icon_name)

    def clear_buttons(self):
        for btn in self._buttons:
            self.button_box.remove(btn)
        self._buttons.clear()

    def add_button(
        self, button: Gtk.Button, suggested: bool = False, destructive: bool = False
    ):
        if suggested:
            button.add_css_class("suggested-action")

        if destructive:
            button.add_css_class("destructive-action")

        button.add_css_class("pill")
        button.set_valign(Gtk.Align.CENTER)
        button.set_halign(Gtk.Align.CENTER)

        self.button_box.append(button)
        self._buttons.append(button)
