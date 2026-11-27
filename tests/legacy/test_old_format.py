"""Characterization tests pinning current behavior of legacy.old_format."""

import csv
from pathlib import Path

import pytest

from legacy.old_format import parse_old_row, to_24h

SAMPLE_CSV = Path(__file__).resolve().parents[2] / "legacy" / "old_bookings.csv"


def _base_row(**overrides: str) -> dict[str, str]:
    row = {
        "room": "Room A",
        "day": "3/14/2031",
        "from": "9:00 AM",
        "to": "10:30 AM",
        "who": "ana",
    }
    row.update(overrides)
    return row


def test_legacy_to_24h_normal_am_pm_and_bare_times():
    assert to_24h("9:00 AM") == "09:00"
    assert to_24h("1:00 PM") == "13:00"
    assert to_24h(" 8:30 ") == "08:30"


# BUG: pinned, not fixed
def test_legacy_to_24h_noon_pm_adds_twelve_hours():
    assert to_24h("12:30 PM") == "24:30"


# BUG: pinned, not fixed
def test_legacy_to_24h_midnight_am_stays_twelve():
    assert to_24h("12:00 AM") == "12:00"


# BUG: pinned, not fixed
def test_legacy_to_24h_lowercase_pm_is_ignored():
    assert to_24h("3:00 pm") == "03:00"


# BUG: pinned, not fixed
def test_legacy_to_24h_single_digit_minute_not_zero_padded():
    assert to_24h("9:5 AM") == "09:5"


# BUG: pinned, not fixed
def test_legacy_to_24h_extra_space_before_pm_is_ignored():
    assert to_24h("9:00  PM") == "09:00"


def test_legacy_to_24h_exceptions():
    with pytest.raises(IndexError):
        to_24h("900")
    with pytest.raises(ValueError):
        to_24h("")
    with pytest.raises(ValueError):
        to_24h("abc:00")
    with pytest.raises(AttributeError):
        to_24h(None)


def test_legacy_parse_old_row_normal_cases_and_rooms():
    assert parse_old_row(_base_row()) == {
        "room_id": 1,
        "date": "2031-03-14",
        "start": "09:00",
        "end": "10:30",
        "booked_by": "Ana",
    }
    assert parse_old_row(
        _base_row(
            room="  Room B ",
            day="3/14/2031",
            **{"from": "1:00 PM", "to": "2:00 PM", "who": "  bo chen"},
        )
    ) == {
        "room_id": 2,
        "date": "2031-03-14",
        "start": "13:00",
        "end": "14:00",
        "booked_by": "Bo chen",
    }
    assert parse_old_row(
        _base_row(
            room="Room C",
            day="12/1/31",
            **{"from": "10:00 AM", "to": "11:30 AM", "who": "Priya"},
        )
    ) == {
        "room_id": 3,
        "date": "2031-12-01",
        "start": "10:00",
        "end": "11:30",
        "booked_by": "Priya",
    }
    assert parse_old_row(
        _base_row(
            room="Room D",
            day="03/02/2031",
            **{"from": "8:30", "to": "10:00", "who": "lee"},
        )
    ) == {
        "room_id": 4,
        "date": "2031-03-02",
        "start": "08:30",
        "end": "10:00",
        "booked_by": "Lee",
    }


# BUG: pinned, not fixed
def test_legacy_parse_old_row_pins_odd_sample_csv_rows():
    with SAMPLE_CSV.open(newline="", encoding="utf-8") as f:
        rows = [parse_old_row(row) for row in csv.DictReader(f)]

    assert rows[4:] == [
        {
            "room_id": 1,
            "date": "2031-03-15",
            "start": "24:30",
            "end": "14:00",
            "booked_by": "Sam",
        },
        {
            "room_id": 2,
            "date": "2031-03-15",
            "start": "03:00",
            "end": "04:00",
            "booked_by": "Mia",
        },
        {
            "room_id": 3,
            "date": "2031-03-16",
            "start": "09:5",
            "end": "10:00",
            "booked_by": "Omar",
        },
    ]


def test_legacy_parse_old_row_unknown_room_and_missing_keys_raise_key_error():
    with pytest.raises(KeyError):
        parse_old_row(_base_row(room="Room Z"))
    for key in ("room", "day", "from", "to", "who"):
        incomplete = _base_row()
        del incomplete[key]
        with pytest.raises(KeyError):
            parse_old_row(incomplete)


def test_legacy_parse_old_row_malformed_day_and_empty_name_raise_index_error():
    with pytest.raises(IndexError):
        parse_old_row(_base_row(day="3/14"))
    with pytest.raises(IndexError):
        parse_old_row(_base_row(day="2031-03-14"))
    with pytest.raises(IndexError):
        parse_old_row(_base_row(who=""))
    with pytest.raises(IndexError):
        parse_old_row(_base_row(who="   "))


def test_legacy_parse_old_row_bad_times_propagate_exceptions():
    with pytest.raises(IndexError):
        parse_old_row(_base_row(**{"from": "900"}))
    with pytest.raises(ValueError):
        parse_old_row(_base_row(to="xx:00"))
