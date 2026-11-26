"""Acceptance tests for R1 (list rooms) and R2 (list bookings)."""

import pytest

EXPECTED_ROOMS = [
    {"id": 1, "name": "Quiet Room A", "capacity": 2},
    {"id": 2, "name": "Quiet Room B", "capacity": 2},
    {"id": 3, "name": "Group Room C", "capacity": 6},
    {"id": 4, "name": "Group Room D", "capacity": 8},
]

VALID_BOOKING = {
    "room_id": 1,
    "date": "2031-03-14",
    "start": "09:00",
    "end": "10:00",
    "booked_by": "Ana",
}


def _assert_error(response, expected_status: int, expected_error: str) -> None:
    assert response.status_code == expected_status
    body = response.json()
    assert isinstance(body, dict)
    assert set(body.keys()) == {"error", "message"}
    assert body["error"] == expected_error
    assert isinstance(body["message"], str)


# --- R1: List rooms ---


def test_r1_list_rooms_returns_four_rooms_in_id_order(client):
    """R1: GET /api/rooms returns the 4 fixed rooms ordered by id 1..4."""
    resp = client.get("/api/rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    assert isinstance(rooms, list)
    assert rooms == EXPECTED_ROOMS
    for room in rooms:
        assert set(room.keys()) == {"id", "name", "capacity"}


# --- R2: List bookings ---


def test_r2_list_bookings_empty_date_returns_empty_list(client):
    """R2: A valid date with no bookings returns 200 and an empty list."""
    resp = client.get("/api/bookings", params={"date": "2031-03-14"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_r2_list_bookings_leap_day_allowed(client):
    """R2: A valid leap-year Feb 29 date is accepted."""
    resp = client.get("/api/bookings", params={"date": "2032-02-29"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_r2_list_bookings_ordered_by_room_id_then_start_and_filtered_by_date(client):
    """R2: Bookings for the requested date are returned ordered by room_id, then start."""
    to_create = [
        {"room_id": 3, "date": "2031-03-14", "start": "10:00", "end": "11:00", "booked_by": "Cara"},
        {"room_id": 1, "date": "2031-03-14", "start": "14:00", "end": "15:00", "booked_by": "Ben"},
        {"room_id": 1, "date": "2031-03-14", "start": "09:00", "end": "10:00", "booked_by": "Ana"},
        {"room_id": 2, "date": "2031-03-14", "start": "08:00", "end": "09:00", "booked_by": "Dan"},
        {"room_id": 1, "date": "2031-03-15", "start": "09:00", "end": "10:00", "booked_by": "Eli"},
    ]
    for payload in to_create:
        created = client.post("/api/bookings", json=payload)
        assert created.status_code == 201

    resp = client.get("/api/bookings", params={"date": "2031-03-14"})
    assert resp.status_code == 200
    bookings = resp.json()
    assert len(bookings) == 4
    for booking in bookings:
        assert set(booking.keys()) == {"id", "room_id", "date", "start", "end", "booked_by"}
    assert [(b["room_id"], b["start"], b["booked_by"]) for b in bookings] == [
        (1, "09:00", "Ana"),
        (1, "14:00", "Ben"),
        (2, "08:00", "Dan"),
        (3, "10:00", "Cara"),
    ]


def test_r2_list_bookings_filtered_by_room_id(client):
    """R2: Optional room_id returns only that room's bookings on that date, ordered by start."""
    for payload in [
        {"room_id": 1, "date": "2031-03-14", "start": "13:00", "end": "14:00", "booked_by": "Ben"},
        {"room_id": 1, "date": "2031-03-14", "start": "09:00", "end": "10:00", "booked_by": "Ana"},
        {"room_id": 2, "date": "2031-03-14", "start": "10:00", "end": "11:00", "booked_by": "Cara"},
    ]:
        assert client.post("/api/bookings", json=payload).status_code == 201

    resp = client.get("/api/bookings", params={"date": "2031-03-14", "room_id": 1})
    assert resp.status_code == 200
    bookings = resp.json()
    assert [(b["room_id"], b["start"]) for b in bookings] == [(1, "09:00"), (1, "13:00")]

    empty_room_resp = client.get("/api/bookings", params={"date": "2031-03-14", "room_id": 4})
    assert empty_room_resp.status_code == 200
    assert empty_room_resp.json() == []


def test_r2_list_bookings_missing_date_rejected(client):
    """R2: Missing date query parameter returns 422 invalid_request and changes nothing."""
    created = client.post("/api/bookings", json=VALID_BOOKING).json()

    resp = client.get("/api/bookings")
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": "2031-03-14"}).json() == [created]


@pytest.mark.parametrize(
    "bad_date",
    [
        "",
        "2031/03/14",
        "2031-3-14",
        "2031-03-4",
        "14-03-2031",
        "2031-03-14T09:00",
        "not-a-date",
        "2031-02-29",
        "2031-04-31",
        "2031-13-01",
        "2031-00-10",
        "2031-01-00",
    ],
)
def test_r2_list_bookings_invalid_date_rejected(client, bad_date):
    """R2: Badly formatted or nonexistent calendar date returns 422 invalid_request."""
    created = client.post("/api/bookings", json=VALID_BOOKING).json()

    resp = client.get("/api/bookings", params={"date": bad_date})
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": "2031-03-14"}).json() == [created]


@pytest.mark.parametrize("bad_room_id", ["abc", "1.5", "", "true"])
def test_r2_list_bookings_non_integer_room_id_rejected(client, bad_room_id):
    """R2: Non-integer room_id query parameter returns 422 invalid_request."""
    created = client.post("/api/bookings", json=VALID_BOOKING).json()

    resp = client.get("/api/bookings", params={"date": "2031-03-14", "room_id": bad_room_id})
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": "2031-03-14"}).json() == [created]


@pytest.mark.parametrize("unknown_room_id", [0, -1, 5, 99])
def test_r2_list_bookings_unknown_room_id_returns_404(client, unknown_room_id):
    """R2: Integer room_id outside 1..4 returns 404 room_not_found."""
    created = client.post("/api/bookings", json=VALID_BOOKING).json()

    resp = client.get("/api/bookings", params={"date": "2031-03-14", "room_id": unknown_room_id})
    _assert_error(resp, 404, "room_not_found")
    assert client.get("/api/bookings", params={"date": "2031-03-14"}).json() == [created]
