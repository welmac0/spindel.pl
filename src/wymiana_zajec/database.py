import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# DATABASE_PATH can point to a Docker volume, e.g. /app/data/database.db.
# The fallback keeps local development compatible with the repository layout.
project_root = Path(__file__).resolve().parents[2]
sqlite_file = Path(
    os.getenv("DATABASE_PATH", str(project_root / "database.db"))
).expanduser()
sqlite_url = f"sqlite:///{sqlite_file}"

# check_same_thread=False - SQLite by default guards one connection per
# thread. FastAPI handles requests on different threads, so without
# this flag you'd get random errors.
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
# yield instead of return - FastAPI dependency injection.
# "with Session(...)" closes the connection automatically after the
# request, even if the endpoint raises an exception.
def get_session():
    with Session(engine) as session:
        yield session   