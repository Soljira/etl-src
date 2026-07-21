import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.models import Base, Observation
from src.loaders.postgres_loader import PostgresLoader

@pytest.fixture
def memory_db_loader():
    # Create an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    # Create all tables in the memory db
    Base.metadata.create_all(bind=engine)
    return PostgresLoader(engine=engine)

def test_postgres_loader_insert(memory_db_loader):
    # Setup test data
    df = pd.DataFrame({
        "dataset_id": ["TEST1", "TEST1"],
        "category": ["cat1", "cat1"],
        "entity_name": ["e1", "e2"],
        "variable_name": ["v1", "v1"],
        "year": [2020, 2021],
        "period": ["Q1", "Q2"],
        "value": [10.5, 20.0]
    })
    
    # Run loader
    success = memory_db_loader.load(df, "TEST1")
    assert success
    
    # Verify data in DB
    with Session(memory_db_loader.engine) as session:
        records = session.query(Observation).all()
        assert len(records) == 2
        assert records[0].dataset_id == "TEST1"
        assert records[0].value == 10.5

def test_postgres_loader_idempotent(memory_db_loader):
    """Test that loading the same dataset twice replaces the old data."""
    # First load
    df1 = pd.DataFrame({
        "dataset_id": ["TEST2"],
        "category": ["cat"],
        "entity_name": ["e"],
        "variable_name": ["v"],
        "year": [2020],
        "period": [None],
        "value": [10.0]
    })
    memory_db_loader.load(df1, "TEST2")
    
    # Second load (simulate re-run with updated data)
    df2 = pd.DataFrame({
        "dataset_id": ["TEST2"],
        "category": ["cat"],
        "entity_name": ["e"],
        "variable_name": ["v"],
        "year": [2020],
        "period": [None],
        "value": [999.0] # Value changed
    })
    memory_db_loader.load(df2, "TEST2")
    
    # Verify DB only has the new data (length is 1, not 2)
    with Session(memory_db_loader.engine) as session:
        records = session.query(Observation).filter(Observation.dataset_id == "TEST2").all()
        assert len(records) == 1
        assert records[0].value == 999.0

def test_postgres_loader_empty_df(memory_db_loader):
    """Test that an empty dataframe is handled gracefully."""
    df = pd.DataFrame()
    success = memory_db_loader.load(df, "TEST3")
    assert not success
