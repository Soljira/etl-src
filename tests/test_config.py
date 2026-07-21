import os
from unittest import mock
from src.config.settings import Settings

def test_settings_loads_env_vars():
    with mock.patch.dict(os.environ, {"DATABASE_URL": "postgresql://test_user:test_pass@localhost:5432/test_db", "LOG_LEVEL": "DEBUG"}):
        settings = Settings()
        assert settings.DATABASE_URL == "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert settings.LOG_LEVEL == "DEBUG"

def test_settings_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.DATABASE_URL == "postgresql+pg8000://user:password@localhost:5432/opendata_ph"
        assert settings.LOG_LEVEL == "INFO"
