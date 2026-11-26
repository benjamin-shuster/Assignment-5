# AGENTS.md

## Project

RoomBook, a study-room booking app. The page in `frontend/` is finished and belongs to
another team. The backend in `app/` is built to match `docs/spec.md`.

## General rules

- Read `docs/spec.md` before every change. The spec is the source of truth: when code
  and spec disagree, the spec wins. When the spec is unclear, stop and ask. Do not guess.
- Never edit anything in `frontend/`.
- Never change a test in `tests/acceptance/` to make code pass.
- Do only the task you were given. Do not add endpoints, fields, error codes, rules,
  packages or features that the spec does not ask for.
- Python 3.11 or later. Use only the packages in `requirements.txt`.
- Run the tests with `python -m pytest`.

## Backend rules

- `app/routes.py` handles HTTP only; `app/service.py` enforces every rule in
  section 5 of the spec; `app/repository.py` is the only file with SQL;
  `app/models.py` holds the request shapes.
- `app/main.py` defines `create_app(db_path)` exactly as section 3 of the spec says.
- Every error response uses the one error body in R9.
- Use `sqlite3` from the standard library: no ORM, no new packages.
- Open a new database connection for each request or repository call, never one
  shared connection: FastAPI runs requests on several threads.
- After every task, run `python tools/check_layers.py` and `python -m pytest`.
- Add notes, lessons learned, and decisions to `notes.md` as you work. Add a new heading for each task, and a "Not in this change" section for things you considered but did not do.
- Make no mistakes. If you do, fix them before the next commit. Mistakes include: failing tests, failing `check_layers.py`, code that does not match the spec, and code that does not match your own ledger entries or report.
