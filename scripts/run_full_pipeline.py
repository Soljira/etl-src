"""
Run the entire ETL Pipeline (Extract -> Transform -> Validate -> Load) via CLI or GUI.
"""
import logging
import sys

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from scripts.run_psa_extraction import run as run_extraction
from scripts.run_transformers import run as run_transformation
from scripts.run_validation import run as run_validation
from scripts.run_loader import run as run_load

def run(categories: list[str] = None):
    logger.info("=== FULL ETL PIPELINE: Extract -> Transform -> Validate -> Load ===")
    
    logger.info("--- STEP 1: EXTRACTION ---")
    extracted_files = run_extraction(categories=categories)
    logger.info("Step 1 complete: %d file(s) extracted.", len(extracted_files))
    
    logger.info("--- STEP 2: TRANSFORMATION & VALIDATION ---")
    transformed_files = run_transformation()
    logger.info("Step 2 complete: %d file(s) transformed.", len(transformed_files))
    
    logger.info("--- STEP 3: EXPLICIT VALIDATION REPORT ---")
    run_validation()
    logger.info("Step 3 complete: Validation report generated.")
    
    logger.info("--- STEP 4: LOADING INTO POSTGRESQL ---")
    loaded_count = run_load()
    logger.info("Step 4 complete: %d dataset(s) loaded.", loaded_count)
    
    logger.info("=== FULL ETL PIPELINE COMPLETE ===")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Full ETL Pipeline")
    parser.add_argument("--categories", nargs="+", help="List of category IDs to extract (e.g. 2E 1A)")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run(categories=args.categories)
