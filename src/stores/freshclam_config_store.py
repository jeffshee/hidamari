import os
import tempfile
import shutil
from .paths_config import CLAMAV_FRESHCLAM_CONFIG_PATH
from .stores_config import DEFAULT_FRESHCLAM_CONFIG


def __initialize_freshclam_config():
    if not os.path.exists(CLAMAV_FRESHCLAM_CONFIG_PATH):
        __write_config_atomic(DEFAULT_FRESHCLAM_CONFIG)


def __read_config() -> dict:
    config = {}

    if not os.path.exists(CLAMAV_FRESHCLAM_CONFIG_PATH):
        __initialize_freshclam_config()

    with open(CLAMAV_FRESHCLAM_CONFIG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                key, value = parts
                config[key] = value

    return config


def __write_config_atomic(config: dict):
    """Write config atomically to prevent corruption."""
    dir_name = os.path.dirname(CLAMAV_FRESHCLAM_CONFIG_PATH)
    with tempfile.NamedTemporaryFile(
        "w", dir=dir_name, delete=False, encoding="utf-8"
    ) as tmpfile:
        for key, value in config.items():
            tmpfile.write(f"{key} {value}\n")
        temp_path = tmpfile.name
    shutil.move(temp_path, CLAMAV_FRESHCLAM_CONFIG_PATH)


def load_freshclam_config():
    """Ensure the freshclam configuration is initialized (no-op)."""
    pass


def get_freshclam_config(key: str) -> str | None:
    config = __read_config()
    return config.get(key)


def set_freshclam_config(key: str, value: str):
    config = __read_config()
    config[key] = value
    __write_config_atomic(config)


def delete_freshclam_config(key: str):
    config = __read_config()
    if key in config:
        del config[key]
        __write_config_atomic(config)


# Auto-create config on import
__initialize_freshclam_config()
