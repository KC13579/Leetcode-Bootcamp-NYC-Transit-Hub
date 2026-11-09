import asyncio
from contextlib import asynccontextmanager, suppress
from zipfile import BadZipFile

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.protobuf.message import DecodeError

from backend.app.controllers.router import router
from backend.app.container import build_services
from backend.app.core.errors import APIError
from backend.app.config import get_settings
from backend.app.sources.mta.client import MTAClient
from backend.app.sources.google.client import GoogleClient
from backend.app.sources.firebase.client import FirebaseClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create shared clients and services, optionally run notifications, and release resources on shutdown."""
    settings = get_settings()
    client = MTAClient(settings)
    google = GoogleClient(settings)
    firebase = FirebaseClient(settings)
    app.state.firebase = firebase
    app.state.google = google
    app.state.services = build_services(client, google, firebase)
    worker = None
    try:
        if settings.notifications_enabled:
            firebase.get_app()
            worker = asyncio.create_task(
                app.state.services.notification.run_worker(
                    settings.notification_interval_seconds
                )
            )
        yield
    finally:
        if worker is not None:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker
        await google.close()
        await client.close()


app = FastAPI(title="NYC Transit Hub API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.exception_handler(httpx.HTTPError)
async def mta_error_handler(_: Request, exception: httpx.HTTPError) -> JSONResponse:
    """Convert upstream MTA network failures into safe gateway error responses."""
    timed_out = isinstance(exception, httpx.TimeoutException)
    return JSONResponse(
        status_code=504 if timed_out else 502,
        content={
            "detail": (
                "The MTA data service timed out."
                if timed_out
                else "The MTA data service is temporarily unavailable."
            )
        },
    )


@app.exception_handler(APIError)
async def api_error_handler(_: Request, exception: APIError) -> JSONResponse:
    """Return a structured domain error and the Bearer challenge for authentication failures."""
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": exception.detail},
        headers=(
            {"WWW-Authenticate": "Bearer"} if exception.status_code == 401 else None
        ),
    )


@app.exception_handler(DecodeError)
@app.exception_handler(BadZipFile)
async def invalid_feed_handler(_: Request, exception: Exception) -> JSONResponse:
    """Report malformed upstream transit feeds without exposing parser internals."""
    return JSONResponse(
        status_code=502, content={"detail": "MTA returned invalid transit data."}
    )
