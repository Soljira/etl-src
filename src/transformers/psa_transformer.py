import logging
import os
import re
import pandas as pd
from .base_transformer import BaseTransformer

logger = logging.getLogger(__name__)

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
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return pd.DataFrame()
            
        if df.empty:
            return pd.DataFrame()
            
        # 1. Identify ID columns vs Value columns
        # Assume columns not containing digits and usually at the start are ID columns
        id_vars = []
        value_vars = []
        
        for col in df.columns:
            # If it's a known non-value column or doesn't look like a year/value column
            if col.lower() in ["indicator", "sector", "geographic location", "industry description", "ecosystem/croptype"]:
                id_vars.append(col)
            elif re.search(r'\d{4}', col) or col in ["Total Population", "Household Population", "Number of Households"]:
                value_vars.append(col)
            else:
                # Fallback: if it's the first column it's probably an ID
                if len(id_vars) == 0:
                    id_vars.append(col)
                else:
                    value_vars.append(col)
                    
        if not id_vars:
            # Extreme fallback
            id_vars = [df.columns[0]]
            value_vars = list(df.columns[1:])
            
        # 2. Melt the DataFrame
        melted = pd.melt(df, id_vars=id_vars, value_vars=value_vars, var_name="raw_variable", value_name="value")
        
        # 3. Combine ID columns into a single "entity_name"
        if len(id_vars) > 1:
            melted = melted.assign(entity_name=melted[id_vars].astype(str).agg(' - '.join, axis=1))
        else:
            melted = melted.assign(entity_name=melted[id_vars[0]])
            
        # 4. Parse Year, Period, and Variable Name from the raw_variable
        years = []
        periods = []
        var_names = []
        
        # Regex to find a 4 digit year
        year_pattern = re.compile(r'^(\d{4})')
        # Regex to find period like "Quarter 1", "Semester 1", "Annual"
        period_pattern = re.compile(r'(Quarter \d|Semester \d|Annual)')
        
        for raw_var in melted["raw_variable"].astype(str):
            year = None
            period = None
            var_name = raw_var
            
            # Extract Year
            year_match = year_pattern.search(var_name)
            if year_match:
                year = int(year_match.group(1))
                var_name = var_name.replace(year_match.group(1), "").strip()
            elif re.match(r'^\d{4}$', var_name):
                # The column is literally just a year (like Labor data)
                year = int(var_name)
                var_name = "Value"
                
            # Extract Period
            period_match = period_pattern.search(var_name)
            if period_match:
                period = period_match.group(1)
                var_name = var_name.replace(period_match.group(1), "").strip()
                
            if not var_name:
                var_name = "Value"
                
            years.append(year)
            periods.append(period)
            var_names.append(var_name)
            
        melted = melted.assign(
            year=years,
            period=periods,
            variable_name=var_names
        )
        
        # 5. Clean values (remove non-numeric indicators like '..', '-', converting to NaN)
        cleaned_values = pd.to_numeric(melted['value'].replace(r'[^\d\.\-]', '', regex=True), errors='coerce')
        melted = melted.assign(value=cleaned_values)
        
        # Drop rows with entirely null values (empty observations)
        melted = melted.dropna(subset=['value'])
        
        # 6. Add standard metadata
        melted = melted.assign(
            dataset_id=dataset_id,
            category=category
        )
        
        return melted
