"""Business rules and validation logic for RoomBook (spec section 5)."""

from __future__ import annotations

import datetime
import re

from app import repository
from app.models import CreateBookingRequest, ServiceError

_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TIME_RE = re.compile(r"[0-9]{2}:[0-9]{2}")
_INT_RE = re.compile(r"-?[0-9]+")

_REQUIRED_CREATE_FIELDS = ("room_id", "date", "start", "end", "booked_by")
_OPEN_MINUTES = 8 * 60
_CLOSE_MINUTES = 22 * 60
_MAX_DURATION_MINUTES = 180
_MAX_NAME_LENGTH = 40
_SQLITE_INT_MIN = -(1 << 63)
_SQLITE_INT_MAX = (1 << 63) - 1


def _validate_date(value: object) -> str:
    """Validate YYYY-MM-DD format and real calendar date (R2, R3)."""
    if not isinstance(value, str) or _DATE_RE.fullmatch(value) is None:
        raise ServiceError(
            422,
            "invalid_request",
            "date must be in YYYY-MM-DD format.",
        )
    try:
        datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ServiceError(
            422,
            "invalid_request",
            "date must be a valid calendar date.",
        ) from exc
    return value


def _parse_bounded_int(raw: str) -> int | None:
    """Parse a base-10 integer string, returning None if outside 64-bit SQLite range."""
    negative = raw.startswith("-")
    digits = (raw[1:] if negative else raw).lstrip("0") or "0"
    if len(digits) > 19:
        return None
    value = int(f"-{digits}" if negative and digits != "0" else digits)
    if not (_SQLITE_INT_MIN <= value <= _SQLITE_INT_MAX):
        return None
    return value


def _parse_sqlite_int_str(raw: str, field_name: str) -> int | None:
    """Parse a strict base-10 integer string, returning None if outside 64-bit SQLite range."""
    if _INT_RE.fullmatch(raw) is None:
        raise ServiceError(
            422,
            "invalid_request",
            f"{field_name} must be an integer.",
        )
    return _parse_bounded_int(raw)


def parse_json_int(raw: str) -> int:
    """Parse JSON integer tokens safely without triggering int_max_str_digits ValueError."""
    value = _parse_bounded_int(raw)
    if value is not None:
        return value
    return (_SQLITE_INT_MIN - 1) if raw.startswith("-") else (_SQLITE_INT_MAX + 1)


def _parse_clock_minutes(value: object, field_name: str) -> int:
    """Validate HH:MM (00:00..23:59) and return minutes since midnight (R3)."""
    if not isinstance(value, str) or _TIME_RE.fullmatch(value) is None:
        raise ServiceError(
            422,
            "invalid_request",
            f"{field_name} must be in HH:MM format.",
        )
    hours = int(value[:2])
    minutes = int(value[3:])
    if hours > 23 or minutes > 59:
        raise ServiceError(
            422,
            "invalid_request",
            f"{field_name} must be a valid time between 00:00 and 23:59.",
        )
    return hours * 60 + minutes


def init_db(db_path: str) -> None:
    """Initialize database schema and rooms."""
    repository.init_db(db_path)


def list_rooms(db_path: str) -> list[dict]:
    """Return the four rooms ordered by id (R1)."""
    return repository.list_rooms(db_path)


def list_bookings(
    db_path: str, date: str | None, room_id: str | None
) -> list[dict]:
    """Return bookings for a date and optional room_id (R2)."""
    if date is None:
        raise ServiceError(
            422,
            "invalid_request",
            "Query parameter 'date' is required.",
        )
    valid_date = _validate_date(date)

    room_id_int: int | None = None
    if room_id is not None:
        room_id_int = _parse_sqlite_int_str(room_id, "room_id")
        if room_id_int is None or not repository.room_exists(db_path, room_id_int):
            raise ServiceError(
                404,
                "room_not_found",
                "Room was not found.",
            )

    return repository.list_bookings(db_path, valid_date, room_id_int)


def create_booking(db_path: str, payload: object) -> dict:
    """Validate and create a booking enforcing R3..R7 in R9 precedence order."""
    # R3: Request shape, required fields, types, date and HH:MM clock format.
    if not isinstance(payload, dict):
        raise ServiceError(
            422,
            "invalid_request",
            "Request body must be a JSON object.",
        )
    for field in _REQUIRED_CREATE_FIELDS:
        if field not in payload:
            raise ServiceError(
                422,
                "invalid_request",
                f"Missing required field '{field}'.",
            )

    raw_room_id = payload["room_id"]
    if not isinstance(raw_room_id, int) or isinstance(raw_room_id, bool):
        raise ServiceError(
            422,
            "invalid_request",
            "room_id must be an integer.",
        )

    raw_booked_by = payload["booked_by"]
    if not isinstance(raw_booked_by, str):
        raise ServiceError(
            422,
            "invalid_request",
            "booked_by must be a string.",
        )

    valid_date = _validate_date(payload["date"])
    start_minutes = _parse_clock_minutes(payload["start"], "start")
    end_minutes = _parse_clock_minutes(payload["end"], "end")

    req = CreateBookingRequest(
        room_id=raw_room_id,
        date=valid_date,
        start=payload["start"],
        end=payload["end"],
        booked_by=raw_booked_by,
    )

    # R4: Trimmed booked_by length 1..40.
    trimmed_name = req.booked_by.strip()
    if not (1 <= len(trimmed_name) <= _MAX_NAME_LENGTH):
        raise ServiceError(
            422,
            "invalid_name",
            "booked_by must be between 1 and 40 characters after trimming.",
        )

    # R5: 30-minute steps, 08:00..22:00, start < end, max 180 minutes.
    if (
        start_minutes % 30 != 0
        or end_minutes % 30 != 0
        or start_minutes < _OPEN_MINUTES
        or end_minutes > _CLOSE_MINUTES
        or start_minutes >= end_minutes
        or (end_minutes - start_minutes) > _MAX_DURATION_MINUTES
    ):
        raise ServiceError(
            422,
            "invalid_time",
            "Booking must use 30-minute steps within 08:00 to 22:00 and last at most 3 hours.",
        )

    # R6: Room exists.
    if not (_SQLITE_INT_MIN <= req.room_id <= _SQLITE_INT_MAX) or not repository.room_exists(
        db_path, req.room_id
    ):
        raise ServiceError(
            404,
            "room_not_found",
            "Room was not found.",
        )

    # R7: Atomically enforce no overlapping booking in the same room on the same date.
    booking = repository.create_booking(
        db_path,
        req.room_id,
        req.date,
        req.start,
        req.end,
        trimmed_name,
    )
    if booking is None:
        raise ServiceError(
            409,
            "overlap",
            "Booking overlaps an existing booking.",
        )
    return booking


def cancel_booking(db_path: str, raw_booking_id: str) -> None:
    """Cancel an existing booking by integer id (R8)."""
    booking_id = _parse_sqlite_int_str(raw_booking_id, "id")
    if booking_id is None or not repository.delete_booking(db_path, booking_id):
        raise ServiceError(
            404,
            "booking_not_found",
            "Booking was not found.",
        )
