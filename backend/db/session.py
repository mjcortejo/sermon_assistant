from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import DATABASE_URL, ensure_data_dirs
from backend.db.models import Base

ensure_data_dirs()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    inspector = inspect(engine)
    if "sermons" in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS chat_messages"))
            conn.execute(text("DROP TABLE IF EXISTS notes"))
            conn.execute(text("DROP TABLE IF EXISTS sermons"))
    Base.metadata.create_all(bind=engine)


init_db()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
