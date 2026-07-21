"""
Run the PSA transformer over a sample of raw CSVs to verify output.
"""
import glob
import logging
import os
import sys

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from src.transformers.psa_transformer import PsaTransformer

def run():
    transformer = PsaTransformer(output_dir="data/processed/psa")
    
    # Grab one file from each category
    categories = [
        "Agriculture_Forestry_Fisheries",
        "Labor_and_Employment",
        "Population_and_Vital_Statistics",
        "Mining_Manufacturing_Construction"
    ]
    
    for cat in categories:
        files = glob.glob(f"data/raw/psa/{cat}*.csv")
        if not files:
            print(f"No files found for {cat}")
            continue
            
        test_file = files[0]
        print(f"\n======================================")
        print(f"Transforming: {os.path.basename(test_file)}")
        print(f"======================================")
        
        try:
            df = transformer.transform(test_file)
            if not df.empty:
                print(f"Success! {len(df)} rows transformed.")
                print(df.head(5).to_string(index=False))
                
                # Save it
                transformer.save_processed_data(df, os.path.basename(test_file))
            else:
                print("Transformation resulted in empty DataFrame.")
        except Exception as e:
            print(f"Error transforming: {e}")

if __name__ == "__main__":
    run()
