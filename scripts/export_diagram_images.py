import os
import base64
import urllib.parse
import requests

DIAGRAMS = {
    "erd": '''erDiagram
    CATEGORY ||--|{ DATASET : "organizes"
    DATASET ||--|{ OBSERVATION : "contains"
    DATASET ||--o| VALIDATION_LOG : "generates"

    CATEGORY {
        string category_code PK
        string category_name
    }

    DATASET {
        string dataset_id PK
        string category_code FK
        string dataset_title
        datetime extracted_at
    }

    OBSERVATION {
        integer id PK
        string dataset_id FK
        string category
        string entity_name
        string variable_name
        integer year
        string period
        float value
        datetime created_at
    }

    VALIDATION_LOG {
        integer log_id PK
        string dataset_id FK
        integer initial_rows
        integer final_rows
        float quality_score
        integer anomalies_detected
    }''',

    "use_case_diagram": '''flowchart LR
    subgraph Actors ["Actors"]
        Operator["Pipeline Operator / Cron Job"]
        User["API Client / Researcher"]
        PSA["PSA OpenSTAT API Server"]
    end

    subgraph System ["ETL for Open Data Philippines Framework"]
        UC1("(UC-1: Discover OpenSTAT Datasets)")
        UC2("(UC-2: Download Raw CSV Files)")
        UC3("(UC-3: Transform Wide Tables to Long Schema)")
        UC4("(UC-4: Validate Data Quality & Detect Outliers)")
        UC5("(UC-5: Load Observations to PostgreSQL)")
        UC6("(UC-6: Query Data Observations via REST API)")
        UC7("(UC-7: Filter Data by Year, Category & Entity)")
        UC8("(UC-8: Check API & DB System Health)")
    end

    Operator --> UC1
    Operator --> UC2
    Operator --> UC3
    Operator --> UC4
    Operator --> UC5

    UC1 <-->|GET /PXWeb/api/v1/en/DB| PSA
    UC2 <-->|POST /PXWeb/api/v1/en/table_path| PSA

    User --> UC6
    User --> UC7
    User --> UC8''',

    "extraction_flowchart": '''flowchart TD
    Start([Start Extraction]) --> InitExt[Initialize PsaExtractor]
    InitExt --> LoopCat[Iterate Target Categories]
    LoopCat --> GETNode[GET Request to PXWeb API]
    GETNode --> CheckType{Node Type?}
    
    CheckType -- Folder --> Recurse[Recursively walk subnodes] --> GETNode
    CheckType -- Table --> CollectPath[Collect table path]
    
    CollectPath --> TableLoop[For each table path]
    TableLoop --> GETMeta[GET Metadata Request]
    GETMeta --> BuildPayload[Build POST Payload]
    BuildPayload --> RateLimit[Enforce Rate Limit Delay]
    RateLimit --> POSTData[POST Request Fetch CSV]
    POSTData --> RespOK{HTTP 200 OK?}
    
    RespOK -- Yes --> SaveCSV[Save raw CSV file]
    RespOK -- No --> LogErr[Log extraction error]
    
    SaveCSV --> NextTable{More tables?}
    LogErr --> NextTable
    NextTable -- Yes --> TableLoop
    NextTable -- No --> NextCat{More categories?}
    NextCat -- Yes --> LoopCat
    NextCat -- No --> EndExt([End Extraction])''',

    "transformation_flowchart": '''flowchart TD
    StartT([Start Transformation]) --> ReadCSV[Read Raw CSV]
    ReadCSV --> ExtractMeta[Extract metadata from filename]
    ExtractMeta --> IdentCols[Classify Columns]
    IdentCols --> Melt[Melt Wide Table to Long Format]
    
    Melt --> CombineEntity[Combine ID columns into entity_name]
    CombineEntity --> LoopVars[Parse raw_variable column]
    LoopVars --> RegexYear[Extract Year via Regex]
    RegexYear --> RegexPeriod[Extract Period via Regex]
    RegexPeriod --> ExtractVar[Clean variable_name]
    
    ExtractVar --> CleanValues[Parse value column to float]
    CleanValues --> DropNulls[Drop null rows]
    DropNulls --> PassValidator[Pass to DataValidator]
    
    PassValidator --> CheckComp[Completeness Check]
    CheckComp --> CheckBounds[Consistency Check]
    CheckBounds --> AnomalyCheck[Statistical Anomaly Check]
    AnomalyCheck --> CalcScore[Compute Quality Score]
    CalcScore --> EndT([Return Cleaned Data])''',

    "api_query_flowchart": '''flowchart TD
    StartAPI([HTTP GET /api/v1/observations]) --> Route[Parse Query Params in routes.py]
    Route --> ServiceCall[Initialize Query in services.py]
    ServiceCall --> CheckCat{Category Filter?}
    CheckCat -- Yes --> FilterCat[Apply Category Filter]
    CheckCat -- No --> CheckDS
    FilterCat --> CheckDS{Dataset Filter?}
    
    CheckDS -- Yes --> FilterDS[Apply Dataset Filter]
    CheckDS -- No --> CheckYear
    FilterDS --> CheckYear{Year Filter?}
    
    CheckYear -- Yes --> FilterYear[Apply Year Filter]
    CheckYear -- No --> CheckEntity
    FilterYear --> CheckEntity{Entity Filter?}
    
    CheckEntity -- Yes --> FilterEntity[Apply Entity Filter]
    CheckEntity -- No --> ExecCount
    FilterEntity --> ExecCount[Execute Query Count]
    
    ExecCount --> Paginate[Apply Offset & Limit Pagination]
    Paginate --> Serialize[Serialize Observation Objects to JSON]
    Serialize --> SendResp([Return 200 OK HTTP Response])'''
}

def export_images():
    output_dir = "docs/images"
    os.makedirs(output_dir, exist_ok=True)
    
    for name, code in DIAGRAMS.items():
        b64 = base64.b64encode(code.encode("utf-8")).decode("utf-8")
        quoted_b64 = urllib.parse.quote(b64, safe="")
        
        # PNG
        png_url = f"https://mermaid.ink/img/{quoted_b64}"
        resp_png = requests.get(png_url)
        if resp_png.status_code == 200:
            png_path = os.path.join(output_dir, f"{name}.png")
            with open(png_path, "wb") as f:
                f.write(resp_png.content)
            print(f"Successfully saved {png_path} ({len(resp_png.content)} bytes)")
        else:
            print(f"Failed PNG for {name}: status {resp_png.status_code}")

        # SVG
        svg_url = f"https://mermaid.ink/svg/{quoted_b64}"
        resp_svg = requests.get(svg_url)
        if resp_svg.status_code == 200:
            svg_path = os.path.join(output_dir, f"{name}.svg")
            with open(svg_path, "wb") as f:
                f.write(resp_svg.content)
            print(f"Successfully saved {svg_path} ({len(resp_svg.content)} bytes)")
        else:
            print(f"Failed SVG for {name}: status {resp_svg.status_code}")

if __name__ == "__main__":
    export_images()
