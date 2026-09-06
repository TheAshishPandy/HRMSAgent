from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import Base, init_engine
    from app import models  # noqa: F401

    from app.db import migrate_sqlite

    engine = init_engine()
    Base.metadata.create_all(engine)
    migrate_sqlite(engine)
    yield


def create_app() -> FastAPI:
    get_settings()
    app = FastAPI(title="HRMS", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from app.modules.auth.router import router as auth_router
    from app.modules.jobs.router import router as jobs_router
    from app.modules.candidates.router import apps_router, jobs_apply, me_router
    from app.modules.calendar.router import router as calendar_router
    from app.modules.mail.router import router as mail_router
    from app.modules.feedback.router import router as feedback_router
    from app.modules.tenants.router import router as tenants_router
    from app.modules.employees.router import router as employees_router
    from app.modules.attendance.router import router as attendance_router
    from app.modules.leave.router import router as leave_router

    app.include_router(auth_router)
    app.include_router(jobs_router)
    app.include_router(jobs_apply)
    app.include_router(apps_router)
    app.include_router(me_router)
    app.include_router(calendar_router)
    app.include_router(mail_router)
    app.include_router(feedback_router)
    app.include_router(tenants_router)
    app.include_router(employees_router)
    app.include_router(attendance_router)
    app.include_router(leave_router)
    return app


app = create_app()
