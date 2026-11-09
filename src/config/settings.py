import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+pg8000://user:password@localhost:5432/opendata_ph",
        )
        # Render provides postgresql:// or postgres:// URLs.
        # SQLAlchemy needs the driver suffix (+pg8000).
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
        elif db_url.startswith("postgresql://") and "+pg8000" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)

        self.DATABASE_URL = db_url
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
