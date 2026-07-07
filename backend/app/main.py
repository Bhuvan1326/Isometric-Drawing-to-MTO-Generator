"""FastAPI application factory.

Run with: uvicorn app.main:app --reload --port 8000
Swagger docs at /docs, ReDoc at /redoc.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes import health, mto, upload


def create_app() -> FastAPI:
    app = FastAPI(
        title="Isometric Drawing to MTO Generator",
        description=(
            "Upload a piping isometric drawing (PNG/JPG/PDF) and receive a "
            "structured Material Take-Off. Falls back to a clearly-labelled "
            "mock MTO when no vision LLM API key is configured."
        ),
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(upload.router)
    app.include_router(mto.router)

    # Typed error envelope. Our routes raise HTTPException with a dict detail
    # of the form {"detail": str, "code": str}. We reshape every error into a
    # consistent {"detail", "code"} body so the frontend can switch on `code`.
    @app.exception_handler(HTTPException)
    async def _http_exc(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            code = detail["code"]
            message = detail.get("detail", str(detail))
        else:
            code = "ERROR"
            message = str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": message, "code": code},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "code": "VALIDATION"},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Internal server error: {exc.__class__.__name__}: {exc}",
                "code": "INTERNAL",
            },
        )

    return app


app = create_app()
