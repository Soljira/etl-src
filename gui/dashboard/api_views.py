"""
Django-native REST API views — /api/v1/...

These replace the separate Flask API server.  Everything runs on the same
Django process as the GUI, so no second server is needed.

Endpoints
---------
GET /api/v1/health                           database connectivity
GET /api/v1/datasets                         list datasets + row counts
GET /api/v1/datasets/<dataset_id>            metadata for one dataset
GET /api/v1/categories                       categories + dataset counts
GET /api/v1/observations                     query rows (filter + paginate)
GET /api/v1/files/<kind>                     list raw/processed files (JSON)
GET /api/v1/download/<kind>.zip              download ZIP archive
GET /api/v1/download/<kind>/<path>           download single file
"""

import io
import pathlib
import os
import zipfile
from typing import Optional

from django.db.models import Count, Min, Max
from django.http import (
    FileResponse,
    HttpResponse,
    JsonResponse,
)
from django.views.decorators.http import require_GET

from .models import Observation
from src.db.database import test_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

MAX_PER_PAGE = 500
DEFAULT_PER_PAGE = 50


def _cors(response: HttpResponse) -> HttpResponse:
    """Add CORS header so external clients can call the API."""
    response["Access-Control-Allow-Origin"] = "*"
    return response


def _json(data, status: int = 200) -> JsonResponse:
    r = JsonResponse(data, status=status)
    return _cors(r)


def _safe_data_dir(kind: str) -> pathlib.Path:
    if kind not in ("raw", "processed"):
        raise ValueError("kind must be 'raw' or 'processed'")
    return pathlib.Path(_PROJECT_ROOT) / "data" / kind


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@require_GET
def health(request):
    """GET /api/v1/health — returns database connectivity status."""
    try:
        ok = test_connection()
    except Exception:
        ok = False
    if ok:
        return _json({"status": "healthy", "database": "connected"}, 200)
    return _json({"status": "unhealthy", "database": "disconnected"}, 503)


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

@require_GET
def list_datasets(request):
    """GET /api/v1/datasets — list all dataset_ids with row counts."""
    try:
        rows = (
            Observation.objects
            .values("dataset_id", "category")
            .annotate(row_count=Count("id"))
            .order_by("category", "dataset_id")
        )
        data = [
            {
                "dataset_id": r["dataset_id"],
                "category": r["category"],
                "row_count": r["row_count"],
            }
            for r in rows
        ]
        return _json({"data": data, "count": len(data)})
    except Exception as exc:
        return _json({"error": str(exc)}, 500)


