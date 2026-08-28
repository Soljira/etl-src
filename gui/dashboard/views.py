"""
Dashboard views for the ETL Web GUI.

Pipeline logging uses a background-thread + in-memory log store approach:
  POST /pipeline/run/  → starts the pipeline in a thread, returns run_id (JSON)
  GET  /pipeline/logs/ → returns new log lines since `since` index (JSON, poll every 500 ms)

This avoids WSGI streaming/buffering issues entirely.
"""
import glob
import json
import logging
import threading
import uuid
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Observation
from src.db.database import engine, test_connection
from src.extractors.psa_extractor import PsaExtractor
from src.transformers.psa_transformer import PsaTransformer
from src.validators.base_validator import DataValidator
from src.loaders.postgres_loader import PostgresLoader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory log store  {run_id: {"logs": [...], "done": bool}}
# ---------------------------------------------------------------------------
_RUNS: dict[str, dict] = {}
_RUNS_LOCK = threading.Lock()


class _RunHandler(logging.Handler):
    """Appends formatted log records straight into a run's log list."""

    def __init__(self, run_id: str) -> None:
        super().__init__()
        self._run_id = run_id

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "level": record.levelname,
            "msg": self.format(record),
        }
        with _RUNS_LOCK:
            run = _RUNS.get(self._run_id)
            if run is not None:
                run["logs"].append(entry)


# The 'src' logger is the parent of all pipeline loggers (src.extractors.*, etc.)
# It is configured in settings.LOGGING with level=INFO and propagate=False.
_PIPELINE_LOGGER = "src"


def _attach_handler(run_id: str) -> _RunHandler:
    handler = _RunHandler(run_id)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)
    lg = logging.getLogger(_PIPELINE_LOGGER)
    lg.setLevel(logging.INFO)
    lg.disabled = False
    lg.addHandler(handler)
    return handler


def _detach_handler(handler: _RunHandler) -> None:
    logging.getLogger(_PIPELINE_LOGGER).removeHandler(handler)


def _log(run_id: str, level: str, msg: str) -> None:
    """Append a synthetic log entry formatted identically to the logging module output."""
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    formatted = f"{ts} [{level}] pipeline: {msg}"
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
        if run is not None:
            run["logs"].append({"level": level, "msg": formatted})


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
    qs = Observation.objects.all()

    category = request.GET.get("category", "").strip()
    dataset_id = request.GET.get("dataset_id", "").strip()
    year = request.GET.get("year", "").strip()
    search = request.GET.get("search", "").strip()

    if category:
        qs = qs.filter(category=category)
    if dataset_id:
        qs = qs.filter(dataset_id=dataset_id)
    if year.isdigit():
        qs = qs.filter(year=int(year))
    if search:
        qs = qs.filter(
            models.Q(entity_name__icontains=search)
            | models.Q(variable_name__icontains=search)
            | models.Q(dataset_id__icontains=search)
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

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "years": [y for y in years if y is not None],
        "selected_category": category,
        "selected_dataset_id": dataset_id,
        "selected_year": year,
        "selected_search": search,
        "total_count": paginator.count,
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

    Starts the pipeline action in a background daemon thread.
    Returns JSON: {"run_id": "<uuid>"}
    """
    action = request.POST.get("action", "")
    run_id = str(uuid.uuid4())

    with _RUNS_LOCK:
        _RUNS[run_id] = {"logs": [], "done": False}

    def _worker() -> None:
        handler = _attach_handler(run_id)
        try:
            if action == "extract":
                _log(run_id, "INFO", "=== Starting PSA OpenSTAT Extraction ===")
                extractor = PsaExtractor()
                files = extractor.extract()
                _log(run_id, "INFO", f"=== Done: {len(files)} file(s) downloaded. ===")

            elif action == "transform":
                _log(run_id, "INFO", "=== Starting Transformation & Quality Validation ===")
                raw_files = glob.glob("data/raw/psa/*.csv")
                transformer = PsaTransformer()
                validator = DataValidator()
                processed_count = 0
                for filepath in raw_files:
                    df = transformer.transform(filepath)
                    if not df.empty:
                        clean_df, metrics = validator.validate(df)
                        processed_count += len(clean_df)
                _log(run_id, "INFO", f"=== Done: {len(raw_files)} file(s) → {processed_count} rows. ===")

            elif action == "load":
                _log(run_id, "INFO", "=== Starting PostgreSQL Loading ===")
                raw_files = glob.glob("data/raw/psa/*.csv")
                transformer = PsaTransformer()
                validator = DataValidator()
                loader = PostgresLoader(engine)
                loaded_datasets = 0
                for filepath in raw_files:
                    df = transformer.transform(filepath)
                    if not df.empty:
                        clean_df, _ = validator.validate(df)
                        dataset_id = (
                            clean_df["dataset_id"].iloc[0]
                            if "dataset_id" in clean_df
                            else "unknown"
                        )
                        if loader.load(clean_df, dataset_id):
                            loaded_datasets += 1
                _log(run_id, "INFO", f"=== Done: {loaded_datasets} dataset(s) loaded into PostgreSQL. ===")

            elif action == "all":
                _log(run_id, "INFO", "=== Full ETL Pipeline: Extract → Transform → Validate → Load ===")
                extractor = PsaExtractor()
                files = extractor.extract()
                _log(run_id, "INFO", f"--- Step 1 complete: {len(files)} file(s) extracted ---")
                transformer = PsaTransformer()
                validator = DataValidator()
                loader = PostgresLoader(engine)
                loaded_datasets = 0
                total_rows = 0
                for filepath in files:
                    df = transformer.transform(filepath)
                    if not df.empty:
                        clean_df, _ = validator.validate(df)
                        dataset_id = (
                            clean_df["dataset_id"].iloc[0]
                            if "dataset_id" in clean_df
                            else "unknown"
                        )
                        if loader.load(clean_df, dataset_id):
                            loaded_datasets += 1
                            total_rows += len(clean_df)
                _log(run_id, "INFO", f"=== Done: {total_rows} rows across {loaded_datasets} dataset(s) loaded. ===")

            else:
                _log(run_id, "ERROR", f"Unknown action: '{action}'")

        except Exception as exc:
            _log(run_id, "ERROR", f"Pipeline error: {exc}")
        finally:
            _detach_handler(handler)
            with _RUNS_LOCK:
                run = _RUNS.get(run_id)
                if run is not None:
                    run["done"] = True

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    return JsonResponse({"run_id": run_id})


@require_GET
def pipeline_logs(request):
    """
    GET /pipeline/logs/?run_id=<uuid>&since=<int>

    Returns new log entries since index `since`.
    JSON: {"logs": [{"level": str, "msg": str}, ...], "done": bool}
    """
    run_id = request.GET.get("run_id", "")
    since = int(request.GET.get("since", 0))

    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            return JsonResponse({"error": "Unknown run_id"}, status=404)
        new_logs = run["logs"][since:]
        done = run["done"]

    return JsonResponse({"logs": new_logs, "done": done})
