"""Acceptance tests for R3 (request shape), R4 (name), R5 (times), R6 (room), and P1/P2."""

import pytest

BASE_DATE = "2031-03-14"


def _payload(**overrides):
    data = {
        "room_id": 1,
        "date": BASE_DATE,
        "start": "09:00",
        "end": "10:30",
        "booked_by": "Ana",
    }
    data.update(overrides)
    return data


def _assert_error(response, expected_status: int, expected_error: str) -> None:
    assert response.status_code == expected_status
    body = response.json()
    assert isinstance(body, dict)
    assert set(body.keys()) == {"error", "message"}
    assert body["error"] == expected_error
    assert isinstance(body["message"], str)


# --- R3: Request shape (and P1, P2) ---


def test_r3_create_booking_happy_path(client):
    """R3: Valid POST /api/bookings returns 201 and the 6-field booking object."""
    resp = client.post("/api/bookings", json=_payload())
    assert resp.status_code == 201
    booking = resp.json()
    assert set(booking.keys()) == {"id", "room_id", "date", "start", "end", "booked_by"}
    assert isinstance(booking["id"], int)
    assert booking["room_id"] == 1
    assert booking["date"] == BASE_DATE
    assert booking["start"] == "09:00"
    assert booking["end"] == "10:30"
    assert booking["booked_by"] == "Ana"

    listed = client.get("/api/bookings", params={"date": BASE_DATE}).json()
    assert listed == [booking]


def test_r3_extra_fields_ignored_and_p2_capacity_not_enforced(client):
    """R3 & P2: Extra fields (such as id or attendees) are ignored on POST /api/bookings."""
    payload = _payload(id=999, attendees=100, notes="group study")
    resp = client.post("/api/bookings", json=payload)
    assert resp.status_code == 201
    booking = resp.json()
    assert set(booking.keys()) == {"id", "room_id", "date", "start", "end", "booked_by"}
    assert booking["id"] != 999


def test_r3_p1_past_dates_allowed(client):
    """R3 & P1: Dates in the past are accepted and listed like any other date."""
    past_date = "2000-01-15"
    resp = client.post("/api/bookings", json=_payload(date=past_date))
    assert resp.status_code == 201
    booking = resp.json()
    assert booking["date"] == past_date
    assert client.get("/api/bookings", params={"date": past_date}).json() == [booking]


@pytest.mark.parametrize("raw_body", ["", "{bad json", "[]", '"hello"', "123", "null"])
def test_r3_invalid_json_or_non_object_rejected(client, raw_body):
    """R3: Non-JSON or non-object JSON body returns 422 invalid_request and saves nothing."""
    resp = client.post(
        "/api/bookings",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


@pytest.mark.parametrize("missing_field", ["room_id", "date", "start", "end", "booked_by"])
def test_r3_missing_required_field_rejected(client, missing_field):
    """R3: Missing any required field returns 422 invalid_request and saves nothing."""
    payload = _payload()
    del payload[missing_field]
    resp = client.post("/api/bookings", json=payload)
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"room_id": "1"},
        {"room_id": 1.5},
        {"room_id": True},
        {"room_id": None},
        {"date": 20310314},
        {"date": None},
        {"start": 900},
        {"start": None},
        {"end": 1030},
        {"end": None},
        {"booked_by": 123},
        {"booked_by": True},
        {"booked_by": ["Ana"]},
        {"booked_by": None},
    ],
)
def test_r3_wrong_field_types_rejected(client, overrides):
    """R3: Fields of the wrong JSON type return 422 invalid_request and save nothing."""
    resp = client.post("/api/bookings", json=_payload(**overrides))
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


@pytest.mark.parametrize(
    "bad_date",
    [
        "",
        "2031/03/14",
        "2031-3-14",
        "14-03-2031",
        "2031-03-14 ",
        "2031-02-29",
        "2031-04-31",
        "2031-13-01",
        "2031-00-01",
        "2031-01-00",
    ],
)
def test_r3_bad_date_format_or_calendar_day_rejected(client, bad_date):
    """R3: Malformed or nonexistent date returns 422 invalid_request and saves nothing."""
    resp = client.post("/api/bookings", json=_payload(date=bad_date))
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


