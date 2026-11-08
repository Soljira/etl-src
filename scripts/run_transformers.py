"""
Run transformers over raw CSVs from all sources (PSA + BetterGov).
"""
import glob
import logging
import os
import sys
import pandas as pd

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from src.transformers.psa_transformer import PsaTransformer
from src.transformers.bettergov_transformer import BetterGovTransformer
from src.validators.base_validator import DataValidator


def _process_source(
    raw_dir: str,
    output_dir: str,
    transformer,
    validator: DataValidator,
    source_label: str,
) -> list[str]:
    """
    Transform + validate all raw CSVs in *raw_dir* using *transformer*.
    Returns list of saved processed file paths.
    """
    raw_pattern = os.path.join(raw_dir, "*.csv")
    raw_xlsx = os.path.join(raw_dir, "*.xlsx")
    raw_files = glob.glob(raw_pattern) + glob.glob(raw_xlsx)
    # Exclude metadata sidecar
    raw_files = [f for f in raw_files if os.path.basename(f) != "_metadata.json"]

    if not raw_files:
        logger.warning("No raw files found in %s", raw_dir)
        return []

    logger.info("--- %s: Processing %d raw file(s) ---", source_label, len(raw_files))

    category_dfs: dict[str, list[pd.DataFrame]] = {}

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

    # Clean out old CSV files in output_dir before saving consolidated ones
    for old_file in glob.glob(os.path.join(output_dir, "*.csv")):
        try:
            os.remove(old_file)
        except Exception:
            pass

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

    logger.info(
        "%s: %d category file(s) saved -> %d total rows.",
        source_label, len(processed_files), total_rows,
    )
    return processed_files


def run() -> list[str]:
    logger.info("=== Starting Data Transformation & Quality Validation ===")
    validator = DataValidator()
    all_processed: list[str] = []

    # --- PSA ---
    psa_raw = "data/raw/psa"
    if os.path.isdir(psa_raw) and glob.glob(os.path.join(psa_raw, "*.csv")):
        psa_transformer = PsaTransformer(output_dir="data/processed/psa")
        all_processed += _process_source(
            psa_raw, "data/processed/psa", psa_transformer, validator, "PSA"
        )

    # --- BetterGov ---
    bg_raw = "data/raw/bettergov"
    if os.path.isdir(bg_raw) and (
        glob.glob(os.path.join(bg_raw, "*.csv"))
        or glob.glob(os.path.join(bg_raw, "*.xlsx"))
    ):
        bg_transformer = BetterGovTransformer(output_dir="data/processed/bettergov")
        bg_transformer.load_metadata(raw_dir=bg_raw)
        all_processed += _process_source(
            bg_raw, "data/processed/bettergov", bg_transformer, validator, "BetterGov"
        )

    logger.info(
        "=== Transformation Complete: %d category file(s) saved total. ===",
        len(all_processed),
    )
    return all_processed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run()

