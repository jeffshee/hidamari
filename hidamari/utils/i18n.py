import gettext
import locale
import os
from hidamari.config.app_config import DOMAIN
from hidamari.config.build_config import LOCALEDIR # type: ignore

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
