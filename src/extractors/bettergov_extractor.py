import io
import json
import logging
import os
import zipfile
from typing import Any, Dict, List, Optional

from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)

# Rate limit: 1s between requests (safe within the 60-100 req/min tiers)
BETTERGOV_RATE_LIMIT = 1.0

BETTERGOV_API_BASE = "https://data.bettergov.ph/api/v1"

# MIME types treated as directly tabular
TABULAR_MIME_TYPES = {"text/csv", "application/csv"}
# MIME types treated as directly tabular
SPREADSHEET_MIME_SUBSTRING = "spreadsheet"
# MIME types that may contain CSVs when unzipped
ZIP_MIME_TYPES = {"application/zip", "application/x-zip-compressed", "application/gzip"}


class BetterGovExtractor(BaseExtractor):
    """
    Extractor for the BetterGov Open Data Portal API.

    Uses the REST API (OpenAPI 3.1) to:
    1. Discover all datasets and their resources via paginated listing.
    2. Filter resources to tabular formats (CSV / Excel).
    3. Download each resource from its external ``download_url``.
    4. Save a metadata sidecar JSON so the transformer knows each
       file's dataset name, category, and publisher.

    Docs: https://data.bettergov.ph/docs
    """

    def __init__(
        self,
        output_dir: str = "data/raw/bettergov",
        rate_limit_seconds: float = BETTERGOV_RATE_LIMIT,
    ):
        super().__init__(output_dir=output_dir, rate_limit_seconds=rate_limit_seconds)
        self.api_base = BETTERGOV_API_BASE
        self._metadata: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def _fetch_paginated(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all pages from a paginated BetterGov endpoint.

        Returns the accumulated ``data`` array across all pages.
        """
        all_items: List[Dict[str, Any]] = []
        offset = 0
        base_params = dict(params or {})

        while True:
            base_params["limit"] = limit
            base_params["offset"] = offset

            url = f"{self.api_base}/{endpoint}"
            response = self.fetch_json(url, params=base_params)

            if response is None or not response.get("success"):
                logger.warning(
                    "BetterGov API request failed for %s (offset=%d)", endpoint, offset
                )
                break

            items = response.get("data", [])
            all_items.extend(items)

            pagination = response.get("pagination", {})
            if not pagination.get("has_more", False):
                break

            offset += limit

        return all_items

    def _discover_datasets(self) -> List[Dict[str, Any]]:
        """Fetch all datasets from the BetterGov portal."""
        datasets = self._fetch_paginated("datasets")
        logger.info("Discovered %d dataset(s) on BetterGov.", len(datasets))
        return datasets

    def _discover_resources(self, dataset_id: int) -> List[Dict[str, Any]]:
        """Fetch all resources for a given dataset."""
        resources = self._fetch_paginated(
            "resources", params={"dataset_id": dataset_id}
        )
        return resources

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    @staticmethod
    def _is_tabular(resource: Dict[str, Any]) -> bool:
        """Return True if the resource is a downloadable tabular file (or ZIP of one)."""
        mime = (resource.get("mime_type") or "").lower()
        if mime in TABULAR_MIME_TYPES:
            return True
        if SPREADSHEET_MIME_SUBSTRING in mime:
            return True
        if mime in ZIP_MIME_TYPES:
            return True
        # Also accept files whose download_url ends with known extensions
        url = (resource.get("download_url") or "").lower().split("?")[0]
        for ext in (".csv", ".xlsx", ".xls", ".zip"):
            if url.endswith(ext):
                return True
        return False

    @staticmethod
    def _is_zip(resource: Dict[str, Any]) -> bool:
        """Return True if the resource is a ZIP archive."""
        mime = (resource.get("mime_type") or "").lower()
        if mime in ZIP_MIME_TYPES:
            return True
        url = (resource.get("download_url") or "").lower().split("?")[0]
        return url.endswith(".zip") or url.endswith(".gz")

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_name(text: str) -> str:
        """Convert a string into a filesystem-safe name."""
        return (
            text.replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
            .replace("'", "")
            .replace('"', "")
        )

    def _download_resource(
        self,
        resource: Dict[str, Any],
        category_name: str,
        dataset_id: int,
    ) -> List[str]:
        """
        Download a single resource file and return its local path(s).

        ZIP archives are extracted in-place and each contained CSV/Excel
        is saved as a separate file.  Returns a list because a single ZIP
        may contain multiple tabular files.

        File naming convention:
            {CategoryName}__{DatasetID}__{ResourceID}.csv
        or for ZIP contents:
            {CategoryName}__{DatasetID}__{ResourceID}__{member_name}.csv
        """
        download_url = resource.get("download_url")
        if not download_url:
            logger.warning(
                "Resource %d has no download_url, skipping.", resource.get("id", 0)
            )
            return []

        resource_id = resource.get("id", 0)
        safe_cat = self._safe_name(category_name)

        # --- ZIP archive: download, then extract CSV/Excel members ---
        if self._is_zip(resource):
            return self._download_and_extract_zip(
                download_url, safe_cat, dataset_id, resource_id
            )

        # --- Direct tabular file ---
        ext = ".csv"
        url_lower = download_url.lower().split("?")[0]
        if url_lower.endswith(".xlsx"):
            ext = ".xlsx"
        elif url_lower.endswith(".xls"):
            ext = ".xls"

        filename = f"{safe_cat}__{dataset_id}__{resource_id}{ext}"
        filepath = self.download_file(download_url, filename)
        return [filepath] if filepath else []

    def _download_and_extract_zip(
        self,
        url: str,
        safe_cat: str,
        dataset_id: int,
        resource_id: int,
    ) -> List[str]:
        """
        Download a ZIP archive into memory, then write each tabular member
        (CSV or Excel) to the output directory as individual files.
        """
        self._wait_for_rate_limit()
        logger.info("Downloading ZIP: %s", url)

        try:
            response = self.session.get(url, stream=False, timeout=(15, 60))
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to download ZIP %s: %s", url, e)
            return []

        saved: List[str] = []
        try:
            zf = zipfile.ZipFile(io.BytesIO(response.content))
        except zipfile.BadZipFile:
            logger.warning("Downloaded file is not a valid ZIP: %s", url)
            return []

        for member in zf.namelist():
            member_lower = member.lower()
            if not any(member_lower.endswith(ext) for ext in (".csv", ".xlsx", ".xls")):
                continue  # skip non-tabular members (READMEs, etc.)

            ext = os.path.splitext(member_lower)[1]
            safe_member = self._safe_name(os.path.basename(member)).replace(ext, "")
            filename = f"{safe_cat}__{dataset_id}__{resource_id}__{safe_member}{ext}"
            filepath = os.path.join(self.output_dir, filename)

            try:
                with zf.open(member) as src, open(filepath, "wb") as dst:
                    dst.write(src.read())
                logger.info("Extracted ZIP member → %s", filepath)
                saved.append(os.path.abspath(filepath))
            except Exception as e:
                logger.error("Failed to extract %s from ZIP: %s", member, e)

        if not saved:
            logger.warning("ZIP had no tabular members: %s", url)

        return saved

    # ------------------------------------------------------------------
    # Metadata sidecar
    # ------------------------------------------------------------------

    def _save_metadata(self) -> None:
        """Write the metadata mapping to a JSON sidecar file."""
        path = os.path.join(self.output_dir, "_metadata.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._metadata, fh, indent=2, ensure_ascii=False)
        logger.info("Saved metadata sidecar → %s (%d entries)", path, len(self._metadata))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract(self, categories: list[str] = None) -> list[str]:
        """
        Discover and download all tabular resources from BetterGov.

        Args:
            categories: Optional list of category names to filter by
                        (e.g. ``["Government", "Finance"]``).
                        If None, all datasets are extracted.

        Returns:
            A list of absolute file paths for all successfully downloaded files.
        """
        all_files: list[str] = []
        datasets = self._discover_datasets()

        if categories:
            logger.info("Category filter active: %s", categories)
        else:
            logger.info("No category filter — extracting all datasets.")

        for dataset in datasets:
            try:
                ds_id = dataset.get("id")
                ds_name = dataset.get("name", "Unknown")
                category_info = dataset.get("category", {})
                category_name = category_info.get("name", "Uncategorized")
                publisher_info = dataset.get("publisher", {})

                # Apply category filter if provided
                if categories:
                    if category_name not in categories:
                        logger.info(
                            "Skipping dataset %d (%s) — category '%s' not in filter.",
                            ds_id, ds_name, category_name,
                        )
                        continue

                logger.info(
                    "=== Processing dataset: %s (ID: %d, Category: %s) ===",
                    ds_name, ds_id, category_name,
                )

                resources = self._discover_resources(ds_id)
                tabular = [r for r in resources if self._is_tabular(r)]

                if not tabular:
                    logger.info(
                        "  No tabular resources found for dataset %d. Skipping.", ds_id
                    )
                    continue

                logger.info(
                    "  Found %d tabular resource(s) out of %d total.",
                    len(tabular), len(resources),
                )

                for resource in tabular:
                    file_paths = self._download_resource(resource, category_name, ds_id)
                    for filepath in file_paths:
                        all_files.append(filepath)

                        # Record metadata for the transformer
                        basename = os.path.basename(filepath)
                        self._metadata[basename] = {
                            "dataset_id": ds_id,
                            "dataset_name": ds_name,
                            "category": category_name,
                            "publisher": publisher_info.get("name", "Unknown"),
                            "resource_id": resource.get("id"),
                            "resource_name": resource.get("name", ""),
                            "resource_description": resource.get("description", ""),
                            "mime_type": resource.get("mime_type", ""),
                            "attribution": dataset.get("attribution", []),
                            "license": dataset.get("license"),
                        }

            except Exception as e:
                logger.error(
                    "Error processing dataset %s: %s",
                    dataset.get("name", "?"), e,
                    exc_info=True,
                )

        self._save_metadata()

        logger.info(
            "BetterGov extraction complete. Total files: %d", len(all_files)
        )
        return all_files
