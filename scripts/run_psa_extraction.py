"""
Run the PSA extractor against the live OpenSTAT API.
"""
import logging
import os
import sys

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)

from src.extractors.psa_extractor import PsaExtractor

def run():
    logger.info("=== Starting PSA OpenSTAT Extraction ===")
    extractor = PsaExtractor()
    files = extractor.extract()
    logger.info("========== EXTRACTION RESULTS ==========")
    logger.info("Total files downloaded: %d", len(files))
    for f in files:
        if os.path.exists(f):
            size_kb = os.path.getsize(f) / 1024
            logger.info("  %s  (%.1f KB)", f, size_kb)
    return files

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run()
