"""Converts rows from the old booking system's export (legacy/old_bookings.csv)
into the format of the new backend.

Written years ago for the old system. Nobody remembers every case it handles, and it
has no tests. The plan is to import the old bookings next term, so this code has to
be made safe to change first.

Run it on the sample export:
    python -m legacy.old_format legacy/old_bookings.csv
"""

from __future__ import annotations

from collections.abc import Mapping

ROOMS: dict[str, int] = {"Room A": 1, "Room B": 2, "Room C": 3, "Room D": 4}

_TIME_PART_SEPARATOR = " "
_TIME_SEPARATOR = ":"
_PM_MARKER = "PM"
_PM_HOUR_OFFSET = 12
_PAD_WIDTH = 2
_DATE_SEPARATOR = "/"
_ISO_DATE_SEPARATOR = "-"
_SHORT_YEAR_LENGTH = 2
_CENTURY_PREFIX = "20"


def to_24h(text: str) -> str:
    """Convert a legacy time string into 24-hour HH:MM text (preserving legacy quirks)."""
    parts = text.strip().split(_TIME_PART_SEPARATOR)
    time_parts = parts[0].split(_TIME_SEPARATOR)
    hour = int(time_parts[0])
    minute = time_parts[1]
    if len(parts) > 1 and parts[1] == _PM_MARKER:
        hour += _PM_HOUR_OFFSET
    return f"{str(hour).zfill(_PAD_WIDTH)}{_TIME_SEPARATOR}{minute}"


def parse_old_row(row: Mapping[str, str]) -> dict[str, int | str]:
    """Parse one CSV dict row from the legacy export into the new booking shape."""
    room_id = ROOMS[row["room"].strip()]
    date_parts = row["day"].strip().split(_DATE_SEPARATOR)
    month = date_parts[0]
    day_of_month = date_parts[1]
    year = date_parts[2]
    if len(year) == _SHORT_YEAR_LENGTH:
        year = _CENTURY_PREFIX + year
    date = (
        f"{year}{_ISO_DATE_SEPARATOR}"
        f"{month.zfill(_PAD_WIDTH)}{_ISO_DATE_SEPARATOR}"
        f"{day_of_month.zfill(_PAD_WIDTH)}"
    )
    raw_name = row["who"].strip()
    booked_by = raw_name[0].upper() + raw_name[1:]
    return {
        "room_id": room_id,
        "date": date,
        "start": to_24h(row["from"]),
        "end": to_24h(row["to"]),
        "booked_by": booked_by,
    }


if __name__ == "__main__":
    import csv
    import sys

    with open(sys.argv[1], newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            print(parse_old_row(row))
