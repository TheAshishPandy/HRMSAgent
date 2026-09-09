from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    url = url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    kwargs = {}
    if ":memory:" in url:
        kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, **kwargs)


SessionLocal = None
engine = None


def migrate_sqlite(engine):
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        if "users" in tables:
            cols = {c["name"] for c in insp.get_columns("users")}
            if "organization_id" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN organization_id VARCHAR(36)"))
        if "jobs" in tables:
            cols = {c["name"] for c in insp.get_columns("jobs")}
            if "organization_id" not in cols:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN organization_id VARCHAR(36)"))
        if "organizations" in tables:
            cols = {c["name"] for c in insp.get_columns("organizations")}
            if "theme_overrides" not in cols:
                conn.execute(text("ALTER TABLE organizations ADD COLUMN theme_overrides JSON"))
        if "employees" in tables:
            cols = {c["name"] for c in insp.get_columns("employees")}
            if "exit_date" not in cols:
                conn.execute(text("ALTER TABLE employees ADD COLUMN exit_date VARCHAR"))
            if "exit_reason" not in cols:
                conn.execute(text("ALTER TABLE employees ADD COLUMN exit_reason VARCHAR"))


def init_engine():
    global SessionLocal, engine
    engine = make_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
