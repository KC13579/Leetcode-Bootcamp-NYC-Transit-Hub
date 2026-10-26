from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.sources.mta.client import MTAClient
from app.transit.service import TransitService
from app.transit.station_registry import StationRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = MTAClient(get_settings())
    app.state.transit_service = TransitService(client, StationRegistry(client))
    yield
    await client.close()


app = FastAPI(
    title="NYC Transit Hub API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().allowed_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.exception_handler(httpx.HTTPError)
async def mta_error_handler(_: Request, exception: httpx.HTTPError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "The MTA data service is temporarily unavailable."},
    )
