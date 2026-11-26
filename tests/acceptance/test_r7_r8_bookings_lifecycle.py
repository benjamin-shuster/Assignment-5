"""Acceptance tests for R7 (no overlap, P4) and R8 (cancel, P3)."""

import pytest

BASE_DATE = "2031-03-14"


def _payload(**overrides):
    data = {
        "room_id": 1,
        "date": BASE_DATE,
        "start": "10:00",
        "end": "11:30",
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


# --- R7: No overlap (and P4) ---


@pytest.mark.parametrize(
    "start,end",
    [
        ("10:00", "11:30"),
        ("10:30", "11:00"),
        ("09:30", "12:00"),
        ("09:00", "10:30"),
        ("11:00", "12:00"),
    ],
)
def test_r7_overlapping_bookings_same_room_and_date_rejected(client, start, end):
    """R7: Exact, contained, enclosing, or partial overlap returns 409 overlap and saves nothing."""
    existing = client.post("/api/bookings", json=_payload(start="10:00", end="11:30")).json()

    resp = client.post(
        "/api/bookings",
        json=_payload(start=start, end=end, booked_by="Ben"),
    )
    _assert_error(resp, 409, "overlap")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [existing]


def test_r7_touching_bookings_allowed(client):
    """R7: Bookings that only touch at start/end boundaries do not overlap."""
    assert client.post("/api/bookings", json=_payload(start="10:00", end="11:00")).status_code == 201
    before = client.post(
        "/api/bookings", json=_payload(start="09:00", end="10:00", booked_by="Ben")
    )
    after = client.post(
        "/api/bookings", json=_payload(start="11:00", end="12:00", booked_by="Cara")
    )
    assert before.status_code == 201
    assert after.status_code == 201

    bookings = client.get("/api/bookings", params={"date": BASE_DATE, "room_id": 1}).json()
    assert [(b["start"], b["end"]) for b in bookings] == [
        ("09:00", "10:00"),
        ("10:00", "11:00"),
        ("11:00", "12:00"),
    ]


def test_r7_p4_same_person_back_to_back_slots_allowed(client):
    """R7 & P4: The same person may book back-to-back slots in the same room."""
    first = client.post("/api/bookings", json=_payload(start="09:00", end="10:00", booked_by="Ana"))
    second = client.post("/api/bookings", json=_payload(start="10:00", end="11:00", booked_by="Ana"))
    assert first.status_code == 201
    assert second.status_code == 201


def test_r7_same_time_different_room_allowed(client):
    """R7: Identical time slots in different rooms on the same date do not conflict."""
    assert client.post("/api/bookings", json=_payload(room_id=1)).status_code == 201
    other_room = client.post("/api/bookings", json=_payload(room_id=2))
    assert other_room.status_code == 201


def test_r7_same_time_different_date_allowed(client):
    """R7: Identical time slots in the same room on different dates do not conflict."""
    assert client.post("/api/bookings", json=_payload(date="2031-03-14")).status_code == 201
    other_date = client.post("/api/bookings", json=_payload(date="2031-03-15"))
    assert other_date.status_code == 201


# --- R8: Cancel (and P3) ---


def test_r8_p3_cancel_removes_booking_and_frees_slot(client):
    """R8 & P3: DELETE /api/bookings/{id} needs no auth, returns 204 empty body, and frees slot."""
    created = client.post("/api/bookings", json=_payload(booked_by="Ana")).json()
    booking_id = created["id"]

    delete_resp = client.delete(f"/api/bookings/{booking_id}")
    assert delete_resp.status_code == 204
    assert delete_resp.content == b""

    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []

    rebooked = client.post("/api/bookings", json=_payload(booked_by="Ben"))
    assert rebooked.status_code == 201
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [rebooked.json()]


def test_r8_cancel_twice_second_returns_not_found(client):
    """R8: Canceling an already-deleted booking returns 404 booking_not_found."""
    booking_id = client.post("/api/bookings", json=_payload()).json()["id"]
    assert client.delete(f"/api/bookings/{booking_id}").status_code == 204

    second = client.delete(f"/api/bookings/{booking_id}")
    _assert_error(second, 404, "booking_not_found")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == []


@pytest.mark.parametrize("missing_id", [0, -1, 9999])
def test_r8_cancel_unknown_id_returns_not_found_without_affecting_existing(client, missing_id):
    """R8: Unknown integer id returns 404 booking_not_found and leaves existing bookings intact."""
    existing = client.post("/api/bookings", json=_payload()).json()

    resp = client.delete(f"/api/bookings/{missing_id}")
    _assert_error(resp, 404, "booking_not_found")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [existing]


@pytest.mark.parametrize("bad_id", ["abc", "1.5"])
def test_r8_cancel_non_integer_id_returns_invalid_request(client, bad_id):
    """R8: Non-integer id path parameter returns 422 invalid_request and changes nothing."""
    existing = client.post("/api/bookings", json=_payload()).json()

    resp = client.delete(f"/api/bookings/{bad_id}")
    _assert_error(resp, 422, "invalid_request")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [existing]
