import io
import logging
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.database import engine as default_engine
from src.db.models import Observation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# File-download helpers (no DB required)
# ---------------------------------------------------------------------------

def _data_dir(kind: str) -> Path:
    """
    Return the absolute path of the raw or processed data directory.
    'kind' must be 'raw' or 'processed'.
    """
    try:
        base = current_app.config.get(f"{kind.upper()}_DATA_DIR", "")
    except RuntimeError:
        base = ""
    if not base:
        # Fallback: resolve relative to the project root (cwd)
        base = os.path.join(os.getcwd(), "data", kind)
    return Path(base)


def list_files(kind: str) -> List[Dict[str, str]]:
    """
    Return a list of dicts describing every file in the data/<kind>/ directory.
    Each dict has 'name' and 'url' keys.
    """
    directory = _data_dir(kind)
    if not directory.exists():
        return []
    files = [
        {
            "name": f.name,
            "url": f"/api/v1/download/{kind}/{f.name}",
        }
        for f in sorted(directory.rglob("*"))
        if f.is_file() and not f.name.startswith(".")
    ]
    return files


def build_zip_bytes(kind: str) -> bytes:
    """
    Create an in-memory ZIP archive of all files in data/<kind>/.
    Returns the raw bytes of the ZIP.
    """
    directory = _data_dir(kind)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if directory.exists():
            for filepath in sorted(directory.rglob("*")):
                if filepath.is_file() and not filepath.name.startswith("."):
                    arcname = filepath.relative_to(directory)
                    zf.write(filepath, arcname=arcname)
    buf.seek(0)
    return buf.read()


def _get_engine():
    """Get the active engine — from Flask app config if available, else default."""
    try:
        return current_app.config["ENGINE"]
    except RuntimeError:
        return default_engine

MAX_PER_PAGE = 500
DEFAULT_PER_PAGE = 50


def list_datasets() -> List[Dict[str, Any]]:
    """Return every unique dataset_id with its category and row count."""
    with Session(_get_engine()) as session:
        rows = (
            session.query(
                Observation.dataset_id,
                Observation.category,
                func.count(Observation.id).label("row_count"),
            )
            .group_by(Observation.dataset_id, Observation.category)
            .order_by(Observation.category)
            .all()
        )
        return [
            {
                "dataset_id": r.dataset_id,
                "category": r.category,
                "row_count": r.row_count,
            }
            for r in rows
        ]


def get_dataset_metadata(dataset_id: str) -> Optional[Dict[str, Any]]:
    """Return metadata for a single dataset."""
    with Session(_get_engine()) as session:
        row_count = (
            session.query(func.count(Observation.id))
            .filter(Observation.dataset_id == dataset_id)
            .scalar()
        )
        if row_count == 0:
            return None

        variables = (
            session.query(Observation.variable_name)
            .filter(Observation.dataset_id == dataset_id)
            .distinct()
            .all()
        )
        year_range = (
            session.query(
                func.min(Observation.year), func.max(Observation.year)
            )
            .filter(
                Observation.dataset_id == dataset_id,
                Observation.year.isnot(None),
            )
            .one()
        )
        category = (
            session.query(Observation.category)
            .filter(Observation.dataset_id == dataset_id)
            .limit(1)
            .scalar()
        )

        return {
            "dataset_id": dataset_id,
            "category": category,
            "row_count": row_count,
            "variables": [v[0] for v in variables],
            "year_min": year_range[0],
            "year_max": year_range[1],
        }


def list_categories() -> List[Dict[str, Any]]:
    """Return all categories with dataset counts."""
    with Session(_get_engine()) as session:
        rows = (
            session.query(
                Observation.category,
                func.count(func.distinct(Observation.dataset_id)).label(
                    "dataset_count"
                ),
                func.count(Observation.id).label("total_rows"),
            )
            .group_by(Observation.category)
            .order_by(Observation.category)
            .all()
        )
        return [
            {
                "category": r.category,
                "dataset_count": r.dataset_count,
                "total_rows": r.total_rows,
            }
            for r in rows
        ]


def query_observations(
    category: Optional[str] = None,
    dataset_id: Optional[str] = None,
    year: Optional[int] = None,
    entity_name: Optional[str] = None,
    variable_name: Optional[str] = None,
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Query observations with optional filters and pagination.
    Returns (results_list, pagination_dict).
    """
    per_page = min(per_page, MAX_PER_PAGE)
    if page < 1:
        page = 1

    with Session(_get_engine()) as session:
        query = session.query(Observation)

        # Apply filters
        if category:
            query = query.filter(Observation.category == category)
        if dataset_id:
            query = query.filter(Observation.dataset_id == dataset_id)
        if year is not None:
            query = query.filter(Observation.year == year)
        if entity_name:
            query = query.filter(
                Observation.entity_name.ilike(f"%{entity_name}%")
            )
        if variable_name:
            query = query.filter(
                Observation.variable_name.ilike(f"%{variable_name}%")
            )

        # Get total before pagination
        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)

        # Paginate
        offset = (page - 1) * per_page
        results = query.order_by(Observation.id).offset(offset).limit(per_page).all()

        data = [
            {
                "id": obs.id,
                "dataset_id": obs.dataset_id,
                "category": obs.category,
                "entity_name": obs.entity_name,
                "variable_name": obs.variable_name,
                "year": obs.year,
                "period": obs.period,
                "value": obs.value,
            }
            for obs in results
        ]

        pagination = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": total_pages,
        }

        return data, pagination
