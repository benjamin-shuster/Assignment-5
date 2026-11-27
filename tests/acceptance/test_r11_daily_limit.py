"""Acceptance tests for R11 (daily limit)."""

BASE_DATE = "2031-03-14"
OTHER_DATE = "2031-03-15"


def _payload(**overrides):
    data = {
        "room_id": 1,
        "date": BASE_DATE,
        "start": "09:00",
        "end": "10:00",
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


def test_r11_third_booking_same_date_rejected_and_not_saved(client):
    """R11: A third booking by the same person on one date (across rooms) returns 409 daily_limit and is not saved."""
    first = client.post(
        "/api/bookings",
        json=_payload(room_id=1, start="09:00", end="10:00", booked_by="Ana"),
    )
    second = client.post(
        "/api/bookings",
        json=_payload(room_id=2, start="11:00", end="12:00", booked_by="Ana"),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    saved_before = [first.json(), second.json()]

    third = client.post(
        "/api/bookings",
        json=_payload(room_id=3, start="13:00", end="14:00", booked_by="Ana"),
    )
    _assert_error(third, 409, "daily_limit")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == saved_before


def test_r11_same_name_ignores_case_and_surrounding_spaces(client):
    """R11: Names that match after trimming spaces and ignoring case count as the same person."""
    first = client.post(
        "/api/bookings",
        json=_payload(room_id=1, start="09:00", end="10:00", booked_by="Ana"),
    )
    second = client.post(
        "/api/bookings",
        json=_payload(room_id=2, start="10:00", end="11:00", booked_by="  ana  "),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    saved_before = [first.json(), second.json()]

    third = client.post(
        "/api/bookings",
        json=_payload(room_id=3, start="12:00", end="13:00", booked_by="  ANA\t"),
    )
    _assert_error(third, 409, "daily_limit")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == saved_before


def test_r11_cancelling_one_booking_allows_new_booking(client):
    """R11: Cancelling one of two bookings on a date frees a slot for a new booking."""
    first = client.post(
        "/api/bookings",
        json=_payload(room_id=1, start="09:00", end="10:00", booked_by="Ana"),
    )
    second = client.post(
        "/api/bookings",
        json=_payload(room_id=1, start="11:00", end="12:00", booked_by="Ana"),
    )
    assert first.status_code == 201
    assert second.status_code == 201

    blocked = client.post(
        "/api/bookings",
        json=_payload(room_id=2, start="13:00", end="14:00", booked_by="Ana"),
    )
    _assert_error(blocked, 409, "daily_limit")

    cancel_resp = client.delete(f"/api/bookings/{first.json()['id']}")
    assert cancel_resp.status_code == 204

    replacement = client.post(
        "/api/bookings",
        json=_payload(room_id=2, start="13:00", end="14:00", booked_by="Ana"),
    )
    assert replacement.status_code == 201
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [
        second.json(),
        replacement.json(),
    ]


def test_r11_different_dates_and_different_people_allowed(client):
    """R11: The 2-booking limit applies per person per date, not across dates or people."""
    assert (
        client.post(
            "/api/bookings",
            json=_payload(room_id=1, date=BASE_DATE, start="09:00", end="10:00", booked_by="Ana"),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/bookings",
            json=_payload(room_id=2, date=BASE_DATE, start="10:00", end="11:00", booked_by="Ana"),
        ).status_code
        == 201
    )

    other_day = client.post(
        "/api/bookings",
        json=_payload(room_id=1, date=OTHER_DATE, start="09:00", end="10:00", booked_by="Ana"),
    )
    other_person = client.post(
        "/api/bookings",
        json=_payload(room_id=3, date=BASE_DATE, start="09:00", end="10:00", booked_by="Ben"),
    )
    assert other_day.status_code == 201
    assert other_person.status_code == 201
