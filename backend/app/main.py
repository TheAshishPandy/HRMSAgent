from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import Base, init_engine
    from app import models  # noqa: F401

    engine = init_engine()
    Base.metadata.create_all(engine)
    yield


def create_app() -> FastAPI:
    get_settings()
    app = FastAPI(title="ATS", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from app.modules.auth.router import router as auth_router

    app.include_router(auth_router)
    return app


app = create_app()
