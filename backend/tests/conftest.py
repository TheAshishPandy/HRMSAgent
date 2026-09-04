import os
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-chars-long")
os.environ.setdefault("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.config import get_settings
get_settings.cache_clear()
from app.db import Base, get_db, make_engine
from sqlalchemy.orm import sessionmaker
from app.main import create_app
from app import models  # noqa: F401


@pytest.fixture
def db():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app = create_app()

    def _get():
        yield db

    app.dependency_overrides[get_db] = _get
    return TestClient(app)
