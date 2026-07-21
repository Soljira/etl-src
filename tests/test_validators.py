import pandas as pd
import numpy as np
import pytest
from src.validators.base_validator import DataValidator

@pytest.fixture
def validator():
    return DataValidator()

def test_validator_completeness(validator):
    # Missing critical value should drop row
    df = pd.DataFrame({
        "dataset_id": ["A", "B", "C"],
        "category": ["cat1", "cat2", "cat3"],
        "entity_name": ["e1", "e2", "e3"],
        "variable_name": ["v1", "v2", "v3"],
        "year": [2020, 2021, np.nan],
        "period": [None, None, None],
        "value": [10.5, np.nan, 30.0]  # Row B is missing value
    })
    
    clean_df, metrics = validator.validate(df)
    
    assert len(clean_df) == 2
    assert "B" not in clean_df["dataset_id"].values
    assert "Dropped 1 rows due to missing critical columns." in metrics["warnings"]
    assert "1 rows are missing 'year' information." in metrics["warnings"]

def test_validator_consistency_bounds(validator):
    # Year out of bounds and negative population
    df = pd.DataFrame({
        "dataset_id": ["A", "B"],
        "category": ["cat", "cat"],
        "entity_name": ["e1", "e2"],
        "variable_name": ["Total Population", "Other"],
        "year": [3000, 2020], # 3000 is impossible
        "period": [None, None],
        "value": [-50.0, 100.0] # -50 population is impossible
    })
    
    clean_df, metrics = validator.validate(df)
    
    assert len(clean_df) == 2
    
    # Year should be nullified
    assert pd.isna(clean_df.loc[clean_df["dataset_id"] == "A", "year"].iloc[0])
    # Negative population should be nullified
    assert pd.isna(clean_df.loc[clean_df["dataset_id"] == "A", "value"].iloc[0])
    
    assert any("out-of-bounds years" in w for w in metrics["warnings"])
    assert any("impossible negative Population" in w for w in metrics["warnings"])

def test_validator_anomalies(validator):
    # Create a distribution where one value is a massive outlier (>3 stdev)
    # Using 20 normal values so the outlier doesn't pull the standard deviation too hard
    values = [10, 11, 12, 10, 11, 9, 10, 11, 10, 10, 12, 9, 10, 11, 10, 10, 11, 12, 9, 10000]
    
    df = pd.DataFrame({
        "dataset_id": ["A"] * 20,
        "category": ["cat"] * 20,
        "entity_name": [f"e{i}" for i in range(20)],
        "variable_name": ["var1"] * 20,
        "year": [2020] * 20,
        "period": [None] * 20,
        "value": values
    })
    
    clean_df, metrics = validator.validate(df)
    
    assert metrics["anomalies_detected"] == 1
    assert any("extreme statistical outliers" in w for w in metrics["warnings"])
    
    # Check that quality score was deducted
    assert metrics["quality_score"] < 100.0
