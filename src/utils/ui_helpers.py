from src.messages.messages import (
    HOSTILES,
    REPORT,
    DATE,
    HOSTILES_DETECTED,
    DURATION,
    ENGINE,
    UNKNOWN,
)


def get_logbook_structure(entry):
    structure = []

    # Hostiles page only if hostile_list exists and is not empty
    if entry.get("hostile_list"):
        hostiles_rows = [
            {"title": hostile["signature"], "subtitle": hostile["file"]}
            for hostile in entry["hostile_list"]
        ]

        structure.append(
            {
                "title": HOSTILES,
                "icon": "face-devilish-symbolic",
                "groups": [{"rows": hostiles_rows}],
            }
        )

    # Report page always present
    engine_parts = []
    for key in ["engine", "db_version", "db_date"]:
        value = entry.get(key)
        if value:
            engine_parts.append(str(value))
    engine_info = "\n".join(engine_parts) if engine_parts else UNKNOWN

    structure.append(
        {
            "title": REPORT,
            "icon": "x-office-presentation-symbolic",
            "groups": [
                {
                    "rows": [
                        {
                            "title": DATE,
                            "subtitle": entry["timestamp"],
                        },
                        {
                            "title": HOSTILES_DETECTED,
                            "subtitle": str(entry["hostile_count"]),
                        },
                        {
                            "title": DURATION,
                            "subtitle": entry.get("duration") or UNKNOWN,
                        },
                        {
                            "title": ENGINE,
                            "subtitle": engine_info,
                        },
                    ],
                }
            ],
        }
    )

    return structure
