"""
Run the BetterGov extractor against the live Open Data Portal API.
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from src.extractors.bettergov_extractor import BetterGovExtractor


def run(categories: list[str] = None) -> list[str]:
    logger.info("=== Starting BetterGov Open Data Portal Extraction ===")
    extractor = BetterGovExtractor()
    files = extractor.extract(categories=categories)
    logger.info("========== EXTRACTION RESULTS ==========")
    logger.info("Total files downloaded: %d", len(files))
    for f in files:
        if os.path.exists(f):
            size_kb = os.path.getsize(f) / 1024
            logger.info("  %s  (%.1f KB)", f, size_kb)
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run BetterGov Open Data Extraction")
    parser.add_argument(
        "--categories",
        nargs="+",
        help="List of category names to extract (e.g. Government Finance)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run(categories=args.categories)
