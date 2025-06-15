from hidamari.messages.messages import (
    QUIT,
    PREFERENCES,
    ABOUT,
    SHOW_SHORTCUTS,
    GENERAL,
)

SHORTCUT_TITLES = {
    "quit": QUIT,
    "preferences": PREFERENCES,
    "about": ABOUT,
    "shortcuts": SHOW_SHORTCUTS,
}

SHORTCUTS = {
    GENERAL: {
        "quit": ["<primary>q"],
        "about": ["F1"],
        "preferences": ["<primary>comma"],
        "shortcuts": ["<primary>slash"],
    },
}
