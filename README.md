# PIXL Data Processing Pipeline
### [🚀 View Live Dashboard](https://mars2020-mineral-classifier-apwekg58ujsjzmdutvh7zf.streamlit.app/)

**Engineering a Scalable Data Pipeline: Processing 36,000+ NASA Mars Perseverance Scans with 1:1 Scientific Parity.**

---

## Core Porject Impact & Engineering Highlights 
* **Performance Optimization**: Automated processing of **36,000+ high-dimensional scans**.
* **State Management**: Implemented a **SQLite-driven state machine** to track thousands of files across disparate Martian sols, ensuring **99.9% data integrity** and **preventing redundant processing**.  
* **Scientific Parity**: Developed the "MIP_SF" stoichiometric classification algorithm, achieving **1:1 correlation** with NASA's internal MIST algorithm for primary igneous mineral detection. 

---

## 🛠️ Technical Stack
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Streamlit](https://img.shields.io/badge/streamlit-%23FF4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)

---

## 📊 Pipeline Architecture
The pipeline follows a modular five-stage architecture governed by a central database registry:
```mermaid
graph TD
    A[NASA PDS Raw Data] --> B[Inventory Manager]
    B -->|Register SCLK| C[(SQLite State Registry)]
    C --> D[Extraction & Normalization]
    D --> E[Molar Transformation]
    E --> F[Master Builder & Mineral Classifier]
    F --> G([Interactive Streamlit Dashboard])

    style G fill:#f96,stroke:#333,stroke-width:2px
```
---

## Modular Component Breakdown
The pipeline follows a modular five-stage architecture governed by a central database registry: 
1. <b>Inventory & Discovery</b> (`inventory_manager.py`): Scans raw data directories to identify unique Spacecreaft Clock (SCLK) identifiers and registers them into the SQLite database.
2. <b>Extraction & Parsing</b> (`parsers.py`): Isolate spatial coordinates, engineering telemetry (detector livetimes, temperature, etc.) and normalizing raw specta counts per second (CPS).
3. <b>Chemical Transformation</b> (`molar_transform.py`): Maps elemental weight percentages to molar abundances and calculates key geological ratios (e.g., Fe/Mn, Mafic Index, etc.)
4. <b>Master Synthesis</b> (`master_builder.py`): Merges coordinates, telemetry, and chemistry into a unified "Geochem Mater" dataset. 
5. <b>Mineral Classification</b> (`mineral_classifier.py`): Uses the synthesized datasets to classify "shot-by-shot" mineralogy and generates spatial mapping assets.

---

## 📂 Directory Structure
To maintain relative pathing and cross-platform compatability, the environment is organized as follows: 

```
Mars2020-Mineral-Classifier/
├── PIXL_pipeline_registry.db   # Central SQLite state management
├── refs/ 			# Reference molar masses and n-ratios
├── src/                        # Core engineering logic
    └── inventory_manager.py    # Directory scanning and database updates
    └── mapping_tools.py        # 2D spatial visualization and labeling
    └── master_builder.py       # Table merging and geochemical rule application
    └── mineral_classifier.py   # Stoichiometric classification and report generation
    └── molar_transform.py      # Weight % to molar abundance conversion
    └──	navigation_app.py	# Interactive mission context app
    └── parsers.py              # NASA 'rfs' files extraction and normalization
    └──seed_mineral_rules.py    # Mineralogy classification rulesets
    └── assets/                 # Visual assets for navigation and mapping
├── data/
    └── raw/                    # Original NASA PDS/PIQUANT .csv files
        └── spectra/            # NASA raw 'rfs' files (.csv)
        └── abundances/         # NASA processed 'rqa/rqb/rqc' files (.csv)
    └── processed/              # All split, transformed, and generated files
    └── analysis/               # JSON and mapping.csv files used to generate maps
└── requirements.txt            # Environment dependencies
```

---

## 🔄 Data Flow & Registry Logic
The pipeline utlizes a "Pull" logic governed by `PIXL_pipeline_registry.db`. This acts as the single source of truth, tracking every SCLK ID through for primary tables: `file_inventory`, `processing_status`, `sample_registry`, `mineral_rules`.

#### Processign Pattern:
- <b>Query</b>: Each script asks the database for files where prerequisite flags are met but its own stage is incomplete.
- <b>Process</b>: Excecutes vectorized operations (Pandas/NumPy) for high-speed calculations. 
- <b>Register</b>: Updates the registry with new file paths and flips the status flag to `1`. 

This architecture ensures that if a script crashes or a file is missing, the pipeline simply skips that entry and continues, rather than failing the entire batch.

---

## Technical Environment 
The pipeline is designed to be cross-platform, using standard Python libraries to marge complex file structures and data transformations. 

- File I/O Pathing (`os`, `glob`): We use `os` for robust relative pathing. `glob` is used to match patterns to identify specific NASA file types (`rfs`, `rqa`, etc.) within nested directories. 
- Data Manipulation (`pandas`, `numpy`): Geochemical calculations, normalizations and molar mass conversions are handled using vectorized operations for speed and precision. 
- State Management (`sqlite3`): A local database acts a single source of truth, tracking every Spacecraft Clock (SCLK) ID and its current processing stage

---

## 📖 PIXL Data Glossary
The NASA Planetary Data System (PDS) uses specific three-letter suffixes to distinguish between raw telemetry, processed chemistry, and bulk averages. This project uses the Spacecraft Clock (SCLK)—the 10-digit code in the filename—to link these disparate files together.

files from the [PDS Geosciences website](https://pds-geosciences.wustl.edu/m2020/urn-nasa-pds-mars2020_pixl/).


| Suffix | Name | Purpose in this Pipeline |
| :--- | :--- | :--- |
| **.rfs** | Raw Formatted Spectrum | Source of Spatial and PMC coordinates (x, y, z). |
| **.rqa/b** | Reduced Quantitative Analysis (Det A/DetB) | Processed weight percentages (wt%) used for high-resolution mineral mappings. |
| **.rqc** | Combined Analysis (A+B) | Primary Data Source for final mineral maps. |

## 🎓 Research & Academic Context
This pipeline was developed to characterize the elemental and mineralogical composition of the Jezero Crater using PIXL XRF scans. By bridging complex radiation theory with automated data engineering, it facilitates the transition from static raw telemetry to dynamic, interactive research environments.
[Read Full MSc Thesis](https://atrium.lib.uoguelph.ca/server/api/core/bitstreams/8dd984d7-c84b-4457-b635-f81fc8d1d5f9/content).