@pytest.mark.parametrize(
    "field,bad_time",
    [
        ("start", "9:00"),
        ("start", "09:0"),
        ("start", "0900"),
        ("start", "09:00:00"),
        ("start", " 09:00"),
        ("start", "24:00"),
        ("start", "09:60"),
        ("start", "-1:00"),
        ("end", "10:0"),
        ("end", "1000"),
        ("end", "24:00"),
        ("end", "10:60"),
    ],
)
def test_r3_bad_time_format_or_clock_range_rejected(client, field, bad_time):
    """R3: Time not in exact HH:MM (00:00..23:59) returns 422 invalid_request."""
    resp = client.post("/api/bookings", json=_payload(**{field: bad_time}))
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


# --- R4: Name ---


def test_r4_name_is_trimmed_and_stored(client):
    """R4: Leading and trailing whitespace is stripped from booked_by."""
    resp = client.post("/api/bookings", json=_payload(booked_by="  Ana Maria  "))
    assert resp.status_code == 201
    booking = resp.json()
    assert booking["booked_by"] == "Ana Maria"
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json()[0]["booked_by"] == "Ana Maria"


@pytest.mark.parametrize("valid_name", ["A", "a" * 40, "   " + ("b" * 40) + "\t"])
def test_r4_name_length_boundaries_accepted(client, valid_name):
    """R4: Trimmed length of 1 and 40 characters (even with surrounding spaces) is accepted."""
    resp = client.post("/api/bookings", json=_payload(booked_by=valid_name))
    assert resp.status_code == 201
    assert resp.json()["booked_by"] == valid_name.strip()


@pytest.mark.parametrize("invalid_name", ["", "   ", "\t\n ", "a" * 41])
def test_r4_invalid_name_rejected(client, invalid_name):
    """R4: Trimmed length 0 or > 40 returns 422 invalid_name and saves nothing."""
    resp = client.post("/api/bookings", json=_payload(booked_by=invalid_name))
    _assert_error(resp, 422, "invalid_name")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


# --- R5: Times ---


@pytest.mark.parametrize(
    "start,end",
    [
        ("08:00", "08:30"),
        ("21:30", "22:00"),
        ("09:00", "12:00"),
        ("19:00", "22:00"),
    ],
)
def test_r5_valid_time_boundaries_accepted(client, start, end):
    """R5: Boundaries 08:00..22:00, 30-minute steps, and max 180-minute duration succeed."""
    resp = client.post("/api/bookings", json=_payload(start=start, end=end))
    assert resp.status_code == 201


@pytest.mark.parametrize(
    "start,end",
    [
        ("09:15", "10:00"),
        ("09:00", "10:45"),
        ("09:01", "09:30"),
        ("07:30", "08:30"),
        ("00:00", "01:00"),
        ("21:00", "22:30"),
        ("22:00", "23:00"),
        ("10:00", "10:00"),
        ("11:00", "10:00"),
        ("09:00", "12:30"),
        ("08:00", "22:00"),
    ],
)
def test_r5_invalid_times_rejected(client, start, end):
    """R5: Bad step, outside 08:00..22:00, start >= end, or > 180 min gives 422 invalid_time."""
    resp = client.post("/api/bookings", json=_payload(start=start, end=end))
    _assert_error(resp, 422, "invalid_time")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


# --- R6: Room ---


@pytest.mark.parametrize("room_id", [1, 2, 3, 4])
def test_r6_all_four_rooms_can_be_booked(client, room_id):
    """R6: Each of the four defined room ids (1..4) is valid for booking."""
    resp = client.post("/api/bookings", json=_payload(room_id=room_id))
    assert resp.status_code == 201
    assert resp.json()["room_id"] == room_id


@pytest.mark.parametrize("bad_room_id", [0, -1, 5, 999])
def test_r6_unknown_room_id_rejected(client, bad_room_id):
    """R6: Integer room_id not in 1..4 returns 404 room_not_found and saves nothing."""
    resp = client.post("/api/bookings", json=_payload(room_id=bad_room_id))
    _assert_error(resp, 404, "room_not_found")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []
