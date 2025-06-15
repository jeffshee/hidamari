from gi.repository import Adw
from hidamari.config.app_config import (
    DEVELOPER,
    RELEASE_YEAR,
    LICENSE,
    APP_ID,
    REPOSITORY_URL,
    ISSUES_URL,
)
from hidamari.config.build_config import BUILD_VERSION # type: ignore
from hidamari.config.ui_config import APP_NAME, APP_SUMMARY, APP_TRANSLATOR_CREDITS


def show_about_dialog(active_window):
    about = Adw.AboutDialog.new()

    about.set_application_name(APP_NAME)
    about.set_license_type(LICENSE)
    about.set_version(BUILD_VERSION)
    about.set_developer_name(DEVELOPER)
    about.set_developers([DEVELOPER])
    about.set_comments(APP_SUMMARY)
    about.set_copyright(f"© {RELEASE_YEAR} {DEVELOPER}")
    about.set_website(REPOSITORY_URL)
    about.set_issue_url(ISSUES_URL)
    about.set_application_icon(APP_ID)
    about.set_translator_credits(APP_TRANSLATOR_CREDITS)

    about.present(active_window)
