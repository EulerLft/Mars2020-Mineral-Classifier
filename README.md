# PIXL Data Processing Pipeline

This repository provides an automated, database-driven pipeline for processing and normalizing NASA PIXL (Planetary Instrument for X-ray Lithochemistry) data. The pipeline transforms raw Localized Full Spectra (RFS) and Elemental Abundance files into research-ready geochemical datasets. 

The system utilizes a SQLite registry to manage state, tracking thousands of files across different mission sols to ensure data integrity and prevent redundant processing. 


## Pipeline Overview
The pipeline follows a modular four-stage architecture: 
1. Inventory & Discovery (`inventory_manager.py`): 
    - Scans raw data directories, identifies unique Spacecreaft Clock (SCLK) identifiers, and registers new files into the SQLite database 
2. Metadata and Geochemical Data Extraction (`parsers.py`):
    - Parses NASA `rfs` files to isolate spatial coordinates (x, y, z), engineering tables (detector livetimes, temperature, etc.), raw spectra (detA/detB) and normalize counts per second (cps) for each individual measurement (PMC)
3. Chemical Transformation (`molar_transform.py`):
    - Maps elemental weight percentages from abundance files (`rqa/rqb/rqc`) to molar abundances and calculates fundamental geological ratios (e.g., Fe/Mn, Mafic Index, etc.)
4. Master Synthesis (`master_builder.py`):
    - Obtains key units used for petrology using oxide abundances and molar reatios.
    - Performs a high-precision horizontal merge of coordinates, timing, oxides, and molar data ubti a final "Geochem Master" CSV for each individual sample 

## System Requirements & Setup
The pipeline is built with Pyhton 3.x and requires the following libraries: 
- pandas 
- numpy 
- sqlite3
- os 
- glob

