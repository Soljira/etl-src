"""
Run the PostgreSQL loader over processed CSV files.
"""
import glob
import logging
import os
import sys
import pandas as pd

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from src.db.database import engine, init_db
from src.validators.base_validator import DataValidator
from src.loaders.postgres_loader import PostgresLoader

def run():
    logger.info("=== Starting PostgreSQL Loading ===")
    init_db()
    
    validator = DataValidator()
    loader = PostgresLoader(engine=engine)
    
    files = glob.glob("data/processed/psa/*.csv") + glob.glob("data/processed/*.csv")
    # Deduplicate while preserving order
    files = list(dict.fromkeys(files))
    
    if not files:
        logger.warning("No processed files found in data/processed/psa/")
        return 0
        
    loaded_count = 0
    for file in files:
        logger.info("Loading: %s", os.path.basename(file))
        
        try:
            df = pd.read_csv(file, low_memory=False)
            if df.empty:
                logger.warning("File %s is empty, skipping.", file)
                continue
                
            clean_df, metrics = validator.validate(df)
            cat_name = clean_df["category"].iloc[0] if not clean_df.empty and "category" in clean_df else os.path.basename(file)
            
            success = loader.load(clean_df)
            if success:
                loaded_count += 1
                logger.info("Successfully loaded category '%s' (%d rows) into PostgreSQL.", cat_name, len(clean_df))
            else:
                logger.error("Failed to load dataset %s.", cat_name)
        except Exception as e:
            logger.error("Error loading %s: %s", file, e)

    logger.info("=== Loading Complete: %d dataset(s) loaded into PostgreSQL. ===", loaded_count)
    return loaded_count

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run()
