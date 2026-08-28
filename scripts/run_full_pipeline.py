"""
Run the entire ETL Pipeline (Extract -> Transform -> Validate -> Load) via CLI.
"""
import glob
import logging
import os
import sys

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from src.extractors.psa_extractor import PsaExtractor
from src.transformers.psa_transformer import PsaTransformer
from src.validators.base_validator import DataValidator
from src.loaders.postgres_loader import PostgresLoader
from src.db.database import engine, init_db

def run():
    logger.info("=== 1. Starting Data Extraction ===")
    extractor = PsaExtractor()
    extracted_files = extractor.extract()
    logger.info("Downloaded %d CSV files.", len(extracted_files))
    
    logger.info("=== 2. Initializing Database Schema ===")
    init_db()
    
    logger.info("=== 3. Starting Transformation, Validation, and Loading ===")
    transformer = PsaTransformer(output_dir="data/processed/psa")
    validator = DataValidator()
    loader = PostgresLoader(engine=engine)
    
    raw_files = glob.glob("data/raw/psa/*.csv")
    if not raw_files:
        logger.warning("No raw CSV files found to process.")
        return
        
    loaded_count = 0
    total_observations = 0
    
    for filepath in raw_files:
        df = transformer.transform(filepath)
        if not df.empty:
            clean_df, metrics = validator.validate(df)
            dataset_id = clean_df["dataset_id"].iloc[0] if "dataset_id" in clean_df else "unknown"
            
            if loader.load(clean_df, dataset_id):
                loaded_count += 1
                total_observations += len(clean_df)
                logger.info("Loaded dataset %s (Quality Score: %.2f)", dataset_id, metrics.get("quality_score", 100.0))
                
    logger.info("=== ETL PIPELINE COMPLETE ===")
    logger.info("Successfully loaded %d datasets (%d total rows) into PostgreSQL.", loaded_count, total_observations)

if __name__ == "__main__":
    run()
