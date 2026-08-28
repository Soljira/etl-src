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

    def load(self, df: pd.DataFrame, dataset_id: str = None) -> bool:
        """
        Loads the DataFrame into the 'observations' table.
        Deletes any existing records for datasets present in df before inserting
        to prevent duplicate data across multiple pipeline runs.
        """
        if df.empty:
            logger.warning("Skipping load: DataFrame is empty.")
            return False
            
        try:
            # 1. Delete existing records to make operations idempotent
            if dataset_id:
                target_ids = [dataset_id]
            elif "dataset_id" in df.columns:
                target_ids = [str(x) for x in df["dataset_id"].dropna().unique()]
            else:
                target_ids = []

            # Perform deletion using a separate Session to avoid locking during bulk insert
            if target_ids:
                try:
                    with Session(self.engine) as del_session:
                        deleted_count = del_session.query(Observation).filter(Observation.dataset_id.in_(target_ids)).delete(synchronize_session=False)
                        if deleted_count > 0:
                            logger.info(f"Deleted {deleted_count} existing records for dataset(s): {target_ids[:5]}...")
                        del_session.commit()
                except Exception as del_err:
                    logger.error(f"Failed to delete existing records for dataset(s) {target_ids}: {del_err}")
                

                
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
            
            # 3. Bulk insert new records in chunks with progress logging
            total_records = len(insert_df)
            batch_size = 50000
            total_batches = (total_records + batch_size - 1) // batch_size
            
            logger.info(f"Inserting {total_records} records into PostgreSQL in {total_batches} batch(es)...")
            
            with self.engine.begin() as conn:
                # If there are target_ids, delete existing records first
                if target_ids:
                    from sqlalchemy import delete
                    del_stmt = delete(Observation).where(Observation.dataset_id.in_(target_ids))
                    result = conn.execute(del_stmt)
                    deleted_count = result.rowcount
                    if deleted_count and deleted_count > 0:
                        logger.info(f"Deleted {deleted_count} existing records for dataset(s): {target_ids[:5]}...")
                # Bulk insert new records in chunks with progress logging
                for i in range(0, total_records, batch_size):
                    chunk_df = insert_df.iloc[i : i + batch_size]
                    chunk_df.to_sql(
                        name=Observation.__tablename__,
                        con=conn,
                        if_exists="append",
                        index=False,
                        method="multi",  # Uses multi-row INSERTs
                        chunksize=5000,  # 5000 rows per SQL multi-INSERT (35,000 params, under Postgres 65,535 limit)
                    )
                    current_batch = (i // batch_size) + 1
                    inserted_so_far = min(i + batch_size, total_records)
                    logger.info(f"Loaded batch {current_batch}/{total_batches} ({inserted_so_far}/{total_records} rows)...")
                
            logger.info(f"Successfully loaded all {total_records} records into PostgreSQL.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load dataset {dataset_id} into PostgreSQL: {e}")
            return False
