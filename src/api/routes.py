import os

from flask import Blueprint, jsonify, request, send_from_directory, Response

from src.api import services
from src.db.database import test_connection

api_bp = Blueprint("api", __name__)


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check — verifies database connectivity."""
    db_ok = test_connection()
    status = "healthy" if db_ok else "unhealthy"
    code = 200 if db_ok else 503
    return jsonify({"status": status, "database": "connected" if db_ok else "disconnected"}), code


@api_bp.route("/datasets", methods=["GET"])
def list_datasets():
    """List all datasets with row counts."""
    data = services.list_datasets()
    return jsonify({"data": data, "count": len(data)})


@api_bp.route("/datasets/<dataset_id>", methods=["GET"])
def get_dataset(dataset_id: str):
    """Get metadata for a specific dataset."""
    meta = services.get_dataset_metadata(dataset_id)
    if meta is None:
        return jsonify({"error": f"Dataset '{dataset_id}' not found."}), 404
    return jsonify({"data": meta})


@api_bp.route("/categories", methods=["GET"])
def list_categories():
    """List all categories."""
    data = services.list_categories()
    return jsonify({"data": data, "count": len(data)})


@api_bp.route("/observations", methods=["GET"])
def query_observations():
    """Query observations with filtering and pagination."""
    # Parse query parameters
    category = request.args.get("category")
    dataset_id = request.args.get("dataset_id")
    entity_name = request.args.get("entity_name")
    variable_name = request.args.get("variable_name")

    year = request.args.get("year", type=int)
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)

    data, pagination = services.query_observations(
        category=category,
        dataset_id=dataset_id,
        year=year,
        entity_name=entity_name,
        variable_name=variable_name,
        page=page,
        per_page=per_page,
    )

    return jsonify({"data": data, "pagination": pagination})


# ---------------------------------------------------------------------------
# File download routes (no DB required)
# ---------------------------------------------------------------------------

@api_bp.route("/files/<kind>", methods=["GET"])
def list_files(kind: str):
    """Return JSON list of available raw or processed files plus a ZIP download URL."""
    if kind not in ("raw", "processed"):
        return jsonify({"error": "kind must be 'raw' or 'processed'."}), 400
    files = services.list_files(kind)
    return jsonify({
        "zip_url": f"/api/v1/download/{kind}.zip",
        "count": len(files),
        "files": files,
    })


@api_bp.route("/download/<kind>.zip", methods=["GET"])
def download_zip(kind: str):
    """Stream a ZIP archive of all raw or processed data files."""
    if kind not in ("raw", "processed"):
        return jsonify({"error": "kind must be 'raw' or 'processed'."}), 400
    zip_bytes = services.build_zip_bytes(kind)
    return Response(
        zip_bytes,
        status=200,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{kind}_files.zip"',
            "Content-Length": str(len(zip_bytes)),
        },
    )


@api_bp.route("/download/<kind>/<path:filename>", methods=["GET"])
def download_single_file(kind: str, filename: str):
    """Download a single raw or processed file by name."""
    if kind not in ("raw", "processed"):
        return jsonify({"error": "kind must be 'raw' or 'processed'."}), 400
    directory = str(services._data_dir(kind))
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": f"File '{filename}' not found."}), 404
    except Exception as exc:  # noqa: BLE001
        # werkzeug raises NotFound (HTTPException) for missing files in some versions
        from werkzeug.exceptions import NotFound
        if isinstance(exc, NotFound):
            return jsonify({"error": f"File '{filename}' not found."}), 404
        return jsonify({"error": str(exc)}), 500

