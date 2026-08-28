import logging
import os
import time
from typing import Optional

import requests

from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)

# Rate limit: max 10 requests per 10 seconds SABI MISMO NG OPENSTAT API. Use 1.1s between requests to be safe
PSA_RATE_LIMIT = 1.1

# Base URL for the OpenSTAT PX-Web API
PSA_API_BASE = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"

# The 4 categories to be extracted. The top-level DB folder IDs
# Confirmed by querying GET /api/v1/en/DB (curl "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB")
TARGET_CATEGORIES = {
    "2E": "Agriculture_Forestry_Fisheries",
    "3A": "Environment",
    "1A": "Population_and_Vital_Statistics",
    "2G": "Mining_Manufacturing_Construction",
}


class PsaExtractor(BaseExtractor):
    """
    Extractor for the Philippine Statistics Authority (PSA) OpenSTAT API.

    Uses the PX-Web REST API to:
    1. Discover all tables under the target categories.
    2. Fetch table variable metadata via GET requests.
    3. Download the full dataset as CSV via POST requests.

    API rate limit: 10 requests per 10 seconds.
    """

    def __init__(
        self,
        output_dir: str = "data/raw/psa",
        rate_limit_seconds: float = PSA_RATE_LIMIT,
    ):
        super().__init__(output_dir=output_dir, rate_limit_seconds=rate_limit_seconds)
        self.api_base = PSA_API_BASE
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
        })

    # -------------------------------------------------------------------------
    # Discovery helpers
    # -------------------------------------------------------------------------

    def _get_nodes(self, path: str) -> list[dict]:
        """
        GET a node in the PX-Web API tree and return its children as a list.
        Returns an empty list on failure.
        """
        url = f"{self.api_base}/{path}"
        data = self.fetch_json(url)
        if data is None:
            logger.warning("Failed to fetch node: %s", path)
            return []
        return data if isinstance(data, list) else []

    def _discover_tables_recursive(self, path: str) -> list[str]:
        """
        Recursively walk the API tree from the given path and collect
        all table paths (nodes with type == 't').
        """
        table_paths: list[str] = []
        nodes = self._get_nodes(path)
        for node in nodes:
            node_id = node.get("id", "")
            node_type = node.get("type", "")
            child_path = f"{path}/{node_id}"
            if node_type == "t":
                table_paths.append(child_path)
            elif node_type == "l":
                table_paths.extend(self._discover_tables_recursive(child_path))
        return table_paths

    def _discover_tables(self, category_id: str) -> list[str]:
        """
        Walk the API hierarchy under a top-level category and return a list
        of all table paths (strings ending in .px).
        Handles arbitrarily deep nesting (2G/Mining has 3 levels).
        """
        table_paths = self._discover_tables_recursive(f"DB/{category_id}")
        logger.info(
            "Discovered %d table(s) under category %s", len(table_paths), category_id
        )
        return table_paths

    # -------------------------------------------------------------------------
    # Download helpers
    # -------------------------------------------------------------------------

    def _get_table_variables(self, table_path: str) -> list[dict]:
        """
        GET a table's metadata and return its list of variable descriptors.
        Each descriptor has: code, text, values, valueTexts.
        """
        url = f"{self.api_base}/{table_path}"
        data = self.fetch_json(url)
        if data is None or "variables" not in data:
            logger.warning("No variable metadata for table: %s", table_path)
            return []
        return data["variables"]

    def _build_payload(self, variables: list[dict]) -> dict:
        """
        Build a PX-Web POST payload that selects ALL values for every variable.

        Uses 'item' filter with explicit values (not wildcard 'all'/'*') because
        some OpenSTAT tables return 403 Forbidden when wildcard selection is used.
        """
        query = []
        for var in variables:
            values = var.get("values", [])
            query.append(
                {
                    "code": var["code"],
                    "selection": {
                        "filter": "item",
                        "values": values,
                    },
                }
            )
        return {"query": query, "response": {"format": "csv"}}

    def _download_table(
        self, table_path: str, label: str
    ) -> Optional[str]:
        """
        Download a single table as CSV and save it to the output directory.

        Args:
            table_path: PX-Web path, e.g. 'DB/2E/CS/0012E4EVCP0.px'
            label: Human-readable name used as the filename base.

        Returns:
            The saved file path, or None on failure.
        """
        variables = self._get_table_variables(table_path)
        if not variables:
            return None

        payload = self._build_payload(variables)

        self._wait_for_rate_limit()
        url = f"{self.api_base}/{table_path}"
        logger.info("Downloading table: %s", table_path)

        try:
            response = self.session.post(url, json=payload, timeout=60)
            if response.status_code == 403:
                # Some tables forbid bulk downloads entirely — skip gracefully
                logger.warning(
                    "Table %s returned 403 Forbidden (restricted by PSA). Skipping.",
                    table_path,
                )
                return None
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error("Failed to download table %s: %s", table_path, e)
            return None

        # Build a safe filename from the label and table ID
        table_id = table_path.rsplit("/", 1)[-1].replace(".px", "")
        filename = f"{label}__{table_id}.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(response.text)

        logger.info("Saved → %s", filepath)
        return os.path.abspath(filepath)

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def extract(self) -> list[str]:
        """
        Discover and download all tables under the 4 target categories.
        Returns a list of file paths for all successfully downloaded CSVs.
        """
        all_files: list[str] = []

        for category_id, category_label in TARGET_CATEGORIES.items():
            logger.info(
                "=== Extracting category: %s (%s) ===", category_label, category_id
            )

            table_paths = self._discover_tables(category_id)

            for table_path in table_paths:
                filepath = self._download_table(table_path, category_label)
                if filepath:
                    all_files.append(filepath)

            logger.info(
                "Finished category %s: %d file(s) downloaded.",
                category_label,
                len([f for f in all_files if category_label in f]),
            )

        logger.info("PSA extraction complete. Total files: %d", len(all_files))
        return all_files
