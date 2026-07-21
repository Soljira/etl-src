"""
Quick smoke test: run the PSA extractor against the live OpenSTAT API.
This hits the real API — only run manually, never in CI.
"""
import sys
import logging

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from src.extractors.psa_extractor import PsaExtractor

extractor = PsaExtractor()
files = extractor.extract()

print("\n========== EXTRACTION RESULTS ==========")
print(f"Total files downloaded: {len(files)}")
for f in files:
    import os
    size_kb = os.path.getsize(f) / 1024
    print(f"  {f}  ({size_kb:.1f} KB)")
