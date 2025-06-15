from gi.repository import Gtk


class ConditionalStack(Gtk.Stack):
    def __init__(self):
        super().__init__()
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.__views = {}

    def add_view(self, name: str, widget: Gtk.Widget):
        self.__views[name] = widget
        self.add_named(widget, name)

    def set_state(self, name: str):
        if name in self.__views:
            self.set_visible_child_name(name)

    def clear(self):
        for child in self.get_children():
            self.remove(child)
        self.__views.clear()
