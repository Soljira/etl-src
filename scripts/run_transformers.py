"""
Run the PSA transformer over raw CSVs to transform and validate output.
"""
import glob
import logging
import os
import sys
import pandas as pd

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from src.transformers.psa_transformer import PsaTransformer
from src.validators.base_validator import DataValidator

def run():
    logger.info("=== Starting Data Transformation & Quality Validation ===")
    transformer = PsaTransformer(output_dir="data/processed/psa")
    validator = DataValidator()
    
    raw_files = glob.glob("data/raw/psa/*.csv")
    if not raw_files:
        logger.warning("No raw CSV files found in data/raw/psa/")
        return []

    # Dictionary mapping category_name -> list of transformed DataFrames
    category_dfs = {}
    
    for raw_file in raw_files:
        try:
            logger.info("Transforming: %s", os.path.basename(raw_file))
            df = transformer.transform(raw_file)
            if not df.empty:
                cat = df["category"].iloc[0] if "category" in df.columns and pd.notna(df["category"].iloc[0]) else "Unknown"
                if cat not in category_dfs:
                    category_dfs[cat] = []
                category_dfs[cat].append(df)
            else:
                logger.warning("Transformation resulted in empty DataFrame for %s", raw_file)
        except Exception as e:
            logger.error("Error transforming %s: %s", raw_file, e)

    processed_files = []
    total_rows = 0

    # Clean out any old individual CSV files in output_dir before saving consolidated ones
    for old_file in glob.glob(os.path.join(transformer.output_dir, "*.csv")):
        try:
            os.remove(old_file)
        except Exception:
            pass

    # Save one consolidated CSV file per category
    for cat, dfs in category_dfs.items():
        cat_df = pd.concat(dfs, ignore_index=True)
        clean_df, metrics = validator.validate(cat_df)
        out_filename = f"{cat}.csv"
        saved_path = transformer.save_processed_data(clean_df, out_filename)
        processed_files.append(saved_path)
        total_rows += len(clean_df)
        logger.info(
            "Saved Category '%s' -> %d rows into %s (Quality Score: %.2f)",
            cat, len(clean_df), out_filename, metrics.get("quality_score", 100.0)
        )

    logger.info("=== Transformation Complete: %d category file(s) saved -> %d total rows. ===", len(processed_files), total_rows)
    return processed_files

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run()
