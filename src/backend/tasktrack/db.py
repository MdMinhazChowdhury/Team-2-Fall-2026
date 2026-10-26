from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tasktrack.config import settings


def now() -> datetime:
    return settings().test_now or datetime.now(UTC)


class Base(DeclarativeBase):
    pass


engine = create_engine(settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def database() -> Iterator[Session]:
    with SessionLocal() as session, session.begin():
        yield session
