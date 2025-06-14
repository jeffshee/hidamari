from gi.repository import Gtk

APP = "Hidamari"
DEVELOPER = "zynequ"
RELEASE_YEAR = "2025"

LICENSE = Gtk.License.GPL_3_0

DOMAIN = APP.lower()
NAMESPACE = ("page", "codeberg", DEVELOPER, APP)
APP_ID = ".".join(NAMESPACE)

REPOSITORY_URL = f"https://codeberg.org/{DEVELOPER}/{APP}"
ISSUES_URL = f"{REPOSITORY_URL}/issues"

WEBLATE_URL = "https://translate.codeberg.org"
TRANSLATE_URL = f"{WEBLATE_URL}/projects/{DOMAIN}"
TRANSLATE_CREDITS_URL = f"{WEBLATE_URL}/user/?q=%20contributes:{DOMAIN}"