@require_GET
def get_dataset(request, dataset_id: str):
    """GET /api/v1/datasets/<dataset_id> — metadata for one dataset."""
    try:
        qs = Observation.objects.filter(dataset_id=dataset_id)
        row_count = qs.count()
        if row_count == 0:
            return _json({"error": f"Dataset '{dataset_id}' not found."}, 404)

        variables = list(
            qs.values_list("variable_name", flat=True).distinct()
        )
        agg = qs.aggregate(year_min=Min("year"), year_max=Max("year"))
        category = qs.values_list("category", flat=True).first()

        return _json({
            "data": {
                "dataset_id": dataset_id,
                "category": category,
                "row_count": row_count,
                "variables": variables,
                "year_min": agg["year_min"],
                "year_max": agg["year_max"],
            }
        })
    except Exception as exc:
        return _json({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@require_GET
def list_categories(request):
    """GET /api/v1/categories — categories with dataset + row counts."""
    try:
        rows = (
            Observation.objects
            .values("category")
            .annotate(
                dataset_count=Count("dataset_id", distinct=True),
                total_rows=Count("id"),
            )
            .order_by("category")
        )
        data = [
            {
                "category": r["category"],
                "dataset_count": r["dataset_count"],
                "total_rows": r["total_rows"],
            }
            for r in rows
        ]
        return _json({"data": data, "count": len(data)})
    except Exception as exc:
        return _json({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

@require_GET
def query_observations(request):
    """
    GET /api/v1/observations
    Query params: category, dataset_id, entity_name, variable_name,
                  year, page (default 1), per_page (default 50, max 500)
    """
    try:
        category = request.GET.get("category", "").strip() or None
        dataset_id = request.GET.get("dataset_id", "").strip() or None
        entity_name = request.GET.get("entity_name", "").strip() or None
        variable_name = request.GET.get("variable_name", "").strip() or None

        try:
            year: Optional[int] = int(request.GET["year"])
        except (KeyError, ValueError):
            year = None

        try:
            page = max(1, int(request.GET.get("page", 1)))
        except ValueError:
            page = 1

        try:
            per_page = min(MAX_PER_PAGE, max(1, int(request.GET.get("per_page", DEFAULT_PER_PAGE))))
        except ValueError:
            per_page = DEFAULT_PER_PAGE

        qs = Observation.objects.all()
        if category:
            qs = qs.filter(category=category)
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        if entity_name:
            qs = qs.filter(entity_name__icontains=entity_name)
        if variable_name:
            qs = qs.filter(variable_name__icontains=variable_name)
        if year is not None:
            qs = qs.filter(year=year)

        total = qs.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page
        results = qs.order_by("id")[offset: offset + per_page]

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

        return _json({
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": total_pages,
            },
        })
    except Exception as exc:
        return _json({"error": str(exc)}, 500)


# ---------------------------------------------------------------------------
# File download API (same logic as views.py but under /api/v1/)
# ---------------------------------------------------------------------------

@require_GET
def api_files_list(request, kind: str):
    """GET /api/v1/files/<kind> — JSON list of raw or processed files."""
    try:
        data_dir = _safe_data_dir(kind)
    except ValueError:
        return _json({"error": "kind must be 'raw' or 'processed'"}, 400)

    file_list = []
    if data_dir.exists():
        for f in sorted(data_dir.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                rel = f.relative_to(data_dir)
                file_list.append({
                    "name": str(rel),
                    "url": f"/api/v1/download/{kind}/{rel}",
                })

    return _json({
        "zip_url": f"/api/v1/download/{kind}.zip",
        "count": len(file_list),
        "files": file_list,
    })


@require_GET
def api_download_zip(request, kind: str):
    """GET /api/v1/download/<kind>.zip — stream ZIP of all files."""
    try:
        data_dir = _safe_data_dir(kind)
    except ValueError:
        return _json({"error": "kind must be 'raw' or 'processed'"}, 400)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        if data_dir.exists():
            for fp in sorted(data_dir.rglob("*")):
                if fp.is_file() and not fp.name.startswith("."):
                    zf.write(fp, arcname=fp.relative_to(data_dir))
    buf.seek(0)

    response = HttpResponse(buf.read(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{kind}_files.zip"'
    response["Access-Control-Allow-Origin"] = "*"
    return response


@require_GET
def api_download_file(request, kind: str, filepath: str):
    """GET /api/v1/download/<kind>/<filepath> — download a single file."""
    try:
        data_dir = _safe_data_dir(kind)
    except ValueError:
        return _json({"error": "kind must be 'raw' or 'processed'"}, 400)

    target = (data_dir / filepath).resolve()
    if not str(target).startswith(str(data_dir.resolve())):
        return _json({"error": "Invalid path."}, 400)
    if not target.exists() or not target.is_file():
        return _json({"error": f"File '{filepath}' not found."}, 404)

    response = FileResponse(open(target, "rb"), as_attachment=True, filename=target.name)
    response["Access-Control-Allow-Origin"] = "*"
    return response


# ---------------------------------------------------------------------------
# API index — /api/v1  and  /api/v1/
# ---------------------------------------------------------------------------

@require_GET
def api_index(request):
    """GET /api/v1 — returns a JSON directory of all available endpoints."""
    base = request.build_absolute_uri("/").rstrip("/")
    endpoints = [
        {"method": "GET", "path": "/api/v1/health",                          "description": "Database connectivity check"},
        {"method": "GET", "path": "/api/v1/datasets",                         "description": "List all datasets with row counts"},
        {"method": "GET", "path": "/api/v1/datasets/{dataset_id}",            "description": "Metadata for a single dataset"},
        {"method": "GET", "path": "/api/v1/categories",                       "description": "List all categories with counts"},
        {"method": "GET", "path": "/api/v1/observations",                     "description": "Query observations (filter + paginate)"},
        {"method": "GET", "path": "/api/v1/files/{kind}",                     "description": "List raw or processed files (kind: raw|processed)"},
        {"method": "GET", "path": "/api/v1/download/{kind}.zip",              "description": "Download all files as a ZIP archive"},
        {"method": "GET", "path": "/api/v1/download/{kind}/{filepath}",       "description": "Download a single file by path"},
    ]
    return _json({
        "name": "Open Data Philippines ETL — REST API",
        "version": "v1",
        "base_url": f"{base}/api/v1",
        "docs_url": f"{base}/api-docs/",
        "endpoints": endpoints,
    })
