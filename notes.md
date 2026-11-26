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
