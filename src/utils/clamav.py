from src.config.paths_config import CLAMAV_DATABASE_DIR, CLAMAV_FRESHCLAM_CONFIG_PATH
from src.config.stores_config import DEFAULT_PREFERENCES
from src.utils.process import report_result, run_async_process
from src.stores.freshclam_config_store import load_freshclam_config
from src.stores.preferences_store import get_preference_bool
from src.messages.messages import NO_FILES_AVAILABLE_FOR_SCANNING, UNKNOWN

# Ensure the config file exists before any of the methods that rely on it
load_freshclam_config()


def get_clamscan_args_from_preferences() -> list[str]:
    args = []

    for key in DEFAULT_PREFERENCES["clamscan"].keys():
        if get_preference_bool("clamscan", key):
            args.append("--" + key.replace("_", "-"))

    return args


def scan_for_malware(target: list[str], callback: callable) -> None:
    if not target:
        report_result(callback, False, NO_FILES_AVAILABLE_FOR_SCANNING)
        return

    command_args = ["clamscan", "--no-summary", "-i"]

    # Inject dynamic args based on preferences
    command_args += get_clamscan_args_from_preferences()

    # Append database dir and target paths
    command_args += ["-d", CLAMAV_DATABASE_DIR]
    command_args += target

    run_async_process(command_args, callback)


def extract_infections_from_scan_result(message: str) -> list:
    infections = []
    for line in message.strip().splitlines():
        if line.endswith("FOUND"):
            filepath, virus = line.rsplit(":", 1)
            infections.append(
                {
                    "file": filepath.strip(),
                    "signature": virus.replace("FOUND", "").strip(),
                }
            )

    return infections


def __extract_clamav_version_info(message: str) -> dict:
    result = {"engine": UNKNOWN, "db_version": UNKNOWN, "db_date": UNKNOWN}

    try:
        parts = message.strip().split("/")
        if len(parts) > 0:
            result["engine"] = parts[0].strip()
        if len(parts) > 1:
            result["db_version"] = parts[1].strip()
        if len(parts) > 2:
            result["db_date"] = parts[2].strip()
    except AttributeError:
        pass

    return result


def get_clamav_version(on_ready: callable) -> None:
    command_args = ["clamscan", "-d", CLAMAV_DATABASE_DIR, "--version"]

    def handle_result(success: bool, message: str):
        if not success:
            message = ""  # Make version info unknown
        version_info = __extract_clamav_version_info(message)
        on_ready(version_info)

    run_async_process(command_args, handle_result)


def update_malware_definitions(on_ready: callable) -> None:
    command_args = [
        "freshclam",
        "--quiet",
        f"--config-file={CLAMAV_FRESHCLAM_CONFIG_PATH}",
    ]

    def handle_result(success: bool, message: str):
        on_ready(success, message)

    run_async_process(command_args, handle_result)


def is_ready_to_scan(version_info: dict) -> bool:
    return all(
        version_info.get(key) != UNKNOWN for key in ("engine", "db_version", "db_date")
    )
