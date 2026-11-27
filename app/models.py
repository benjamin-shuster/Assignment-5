"""Domain models and error types for RoomBook."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateBookingRequest:
    """Validated request shape for creating a booking (R3)."""

    room_id: int
    date: str
    start: str
    end: str
    booked_by: str


class ServiceError(Exception):
    """Domain or validation error serialized into the R9 two-field JSON body."""

    def __init__(self, status_code: int, error: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message
