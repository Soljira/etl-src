import logging
import os
import pandas as pd
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseTransformer(ABC):
    """
    Abstract base class for data transformers.
    """
    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Unified schema definition
        self.schema = [
            "dataset_id",
            "category",
            "entity_name",
            "variable_name",
            "year",
            "period",
            "value"
        ]

    def save_processed_data(self, df: pd.DataFrame, filename: str) -> str:
        """
        Validates the schema and saves the DataFrame to a CSV.
        """
        # Ensure all schema columns exist, add missing as None
        for col in self.schema:
            if col not in df.columns:
                df[col] = None
                
        # Reorder to match schema exactly and drop extra columns
        df = df[self.schema]
        
        filepath = os.path.join(self.output_dir, filename)
        df.to_csv(filepath, index=False)
        logger.info(f"Saved processed data to {filepath}")
        return filepath

    @abstractmethod
    def transform(self, filepath: str) -> pd.DataFrame:
        """
        Child classes must implement this to transform a raw CSV into the unified schema.
        """
        pass