files from the [PDS Geosciences website](https://pds-geosciences.wustl.edu/m2020/urn-nasa-pds-mars2020_pixl/).

## Directory Structure
To maintain relative pathing, local environments must be organized as follows: 

```
PIXL_2/
├── PIXL_pipeline_registry.db   # This file
├── README.md                   # This file
├── .gitignore                  # Preents temporary files from being saved
├── refs/ 
    └── molar_table.csv         # Reference: molar masses and n-ratios 
├── src/                        # All .py logic files
    └── inventory_manager.py    # Update the inventory files and tables 
    └── mapping_tools.py        # Create 2D scatter plot scans with custom colours, colourbars, grids and axes labels
    └── master_builder.py       # Merges all tables itno final master dataset, and applies geochemical rules
    └── mineral_classifier.py   # Use the goechem files to classify shot by shot, create executive summaries and generate mapping.csv files and JSON files 
    └── molar_transform.py      # Converts weights % from 'rqa/rqb/rqc' files to molar abundances
    └── parsers.py              # Splits raw NASA 'rfs' files into SCLK/PMC/Spectra
    seed_mineral_rules.py       # Create mineral rules tables 
    └── assets                  #
        └── nav_01_jezero_crater_wide.JPG
        └── nav_02_crater_floor_campaign.JPG
        └── nav_02a_seitah_zoom.JPG
        └── nav_02b_maaz_zoom.JPG
        └── nav_03_delta_front_campaign.JPG
        └── nav_03a_shenandoah_zoom.JPG
        
├── data/
    └── raw/                    # Place original .csv files from PDS/PIQUANT output here
        └── spectra/            # NASA raw 'rfs' files (.csv)
        └── abundances/         # NASA processed 'rqa/rqb/rqc' files (.csv)
    └── processed/              # All split, transformed, and generated files (e.g., molar, geochem, etc.)
    └── analysis/               # JSON and mapping.csv files used to generate maps
```

# Pipeline Hierarchy

### Stage 1: Extraction & Data Cleaning (`parsers.py`)
- Input: Raw NASA `rfs` files
- Action: Break the embedded CSV into separated tables
- Output: Foundational files (`SCLK`, `PMC`, `DetA`, `DetB`)

### Stage 2: Geochemical Transformation (`ox%_to_molar.py`)
- Input: Elemental oxide weight percentages (from PIQUANT output/NASA PDS website) + Molar Reference table.
- Action: Convert weight percentages (e.g., $SiO_2 %$) into molar abundances ($Si$ moles)
- Output: Molar tables and geological indicators (mafic index and Fe/Mn ratio)

### Stage 3: Integration (`master_file_builder.py`)
- Input: `PMC`, `SCLK`, `oxide tables`, and `molar tables`
- Action: Merge into a single master CSV, and calculate oxide scores (mafic vs. felsic balance)
- Output: Final dataset used for plotting and mineral identification 


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

## Database Registry 
The `PIXL_pipeline_registry.db` contains three tables that act as the centre of operations. 

1. `file_inventory`: Records every file associated with the project, whether it is a raw input from NASA or a processed output from our scripts 
    - sclk: 10-digit unique identifier of the sample 
    - file_type: categorizes the file (e.g., `raw_spectra`, `rqa_molar`, `metadata`, etc.)
    - file_path: the absolute or relative path to the file on the directory
    
2. `processing_status`: A high-level dashboard that the scripts use to determine the next task
    - raw_spectra_ready: Set to `1` once `inventory_manager.py` find the spectrum file. 
    - metadata_ready: Set to `1` once `parsers.py` has extracted coordinates and livetimes. 
    - molar_ready: Set to `1` once `molar_transform.py` finishes chemical conversions.
    - is_processed: The final flag; set `1` once `master_builder.py` exports the final geochem master .csv
    
3. `sample_registry`: Anchor for the pipeline, mapping the technical identifiers to a mission-specific context that is human-readble
    - sclk: 10-digit code used as the primary key across the entire pipeline
    - nominal_sol: The martian day (Sol) on which the measurement was taken. This is critical for temporal analysis and cross-referencing with the Mars2020 mission timeline
    - targt_name (Optional): The specific rock or soil target name assigned by the Mars2020 Team 
    
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
| **.rbq** | Reduced Bulk Quantitative | The "Bulk" version of the scan. | **Averaging:** Provides the average composition of the entire area. |

## The Naming Key
Every file follows a standard NASA string. To navigate this repository, look for the SCLK bridge:
ps__0125_0678032243_000rfs...
•	Sample ID: ps__0125 (Human-readable site name)
•	Linking Key: 0678032243 (10-digit SCLK; use this to match a .rfs file to its corresponding .rqc results).



<b>Technical Note on RFS Files</b> \
RFS files contain multiple tables within a single CSV. This pipeline extracts:
- PMC: Spatial coordinates (x, y, z) in the PIXL base frame.
- SCLK: Housekeeping data including live_time for normalization.
- Detectors A & B: Calibrated energy spectra.

3. Data Product Reference (NASA PIXL)
For a full breakdown of PIXL calibrated products, refer to the [PIXL User Guide](https://pds-geosciences.wustl.edu/m2020/urn-nasa-pds-mars2020_pixl/document/pixl_user_guide.pdf).

| Product ID | Description |
| :--- | :--- |
| **E08** | Housekeeping Frame |
| **ENA** | Histogram Normal A |
| **ENB** | Histogram Normal B |
| **EDA** | Histogram Dwell A |
| **EDB** | Histogram Dwell B |
| **EPN** | PseudoIntensity Normal |
| **EPD** | PseudoIntensity Dwell |
| **EMA** | Hist Max Val A |
| **EMB** | Hist Max Val B |
| **EBA** | Hist Bulk Sum A |
| **EBB** | Hist Bulk Sum B |
| **E34** | Scan Log |
| **ESO** | MCC OLM TRN Estimate |
| **ESF** | MCC SLI Estimate |
| **EDR** | MCC Image |
| **RBQ** | Histogram Bulk Quantitative Measurement |
| **RBS** | Histogram Bulk Summed Spectrum A/B |
| **RCI** | MCC Context Image |
| **RCM** | MCC Context Image w/ Mark-up |
| **RCS** | Rock Component Sums |
| **RFS** | Localized Full Spectra |
| **RMS** | Histogram Bulk Max Value A/B |
| **RPM** | PseudoIntensity Plots/Maps |
| **RXL** | Drift Corrected X-ray Beam Locations |
| **R08** | Engineering Value Housekeeping Frame |

<b>Calibrated Products</b>
The PIXL calibrated data products are calibrated products. These products are reported in physical units. 
All calibrated products can be found in the mars2020_pixl: data_processed collection:

- 1. MCC CONTEXT IMAGE (RCI) - Images taken by the Micro-Context Camera (MCC) at the center location of the scan, typically with one captured before the scan starts and another after the scan completes. The image is annotated with the X-ray shot locations to allow PIXL scientists to more easily associate each X-ray histogram with the corresponding position on a target.
  
- 2. ENGINEERING VALUE HOUSEKEEPING FRAME (R08) - The HK Frame product is an ASCII CSV table that records the state of the instrument (e.g. temperatures, voltages,
currents etc.) at the time of each observation. The R08 product contains the data converted from Digital Number to Physical Unit. Each data product is a collection of records from a single PIXL scan.

- 3. DRIFT CORRECTED X_RAY BEAM LOCATIONS (RXL) - A CSV file containing a set of (x, y, z) positions in the PIXL base frame of each X-ray Beam location on the target surface and the corresponding location in the MCC image (as pixel coordinates), corrected for thermal drift of the robotic arm position or other unexpected motion.

- 4. HISTOGRAM BULK MAX VALUE SPECTRUM (RMS) - Maximum Value Spectrum (maximum measured value for each channel in the set of spectra for this target) with energy calibration. The product format is a .MSA file containing a header and a series of rows representing the energy-calibrated bulk sum spectra. Each row contains two integer values (comma-delimited), representing intensity at each channel for each detector.

- 5. HISTOGRAM BULK SUMMED SPECTRUM (RBS) - Bulk Sum Spectrum (one for each target, all PIXL point spectra for this target summed) with energy calibration. The product format is an MSA file containing a header and a series of rows representing the energy-calibrated bulk sum spectra. Each row contains two integer values (commadelimited), representing intensity at each channel for each detector.

- 6. LOCALIZED FULL SPECTRA (RFS) - XRF spectrum for each measured location on the target with energy calibration, spatial location, and pixel location in context image. The product format is CSV.

- 7. MCC CONTEXT IMAGE WITH MARKUP (RCM) - Annotated images showing X-ray beam locations as an overlay, with the (x, y) pixel positions of each X-ray beam location marked on the overlay. The images are stored as a multi-layer .TIF file, with the first layer containing the greyscale MCC context image and the second layer containing an image with X-ray bean locations (pixel value 255).

- 8. PSEUDOINTENSITY PLOTS/MAPS (RPM)- The pseudointensity values are generated from on-board processing algorithms, which calculate spectral backgrounds, subtract the background, and calculate the integrated intensity for a region 