"""
Unit tests for BetterGovExtractor.

Uses mocked HTTP responses so no real API calls are made.
"""
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, ".")

from src.extractors.bettergov_extractor import BetterGovExtractor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_output(tmp_path):
    """Provide a temporary output directory."""
    return str(tmp_path / "bettergov")


@pytest.fixture
def extractor(tmp_output):
    """BetterGovExtractor with fast rate limit and temp output."""
    return BetterGovExtractor(output_dir=tmp_output, rate_limit_seconds=0.0)


# ---------------------------------------------------------------------------
# Mock API responses
# ---------------------------------------------------------------------------

MOCK_DATASETS_PAGE1 = {
    "success": True,
    "data": [
        {
            "id": 20,
            "name": "BIR Tax Collection Data",
            "publisher_id": 2,
            "category_id": 7,
            "tags": '["bir","tax"]',
            "size_bytes": 218951,
            "latest_version_date": "2025-12-03",
            "attribution": [],
            "license": "CC0 1.0",
            "license_url": None,
            "publisher": {"id": 2, "name": "BetterGov.PH"},
            "category": {"id": 7, "name": "Government"},
            "resource_count": 7,
        }
    ],
    "pagination": {
        "total": 1,
        "limit": 100,
        "offset": 0,
        "has_more": False,
        "current_page": 1,
        "total_pages": 1,
    },
}

MOCK_RESOURCES = {
    "success": True,
    "data": [
        {
            "id": 412,
            "dataset_id": 20,
            "name": "2024 BIR Tax Collection",
            "description": "BIR tax collection data for 2024.",
            "mime_type": "text/csv",
            "size_bytes": 16800,
            "download_url": "https://example.com/2024_bir.csv",
            "source_url": "https://example.com",
        },
        {
            "id": 407,
            "dataset_id": 20,
            "name": "BIR (Parquet)",
            "description": "Parquet format.",
            "mime_type": "application/vnd.apache.parquet",
            "size_bytes": 133000,
            "download_url": "https://example.com/bir.parquet",
            "source_url": "https://example.com",
        },
    ],
    "pagination": {
        "total": 2,
        "limit": 100,
        "offset": 0,
        "has_more": False,
        "current_page": 1,
        "total_pages": 1,
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBetterGovExtractor:

    def test_discover_datasets(self, extractor):
        """Should paginate through the datasets endpoint."""
        with patch.object(extractor, "fetch_json", return_value=MOCK_DATASETS_PAGE1):
            datasets = extractor._discover_datasets()
        assert len(datasets) == 1
        assert datasets[0]["name"] == "BIR Tax Collection Data"

    def test_discover_resources(self, extractor):
        """Should fetch resources for a given dataset_id."""
        with patch.object(extractor, "fetch_json", return_value=MOCK_RESOURCES):
            resources = extractor._discover_resources(20)
        assert len(resources) == 2

    def test_is_tabular_csv(self):
        """CSV mime type should be tabular."""
        assert BetterGovExtractor._is_tabular({"mime_type": "text/csv", "download_url": ""})

    def test_is_tabular_spreadsheet(self):
        """Spreadsheet mime type should be tabular."""
        r = {"mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "download_url": ""}
        assert BetterGovExtractor._is_tabular(r)

    def test_is_tabular_parquet_rejected(self):
        """Parquet should NOT be considered tabular."""
        assert not BetterGovExtractor._is_tabular(
            {"mime_type": "application/vnd.apache.parquet", "download_url": "https://x.com/file.parquet"}
        )

    def test_is_tabular_url_csv(self):
        """A download_url ending in .csv should be tabular even with unknown mime."""
        assert BetterGovExtractor._is_tabular(
            {"mime_type": "application/octet-stream", "download_url": "https://x.com/data.csv"}
        )

    def test_filter_resources_excludes_parquet(self, extractor):
        """Only tabular resources should be kept after filtering."""
        resources = MOCK_RESOURCES["data"]
        tabular = [r for r in resources if BetterGovExtractor._is_tabular(r)]
        assert len(tabular) == 1
        assert tabular[0]["id"] == 412

    def test_safe_name(self):
        """Special characters should be cleaned from filenames."""
        assert BetterGovExtractor._safe_name("Weather and Climate") == "Weather_and_Climate"
        assert BetterGovExtractor._safe_name("Gov/Admin (Test)") == "Gov_Admin_Test"

    def test_extract_downloads_csv_only(self, extractor, tmp_output):
        """Full extract should download only CSV resources and write metadata."""
        csv_content = b"Region,Value\nNCR,100\n"

        def mock_fetch_json(url, params=None):
            if "datasets" in url:
                return MOCK_DATASETS_PAGE1
            if "resources" in url:
                return MOCK_RESOURCES
            return None

        with patch.object(extractor, "fetch_json", side_effect=mock_fetch_json), \
             patch.object(extractor, "download_file", return_value=os.path.join(tmp_output, "test.csv")):

            os.makedirs(tmp_output, exist_ok=True)
            # Create the dummy file so the path exists
            with open(os.path.join(tmp_output, "test.csv"), "wb") as f:
                f.write(csv_content)

            files = extractor.extract()

        assert len(files) == 1
        # Metadata should be saved
        meta_path = os.path.join(tmp_output, "_metadata.json")
        assert os.path.exists(meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert len(meta) == 1

    def test_category_filter(self, extractor):
        """Extraction with category filter should skip non-matching datasets."""
        with patch.object(extractor, "fetch_json", return_value=MOCK_DATASETS_PAGE1), \
             patch.object(extractor, "_discover_resources") as mock_resources:

            files = extractor.extract(categories=["Finance"])

        # "Government" dataset should be skipped when filtering for "Finance"
        mock_resources.assert_not_called()
        assert files == []

    def test_api_failure_returns_empty(self, extractor):
        """API failure should return empty list gracefully."""
        with patch.object(extractor, "fetch_json", return_value=None):
            files = extractor.extract()
        assert files == []
