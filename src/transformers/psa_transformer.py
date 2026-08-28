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
        
        # 3. Separate ID columns into entity_name and variable_name if possible
        explicit_var_col = None
        for col in id_vars:
            if col.lower() in ["indicator", "variable", "commodity"]:
                explicit_var_col = col
                break
                
        if explicit_var_col:
            entity_cols = [c for c in id_vars if c != explicit_var_col]
            if not entity_cols:
                melted = melted.assign(entity_name="Total / Default")
            elif len(entity_cols) > 1:
                melted = melted.assign(entity_name=melted[entity_cols].astype(str).agg(' - '.join, axis=1))
            else:
                melted = melted.assign(entity_name=melted[entity_cols[0]])
            melted["explicit_var"] = melted[explicit_var_col]
        else:
            if len(id_vars) > 1:
                melted = melted.assign(entity_name=melted[id_vars].astype(str).agg(' - '.join, axis=1))
            else:
                melted = melted.assign(entity_name=melted[id_vars[0]])
            melted["explicit_var"] = None
            
        # 4. Parse Year, Period, and Variable Name from the raw_variable
        years = []
        periods = []
        var_names = []
        
        # Regex to find a 4 digit year
        year_pattern = re.compile(r'^(\d{4})')
        # Regex to find period like "Quarter 1", "Semester 1", "Annual"
        period_pattern = re.compile(r'(Quarter \d|Semester \d|Annual)')
        
        for idx, row in melted.iterrows():
            raw_var = str(row["raw_variable"])
            expl_var = row["explicit_var"]
            
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
                var_name = ""
                
            # Extract Period
            period_match = period_pattern.search(var_name)
            if period_match:
                period = period_match.group(1)
                var_name = var_name.replace(period_match.group(1), "").strip()
                
            # Determine final variable name
            if not var_name or var_name.lower() == "value":
                if pd.notna(expl_var) and expl_var:
                    var_name = str(expl_var)
                else:
                    var_name = f"Dataset {dataset_id} Metric"
                    
            years.append(year)
            periods.append(period)
            var_names.append(var_name)
            
        melted = melted.assign(
            year=years,
            period=periods,
            variable_name=var_names
        )
        
        # Drop the temporary column
        melted = melted.drop(columns=["explicit_var", "raw_variable"])
        
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
