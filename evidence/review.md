### Review Report: `app/` against `docs/spec.md` and `AGENTS.md`

**Layer Rules (L1–L5) & `AGENTS.md` Backend Rules:**
- **L1 (SQL only in `app/repository.py`):** Pass. Only `app/repository.py` imports `sqlite3` and contains SQL statements.
- **L2 (HTTP only in `app/routes.py` and `app/main.py`):** Pass. `service.py`, `repository.py`, and `models.py` do not import `fastapi` or `starlette`.
- **L3 (`app/routes.py` does not import `app.repository`):** Pass. `routes.py` only calls `app.service` (and uses `ServiceError` from `app.models`).
- **L4 (Five modules exist and `app/main.py` defines `create_app`):** Pass.
- **L5 (No ORM or other DB library):** Pass. Standard library `sqlite3` only, with a fresh connection per repository call (`_connect` in `app/repository.py`).

**Spec Rules (R1–R10):**
Overall implementation closely matches `docs/spec.md` (R1–R10, section 4 API shapes/status codes, section 6 error codes, and R9 precedence order `R3 -> R4 -> R5 -> R6 -> R7`). No blocking issues found. Two minor issues identified:

#### Findings

1. **File:** `app/service.py` (lines 184–200) and `app/repository.py` (lines 103–145)
   - **Rule ID:** R7 (No overlap)
   - **Severity:** minor
   - **Problem:** `create_booking` checks for overlaps in `repository.has_overlap(...)` (connection/transaction 1) and then inserts the booking in `repository.create_booking(...)` (connection/transaction 2). Because these run in separate connections and transactions, two concurrent `POST /api/bookings` requests on FastAPI's threadpool for the same room, date, and overlapping time can both pass `has_overlap` before either commits, resulting in overlapping bookings in the database. Checking overlap and inserting atomically inside a single `BEGIN IMMEDIATE` transaction in `app/repository.py` would prevent this race.

2. **File:** `app/service.py` (lines 41–49, 95–96, 123–129, 176, 205–206) and `app/repository.py` (lines 65–72, 148–155)
   - **Rule ID:** R2, R6, R8, R9
   - **Severity:** minor
   - **Problem:** Integer inputs outside SQLite's signed 64-bit integer range (`-9223372036854775808` to `9223372036854775807`), such as `room_id=99999999999999999999` in `GET /api/bookings` or `POST /api/bookings`, or `id=99999999999999999999` in `DELETE /api/bookings/{id}`, cause `sqlite3` to raise `OverflowError` (an unhandled 500 error instead of `404 room_not_found` / `404 booking_not_found` and violating R9's two-field error body). Additionally, integer strings longer than Python's 4300-digit conversion limit in `_parse_int_str` raise `ValueError` instead of returning a controlled `404`/`422` R9 error response.
