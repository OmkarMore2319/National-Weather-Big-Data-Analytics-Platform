import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Configurable database path (defaults to weather_platform.db inside backend folder)
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "weather_platform.db"
DB_PATH = os.getenv("DB_PATH", str(DEFAULT_DB_PATH))
DATABASE_URL = f"sqlite:///{DB_PATH}"


# Create SQLite engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Enable WAL (Write-Ahead Logging) mode and normal synchronous mode per contract
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides an active database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)
