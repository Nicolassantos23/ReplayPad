import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, String, DateTime, func
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from server.config import SERVER_CONFIG


class Base(DeclarativeBase):
    pass


class ReplayModel(Base):
    __tablename__ = "replays"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)


engine = create_engine(SERVER_CONFIG["database_url"].replace("+asyncpg", ""))
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
