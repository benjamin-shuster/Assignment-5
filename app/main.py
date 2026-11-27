"""FastAPI application factory and frontend static routes for RoomBook."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app import service
from app.models import ServiceError
from app.routes import router

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app(db_path: str = "roombook.db") -> FastAPI:
    """Create and configure a RoomBook FastAPI application for db_path."""
    service.init_db(db_path)

    app = FastAPI()
    app.state.db_path = db_path

    @app.exception_handler(ServiceError)
    async def handle_service_error(
        _request: Request, exc: ServiceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_request",
                "message": "Invalid request.",
            },
        )

    @app.get("/")
    def serve_index() -> FileResponse:
        return FileResponse(_FRONTEND_DIR / "index.html")

    @app.get("/app.js")
    def serve_app_js() -> FileResponse:
        return FileResponse(_FRONTEND_DIR / "app.js")

    @app.get("/styles.css")
    def serve_styles_css() -> FileResponse:
        return FileResponse(_FRONTEND_DIR / "styles.css")

    app.include_router(router)
    return app
