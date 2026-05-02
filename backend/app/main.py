"""
PersonaPlay Pro — FastAPI application factory.

This file only configures the app: middleware, routers.
No business logic lives here.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as rest_router
from app.api.websocket import router as ws_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="PersonaPlay Pro",
        description="Multi-Agent Theater Simulation Engine",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ws_router)
    app.include_router(rest_router)

    return app


app = create_app()
