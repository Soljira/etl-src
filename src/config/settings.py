import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+pg8000://user:password@localhost:5432/opendata_ph")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
