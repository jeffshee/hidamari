import os
import shutil
import tempfile
import configparser
import threading
import fcntl
from contextlib import contextmanager
from hidamari.config.paths_config import PREFERENCES_PATH
from hidamari.config.stores_config import DEFAULT_PREFERENCES

"""
Internal core (not for import)
"""

__config_cache: configparser.ConfigParser | None = None
__config_lock = threading.RLock()


@contextmanager
def flock_shared(file_obj):
    """Context manager for shared (read) lock on a file object."""
    fcntl.flock(file_obj.fileno(), fcntl.LOCK_SH)
    try:
        yield
    finally:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


@contextmanager
def flock_exclusive(file_obj):
    """Context manager for exclusive (write) lock on a file object."""
    fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


def __read_config() -> configparser.ConfigParser:
    global __config_cache
    with __config_lock:
        if __config_cache is None:
            config = configparser.ConfigParser(interpolation=None)
            if os.path.exists(PREFERENCES_PATH):
                try:
                    with open(PREFERENCES_PATH, "r", encoding="utf-8") as f:
                        with flock_shared(f):
                            config.read_file(f)
                except Exception:
                    __write_preferences(DEFAULT_PREFERENCES)
                    config = configparser.ConfigParser(interpolation=None)
                    with open(PREFERENCES_PATH, "r", encoding="utf-8") as f:
                        with flock_shared(f):
                            config.read_file(f)
            __config_cache = config
        return __config_cache


def __write_config_atomic(config: configparser.ConfigParser):
    global __config_cache
    with __config_lock:
        with tempfile.NamedTemporaryFile(
            "w", delete=False, encoding="utf-8"
        ) as tmpfile:
            config.write(tmpfile)
            tmp_path = tmpfile.name

        with open(PREFERENCES_PATH, "a+") as f:
            with flock_exclusive(f):
                try:
                    shutil.move(tmp_path, PREFERENCES_PATH)
                except Exception:
                    os.remove(tmp_path)
                    raise

        __config_cache = config


def __write_preferences(prefs: dict):
    config = configparser.ConfigParser(interpolation=None)
    for section, kv in prefs.items():
        config.add_section(section)
        for key, value in kv.items():
            config.set(section, key, value)
    __write_config_atomic(config)


def __initialize_preferences():
    """Ensure preferences exist and are migrated if needed."""
    if not os.path.exists(PREFERENCES_PATH):
        __write_preferences(DEFAULT_PREFERENCES)
        return

    config = __read_config()
    changed = False

    for section, default_keys in DEFAULT_PREFERENCES.items():
        if not config.has_section(section):
            config.add_section(section)
            changed = True
        for key, value in default_keys.items():
            if not config.has_option(section, key):
                config.set(section, key, value)
                changed = True

    for section in list(config.sections()):
        if section not in DEFAULT_PREFERENCES:
            config.remove_section(section)
            changed = True
            continue

        default_keys = DEFAULT_PREFERENCES[section]
        for key in list(config.options(section)):
            if key not in default_keys:
                config.remove_option(section, key)
                changed = True

    if changed:
        __write_config_atomic(config)


def __get_preference(section: str, key: str) -> str | None:
    with __config_lock:
        config = __read_config()
        if config.has_section(section):
            return config.get(section, key, fallback=None)
        return None


def __set_preference(section: str, key: str, value: str):
    with __config_lock:
        config = __read_config()
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, key, value)
        __write_config_atomic(config)


"""
Public, type-conscious API
"""


def force_reload_preferences():
    """Force a reload of preferences from src.disk (if modified externally)."""
    global __config_cache
    with __config_lock:
        __config_cache = None


def reset_preferences():
    """Reset all preferences to their default values."""
    global __config_cache
    with __config_lock:
        __write_preferences(DEFAULT_PREFERENCES)
        __config_cache = None


def list_preferences_sections() -> list[str]:
    with __config_lock:
        return __read_config().sections()


def list_preferences_keys(section: str) -> list[str]:
    with __config_lock:
        config = __read_config()
        if config.has_section(section):
            return config.options(section)
        return []


def get_preference_str(section: str, key: str) -> str | None:
    return __get_preference(section, key)


def get_preference_int(section: str, key: str) -> int | None:
    value = __get_preference(section, key)
    if value is not None:
        try:
            return int(value)
        except ValueError:
            return None
    return None


def get_preference_bool(section: str, key: str) -> bool | None:
    value = __get_preference(section, key)
    if value is not None:
        return value.lower() in {"1", "true", "yes", "on"}
    return None


def set_preference_str(section: str, key: str, value: str):
    __set_preference(section, key, value)


def set_preference_int(section: str, key: str, value: int):
    __set_preference(section, key, str(value))


def set_preference_bool(section: str, key: str, value: bool):
    __set_preference(section, key, "true" if value else "false")


def delete_preference(section: str, key: str):
    with __config_lock:
        config = __read_config()
        if config.has_section(section) and config.has_option(section, key):
            config.remove_option(section, key)
            __write_config_atomic(config)


# Auto-init and migrate
__initialize_preferences()
