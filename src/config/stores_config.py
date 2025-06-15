from src.config.paths_config import CLAMAV_DATABASE_DIR

DEFAULT_FRESHCLAM_CONFIG = {
    "DatabaseMirror": "database.clamav.net",
    "DatabaseDirectory": CLAMAV_DATABASE_DIR,
}


"""
IMPORTANT:
- 'clamscan' keys must be boolean and exactly correspond to
  valid clamscan CLI flags (underscores replaced by hyphens).
"""
DEFAULT_PREFERENCES = {
    "clamscan": {
        "recursive": "false",
        "detect_pua": "false",
        "detect_structured": "false",
        "heuristic_alerts": "true",
    },
    "logbook": {"delete_on_exit": "false"},
    "freshclam": {"auto_update_on_start": "false"},
}
