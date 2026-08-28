"""
Run the entire ETL Pipeline (Extract -> Transform -> Validate -> Load) via CLI or GUI.
"""
import logging
import sys

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from scripts.run_psa_extraction import run as run_extraction
from scripts.run_transformers import run as run_transformation
from scripts.run_loader import run as run_load

def run():
    logger.info("=== FULL ETL PIPELINE: Extract -> Transform -> Validate -> Load ===")
    
    logger.info("--- STEP 1: EXTRACTION ---")
    extracted_files = run_extraction()
    logger.info("Step 1 complete: %d file(s) extracted.", len(extracted_files))
    
    logger.info("--- STEP 2: TRANSFORMATION & VALIDATION ---")
    transformed_files = run_transformation()
    logger.info("Step 2 complete: %d file(s) transformed.", len(transformed_files))
    
    logger.info("--- STEP 3: LOADING INTO POSTGRESQL ---")
    loaded_count = run_load()
    logger.info("Step 3 complete: %d dataset(s) loaded.", loaded_count)
    
    logger.info("=== FULL ETL PIPELINE COMPLETE ===")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run()
