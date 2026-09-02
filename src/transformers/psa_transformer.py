import logging
import os
import re

import pandas as pd

from .base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


"""
Algo:
Reads a messy, wide PSA CSV where each column header is a mini-sentence like "2023 Q1", uses pd.melt() 
to turn columns into rows, then uses regex pattern matching to parse each header apart into clean year, period, and 
variable_name field, producing rows that all conform to the unified 7-column schema.

1. Get metadata from the filename 
2. Read the CSV
3. Classify columns
4. Melt. Take every value column and turn it into rows
5. Figure out which ID columns mean what
"""
class PsaTransformer(BaseTransformer):
    """
    Transforms wide-format PSA CSVs into the long-format unified schema.
    """

    def transform(self, filepath: str) -> pd.DataFrame:
        logger.info(f"Transforming PSA file: {filepath}")

        # Extract metadata from filename: Category__DatasetID.csv
        basename = os.path.basename(filepath)
        name_parts = basename.replace(".csv", "").split("__")
        category = name_parts[0] if len(name_parts) > 0 else "Unknown"
        dataset_id = name_parts[1] if len(name_parts) > 1 else "Unknown"

        # Read the raw CSV
        try:
            df = pd.read_csv(filepath)
            # print(df)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to read {filepath}: {e}")
            return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        # 1. Identify ID columns vs Value columns
        # Assume columns not containing digits and usually at the start are ID columns
        id_vars = []
        value_vars = []

        for col in df.columns:
            col_lower = col.lower()
            # If it explicitly looks like a year header or known wide value column
            if re.search(r"\d{4}", col) or col in [
                "Total Population",
                "Household Population",
                "Number of Households",
            ]:
                value_vars.append(col)
            else:
                # All non-year metadata columns (Sex, Age Group, Geographic Location, Inputs, Sector, etc.) are ID columns
                id_vars.append(col)

        if not id_vars:
            # Extreme fallback
            id_vars = [df.columns[0]]
            value_vars = list(df.columns[1:])

        # 2. Melt the DataFrame
        melted = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="raw_variable",
            value_name="value",
        )

        # 3. Identify special columns within id_vars
        explicit_var_col = None
        explicit_year_col = None
        entity_cols = []

        for col in id_vars:
            col_lower = col.lower()
            if col_lower in ["indicator", "variable", "commodity", "inputs", "type"]:
                explicit_var_col = col
            elif col_lower == "year":
                explicit_year_col = col
            else:
                entity_cols.append(col)

        # 4. Map columns for each row
        years = []
        periods = []
        var_names = []
        entity_names = []

        # Regexes
        year_pattern = re.compile(r"^(\d{4})")
        period_pattern = re.compile(r"(Quarter \d|Semester \d|Annual)")

        for idx, row in melted.iterrows():
            raw_var = str(row["raw_variable"])

            # Start with explicit mappings if available
            row_year = (
                int(row[explicit_year_col])
                if explicit_year_col and pd.notna(row[explicit_year_col])
                else None
            )
            row_var = (
                str(row[explicit_var_col])
                if explicit_var_col and pd.notna(row[explicit_var_col])
                else None
            )
            row_period = None

            # Extract from raw_var if year/var are not yet satisfied
            leftover_raw = raw_var

            # If we don't have a year yet, try to find it in raw_var
            if not row_year:
                year_match = year_pattern.search(leftover_raw)
                if year_match:
                    row_year = int(year_match.group(1))
                    leftover_raw = leftover_raw.replace(year_match.group(1), "").strip()
                elif re.match(r"^\d{4}$", leftover_raw):
                    row_year = int(leftover_raw)
                    leftover_raw = ""

            # Try to find period in raw_var
            period_match = period_pattern.search(leftover_raw)
            if period_match:
                row_period = period_match.group(1)
                leftover_raw = leftover_raw.replace(period_match.group(1), "").strip()

            # If we STILL don't have a variable_name, use a descriptive metric name based on category
            if not row_var or row_var.lower() == "value":
                if leftover_raw and leftover_raw.lower() != "value":
                    row_var = leftover_raw
                    leftover_raw = ""  # Consumed
                elif category.lower().startswith("population"):
                    row_var = "Population Count"
                else:
                    row_var = "Observed Value"

            # Construct the entity name from entity_cols AND any leftover raw_var
            row_entities = []
            for ec in entity_cols:
                if pd.notna(row[ec]):
                    row_entities.append(str(row[ec]))
            if leftover_raw and leftover_raw.lower() != "value":
                row_entities.append(leftover_raw)

            row_entity = " - ".join(row_entities) if row_entities else "Total / Default"

            years.append(row_year)
            periods.append(row_period)
            var_names.append(row_var)
            entity_names.append(row_entity)

        melted = melted.assign(
            year=years,
            period=periods,
            variable_name=var_names,
            entity_name=entity_names,
        )

        # Drop raw columns to clean up
        melted = melted.drop(columns=id_vars + ["raw_variable"])

        # 5. Clean values (remove non-numeric indicators like '..', '-', converting to NaN)
        cleaned_values = pd.to_numeric(
            melted["value"].replace(r"[^\d\.\-]", "", regex=True), errors="coerce"
        )
        melted = melted.assign(value=cleaned_values)

        # Drop rows with entirely null values (empty observations)
        melted = melted.dropna(subset=["value"])

        # 6. Add standard metadata
        melted = melted.assign(dataset_id=dataset_id, category=category)

        return melted
