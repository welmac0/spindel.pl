from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Path absolute relative to this file, not the process CWD - without
# this, "sqlite:///database.db" creates a new, empty DB every time you
# run the app from a different working directory (e.g. IDE vs terminal).
sqlite_file = Path(__file__).resolve().parent / "database.db"
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