import os
import glob
import logging
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Count
from django.contrib import messages

from .models import Observation
from src.db.database import engine, test_connection
from src.extractors.psa_extractor import PsaExtractor
from src.transformers.psa_transformer import PsaTransformer
from src.validators.base_validator import DataValidator
from src.loaders.postgres_loader import PostgresLoader

logger = logging.getLogger(__name__)

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
            total_datasets = Observation.objects.values('dataset_id').distinct().count()
            total_categories = Observation.objects.values('category').distinct().count()
            
            category_stats = Observation.objects.values('category').annotate(count=Count('id')).order_by('-count')
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        messages.error(request, f"Database connection warning: {e}")

    # Check local raw data files
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
    
    # Query parameters
    category = request.GET.get('category', '').strip()
    dataset_id = request.GET.get('dataset_id', '').strip()
    year = request.GET.get('year', '').strip()
    search = request.GET.get('search', '').strip()
    
    if category:
        qs = qs.filter(category=category)
    if dataset_id:
        qs = qs.filter(dataset_id=dataset_id)
    if year.isdigit():
        qs = qs.filter(year=int(year))
    if search:
        qs = qs.filter(
            models.Q(entity_name__icontains=search) | 
            models.Q(variable_name__icontains=search) |
            models.Q(dataset_id__icontains=search)
        )
        
    paginator = Paginator(qs, 50)  # 50 rows per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Distinct lists for filter dropdowns
    categories = Observation.objects.values_list('category', flat=True).distinct().order_by('category')
    years = Observation.objects.values_list('year', flat=True).distinct().order_by('-year')
    
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
    """Pipeline Control Center to run Extraction, Transformation, Validation, and Loading."""
    logs = []
    
    if request.method == "POST":
        action = request.POST.get("action", "")
        
        if action == "extract":
            logs.append("=== Starting PSA OpenSTAT Extraction ===")
            try:
                extractor = PsaExtractor()
                files = extractor.extract()
                logs.append(f"Successfully extracted {len(files)} dataset files.")
                messages.success(request, f"Extraction complete! Downloaded {len(files)} files.")
            except Exception as e:
                logs.append(f"Extraction Error: {e}")
                messages.error(request, f"Extraction failed: {e}")
                
        elif action == "transform":
            logs.append("=== Starting Transformation & Quality Validation ===")
            try:
                raw_files = glob.glob("data/raw/psa/*.csv")
                transformer = PsaTransformer()
                validator = DataValidator()
                
                processed_count = 0
                total_quality = 0.0
                
                for filepath in raw_files:
                    df = transformer.transform(filepath)
                    if not df.empty:
                        clean_df, metrics = validator.validate(df)
                        processed_count += len(clean_df)
                        total_quality += metrics.get("quality_score", 100.0)
                        
                logs.append(f"Transformed {len(raw_files)} files into {processed_count} validated observations.")
                messages.success(request, f"Transformation complete! Processed {processed_count} rows.")
            except Exception as e:
                logs.append(f"Transformation Error: {e}")
                messages.error(request, f"Transformation failed: {e}")
                
        elif action == "load":
            logs.append("=== Starting PostgreSQL Loading ===")
            try:
                raw_files = glob.glob("data/raw/psa/*.csv")
                transformer = PsaTransformer()
                validator = DataValidator()
                loader = PostgresLoader(engine)
                
                loaded_datasets = 0
                for filepath in raw_files:
                    df = transformer.transform(filepath)
                    if not df.empty:
                        clean_df, _ = validator.validate(df)
                        dataset_id = clean_df["dataset_id"].iloc[0] if "dataset_id" in clean_df else "unknown"
                        if loader.load(clean_df, dataset_id):
                            loaded_datasets += 1
                            
                logs.append(f"Successfully loaded {loaded_datasets} datasets into PostgreSQL.")
                messages.success(request, f"Loading complete! Loaded {loaded_datasets} datasets into Database.")
            except Exception as e:
                logs.append(f"Loading Error: {e}")
                messages.error(request, f"Loading failed: {e}")
                
        elif action == "all":
            logs.append("=== Executing Full ETL Pipeline (Extract -> Transform -> Validate -> Load) ===")
            try:
                # 1. Extract
                extractor = PsaExtractor()
                files = extractor.extract()
                logs.append(f"1. Extracted {len(files)} files.")
                
                # 2. Transform, Validate, Load
                transformer = PsaTransformer()
                validator = DataValidator()
                engine = get_engine()
                loader = PostgresLoader(engine)
                
                loaded_datasets = 0
                total_rows = 0
                
                for filepath in files:
                    df = transformer.transform(filepath)
                    if not df.empty:
                        clean_df, _ = validator.validate(df)
                        dataset_id = clean_df["dataset_id"].iloc[0] if "dataset_id" in clean_df else "unknown"
                        if loader.load(clean_df, dataset_id):
                            loaded_datasets += 1
                            total_rows += len(clean_df)
                            
                logs.append(f"2. Pipeline Complete! Loaded {total_rows} observations across {loaded_datasets} datasets.")
                messages.success(request, f"Full ETL Pipeline executed successfully! {total_rows} rows loaded.")
            except Exception as e:
                logs.append(f"Pipeline Error: {e}")
                messages.error(request, f"Full Pipeline execution failed: {e}")

    context = {
        "logs": logs,
    }
    return render(request, "pipeline.html", context)
