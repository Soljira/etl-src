"""
Dashboard views for the ETL Web GUI.

Pipeline logging uses a background-thread + file-based log store:
  POST /pipeline/run/  → starts the pipeline in a thread, returns run_id (JSON)
  GET  /pipeline/logs/ → reads new log lines from logs/pipeline/{run_id}.jsonl

Each run writes to a JSONL file on disk so logs survive container restarts.
The browser polls /pipeline/logs/ every 500 ms and replays all lines on reload.
"""
import glob
import json
import logging
import os
import threading
import uuid
import pandas as pd
from datetime import datetime

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import Observation
from src.db.database import test_connection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File-based log store
# ---------------------------------------------------------------------------
# Each run writes to:  logs/pipeline/<run_id>.jsonl
# Each line is a JSON object: {"level": "INFO", "msg": "..."} or {"done": true}
# The file is mounted via docker-compose so it persists across restarts.

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "pipeline")
os.makedirs(LOG_DIR, exist_ok=True)

_WRITE_LOCK = threading.Lock()  # serialise concurrent writes to the same file


def _run_log_path(run_id: str) -> str:
    return os.path.join(LOG_DIR, f"{run_id}.jsonl")


def _write_entry(run_id: str, entry: dict) -> None:
    """Append one JSON line to the run's log file (thread-safe)."""
    with _WRITE_LOCK:
        with open(_run_log_path(run_id), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
            fh.flush()


def _read_entries(run_id: str) -> tuple[list[dict], bool]:
    """
    Read all log entries from the run's JSONL file.
    Returns (entries, done) where done is True if the sentinel line exists.
    """
    path = _run_log_path(run_id)
    if not os.path.exists(path):
        return [], False

    entries: list[dict] = []
    done = False
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if obj.get("done"):
                done = True
            else:
                entries.append(obj)
    return entries, done


# ---------------------------------------------------------------------------
# Logging handler that writes to the JSONL file
# ---------------------------------------------------------------------------

class _FileHandler(logging.Handler):
    """Writes formatted log records as JSON lines to the run's log file."""

    def __init__(self, run_id: str) -> None:
        super().__init__()
        self._run_id = run_id

    def emit(self, record: logging.LogRecord) -> None:
        _write_entry(self._run_id, {
            "level": record.levelname,
            "msg": self.format(record),
        })


# The 'src' logger is the parent of all pipeline module loggers.
# Configured in settings.LOGGING with level=INFO and propagate=False.
_PIPELINE_LOGGER = "src"


def _attach_handler(run_id: str) -> _FileHandler:
    handler = _FileHandler(run_id)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)
    
    # Attach to root logger
    lg = logging.getLogger()
    lg.setLevel(logging.INFO)
    lg.addHandler(handler)
    
    # Also attach to 'src' and 'scripts' loggers explicitly because Django 
    # configuration sets propagate=False for them.
    for name in ["src", "scripts"]:
        logger_instance = logging.getLogger(name)
        logger_instance.addHandler(handler)
        
    return handler


def _detach_handler(handler: _FileHandler) -> None:
    logging.getLogger().removeHandler(handler)
    for name in ["src", "scripts"]:
        logging.getLogger(name).removeHandler(handler)


