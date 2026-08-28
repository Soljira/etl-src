import logging
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Validates DataFrames that have been transformed into the Unified Schema.
    Performs completeness checks, consistency bounds, and statistical anomaly detection.
    """
    
    def __init__(self):
        self.critical_columns = ["dataset_id", "category", "entity_name", "variable_name", "value"]
        
    def validate(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Runs all validation checks on the DataFrame.
        Returns the cleaned DataFrame (with fundamentally broken rows removed)
        and a dictionary of quality metrics/warnings.
        """
        if df.empty:
            return df, {"status": "empty", "quality_score": 0.0}
            
        metrics = {
            "initial_rows": len(df),
            "warnings": [],
            "anomalies_detected": 0
        }
        
        # 1. Completeness Checks
        df, metrics = self._check_completeness(df, metrics)
        
        # If all rows were dropped, exit early
        if df.empty:
            metrics["quality_score"] = 0.0
            return df, metrics
            
        # 2. Consistency Checks
        df, metrics = self._check_consistency(df, metrics)
        
        # 3. Statistical Anomaly Detection
        df, metrics = self._detect_anomalies(df, metrics)
        
        # Calculate Quality Score (0 to 100)
        # Deduct points for missing optional data (year/period) and statistical anomalies
        score = 100.0
        
        missing_years_pct = df["year"].isna().mean() * 100
        if missing_years_pct > 0:
            score -= (missing_years_pct * 0.2)  # Max 20 points deduction for missing years
            
        anomaly_rate = metrics["anomalies_detected"] / len(df) * 100
        if anomaly_rate > 0:
            score -= (anomaly_rate * 2.0)  # Heavy deduction for high anomaly rates
            
        metrics["quality_score"] = max(0.0, round(score, 2))
        metrics["final_rows"] = len(df)
        
        return df, metrics

    def _check_completeness(self, df: pd.DataFrame, metrics: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        # Drop rows missing critical values
        initial_len = len(df)
        df_clean = df.dropna(subset=self.critical_columns).copy()
        dropped = initial_len - len(df_clean)
        
        if dropped > 0:
            metrics["warnings"].append(f"Dropped {dropped} rows due to missing critical columns.")
            
        # Check optional columns (just log warnings)
        missing_years = df_clean["year"].isna().sum()
        if missing_years > 0:
            metrics["warnings"].append(f"{missing_years} rows are missing 'year' information.")
            
        return df_clean, metrics
        
    def _check_consistency(self, df: pd.DataFrame, metrics: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        # Ensure year is within reasonable bounds (1900 - 2100)
        invalid_years = df[df["year"].notna() & ((df["year"] < 1900) | (df["year"] > 2100))]
        if not invalid_years.empty:
            metrics["warnings"].append(f"Found {len(invalid_years)} rows with out-of-bounds years (not between 1900 and 2100).")
            # We don't drop them, we just nullify the impossible year
            df.loc[invalid_years.index, "year"] = np.nan
            
        # Specific rule: 'Total Population' cannot be negative
        pop_mask = (df["variable_name"].str.contains("Population", case=False, na=False)) & (df["value"] < 0)
        neg_pop = df[pop_mask]
        if not neg_pop.empty:
            metrics["warnings"].append(f"Found {len(neg_pop)} rows with impossible negative Population counts.")
            # Nullify impossible values
            df.loc[neg_pop.index, "value"] = np.nan
            
        return df, metrics
        
    def _detect_anomalies(self, df: pd.DataFrame, metrics: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        # Vectorized statistical outlier detection per variable (Z-score > 3)
        if not pd.api.types.is_numeric_dtype(df["value"]):
            metrics["warnings"].append("'value' column is not purely numeric.")
            return df, metrics

        if len(df) == 0:
            metrics["anomalies_detected"] = 0
            return df, metrics

        # Group stats in vectorized operations instead of slow python loops
        grouped = df.groupby("variable_name")["value"]
        counts = grouped.transform("count")
        means = grouped.transform("mean")
        stds = grouped.transform("std")

        # Mask for groups with > 5 items and std > 0
        valid_mask = (counts > 5) & (stds > 0) & stds.notna()
        z_scores = np.where(valid_mask, np.abs((df["value"] - means) / stds), 0.0)
        
        num_outliers = int((z_scores > 3.0).sum())
        metrics["anomalies_detected"] = num_outliers
        
        if num_outliers > 0:
            metrics["warnings"].append(f"Detected {num_outliers} extreme statistical outliers across dataset.")

        return df, metrics
