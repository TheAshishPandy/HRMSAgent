from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings


def create_app() -> FastAPI:
    get_settings()
    app = FastAPI(title="ATS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()
