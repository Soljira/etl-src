import glob
import logging
import os
import sys
import pandas as pd

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from src.validators.base_validator import DataValidator

def run():
    logger.info("=== Starting Data Validation ===")
    validator = DataValidator()
    
    files = glob.glob("data/processed/psa/*.csv")
    if not files:
        logger.warning("No processed files found in data/processed/psa/")
        return
        
    for file in files:
        logger.info(f"Validating: {os.path.basename(file)}")
        
        # Read low_memory=False to avoid DtypeWarning
        df = pd.read_csv(file, low_memory=False)
        clean_df, metrics = validator.validate(df)
        
        logger.info(f"Quality Score: {metrics['quality_score']}/100")
        logger.info(f"Initial rows:  {metrics['initial_rows']}")
        logger.info(f"Final rows:    {metrics.get('final_rows', 0)}")
        
        if metrics["warnings"]:
            logger.warning("Warnings:")
            for w in metrics["warnings"]:
                logger.warning(f"  - {w}")
        else:
            logger.info("No warnings! Data is perfectly clean.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run()
