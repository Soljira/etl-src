"""
Transformer for BetterGov Open Data Portal resources.

BetterGov datasets are heterogeneous — each has its own unique column
structure.  This transformer uses a registry of dataset-specific mapping
functions to convert known datasets into the unified 7-column schema.

Unknown datasets are handled by a *best-effort generic mapper* that
attempts to detect ID columns vs value columns and melt automatically.
"""
import json
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from .base_transformer import BaseTransformer

logger = logging.getLogger(__name__)

# Type alias for a mapping function
MapperFn = Callable[[pd.DataFrame, Dict[str, Any]], pd.DataFrame]


class BetterGovTransformer(BaseTransformer):
    """
    Transforms raw BetterGov CSV/Excel files into the unified observation
    schema using dataset-specific column mappers.

    Reads the ``_metadata.json`` sidecar written by ``BetterGovExtractor``
    to identify each file's dataset, category, and publisher.
    """

    def __init__(self, output_dir: str = "data/processed/bettergov"):
        super().__init__(output_dir=output_dir)
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._mappers: Dict[int, MapperFn] = self._build_mapper_registry()

    # ------------------------------------------------------------------
    # Metadata sidecar
    # ------------------------------------------------------------------

    def load_metadata(self, raw_dir: str = "data/raw/bettergov") -> None:
        """Load the metadata JSON produced by BetterGovExtractor."""
        path = os.path.join(raw_dir, "_metadata.json")
        if not os.path.exists(path):
            logger.warning("No metadata sidecar found at %s", path)
            return
        with open(path, "r", encoding="utf-8") as fh:
            self._metadata = json.load(fh)
        logger.info("Loaded metadata for %d file(s).", len(self._metadata))

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------

    @staticmethod
    def _read_file(filepath: str) -> pd.DataFrame:
        """Read a CSV or Excel file into a DataFrame."""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(filepath, engine="openpyxl")
        return pd.read_csv(filepath, low_memory=False, encoding_errors="replace")

    # ------------------------------------------------------------------
    # Mapper registry
    # ------------------------------------------------------------------

    def _build_mapper_registry(self) -> Dict[int, MapperFn]:
        """
        Map BetterGov dataset IDs to their transformation functions.

        Each mapper receives ``(df, meta)`` and returns a DataFrame
        conforming to the unified 7-column schema.
        """
        return {
            20: self._map_bir_tax_collection,
            # Add more mappers here as needed:
            # 13: self._map_national_debt,
            # 12: self._map_government_securities,
        }

    # ------------------------------------------------------------------
    # Dataset-specific mappers
    # ------------------------------------------------------------------

    def _map_bir_tax_collection(
        self, df: pd.DataFrame, meta: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        BIR Tax Collection datasets.

        Two layouts exist:
        A) Monthly wide table:
           Region | PARTICULARS | JANUARY | FEBRUARY | ... | DECEMBER
        B) GAA by Region wide table:
           Year | Region I | Region II | ... | Region XIX
        """
        cols = [c.strip() for c in df.columns]
        df.columns = cols

        resource_name = meta.get("resource_name", "")
        dataset_id_str = f"bettergov_{meta['dataset_id']}_{meta.get('resource_id', 0)}"
        category = meta.get("category", "Government")

        month_names = {
            "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
            "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
        }
        upper_cols = {c.upper() for c in cols}

        # Layout A: Monthly wide table (Region | PARTICULARS | MONTHS...)
        if month_names.intersection(upper_cols):
            # Identify the month columns (case-insensitive match)
            month_cols = [c for c in cols if c.upper().strip() in month_names]
            id_cols = [c for c in cols if c not in month_cols]

            melted = pd.melt(
                df,
                id_vars=id_cols,
                value_vars=month_cols,
                var_name="period",
                value_name="value",
            ).copy()

            # Build entity_name from id columns
            for col in id_cols:
                melted.loc[:, col] = melted[col].astype(str).str.strip()
            melted.loc[:, "entity_name"] = melted[id_cols].apply(
                lambda row: " - ".join(v for v in row if v and v != "nan"), axis=1
            )

            # Extract year from resource name (e.g. "2024 BIR Tax Collection")
            year_match = re.search(r"(\d{4})", resource_name)
            melted.loc[:, "year"] = int(year_match.group(1)) if year_match else None

            melted.loc[:, "period"] = melted["period"].str.strip().str.title()
            melted.loc[:, "variable_name"] = "BIR Tax Collection (PHP Millions)"
            melted.loc[:, "dataset_id"] = dataset_id_str
            melted.loc[:, "category"] = category

            # Clean values — remove commas, spaces, and coerce
            melted.loc[:, "value"] = (
                melted["value"]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            melted.loc[:, "value"] = pd.to_numeric(melted["value"], errors="coerce")
            melted = melted.dropna(subset=["value"])

            return melted[self.schema]

        # Layout B: Year | Region columns (GAA by Region)
        if "Year" in cols or "year" in cols:
            year_col = "Year" if "Year" in cols else "year"
            region_cols = [c for c in cols if c != year_col]

            melted = pd.melt(
                df,
                id_vars=[year_col],
                value_vars=region_cols,
                var_name="entity_name",
                value_name="value",
            ).copy()
            melted.loc[:, "year"] = pd.to_numeric(melted[year_col], errors="coerce")
            melted.loc[:, "period"] = "Annual"
            melted.loc[:, "variable_name"] = resource_name or "GAA Budget Allocation (PHP)"
            melted.loc[:, "dataset_id"] = dataset_id_str
            melted.loc[:, "category"] = category

            melted.loc[:, "value"] = pd.to_numeric(melted["value"], errors="coerce")
            melted = melted.dropna(subset=["value"])

            return melted[self.schema]

        # Fallback: try generic mapper
        return self._map_generic(df, meta)

    # ------------------------------------------------------------------
    # Generic fallback mapper
    # ------------------------------------------------------------------

    def _map_generic(
        self, df: pd.DataFrame, meta: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Best-effort generic mapper for unknown CSV layouts.

        Heuristic:
        1. Columns containing 4-digit years or numeric-only values →
           classified as value columns.
        2. Everything else → ID columns joined into ``entity_name``.
        3. If no clear split can be found, skip the file.
        """
        cols = list(df.columns)
        dataset_id_str = f"bettergov_{meta['dataset_id']}_{meta.get('resource_id', 0)}"
        category = meta.get("category", "Uncategorized")
        resource_name = meta.get("resource_name", "Unknown")

        # Try to detect a year column
        year_col = None
        for c in cols:
            if re.match(r"(?i)^year$", c.strip()):
                year_col = c
                break

        # Try to detect obvious numeric value columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if year_col and len(numeric_cols) > 0:
            value_cols = [c for c in numeric_cols if c != year_col]
            id_cols = [c for c in cols if c not in value_cols and c != year_col]

            if not value_cols:
                logger.warning(
                    "Generic mapper: no value columns found for %s. Skipping.",
                    meta.get("resource_name"),
                )
                return pd.DataFrame(columns=self.schema)

            melted = pd.melt(
                df,
                id_vars=[year_col] + id_cols,
                value_vars=value_cols,
                var_name="variable_name",
                value_name="value",
            ).copy()

            melted.loc[:, "year"] = pd.to_numeric(melted[year_col], errors="coerce")
            for col in id_cols:
                melted.loc[:, col] = melted[col].astype(str).str.strip()
            if id_cols:
                melted.loc[:, "entity_name"] = melted[id_cols].apply(
                    lambda row: " - ".join(v for v in row if v and v != "nan"), axis=1
                )
            else:
                melted.loc[:, "entity_name"] = resource_name

            melted.loc[:, "period"] = "Annual"
            melted.loc[:, "dataset_id"] = dataset_id_str
            melted.loc[:, "category"] = category

            melted.loc[:, "value"] = pd.to_numeric(melted["value"], errors="coerce")
            melted = melted.dropna(subset=["value"])

            return melted[self.schema]

        logger.warning(
            "Generic mapper: cannot determine schema for '%s' (dataset %d). Skipping.",
            resource_name,
            meta.get("dataset_id", 0),
        )
        return pd.DataFrame(columns=self.schema)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def transform(self, filepath: str) -> pd.DataFrame:
        """
        Transform a single raw BetterGov file into the unified schema.

        Uses the metadata sidecar to look up the dataset ID and select
        the appropriate mapper function.
        """
        basename = os.path.basename(filepath)
        meta = self._metadata.get(basename)

        if meta is None:
            logger.warning(
                "No metadata found for %s. Attempting generic transform.", basename
            )
            meta = {
                "dataset_id": 0,
                "resource_id": 0,
                "resource_name": basename,
                "category": "Unknown",
            }

        dataset_id = meta.get("dataset_id", 0)
        resource_name = meta.get("resource_name", basename)

        logger.info(
            "Transforming BetterGov resource: %s (dataset %d)",
            resource_name, dataset_id,
        )

        try:
            df = self._read_file(filepath)
        except Exception as e:
            logger.error("Failed to read %s: %s", filepath, e)
            return pd.DataFrame(columns=self.schema)

        if df.empty:
            logger.warning("File %s is empty.", filepath)
            return pd.DataFrame(columns=self.schema)

        # Use registered mapper if available, else fall back to generic
        mapper = self._mappers.get(dataset_id, self._map_generic)
        try:
            result = mapper(df, meta)
        except Exception as e:
            logger.error(
                "Mapper failed for dataset %d (%s): %s", dataset_id, resource_name, e
            )
            return pd.DataFrame(columns=self.schema)

        if result.empty:
            logger.warning("Transformation produced empty result for %s.", basename)
        else:
            logger.info(
                "  → %d observation(s) from %s", len(result), resource_name
            )

        return result
