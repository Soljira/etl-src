import logging
import warnings
import pandas as pd

# Suppress pandas Copy-on-Write FutureWarnings (harmless until pandas 3.0)
warnings.filterwarnings("ignore", message=".*ChainedAssignmentError.*", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*incompatible dtype.*", category=FutureWarning)
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
                
            # 2. Build a clean, independent DataFrame for insertion.
            # Constructing from a dict breaks any parent-child link to `df`,
            # which prevents pandas Copy-on-Write FutureWarnings entirely.
            model_columns = ["dataset_id", "category", "entity_name", "variable_name", "year", "period", "value"]
            available = [c for c in model_columns if c in df.columns]
            insert_df = pd.DataFrame({col: df[col].values for col in available})
            
            # Truncate strings to prevent DataError (StringDataRightTruncation)
            str_limits = {"category": 100, "entity_name": 255, "variable_name": 255, "period": 50}
            for col, limit in str_limits.items():
                if col in insert_df.columns:
                    insert_df[col] = insert_df[col].astype(str).str.slice(0, limit).replace({"None": None, "nan": None})
            
            # Cast numeric columns to correct dtypes so SQLAlchemy sends
            # INTEGER / FLOAT instead of VARCHAR to PostgreSQL
            if "year" in insert_df.columns:
                insert_df["year"] = pd.to_numeric(insert_df["year"], errors="coerce").astype("Int64")
            if "value" in insert_df.columns:
                insert_df["value"] = pd.to_numeric(insert_df["value"], errors="coerce").astype("Float64")
            
            # 3. Bulk insert new records
            # We use engine.begin() to get a connection with an explicit transaction.
            # If to_sql fails, the context manager rolls back automatically, preventing connection poisoning.
            logger.info(f"Inserting {len(insert_df)} records for dataset {dataset_id}...")
            
            with self.engine.begin() as conn:
                insert_df.to_sql(
                    name=Observation.__tablename__,
                    con=conn,
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