def _log(run_id: str, level: str, msg: str) -> None:
    """Write a synthetic separator/summary line in the same format as the logging module."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    formatted = f"{ts} [{level}] pipeline: {msg}"
    _write_entry(run_id, {"level": level, "msg": formatted})


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def index(request):
    """Dashboard homepage showing system metrics and category breakdown."""
    db_connected = False
    total_observations = 0
    total_datasets = 0
    total_categories = 0
    category_stats = []

    try:
        db_connected = test_connection()
        if db_connected:
            total_observations = Observation.objects.count()
            total_datasets = Observation.objects.values("dataset_id").distinct().count()
            total_categories = Observation.objects.values("category").distinct().count()
            category_stats = (
                Observation.objects.values("category")
                .annotate(count=Count("id"))
                .order_by("-count")
            )
    except Exception as e:
        logger.error("Error fetching dashboard stats: %s", e)
        messages.error(request, f"Database connection warning: {e}")

    raw_files = glob.glob("data/raw/psa/*.csv")

    context = {
        "db_connected": db_connected,
        "total_observations": total_observations,
        "total_datasets": total_datasets,
        "total_categories": total_categories,
        "category_stats": category_stats,
        "raw_files_count": len(raw_files),
    }
    return render(request, "index.html", context)


def observations(request):
    """Filterable Data Explorer with pagination."""
    category = request.GET.get("category", "").strip()
    dataset_id = request.GET.get("dataset_id", "").strip()
    year = request.GET.get("year", "").strip()
    search = request.GET.get("search", "").strip()

    try:
        qs = Observation.objects.all()

        if category:
            qs = qs.filter(category=category)
        if dataset_id:
            qs = qs.filter(dataset_id=dataset_id)
        if year.isdigit():
            qs = qs.filter(year=int(year))
        if search:
            qs = qs.filter(
                Q(entity_name__icontains=search)
                | Q(variable_name__icontains=search)
                | Q(dataset_id__icontains=search)
            )

        paginator = Paginator(qs, 50)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        categories = (
            Observation.objects.values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )
        years = (
            Observation.objects.values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )
        total_count = paginator.count

    except Exception as e:
        # Table may not exist yet — show empty state instead of crashing
        logger.warning("Data Explorer query failed (table may not exist yet): %s", e)
        page_obj = None
        categories = []
        years = []
        total_count = 0

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "years": [y for y in years if y is not None],
        "selected_category": category,
        "selected_dataset_id": dataset_id,
        "selected_year": year,
        "selected_search": search,
        "total_count": total_count,
        "table_missing": page_obj is None,
    }
    return render(request, "observations.html", context)


def pipeline(request):
    """Pipeline Control Center page (just renders the template)."""
    return render(request, "pipeline.html", {})


# ---------------------------------------------------------------------------
# Pipeline async run + log polling endpoints
# ---------------------------------------------------------------------------

@require_POST
def pipeline_run(request):
    """
    POST /pipeline/run/
    Body: action=extract|transform|load|all

    Creates a JSONL log file for this run, starts the pipeline in a daemon
    thread, and immediately returns the run_id so the browser can start polling.
    """
    action = request.POST.get("action", "")
    run_id = str(uuid.uuid4())

    # Create the log file immediately so pipeline_logs can detect it
    open(_run_log_path(run_id), "w").close()

    def _worker() -> None:
        handler = _attach_handler(run_id)
        try:
            if action == "extract":
                from scripts.run_psa_extraction import run as run_extraction
                run_extraction()

            elif action == "transform":
                from scripts.run_transformers import run as run_transformation
                run_transformation()

            elif action == "load":
                from scripts.run_loader import run as run_load
                run_load()

            elif action == "all":
                from scripts.run_full_pipeline import run as run_full
                run_full()

            else:
                _log(run_id, "ERROR", f"Unknown action: '{action}'")

        except Exception as exc:
            _log(run_id, "ERROR", f"Pipeline error: {exc}")
        finally:
            _detach_handler(handler)
            # Write the sentinel "done" line
            _write_entry(run_id, {"done": True})

    threading.Thread(target=_worker, daemon=True).start()
    return JsonResponse({"run_id": run_id})


@require_GET
def pipeline_logs(request):
    """
    GET /pipeline/logs/?run_id=<uuid>&since=<int>

    Reads the JSONL log file for the run and returns entries since index `since`.
    JSON: {"logs": [{"level": str, "msg": str}, ...], "done": bool}
    """
    run_id = request.GET.get("run_id", "")
    since = int(request.GET.get("since", 0))

    # Basic path safety: only allow UUIDs
    try:
        uuid.UUID(run_id)
    except ValueError:
        return JsonResponse({"error": "Invalid run_id"}, status=400)

    entries, done = _read_entries(run_id)
    if not os.path.exists(_run_log_path(run_id)):
        return JsonResponse({"error": "Unknown run_id"}, status=404)

    return JsonResponse({"logs": entries[since:], "done": done})
