"""Acceptance tests for R9 (error shape, atomicity, precedence) and R10 (create_app)."""

BASE_DATE = "2031-03-14"


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


# --- R9: Error shape, atomicity, and rule precedence ---


def test_r9_precedence_r3_before_r4_r5_r6_r7(client):
    """R9: R3 (invalid_request) takes precedence over R4, R5, R6, and R7."""
    existing = client.post("/api/bookings", json=_payload()).json()

    # Bad date (R3) + empty name (R4) + invalid time (R5) + unknown room (R6)
    resp1 = client.post(
        "/api/bookings",
        json=_payload(date="bad-date", booked_by="", start="07:00", end="12:00", room_id=99),
    )
    _assert_error(resp1, 422, "invalid_request")

    # Bad time format "24:00" (R3) + empty name (R4) + invalid time range (R5) + overlap (R7)
    resp2 = client.post(
        "/api/bookings",
        json=_payload(booked_by="", start="09:00", end="24:00"),
    )
    _assert_error(resp2, 422, "invalid_request")

    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [existing]


def test_r9_precedence_r4_before_r5_r6_r7(client):
    """R9: R4 (invalid_name) takes precedence over R5, R6, and R7."""
    existing = client.post("/api/bookings", json=_payload()).json()

    # Empty name (R4) + invalid minutes (R5) + unknown room (R6)
    resp1 = client.post(
        "/api/bookings",
        json=_payload(booked_by="   ", start="09:15", end="10:00", room_id=99),
    )
    _assert_error(resp1, 422, "invalid_name")

    # Over-length name (R4) + overlapping slot (R7)
    resp2 = client.post(
        "/api/bookings",
        json=_payload(booked_by="a" * 41, start="09:00", end="10:00", room_id=1),
    )
    _assert_error(resp2, 422, "invalid_name")

    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [existing]


def test_r9_precedence_r5_before_r6_and_r7(client):
    """R9: R5 (invalid_time) takes precedence over R6 and R7."""
    existing = client.post("/api/bookings", json=_payload()).json()

    # Bad minutes (R5) + unknown room (R6)
    resp1 = client.post(
        "/api/bookings",
        json=_payload(start="09:15", end="10:00", room_id=99),
    )
    _assert_error(resp1, 422, "invalid_time")

    # Bad minutes (R5) + overlaps existing 09:00..10:00 (R7)
    resp2 = client.post(
        "/api/bookings",
        json=_payload(start="09:15", end="10:00", room_id=1),
    )
    _assert_error(resp2, 422, "invalid_time")

    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [existing]


def test_r9_precedence_r6_before_r7(client):
    """R9: R6 (room_not_found) is reported when R3..R5 pass and room_id is invalid."""
    existing = client.post("/api/bookings", json=_payload()).json()

    resp = client.post("/api/bookings", json=_payload(room_id=99))
    _assert_error(resp, 404, "room_not_found")
    assert client.get("/api/bookings", params={"date": BASE_DATE}).json() == [existing]


# --- R10: Application startup, static frontend serving, isolation, persistence ---


def test_r10_serves_frontend_page_and_assets(client):
    """R10: GET /, GET /app.js, and GET /styles.css return 200 with non-empty assets."""
    index_resp = client.get("/")
    assert index_resp.status_code == 200
    assert len(index_resp.content) > 0
    assert "html" in index_resp.headers["content-type"].lower()

    js_resp = client.get("/app.js")
    assert js_resp.status_code == 200
    assert len(js_resp.content) > 0
    assert "javascript" in js_resp.headers["content-type"].lower()

    css_resp = client.get("/styles.css")
    assert css_resp.status_code == 200
    assert len(css_resp.content) > 0
    assert "css" in css_resp.headers["content-type"].lower()


def test_r10_different_db_paths_never_share_data(new_client):
    """R10: Two apps with different db_path values keep completely isolated bookings."""
    c_a = new_client("a.db")
    c_b = new_client("b.db")

    created = c_a.post("/api/bookings", json=_payload()).json()
    assert c_a.get("/api/bookings", params={"date": BASE_DATE}).json() == [created]
    assert c_b.get("/api/bookings", params={"date": BASE_DATE}).json() == []

    # Deleting the booking id from b.db must fail with 404 and leave a.db untouched
    missing = c_b.delete(f"/api/bookings/{created['id']}")
    _assert_error(missing, 404, "booking_not_found")
    assert c_a.get("/api/bookings", params={"date": BASE_DATE}).json() == [created]


def test_r10_same_db_path_persists_data_and_does_not_duplicate_rooms(new_client):
    """R10: Calling create_app again on the same db_path sees saved bookings and 4 rooms."""
    c1 = new_client("persist.db")
    created = c1.post("/api/bookings", json=_payload()).json()

    c2 = new_client("persist.db")
    assert len(c2.get("/api/rooms").json()) == 4
    assert c2.get("/api/bookings", params={"date": BASE_DATE}).json() == [created]

    assert c2.delete(f"/api/bookings/{created['id']}").status_code == 204

    c3 = new_client("persist.db")
    assert c3.get("/api/bookings", params={"date": BASE_DATE}).json() == []
