import os
import pandas as pd
import pytest
from src.transformers.psa_transformer import PsaTransformer

@pytest.fixture
def psa_transformer():
    return PsaTransformer(output_dir="data/processed")

def test_psa_transformer_labor_format(psa_transformer, tmp_path):
    # Setup mock Labor Data (Years are columns)
    df = pd.DataFrame({
        "Indicator": ["Employment Rate"],
        "Sector": ["National"],
        "1995": [90.5],
        "1996": [91.0]
    })
    filepath = os.path.join(tmp_path, "Labor_and_Employment__0013K3E1010.csv")
    df.to_csv(filepath, index=False)
    
    transformed = psa_transformer.transform(filepath)
    
    assert not transformed.empty
    assert len(transformed) == 2
    
    # Check first row (1995)
    row_1995 = transformed[transformed["year"] == 1995].iloc[0]
    assert row_1995["dataset_id"] == "0013K3E1010"
    assert row_1995["category"] == "Labor_and_Employment"
    assert row_1995["entity_name"] == "Employment Rate - National"
    assert row_1995["variable_name"] == "Value"
    assert row_1995["value"] == 90.5

def test_psa_transformer_agri_format(psa_transformer, tmp_path):
    # Setup mock Agriculture Data (Year and Variable combined)
    df = pd.DataFrame({
        "Industry Description": ["Rice Farming"],
        "2015 All Employment Sizes Total employment": [15000],
        "2016 All Employment Sizes Total employment": [16000]
    })
    filepath = os.path.join(tmp_path, "Agriculture_Forestry_Fisheries__0012E4EVCP0.csv")
    df.to_csv(filepath, index=False)
    
    transformed = psa_transformer.transform(filepath)
    
    assert not transformed.empty
    assert len(transformed) == 2
    
    row_2015 = transformed[transformed["year"] == 2015].iloc[0]
    assert row_2015["entity_name"] == "Rice Farming"
    assert row_2015["variable_name"] == "All Employment Sizes Total employment"
    assert row_2015["value"] == 15000.0
    assert pd.isna(row_2015["period"])

def test_psa_transformer_population_format(psa_transformer, tmp_path):
    # Setup mock Population Data (No year in headers)
    df = pd.DataFrame({
        "Geographic Location": ["Philippines", "NCR"],
        "Total Population": [100000000, 12000000]
    })
    filepath = os.path.join(tmp_path, "Population_and_Vital_Statistics__0011A6DPHH0.csv")
    df.to_csv(filepath, index=False)
    
    transformed = psa_transformer.transform(filepath)
    
    assert not transformed.empty
    assert len(transformed) == 2
    
    row_ph = transformed[transformed["entity_name"] == "Philippines"].iloc[0]
    assert pd.isna(row_ph["year"])
    assert row_ph["variable_name"] == "Total Population"
    assert row_ph["value"] == 100000000.0

def test_psa_transformer_dirty_values(psa_transformer, tmp_path):
    # Setup mock data with weird symbols
    df = pd.DataFrame({
        "Indicator": ["A", "B"],
        "2015": ["..", "1,500.50"]
    })
    filepath = os.path.join(tmp_path, "Test__123.csv")
    df.to_csv(filepath, index=False)
    
    transformed = psa_transformer.transform(filepath)
    
    # ".." should become NaN and be dropped
    assert len(transformed) == 1
    
    row_b = transformed[transformed["entity_name"] == "B"].iloc[0]
    assert row_b["value"] == 1500.50
