import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

import app.models  # noqa: F401

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app

TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="function")
def db() -> Session:
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db

    yield session

    fastapi_app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    with TestClient(fastapi_app) as c:
        yield c
