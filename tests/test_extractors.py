import os
import time
from unittest import mock
import pytest
from src.extractors.base_extractor import BaseExtractor

class DummyExtractor(BaseExtractor):
    def extract(self):
        return []

@pytest.fixture
def dummy_extractor(tmp_path):
    # Use tmp_path for output dir so we don't pollute the real workspace
    return DummyExtractor(output_dir=str(tmp_path), rate_limit_seconds=0.1)

def test_base_extractor_initialization(dummy_extractor, tmp_path):
    assert dummy_extractor.output_dir == str(tmp_path)
    assert dummy_extractor.rate_limit_seconds == 0.1
    assert os.path.exists(str(tmp_path))

@mock.patch("requests.Session.get")
def test_download_file_success(mock_get, dummy_extractor):
    # Mock a successful response
    mock_response = mock.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_content.return_value = [b"data1", b"data2"]
    mock_get.return_value = mock_response
    
    result = dummy_extractor.download_file("http://example.com/data.csv", "test.csv")
    
    assert result is not None
    assert "test.csv" in result
    assert os.path.exists(result)
    
    with open(result, "rb") as f:
        assert f.read() == b"data1data2"

@mock.patch("requests.Session.get")
def test_rate_limiting(mock_get, dummy_extractor):
    mock_response = mock.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": "ok"}
    mock_get.return_value = mock_response
    
    start_time = time.time()
    # First call sets the last_request_time
    dummy_extractor.fetch_json("http://example.com/api")
    # Second call should be delayed by rate_limit_seconds (0.1s)
    dummy_extractor.fetch_json("http://example.com/api")
    
    elapsed = time.time() - start_time
    # It should take at least 0.1 seconds because of the rate limit
    assert elapsed >= 0.1

# ---------------------------------------------------------------------------
# PsaExtractor tests — everything is mocked; no live HTTP calls
# ---------------------------------------------------------------------------
from src.extractors.psa_extractor import PsaExtractor

@pytest.fixture
def psa_extractor(tmp_path):
    return PsaExtractor(output_dir=str(tmp_path), rate_limit_seconds=0)


def test_psa_build_payload():
    """_build_payload should create a query with 'all'/'*' for every variable."""
    extractor = PsaExtractor(rate_limit_seconds=0)
    variables = [
        {"code": "Year", "text": "Year", "values": ["37", "38"]},
        {"code": "Geolocation", "text": "Geolocation", "values": ["0", "1"]},
    ]
    payload = extractor._build_payload(variables)

    assert payload["response"]["format"] == "csv"
    assert len(payload["query"]) == 2
    for item in payload["query"]:
        assert item["selection"]["filter"] == "all"
        assert item["selection"]["values"] == ["*"]


@mock.patch("requests.Session.get")
def test_psa_discover_tables_two_levels(mock_get, psa_extractor):
    """_discover_tables should recursively walk all levels and collect table IDs."""
    def side_effect(url, **kwargs):
        resp = mock.Mock()
        resp.raise_for_status.return_value = None
        if url.endswith("DB/2E"):
            resp.json.return_value = [
                {"id": "CS", "type": "l", "text": "Crops"},
            ]
        elif url.endswith("DB/2E/CS"):
            resp.json.return_value = [
                {"id": "0012E4EVCP0.px", "type": "t", "text": "Value of Crops"},
            ]
        else:
            resp.json.return_value = []
        return resp

    mock_get.side_effect = side_effect
    tables = psa_extractor._discover_tables("2E")
    assert tables == ["DB/2E/CS/0012E4EVCP0.px"]


@mock.patch("requests.Session.get")
def test_psa_discover_tables_three_levels(mock_get, psa_extractor):
    """_discover_tables should handle three-level nesting (e.g. DB/2G/CONS/table.px)."""
    def side_effect(url, **kwargs):
        resp = mock.Mock()
        resp.raise_for_status.return_value = None
        if url.endswith("DB/2G"):
            resp.json.return_value = [{"id": "CONS", "type": "l", "text": "Construction"}]
        elif url.endswith("DB/2G/CONS"):
            resp.json.return_value = [{"id": "table.px", "type": "t", "text": "Table"}]
        else:
            resp.json.return_value = []
        return resp

    mock_get.side_effect = side_effect
    tables = psa_extractor._discover_tables("2G")
    assert tables == ["DB/2G/CONS/table.px"]


@mock.patch("requests.Session.post")
@mock.patch("requests.Session.get")
def test_psa_download_table(mock_get, mock_post, psa_extractor):
    """_download_table should fetch metadata then POST and save CSV."""
    # GET returns metadata
    meta_resp = mock.Mock()
    meta_resp.raise_for_status.return_value = None
    meta_resp.json.return_value = {
        "variables": [
            {"code": "Year", "text": "Year", "values": ["37"]},
        ]
    }
    mock_get.return_value = meta_resp

    # POST returns CSV text
    csv_resp = mock.Mock()
    csv_resp.raise_for_status.return_value = None
    csv_resp.text = "Year,Value\n2024,123\n"
    mock_post.return_value = csv_resp

    filepath = psa_extractor._download_table(
        "DB/2E/CS/0012E4EVCP0.px", "Agriculture_Forestry_Fisheries"
    )

    assert filepath is not None
    assert os.path.exists(filepath)
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    assert "Year,Value" in content
