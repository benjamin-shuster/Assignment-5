"""HTTP API routes for RoomBook."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app import service
from app.models import ServiceError

router = APIRouter()


def _db_path(request: Request) -> str:
    return request.app.state.db_path


@router.get("/api/rooms")
def get_rooms(request: Request) -> list[dict]:
    """Return the list of study rooms (R1)."""
    return service.list_rooms(_db_path(request))


@router.get("/api/bookings")
def get_bookings(
    request: Request,
    date: str | None = None,
    room_id: str | None = None,
) -> list[dict]:
    """Return bookings filtered by date and optional room_id (R2)."""
    return service.list_bookings(_db_path(request), date, room_id)


@router.post("/api/bookings")
async def post_booking(request: Request) -> JSONResponse:
    """Create a booking from a JSON request body (R3..R7)."""
    try:
        raw_body = await request.body()
        payload = json.loads(
            raw_body.decode("utf-8"), parse_int=service.parse_json_int
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ServiceError(
            422,
            "invalid_request",
            "Request body must be valid JSON.",
        ) from exc
    booking = service.create_booking(_db_path(request), payload)
    return JSONResponse(status_code=201, content=booking)


@router.delete("/api/bookings/{booking_id}")
def delete_booking(request: Request, booking_id: str) -> Response:
    """Cancel a booking by id (R8)."""
    service.cancel_booking(_db_path(request), booking_id)
    return Response(status_code=204)
