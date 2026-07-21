import glob
import logging
import os
import sys
import pandas as pd

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from src.db.database import engine, init_db
from src.validators.base_validator import DataValidator
from src.loaders.postgres_loader import PostgresLoader

def run():
    logger.info("Initializing database schema...")
    init_db()
    
    validator = DataValidator()
    loader = PostgresLoader(engine=engine)
    
    files = glob.glob("data/processed/psa/*.csv")
    if not files:
        print("No processed files found.")
        return
        
    for file in files:
        print(f"\n======================================")
        print(f"Loading: {os.path.basename(file)}")
        print(f"======================================")
        
        # Load the transformed data
        df = pd.read_csv(file)
        
        # Validate it
        clean_df, metrics = validator.validate(df)
        dataset_id = clean_df["dataset_id"].iloc[0] if not clean_df.empty else "UNKNOWN"
        
        # Load it into Postgres
        success = loader.load(clean_df, dataset_id)
        
        if success:
            print(f"Successfully loaded dataset {dataset_id} into PostgreSQL.")
        else:
            print(f"Failed to load dataset {dataset_id}.")

if __name__ == "__main__":
    run()
