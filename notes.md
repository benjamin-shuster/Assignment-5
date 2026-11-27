# RoomBook Notes

## Acceptance tests for R1 to R10

- Added acceptance test suite in `tests/acceptance/` strictly derived from `docs/spec.md` (rules R1–R10 and decisions P1–P4), using the `client` and `new_client` fixtures from `tests/conftest.py` without importing `app` at module top level or running the suite (no backend exists yet).
- Created four test modules grouped by area:
  - `tests/acceptance/test_r1_r2_read.py` (R1, R2)
  - `tests/acceptance/test_r3_r6_create_validation.py` (R3, R4, R5, R6, P1, P2)
  - `tests/acceptance/test_r7_r8_bookings_lifecycle.py` (R7, R8, P3, P4)
  - `tests/acceptance/test_r9_r10_errors_and_app.py` (R9, R10)
- Every error check asserts the exact two-key body `{"error", "message"}`, the expected `error` code, `isinstance(body["message"], str)` without asserting exact message text, and that failed requests leave existing bookings unchanged.

### Not in this change

- Did not include tests for `daily_limit` (present in `frontend/app.js` `MESSAGES`, absent from `docs/spec.md`).
- Did not implement any backend modules in `app/`.
- Did not run `python -m pytest` or `python tools/check_layers.py` because no backend exists yet and the task instructed not to run the code.

## Task 1: `app/repository.py`

- Implemented `app/repository.py` as the sole module containing `sqlite3` imports and SQL queries, opening and closing a fresh `sqlite3.Connection` via `contextlib.closing` and `with conn:` on every repository call so FastAPI worker threads never share connections.
- Configured `bookings.id` with `INTEGER PRIMARY KEY AUTOINCREMENT` to satisfy decision D3 (deleted booking IDs are never reused) and seeded the 4 fixed rooms from `docs/spec.md` section 2 via `INSERT OR IGNORE` in `init_db` so repeated initialization on the same `db_path` is idempotent (R10).
- Returned plain `dict` / `bool` values from `list_rooms`, `room_exists`, `list_bookings`, `has_overlap`, `create_booking`, and `delete_booking` so Task 1 stays independent of `app/models.py` (which belongs to Task 2).
- Implemented `has_overlap` with half-open interval comparison (`start < ? AND ? < end`) so back-to-back touching slots do not conflict (R7).

### Not in this change

- Did not create `app/models.py`, `app/service.py`, `app/routes.py`, or `app/main.py` (reserved for Tasks 2–3).
- Did not add foreign key constraints or validation logic inside SQL/repository functions; business rules and precedence belong in `app/service.py` (Task 2).
- Did not modify `frontend/`, `tests/acceptance/`, `tests/conftest.py`, or `tools/`.

## Tasks 2 & 3: `app/models.py`, `app/service.py`, `app/routes.py`, and `app/main.py`

- Implemented `app/models.py` with `CreateBookingRequest` (standard-library `dataclasses`) and `ServiceError(status_code, error, message)` so domain/validation failures map uniformly to the R9 two-field JSON error body.
- Implemented `app/service.py` enforcing R1–R9 in exact R9 precedence order (`R3 -> R4 -> R5 -> R6 -> R7`), using `re.fullmatch` with ASCII digit ranges for `YYYY-MM-DD`, `HH:MM`, and integer parsing so trailing newlines or Unicode digits are rejected, and rejecting `bool` values passed as `room_id`.
- Implemented `app/routes.py` for HTTP handling only (no `app.repository` import), reading `request.json()` manually and typing query/path parameters (`date`, `room_id`, `booking_id`) as optional/string so FastAPI's built-in validation does not bypass R9 error formatting.
- Implemented `app/main.py` defining `create_app(db_path: str = "roombook.db")`, initializing the SQLite schema/rooms via `service.init_db`, storing `db_path` on `app.state`, registering `ServiceError` and `RequestValidationError` handlers, serving `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css`, and mounting `router`.

### Not in this change

- Did not implement `daily_limit` / R11 (absent from `docs/spec.md` sections 1–6).
- Did not add authentication, past-date checks, or room capacity enforcement (excluded by P1–P3).
- Did not modify `frontend/`, `tests/acceptance/`, `tests/conftest.py`, or `tools/`.

## Acceptance tests for R11 (`tests/acceptance/test_r11_daily_limit.py`)

- Created `tests/acceptance/test_r11_daily_limit.py` with four `test_r11_...` tests using the `client` fixture from `tests/conftest.py`: third booking on one date rejected with `409 daily_limit` and not saved, case-insensitive and whitespace-trimmed name matching, cancelling one of two bookings allowing a new booking, and independence across dates and different names.
- Confirmed with the user before writing the test file because `docs/spec.md` does not yet define R11 and section 7 D1 states `422`; proceeded with `409 daily_limit` without editing `docs/spec.md` per user choice.

### Not in this change

- Did not edit `docs/spec.md` or implement R11 in `app/`.
- Did not modify `frontend/`, `tests/conftest.py`, or `tools/`.

## R11: Daily limit (`app/repository.py`, `app/service.py`)

- Enforced R11 (`_DAILY_LIMIT = 2` bookings per person per date across all rooms) inside the same `BEGIN IMMEDIATE` transaction as R7 in `app/repository.py:create_booking`, preserving R9 precedence (`R3 -> R4 -> R5 -> R6 -> R7 -> R11`) and preventing concurrent requests from exceeding the daily limit.
- Matched `booked_by` using `.strip().casefold()` so trimmed whitespace and upper/lower case differences count as the same person (consistent with R4/R11), and mapped `"daily_limit"` rejections to `ServiceError(409, "daily_limit", ...)` in `app/service.py`.

### Not in this change

- Did not modify `docs/spec.md`, `frontend/`, `tests/acceptance/`, `tests/conftest.py`, or `tools/`.
