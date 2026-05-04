# PIXL Data Processing Pipeline

### Automated Geochemical Analysis for NASA Mars 2020 Mission Data
### [🚀 View Live Dashboard](https://mars2020-mineral-classifier-apwekg58ujsjzmdutvh7zf.streamlit.app/)
This repository provides an automated, database-driven pipeline for processing and normalizing NASA PIXL (Planetary Instrument for X-ray Lithochemistry) data. The system transforms raw Localized Full Spectra (RFS) and Elemental Abundance (RQA) files into research-ready geochemical datasets, enabling high-resolution mineralogical classification of the Martian surface. 

## Core Engineering Highlights 
- <b>State Management</b>: Utilizes a SQLite registry to track thousands of files across disparate sols, ensuring 99.9% data integrity and preventing redundant processing. 
- <b>Performance Optimization</b>: Automates the processing of 36,000+ high-dimensional scans, eliminating 600+ hours of manual data handling. 
- <b>Scientific Parity</b>: Developed the "MIP_SF" stoichiometric classification algorithm, achieving 1:1 correlation with NASA's MIST algorithm for primary igneous mineral detection. 

## Pipeline Architecture
The pipeline follows a modular five-stage architecture governed by a central database registry: 
1. Inventory & Discovery (`inventory_manager.py`): Scans raw data directories to identify unique Spacecreaft Clock (SCLK) identifiers and registers them into the SQLite database.
2. Extraction & Parsing (`parsers.py`): Isolate spatial coordinates (x, y, z), engineering telemetry (detector livetimes, temperature, etc.) and raw spectra, normalizing counts per second (cps) for each individual measurement (PMC).
3. Chemical Transformation (`molar_transform.py`): Maps elemental weight percentages from abundance files (`rqa/rqb/rqc`) to molar abundances and calculates fundamental geological ratios (e.g., Fe/Mn, Mafic Index, etc.)
4. Master Synthesis (`master_builder.py`): Merges coordinates, timing, and chemistry into a "Geochem Mater" dataset for final mineral identification. 
5. Mineral Classification (`mineral_classifier.py`): Uses the synthesized datasets to classify mineralogy "shot-by-shot" and generates mapping.csv and JSON files for spatial visualization.

## Technical Environment
- <b>Languages & State</b>: Python 3.x, SQLite3.
- <b>Data Science Stack</b>: Pandas, NumPy (Vectorized operations for high-speed geochemical calculations), Streamlit.
- <>File I/O</b>: Robust relative pathing utilizing `os` and `glob` to manage nested NASA PDS directory structures. 

