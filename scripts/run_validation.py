import glob
import logging
import os
import sys
import pandas as pd

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from src.validators.base_validator import DataValidator

def run():
    validator = DataValidator()
    
    files = glob.glob("data/processed/psa/*.csv")
    if not files:
        print("No processed files found in data/processed/psa/")
        return
        
    for file in files:
        print(f"\n======================================")
        print(f"Validating: {os.path.basename(file)}")
        print(f"======================================")
        
        df = pd.read_csv(file)
        clean_df, metrics = validator.validate(df)
        
        print(f"Quality Score: {metrics['quality_score']}/100")
        print(f"Initial rows:  {metrics['initial_rows']}")
        print(f"Final rows:    {metrics.get('final_rows', 0)}")
        
        if metrics["warnings"]:
            print("\nWarnings:")
            for w in metrics["warnings"]:
                print(f"  - {w}")
        else:
            print("\nNo warnings! Data is perfectly clean.")

if __name__ == "__main__":
    run()
