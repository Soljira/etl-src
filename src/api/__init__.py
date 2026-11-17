import os
from typing import Optional

from flask import Flask
from flask_cors import CORS
from sqlalchemy.engine import Engine

from src.db.database import engine as default_engine
from src.db.models import Base


def create_app(engine: Optional[Engine] = None) -> Flask:
    """Flask application factory.

    Args:
        engine: Optional SQLAlchemy engine override (useful for testing).
                Defaults to the production engine from database.py.
    """
    if engine is None:
        engine = default_engine

    app = Flask(__name__)
    app.config["ENGINE"] = engine

    # Resolve data directory paths (absolute so they work regardless of cwd)
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    app.config["RAW_DATA_DIR"] = os.environ.get(
        "RAW_DATA_DIR", os.path.join(_project_root, "data", "raw")
    )
    app.config["PROCESSED_DATA_DIR"] = os.environ.get(
        "PROCESSED_DATA_DIR", os.path.join(_project_root, "data", "processed")
    )

    # Enable CORS for all /api/* routes so the browser can call the API
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass  # DB may be unreachable during testing

    # Register API blueprint
    from src.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    return app

