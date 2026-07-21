import logging
import pandas as pd
from sqlalchemy.orm import Session
from src.loaders.base_loader import BaseLoader
from src.db.models import Observation

logger = logging.getLogger(__name__)

class PostgresLoader(BaseLoader):
    """
    Loads DataFrames into PostgreSQL using SQLAlchemy.
    """
    
    def __init__(self, engine):
        self.engine = engine

    def load(self, df: pd.DataFrame, dataset_id: str) -> bool:
        """
        Loads the DataFrame into the 'observations' table.
        Deletes any existing records for the given dataset_id before inserting
        to prevent duplicate data across multiple pipeline runs.
        """
        if df.empty:
            logger.warning(f"Skipping load for {dataset_id}: DataFrame is empty.")
            return False
            
        try:
            with Session(self.engine) as session:
                # 1. Delete existing records for this dataset to make operations idempotent
                deleted_count = session.query(Observation).filter(Observation.dataset_id == dataset_id).delete()
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} existing records for dataset {dataset_id}.")
                session.commit()
                
            # 2. Bulk insert new records
            # Using pandas 'to_sql' for simplicity and speed.
            # We append to the 'observations' table. 
            # We don't write the DataFrame index.
            
            # Ensure the DataFrame only contains columns that match our model
            model_columns = ["dataset_id", "category", "entity_name", "variable_name", "year", "period", "value"]
            insert_df = df[[c for c in model_columns if c in df.columns]].copy()
            
            # Perform the insert
            logger.info(f"Inserting {len(insert_df)} records for dataset {dataset_id}...")
            insert_df.to_sql(
                name=Observation.__tablename__,
                con=self.engine,
                if_exists="append",
                index=False,
                method="multi", # Uses multi-row INSERTs
                chunksize=1000  # Insert 1000 rows at a time
            )
            logger.info(f"Successfully loaded dataset {dataset_id}.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load dataset {dataset_id} into PostgreSQL: {e}")
            return False
