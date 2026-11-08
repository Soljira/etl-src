import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    
    # 16:9 Widescreen aspect ratio
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    blank_layout = prs.slide_layouts[6]
    
    # Color Palette (Minimalist Dark Theme)
    COLOR_BG = RGBColor(15, 23, 42)        # #0F172A Deep Slate
    COLOR_CARD = RGBColor(30, 41, 59)      # #1E293B Card Background
    COLOR_TEXT = RGBColor(248, 250, 252)   # #F8FAFC Bright Text
    COLOR_MUTED = RGBColor(148, 163, 184)  # #94A3B8 Muted Text
    COLOR_ACCENT = RGBColor(56, 189, 248)   # #38BDF8 Primary Sky Blue
    COLOR_GREEN = RGBColor(34, 197, 94)    # #22C55E Green Accent
    COLOR_PURPLE = RGBColor(168, 85, 247)  # #A855F7 Purple Accent

    def set_slide_background(slide):
        background = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        background.fill.solid()
        background.fill.fore_color.rgb = COLOR_BG
        background.line.color.rgb = COLOR_BG

    def add_header(slide, title_text, category_text):
        # Category Tracker
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.4))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_ACCENT
        p_cat.font.name = 'Inter'

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.85), Inches(11.7), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_TEXT
        p_title.font.name = 'Outfit'

    # -------------------------------------------------------------------------
    # SLIDE 1: Title Slide
    # -------------------------------------------------------------------------
    slide1 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide1)
    
    # Title Box
    t_box1 = slide1.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.333), Inches(3.0))
    tf1 = t_box1.text_frame
    tf1.word_wrap = True
    
    p1 = tf1.paragraphs[0]
    p1.text = "ETL PIPELINE FRAMEWORK FOR OPEN DATA PHILIPPINES DATASETS"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_ACCENT
    p1.font.name = 'Outfit'
    p1.alignment = PP_ALIGN.LEFT
    
    p2 = tf1.add_paragraph()
    p2.text = "Automated Extraction, Schema Standardization, Quality Validation, and API Delivery"
    p2.font.size = Pt(18)
    p2.font.color.rgb = COLOR_TEXT
    p2.font.name = 'Inter'
    p2.space_before = Pt(16)

    p3 = tf1.add_paragraph()
    p3.text = "Undergraduate Computer Science Thesis Presentation"
    p3.font.size = Pt(14)
    p3.font.color.rgb = COLOR_MUTED
    p3.font.name = 'Inter'
    p3.space_before = Pt(30)

    # -------------------------------------------------------------------------
    # SLIDE 2: Project Overview & Problem Statement
    # -------------------------------------------------------------------------
    slide2 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide2)
    add_header(slide2, "Research Context & Problem Statement", "Chapter I — Overview")

    # Left Box: Problem
    card1 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0))
    card1.fill.solid()
    card1.fill.fore_color.rgb = COLOR_CARD
    card1.line.color.rgb = COLOR_CARD
    
    tf_c1 = card1.text_frame
    tf_c1.word_wrap = True
    p = tf_c1.paragraphs[0]
    p.text = "Current Challenges (The Problem)"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = RGBColor(239, 68, 68) # Red accent
    
    points1 = [
        "Data Fragmentation: Government statistics spread across disconnected agency portals.",
        "Inconsistent Formats: Mixed CSV, Excel, and JSON layouts with non-standard column names.",
        "Manual Wrangling Burden: Researchers waste extensive time downloading, cleaning, and un-pivoting wide spreadsheets.",
        "Lack of Unified Access: Absence of programmatic REST API endpoints for seamless integration."
    ]
    for pt in points1:
        p_sub = tf_c1.add_paragraph()
        p_sub.text = "• " + pt
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = COLOR_MUTED
        p_sub.space_before = Pt(12)

    # Right Box: Solution
    card2 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    card2.fill.solid()
    card2.fill.fore_color.rgb = COLOR_CARD
    card2.line.color.rgb = COLOR_CARD
    
    tf_c2 = card2.text_frame
    tf_c2.word_wrap = True
    p = tf_c2.paragraphs[0]
    p.text = "Proposed Solution (The Framework)"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN
    
    points2 = [
        "Automated Extraction: Programmatically discovering & downloading OpenSTAT PSA datasets.",
        "Unified Schema: Reshaping wide multi-header datasets into a clean long-format observation fact table.",
        "Data Quality Engine: Automated completeness checks, consistency rules, and Z-score outlier detection.",
        "REST API & Web GUI: Providing instant filtering, pagination, and JSON export for developers & researchers."
    ]
    for pt in points2:
        p_sub = tf_c2.add_paragraph()
        p_sub.text = "• " + pt
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = COLOR_MUTED
        p_sub.space_before = Pt(12)

    # -------------------------------------------------------------------------
    # SLIDE 3: Objectives of the Study
    # -------------------------------------------------------------------------
    slide3 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide3)
    add_header(slide3, "Objectives of the Study", "Chapter I — Research Goals")

    # 3 Column Layout
    objs = [
        ("1. Design Considerations", "Identify design considerations for system architecture, data warehouse schema, REST API structure, transformation rules, and quality validation procedures.", COLOR_ACCENT),
        ("2. System Development", "Build the automated ETL system to extract OpenSTAT PSA datasets, normalize wide formats into unified long schemas, and bulk-load into PostgreSQL.", COLOR_GREEN),
        ("3. Empirical Evaluation", "Evaluate system performance via quantitative metrics (extraction success, processing throughput, API response latency) and Data Quality Scores (0 - 100).", COLOR_PURPLE)
    ]

    for i, (title, desc, color) in enumerate(objs):
        card = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + i*3.9), Inches(1.8), Inches(3.7), Inches(5.0))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD
        card.line.color.rgb = COLOR_CARD
        
        tf = card.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(16)
        p_t.font.bold = True
        p_t.font.color.rgb = color
        
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(13)
        p_d.font.color.rgb = COLOR_MUTED
        p_d.space_before = Pt(14)

    # -------------------------------------------------------------------------
    # SLIDE 4: Conceptual Framework (IPO Model)
    # -------------------------------------------------------------------------
    slide4 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide4)
    add_header(slide4, "Conceptual Framework (Input-Process-Output)", "Chapter I — Framework")

    ipo_boxes = [
        ("INPUT", ["OpenSTAT PSA API", "4 Domain Categories:", "• Agriculture (2E)", "• Labor (3K)", "• Population (1A)", "• Mining (2G)"], COLOR_ACCENT, Inches(0.8)),
        ("PROCESS", ["1. Programmatic Extraction", "2. Wide-to-Long Melting", "3. Quality Validation", "4. PostgreSQL Bulk Loading", "5. REST API Services"], COLOR_PURPLE, Inches(4.8)),
        ("OUTPUT", ["Centralized Data Warehouse", "RESTful Query API", "Interactive Web GUI", "Data Quality Metrics (0-100)", "System Documentation"], COLOR_GREEN, Inches(8.8))
    ]

    for title, items, color, left_pos in ipo_boxes:
        card = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(1.8), Inches(3.7), Inches(5.0))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD
        card.line.color.rgb = COLOR_CARD
        
        tf = card.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(18)
        p_t.font.bold = True
        p_t.font.color.rgb = color
        
        for item in items:
            p_i = tf.add_paragraph()
            p_i.text = item
            p_i.font.size = Pt(13)
            p_i.font.color.rgb = COLOR_MUTED
            p_i.space_before = Pt(10)

    # -------------------------------------------------------------------------
    # SLIDE 5: Technical Stack Overview
    # -------------------------------------------------------------------------
    slide5 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide5)
    add_header(slide5, "Software Architecture & Technology Stack", "Chapter III — Technical Background")

    tech_stack = [
        ("Core Language", "Python 3.10+", "Primary language for pipeline, transformations, and API development."),
        ("Data Processing", "pandas & NumPy", "Wide-to-long reshaping (`melt`), string cleaning, and Z-score outlier math."),
        ("Data Warehouse", "PostgreSQL 16+", "Centralized relational database storing unified observations."),
        ("Database Driver & ORM", "pg8000 & SQLAlchemy 2.0+", "Pure Python PostgreSQL driver & ORM data access layer."),
        ("REST API & Web GUI", "Flask 3.0+ & Django 4.2+", "Lightweight REST API endpoints & responsive containerized management GUI."),
        ("Containerization", "Docker & Docker Compose", "Multi-container orchestration (PostgreSQL DB + Flask API + Django GUI).")
    ]

    for i, (cat, tech, desc) in enumerate(tech_stack):
        col = i % 2
        row = i // 2
        
        card = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + col*5.9), Inches(1.8 + row*1.7), Inches(5.7), Inches(1.5))
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD
        card.line.color.rgb = COLOR_CARD
        
        tf = card.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = f"{cat}: {tech}"
        p_t.font.size = Pt(15)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_ACCENT
        
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = COLOR_MUTED
        p_d.space_before = Pt(6)

    # -------------------------------------------------------------------------
    # SLIDE 6: Data Extraction Module (PsaExtractor)
    # -------------------------------------------------------------------------
    slide6 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide6)
    add_header(slide6, "Data Extraction Module (PsaExtractor)", "Chapter III — Pipeline Architecture")

    card_ext = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.733), Inches(5.0))
    card_ext.fill.solid()
    card_ext.fill.fore_color.rgb = COLOR_CARD
    card_ext.line.color.rgb = COLOR_CARD

    tf_ext = card_ext.text_frame
    tf_ext.word_wrap = True
    
    p = tf_ext.paragraphs[0]
    p.text = "Key Extraction Mechanisms:"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT

    steps_ext = [
        "Recursive Tree Discovery: Walks OpenSTAT PX-Web API nodes (`/PXWeb/api/v1/en/DB`) to locate table files (`.px`), handling variable nesting depths (e.g. 4 levels deep in Mining datasets).",
        "Metadata Inspection: Issues GET requests to inspect table variable descriptors (`code`, `text`, `values`, `valueTexts`).",
        "POST Payload Generation: Dynamically builds PX-Web JSON query payload selecting all variable values (`'filter': 'all', 'values': ['*']`).",
        "Rate-Limitation Compliance: Enforces a 1.1-second sleep delay between API requests to strictly comply with OpenSTAT's limit of 10 requests per 10 seconds.",
        "Raw Storage: Downloads tables in CSV format and saves them to `data/raw/psa/{Category}__{TableID}.csv`."
    ]

    for step in steps_ext:
        p_s = tf_ext.add_paragraph()
        p_s.text = "• " + step
        p_s.font.size = Pt(13)
        p_s.font.color.rgb = COLOR_MUTED
        p_s.space_before = Pt(10)

    # -------------------------------------------------------------------------
    # SLIDE 7: Data Transformation Module (PsaTransformer)
    # -------------------------------------------------------------------------
    slide7 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide7)
    add_header(slide7, "Data Transformation & Normalization", "Chapter III — Pipeline Architecture")

    card_tr = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.733), Inches(5.0))
    card_tr.fill.solid()
    card_tr.fill.fore_color.rgb = COLOR_CARD
    card_tr.line.color.rgb = COLOR_CARD

    tf_tr = card_tr.text_frame
    tf_tr.word_wrap = True
    
    p = tf_tr.paragraphs[0]
    p.text = "Standardization Rules (Wide to Long Schema):"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN

    steps_tr = [
        "Wide-to-Long Melting (`pd.melt`): Transforms multi-column periodic spreadsheets (where years/quarters are column headers) into normalized observations.",
        "Entity Header Concatenation: Combines multiple structural identification columns (e.g. Region, Industry, Ecosystem) into a single descriptive `entity_name`.",
        "Regex Temporal Parsing: Extracts 4-digit calendar years (`r'^(\\d{4})'`) and sub-annual periodicity intervals (`r'(Quarter \\d|Semester \\d|Annual)'`).",
        "Numeric Cleaning: Strips non-numeric characters and missing data symbols (`..`, `-`), converting text measurements to float values and dropping empty null rows.",
        "Metadata Lineage: Attaches `dataset_id` and domain `category` codes to every individual row record."
    ]

    for step in steps_tr:
        p_s = tf_tr.add_paragraph()
        p_s.text = "• " + step
        p_s.font.size = Pt(13)
        p_s.font.color.rgb = COLOR_MUTED
        p_s.space_before = Pt(10)

    # -------------------------------------------------------------------------
    # SLIDE 8: Data Quality Validation & Z-Score Anomaly Detection
    # -------------------------------------------------------------------------
    slide8 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide8)
    add_header(slide8, "Data Quality Validation & Z-Score Detection", "Chapter III — Quality Engine")

    # Left Box: 3 Validation Stages
    c_val1 = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0))
    c_val1.fill.solid()
    c_val1.fill.fore_color.rgb = COLOR_CARD
    c_val1.line.color.rgb = COLOR_CARD
    
    tf_v1 = c_val1.text_frame
    tf_v1.word_wrap = True
    p = tf_v1.paragraphs[0]
    p.text = "Multi-Stage Validation Checks"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    v_stages = [
        "1. Completeness Check: Ensures critical columns (`dataset_id`, `category`, `entity_name`, `variable_name`, `value`) exist without missing values.",
        "2. Consistency Check: Validates year ranges (1900–2100) and enforces business rules (e.g. Population counts cannot be negative).",
        "3. Statistical Anomaly Detection: Identifies extreme statistical outliers per variable using Z-Score analysis."
    ]
    for v in v_stages:
        p_v = tf_v1.add_paragraph()
        p_v.text = v
        p_v.font.size = Pt(12)
        p_v.font.color.rgb = COLOR_MUTED
        p_v.space_before = Pt(12)

    # Right Box: Z-Score Math & Scoring
    c_val2 = slide8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    c_val2.fill.solid()
    c_val2.fill.fore_color.rgb = COLOR_CARD
    c_val2.line.color.rgb = COLOR_CARD
    
    tf_v2 = c_val2.text_frame
    tf_v2.word_wrap = True
    p = tf_v2.paragraphs[0]
    p.text = "Z-Score Outlier Formula & Scoring"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT

    v_math = [
        "Z-Score Formula: Z = (X - μ) / σ",
        "• X = Data value | μ = Variable mean | σ = Standard deviation",
        "Threshold Rule (|Z| > 3.0): Based on the 99.7% Empirical Rule of normal distribution, values exceeding 3 standard deviations are flagged as extreme outliers.",
        "Quality Score Formula (0 - 100):",
        "Score = max(0, 100.0 - (MissingYears% * 0.2) - (AnomalyRate% * 2.0))"
    ]
    for vm in v_math:
        p_vm = tf_v2.add_paragraph()
        p_vm.text = vm
        p_vm.font.size = Pt(12)
        p_vm.font.color.rgb = COLOR_MUTED
        p_vm.space_before = Pt(10)

    # -------------------------------------------------------------------------
    # SLIDE 9: PostgreSQL Data Warehouse Schema
    # -------------------------------------------------------------------------
    slide9 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide9)
    add_header(slide9, "PostgreSQL Data Warehouse Schema", "Chapter III — Database Design")

    # Single Observations Table Schema
    c_schema = slide9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.733), Inches(5.0))
    c_schema.fill.solid()
    c_schema.fill.fore_color.rgb = COLOR_CARD
    c_schema.line.color.rgb = COLOR_CARD

    tf_sc = c_schema.text_frame
    tf_sc.word_wrap = True
    
    p = tf_sc.paragraphs[0]
    p.text = "Unified Fact Storage Table (`observations`):"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT

    fields = [
        "id (SERIAL PRIMARY KEY) — Auto-incrementing unique surrogate key.",
        "dataset_id (VARCHAR 100, INDEXED) — PSA OpenSTAT table identifier (e.g. '0012E4EVCP0').",
        "category (VARCHAR 100, INDEXED) — Sector category (e.g. 'Agriculture_Forestry_Fisheries').",
        "entity_name (VARCHAR 255) — Geographic region, province, or commodity entity name.",
        "variable_name (VARCHAR 255) — Measured metric indicator (e.g. 'Palay Production in Metric Tons').",
        "year (INTEGER, INDEXED) — Observation calendar year (e.g. 2023).",
        "period (VARCHAR 50) — Temporal breakdown interval (Quarter 1, Semester 1, Annual).",
        "value (DOUBLE PRECISION) — Standardized numerical measurement value.",
        "created_at (TIMESTAMPTZ) — Database record insertion timestamp."
    ]

    for f in fields:
        p_f = tf_sc.add_paragraph()
        p_f.text = "• " + f
        p_f.font.size = Pt(12)
        p_f.font.color.rgb = COLOR_MUTED
        p_f.space_before = Pt(8)

    # -------------------------------------------------------------------------
    # SLIDE 10: REST API & Containerized Web GUI
    # -------------------------------------------------------------------------
    slide10 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide10)
    add_header(slide10, "RESTful API & Web Management GUI", "Chapter III — Application Layer")

    # Left: Flask REST API
    c_api = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0))
    c_api.fill.solid()
    c_api.fill.fore_color.rgb = COLOR_CARD
    c_api.line.color.rgb = COLOR_CARD
    
    tf_api = c_api.text_frame
    tf_api.word_wrap = True
    p = tf_api.paragraphs[0]
    p.text = "Flask RESTful API (Port 5000)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT

    api_pts = [
        "GET /api/v1/health — Database & service connectivity status.",
        "GET /api/v1/datasets — List unique dataset codes & row counts.",
        "GET /api/v1/categories — List statistical domain categories.",
        "GET /api/v1/observations — Query observations with filtering (`?category=...&year=2023`) and pagination (`?page=1&per_page=50`)."
    ]
    for ap in api_pts:
        p_ap = tf_api.add_paragraph()
        p_ap.text = "• " + ap
        p_ap.font.size = Pt(12)
        p_ap.font.color.rgb = COLOR_MUTED
        p_ap.space_before = Pt(10)

    # Right: Django Web GUI
    c_gui = slide10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    c_gui.fill.solid()
    c_gui.fill.fore_color.rgb = COLOR_CARD
    c_gui.line.color.rgb = COLOR_CARD
    
    tf_gui = c_gui.text_frame
    tf_gui.word_wrap = True
    p = tf_gui.paragraphs[0]
    p.text = "Django Web GUI (Port 8000)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN

    gui_pts = [
        "Dashboard Overview: Real-time warehouse metrics, row counts, and category statistics.",
        "Data Explorer: Searchable, filterable observation tables with interactive pagination.",
        "Pipeline Control Center: On-demand execution triggers for Extraction, Transformation, Validation, and Loading.",
        "Dockerized Deployment: Configured in `docker-compose.yml`."
    ]
    for gp in gui_pts:
        p_gp = tf_gui.add_paragraph()
        p_gp.text = "• " + gp
        p_gp.font.size = Pt(12)
        p_gp.font.color.rgb = COLOR_MUTED
        p_gp.space_before = Pt(10)

    # -------------------------------------------------------------------------
    # SLIDE 11: Quantitative Evaluation & Thesis Results
    # -------------------------------------------------------------------------
    slide11 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide11)
    add_header(slide11, "Evaluation & Thesis Demonstration", "Chapter I & III — Scope & Evaluation")

    c_eval = slide11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.733), Inches(5.0))
    c_eval.fill.solid()
    c_eval.fill.fore_color.rgb = COLOR_CARD
    c_eval.line.color.rgb = COLOR_CARD

    tf_ev = c_eval.text_frame
    tf_ev.word_wrap = True
    
    p = tf_ev.paragraphs[0]
    p.text = "Empirical Validation Metrics:"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    eval_pts = [
        "Extraction Success Rate: 215 CSV files successfully extracted across 4 domain categories (Agriculture, Labor, Population, Mining).",
        "Data Quality Scoring: Multi-stage validation achieves automated quality scores (0-100) per dataset while filtering Z-score outliers.",
        "Time Savings vs. Manual Processing: Automated pipeline reduces dataset integration time from hours of manual spreadsheet editing to seconds of automated execution.",
        "API Throughput & Latency: Indexed PostgreSQL tables deliver sub-100ms response times for filtered observation queries."
    ]

    for ev in eval_pts:
        p_ev = tf_ev.add_paragraph()
        p_ev.text = "• " + ev
        p_ev.font.size = Pt(13)
        p_ev.font.color.rgb = COLOR_MUTED
        p_ev.space_before = Pt(12)

    # -------------------------------------------------------------------------
    # SLIDE 12: Conclusion & Q&A Slide
    # -------------------------------------------------------------------------
    slide12 = prs.slides.add_slide(blank_layout)
    set_slide_background(slide12)

    t_box12 = slide12.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.333), Inches(3.0))
    tf12 = t_box12.text_frame
    tf12.word_wrap = True
    
    p1 = tf12.paragraphs[0]
    p1.text = "THANK YOU!"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_ACCENT
    p1.font.name = 'Outfit'
    p1.alignment = PP_ALIGN.CENTER
    
    p2 = tf12.add_paragraph()
    p2.text = "ETL Pipeline Framework for Open Data Philippines Datasets"
    p2.font.size = Pt(18)
    p2.font.color.rgb = COLOR_TEXT
    p2.font.name = 'Inter'
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(16)

    p3 = tf12.add_paragraph()
    p3.text = "Questions & Feedback"
    p3.font.size = Pt(16)
    p3.font.color.rgb = COLOR_MUTED
    p3.font.name = 'Inter'
    p3.alignment = PP_ALIGN.CENTER
    p3.space_before = Pt(30)

    # Save Presentation
    output_path = "docs/THESIS_PRESENTATION.pptx"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prs.save(output_path)
    print(f"Successfully generated presentation deck: {output_path}")

if __name__ == "__main__":
    create_presentation()
