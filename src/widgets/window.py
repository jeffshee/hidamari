from gi.repository import Adw, Gtk, Gio
from src.config.paths_config import WINDOW_RESOURCE_PATH, USER_DATA_DIR
from src.config.ui_config import APP_NAME, MENU_TOOLTIP_TEXT, MENU_ITEMS
from src.stores.preferences_store import get_preference_bool

from src.widgets.gallery.gallery import Gallery
from src.widgets.logbook.logbook import Logbook
from src.widgets.update.update import Update

from src.messages.messages import GALLERY, LOGBOOK, UPDATE


@Gtk.Template(resource_path=WINDOW_RESOURCE_PATH)
class Window(Adw.ApplicationWindow):
    __gtype_name__ = "Window"

    toolbar_view: Adw.ToolbarView = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.application = self.get_application()

        self.__setup_title()
        self.__setup_view_stack()
        self.__setup_view_switcher()
        self.__setup_menu_button()
        self.__setup_header_bar()
        self.__setup_toolbar_view()
        self.__add_menu_items()
        self.__handle_startup_routing()

    def __setup_title(self):
        self.set_title(APP_NAME)

    def __setup_view_stack(self):
        self.view_stack = Adw.ViewStack()

    def __setup_view_switcher(self):
        self.view_switcher = Adw.ViewSwitcher()
        self.view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        self.view_switcher.set_stack(self.view_stack)

    def __setup_menu_button(self):
        self.menu_section = Gio.Menu()
        self.menu_model = Gio.Menu()
        self.menu_model.append_section(None, self.menu_section)

        self.menu_button = Gtk.MenuButton.new()
        self.menu_button.set_tooltip_text(MENU_TOOLTIP_TEXT)
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_property("primary", True)
        self.menu_button.set_menu_model(self.menu_model)

    def __setup_header_bar(self):
        self.header_bar = Adw.HeaderBar()
        self.header_bar.set_title_widget(self.view_switcher)
        self.header_bar.pack_end(self.menu_button)

    def __setup_toolbar_view(self):
        self.toolbar_view.add_top_bar(self.header_bar)
        self.toolbar_view.set_content(self.view_stack)

    def __add_menu_items(self):
        for name, action in MENU_ITEMS:
            self.menu_section.append(name, action)

    def __add_gallery_tab(self):
        self.gallery = Gallery()
        self.view_stack.add_titled(self.gallery, "gallery", GALLERY)
        self.view_stack.get_page(self.gallery).set_icon_name(
            "image-x-generic-symbolic"
        )

    def __add_logbook_tab(self):
        self.logbook = Logbook(application=self.application, window=self)
        self.view_stack.add_titled(self.logbook, "logbook", LOGBOOK)
        self.view_stack.get_page(self.logbook).set_icon_name(
            "x-office-document-symbolic"
        )

    def __add_update_tab(self, auto_update_mode=False):
        self.update = Update(auto_update_mode)
        if auto_update_mode:
            self.update.connect(
                "auto-update-success", lambda w: self.__render_main_interface()
            )

        self.view_stack.add_titled(self.update, "update", UPDATE)
        self.view_stack.get_page(self.update).set_icon_name("view-refresh-symbolic")

    def __render_main_interface(self):
        for page in self.view_stack.get_pages():
            self.view_stack.remove(page.get_child())

        self.__add_gallery_tab()
        self.__add_logbook_tab()
        self.__add_update_tab()

    def __handle_startup_routing(self):
        if get_preference_bool("freshclam", "auto_update_on_start"):
            self.__add_update_tab(auto_update_mode=True)
        else:
            self.__render_main_interface()
