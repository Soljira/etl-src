"""
Unit tests for BetterGovTransformer.

Tests the dataset-specific mappers (BIR Tax Collection monthly & GAA)
and the generic fallback mapper against sample DataFrames.
"""
import os
import json
import sys
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, ".")

from src.transformers.bettergov_transformer import BetterGovTransformer

UNIFIED_SCHEMA = [
    "dataset_id", "category", "entity_name",
    "variable_name", "year", "period", "value",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def transformer(tmp_path):
    t = BetterGovTransformer(output_dir=str(tmp_path / "processed"))
    return t


@pytest.fixture
def bir_monthly_csv(tmp_path):
    """BIR Tax Collection monthly wide-format CSV."""
    content = (
        "Region ,PARTICULARS, JANUARY , FEBRUARY , MARCH \n"
        'NCR,City of Makati," 16,377.06 "," 6,171.35 "," 6,633.28 "\n'
        "NCR,City of Manila, 875.36 , 321.90 , 368.44 \n"
    )
    path = tmp_path / "Government__20__412.csv"
    path.write_text(content)
    return str(path)


@pytest.fixture
def bir_gaa_csv(tmp_path):
    """GAA by Region wide-format CSV (Year + region columns)."""
    content = (
        "Year,Region I,Region II,NCR\n"
        "2020,3453911000.00,3398294000.00,82288390000.00\n"
        "2021,67082684000.00,57707237000.00,1799923823000.00\n"
    )
    path = tmp_path / "Government__20__413.csv"
    path.write_text(content)
    return str(path)


@pytest.fixture
def generic_csv(tmp_path):
    """A simple generic CSV with a Year column and numeric value columns."""
    content = (
        "Year,Province,Amount,Count\n"
        "2022,Cebu,1000.50,42\n"
        "2023,Davao,2000.75,88\n"
    )
    path = tmp_path / "Finance__99__500.csv"
    path.write_text(content)
    return str(path)


@pytest.fixture
def meta_bir_monthly():
    return {
        "dataset_id": 20,
        "dataset_name": "BIR Tax Collection Data",
        "category": "Government",
        "publisher": "BetterGov.PH",
        "resource_id": 412,
        "resource_name": "2024 BIR Tax Collection",
        "resource_description": "",
        "mime_type": "text/csv",
    }


@pytest.fixture
def meta_bir_gaa():
    return {
        "dataset_id": 20,
        "dataset_name": "BIR Tax Collection Data",
        "category": "Government",
        "publisher": "BetterGov.PH",
        "resource_id": 413,
        "resource_name": "GAA by Region",
        "resource_description": "",
        "mime_type": "text/csv",
    }


@pytest.fixture
def meta_generic():
    return {
        "dataset_id": 99,
        "dataset_name": "Unknown Finance Dataset",
        "category": "Finance",
        "publisher": "Treasury",
        "resource_id": 500,
        "resource_name": "Budget Data",
        "resource_description": "",
        "mime_type": "text/csv",
    }


# ---------------------------------------------------------------------------
# Tests — BIR Monthly Mapper
# ---------------------------------------------------------------------------

class TestBIRMonthlyMapper:

    def test_output_schema(self, transformer, bir_monthly_csv, meta_bir_monthly):
        transformer._metadata = {"Government__20__412.csv": meta_bir_monthly}
        result = transformer.transform(bir_monthly_csv)

        assert list(result.columns) == UNIFIED_SCHEMA

    def test_row_count(self, transformer, bir_monthly_csv, meta_bir_monthly):
        """2 entities × 3 months = 6 observations."""
        transformer._metadata = {"Government__20__412.csv": meta_bir_monthly}
        result = transformer.transform(bir_monthly_csv)
        assert len(result) == 6

    def test_year_extracted(self, transformer, bir_monthly_csv, meta_bir_monthly):
        """Year should be extracted from resource name '2024 BIR Tax Collection'."""
        transformer._metadata = {"Government__20__412.csv": meta_bir_monthly}
        result = transformer.transform(bir_monthly_csv)
        assert all(result["year"] == 2024)

    def test_period_values(self, transformer, bir_monthly_csv, meta_bir_monthly):
        transformer._metadata = {"Government__20__412.csv": meta_bir_monthly}
        result = transformer.transform(bir_monthly_csv)
        periods = set(result["period"].unique())
        assert periods == {"January", "February", "March"}

    def test_values_numeric(self, transformer, bir_monthly_csv, meta_bir_monthly):
        """Comma-separated numbers should be properly parsed."""
        transformer._metadata = {"Government__20__412.csv": meta_bir_monthly}
        result = transformer.transform(bir_monthly_csv)
        # Makati January = 16377.06
        makati_jan = result[
            (result["entity_name"].str.contains("Makati"))
            & (result["period"] == "January")
        ]["value"].iloc[0]
        assert abs(makati_jan - 16377.06) < 0.01


# ---------------------------------------------------------------------------
# Tests — GAA by Region Mapper
# ---------------------------------------------------------------------------

class TestGAARegionMapper:

    def test_output_schema(self, transformer, bir_gaa_csv, meta_bir_gaa):
        transformer._metadata = {"Government__20__413.csv": meta_bir_gaa}
        result = transformer.transform(bir_gaa_csv)
        assert list(result.columns) == UNIFIED_SCHEMA

    def test_row_count(self, transformer, bir_gaa_csv, meta_bir_gaa):
        """2 years × 3 regions = 6 observations."""
        transformer._metadata = {"Government__20__413.csv": meta_bir_gaa}
        result = transformer.transform(bir_gaa_csv)
        assert len(result) == 6

    def test_entity_names(self, transformer, bir_gaa_csv, meta_bir_gaa):
        transformer._metadata = {"Government__20__413.csv": meta_bir_gaa}
        result = transformer.transform(bir_gaa_csv)
        entities = set(result["entity_name"].unique())
        assert "Region I" in entities
        assert "NCR" in entities

    def test_period_is_annual(self, transformer, bir_gaa_csv, meta_bir_gaa):
        transformer._metadata = {"Government__20__413.csv": meta_bir_gaa}
        result = transformer.transform(bir_gaa_csv)
        assert all(result["period"] == "Annual")


# ---------------------------------------------------------------------------
# Tests — Generic Fallback Mapper
# ---------------------------------------------------------------------------

class TestGenericMapper:

    def test_output_schema(self, transformer, generic_csv, meta_generic):
        transformer._metadata = {"Finance__99__500.csv": meta_generic}
        result = transformer.transform(generic_csv)
        assert list(result.columns) == UNIFIED_SCHEMA

    def test_row_count(self, transformer, generic_csv, meta_generic):
        """2 rows × 2 numeric cols (Amount, Count) = 4 observations."""
        transformer._metadata = {"Finance__99__500.csv": meta_generic}
        result = transformer.transform(generic_csv)
        assert len(result) == 4

    def test_year_preserved(self, transformer, generic_csv, meta_generic):
        transformer._metadata = {"Finance__99__500.csv": meta_generic}
        result = transformer.transform(generic_csv)
        assert set(result["year"].unique()) == {2022, 2023}

    def test_category_set(self, transformer, generic_csv, meta_generic):
        transformer._metadata = {"Finance__99__500.csv": meta_generic}
        result = transformer.transform(generic_csv)
        assert all(result["category"] == "Finance")


# ---------------------------------------------------------------------------
# Tests — Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_csv(self, transformer, tmp_path):
        """Empty CSV should return empty DataFrame with correct schema."""
        path = tmp_path / "empty__0__0.csv"
        path.write_text("")
        transformer._metadata = {"empty__0__0.csv": {
            "dataset_id": 0, "resource_id": 0,
            "resource_name": "empty", "category": "Test",
        }}
        result = transformer.transform(str(path))
        assert result.empty
        assert list(result.columns) == UNIFIED_SCHEMA

    def test_unknown_dataset_uses_generic(self, transformer, generic_csv, meta_generic):
        """Unknown dataset ID should fall through to generic mapper."""
        meta_generic["dataset_id"] = 9999
        transformer._metadata = {"Finance__99__500.csv": meta_generic}
        result = transformer.transform(generic_csv)
        # Should still produce results via generic mapper
        assert len(result) > 0

    def test_no_metadata_still_works(self, transformer, generic_csv):
        """Missing metadata should not crash — uses fallback."""
        transformer._metadata = {}
        result = transformer.transform(generic_csv)
        # Generic mapper may or may not produce rows, but should not crash
        assert isinstance(result, pd.DataFrame)

    def test_save_processed_data(self, transformer, generic_csv, meta_generic):
        """save_processed_data should write a valid CSV."""
        transformer._metadata = {"Finance__99__500.csv": meta_generic}
        result = transformer.transform(generic_csv)
        saved = transformer.save_processed_data(result, "test_output.csv")
        assert os.path.exists(saved)
        reloaded = pd.read_csv(saved)
        assert list(reloaded.columns) == UNIFIED_SCHEMA
