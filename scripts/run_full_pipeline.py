"""
Run the entire ETL Pipeline (Extract -> Transform -> Validate -> Load) via CLI or GUI.

Supports multiple data sources:
  --source psa       → PSA OpenSTAT only
  --source bettergov → BetterGov Open Data Portal only
  --source all       → Both sources (default)
"""
import argparse
import logging
import sys

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from scripts.run_transformers import run as run_transformation
from scripts.run_validation import run as run_validation
from scripts.run_loader import run as run_load


def run(categories: list[str] = None, source: str = "all"):
    logger.info("=== FULL ETL PIPELINE: Extract -> Transform -> Validate -> Load ===")
    logger.info("Source: %s", source)

    # --- STEP 1: EXTRACTION ---
    logger.info("--- STEP 1: EXTRACTION ---")
    extracted_files: list[str] = []

    if source in ("psa", "all"):
        from scripts.run_psa_extraction import run as run_psa_extraction
        psa_files = run_psa_extraction(categories=categories)
        extracted_files.extend(psa_files)

    if source in ("bettergov", "all"):
        from scripts.run_bettergov_extraction import run as run_bg_extraction
        # BetterGov categories are names like "Government", not codes like "2E"
        bg_categories = categories if source == "bettergov" else None
        bg_files = run_bg_extraction(categories=bg_categories)
        extracted_files.extend(bg_files)

    logger.info("Step 1 complete: %d file(s) extracted.", len(extracted_files))

    # --- STEP 2: TRANSFORMATION & VALIDATION ---
    logger.info("--- STEP 2: TRANSFORMATION & VALIDATION ---")
    transformed_files = run_transformation()
    logger.info("Step 2 complete: %d file(s) transformed.", len(transformed_files))

    # --- STEP 3: EXPLICIT VALIDATION REPORT ---
    logger.info("--- STEP 3: EXPLICIT VALIDATION REPORT ---")
    run_validation()
    logger.info("Step 3 complete: Validation report generated.")

    # --- STEP 4: LOADING INTO POSTGRESQL ---
    logger.info("--- STEP 4: LOADING INTO POSTGRESQL ---")
    loaded_count = run_load()
    logger.info("Step 4 complete: %d dataset(s) loaded.", loaded_count)

    logger.info("=== FULL ETL PIPELINE COMPLETE ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Full ETL Pipeline")
    parser.add_argument(
        "--categories", nargs="+",
        help="List of category IDs/names to extract (e.g. 2E 1A or Government Finance)",
    )
    parser.add_argument(
        "--source", choices=["psa", "bettergov", "all"], default="all",
        help="Data source to extract from (default: all)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run(categories=args.categories, source=args.source)

