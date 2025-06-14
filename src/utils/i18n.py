import gettext
import locale
import os
from .app_config import DOMAIN
from .build_config import LOCALEDIR

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    try:
        os.environ["LANG"] = "C.UTF-8"
        locale.setlocale(locale.LC_ALL, "C.UTF-8")
    except locale.Error:
        os.environ["LANG"] = "C"
        locale.setlocale(locale.LC_ALL, "C")

gettext.bindtextdomain(DOMAIN, LOCALEDIR)
gettext.textdomain(DOMAIN)

_ = gettext.gettext