files from the [PDS Geosciences website](https://pds-geosciences.wustl.edu/m2020/urn-nasa-pds-mars2020_pixl/).

## Directory Structure
To maintain relative pathing, local environments must be organized as follows: 

```
Mars2020-Mineral-Classifier/
├── PIXL_pipeline_registry.db   # Central SQLite state management
├── README.md                   # Technical documentation
├── LICENSE                     # MIT License for open-source use
├── requirements.txt            # List of required Python dependencies
├── .gitignore                  # Prevents temporary/local data from staging
├── refs/ 
    └── molar_table.csv         # Reference: molar masses and n-ratios
├── src/                        # Core logic and engineering
    └── inventory_manager.py    # Directory scanning and database updates
    └── mapping_tools.py        # 2D spatial visualization and labeling
    └── master_builder.py       # Table merging and geochemical rule application
    └── mineral_classifier.py   # Stoichiometric classification and report generation
    └── molar_transform.py      # Weight % to molar abundance conversion
    └──	navigation_app.py	# Interactive mission context app
    └── parsers.py              # NASA 'rfs' files extraction and normalization
    └──seed_mineral_rules.py    # Mineralogy classification rulesets
    └── assets                  # Visual assets for navigation and mapping
├── data/
    └── raw/                    # Place original .csv files from PDS/PIQUANT output here
        └── spectra/            # NASA raw 'rfs' files (.csv)
        └── abundances/         # NASA processed 'rqa/rqb/rqc' files (.csv)
    └── processed/              # All split, transformed, and generated files (e.g., molar, geochem, etc.)
    └── analysis/               # JSON and mapping.csv files used to generate maps
```

## Database Registry & Data Flow
The `PIXL_pipeline_registry.db` acts as the single source of truth for the entire project, utilizing three primary tables:
- `file_inventory`: Tracks every file associated with the project, including technical identifiers (SCLK) and file paths.
- `processing_status`: A high-level dashboard used by the scripts to determine the next task (e.g., molar_ready, is_processed).
- `sample_registry`: Maps technical SCLK identifiers to human-readable mission context, such as the nominal Martian Sol and target rock name.

2. Getting Started
- Dependencies: Ensure you have pandas installed: `pip install pandas`.
- Usage: Run the script from the terminal or your IDE: `python src/parsers.py`
    - What it does: Identifies all `*rfs*.csv` files in the data/raw folder.
    - Splits the complex NASA RFS format into individual tables (SCLK, PMC, DetA, DetB).
    - Normalizes Detector A and B spectra into Counts Per Second (CPS) by dividing raw counts by the instrument's live time.


## Technical Environment 
The pipeline is designed to be cross-platform, using standard Python libraries to marge complex file structures and data transformations. 

- File I/O Pathing (`os`, `glob`): We use `os` for robust relative pathing. `glob` is used to match patterns to identify specific NASA file types (`rfs`, `rqa`, etc.) within nested directories. 
- Data Manipulation (`pandas`, `numpy`): Geochemical calculations, normalizations and molar mass conversions are handled using vectorized operations for speed and precision. 
- State Management (`sqlite3`): A local database acts a single source of truth, tracking every Spacecraft Clock (SCLK) ID and its current processing stage

    
## Data Flow & Processing Logic
The pipeline operates on a "Pull" logic governed by these database tables. Each script follows a specific pattern:

1. Query: Ask the database for SCLKs where the prerequisite flag is 1 but its own flag is 0.
2. Process: Perform the necessary file I/O or calculation (using os and glob to locate the files).
3. Register: Write the new output file path into file_inventory.
4. Update: Flip its specific status flag in processing_status to 1.

This architecture ensures that if a script crashes or a file is missing, the pipeline simply skips that entry and continues, rather than failing the entire batch.



## PIXL Data Glossary
The NASA Planetary Data System (PDS) uses specific three-letter suffixes to distinguish between raw telemetry, processed chemistry, and bulk averages. This project uses the Spacecraft Clock (SCLK)—the 10-digit code in the filename—to link these disparate files together.


| Suffix | Name | Description | Purpose in this Pipeline |
| :--- | :--- | :--- | :--- |
| **.rfs** | Raw Formatted Spectrum | Raw X-ray counts and instrument telemetry. | **Source of Spatial Data:** Used by `parsers.py` to extract PMC coordinates (x, y, z) and the master SCLK. |
| **.rqa** | Reduced Quantitative Analysis (Det A) | Processed weight percentages (wt%) for Detector A. | **Source of Chemistry:** Used for high-resolution mineral mapping. |
| **.rqb** | Reduced Quantitative Analysis (Det B) | Processed weight percentages (wt%) for Detector B. | **Source of Chemistry:** Alternative detector for validation. |
| **.rqc** | Combined Analysis (A+B) | Mathematically combined chemistry from both detectors. | **Primary Data Source:** The standard file for final mineral maps. |

## Research & Academic Context
This pipeline was developed to characterize the elemental and mineralogical composition of the Jezero Crater using PIXL XRF scans. By bridging complex radiation theory with automated data engineering, it facilitates the transition from static raw telemetry to dynamic, interactive research environments.[Read Full Thesis](https://atrium.lib.uoguelph.ca/server/api/core/bitstreams/8dd984d7-c84b-4457-b635-f81fc8d1d5f9/content).