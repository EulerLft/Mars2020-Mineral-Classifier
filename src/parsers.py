# -*- coding: utf-8 -*-
"""
Updated on Tue Apr 28 2026
@author: salva
"""

import os
import pandas as pd
import sqlite3
from inventory_manager import scan_folders

# --- PATH SET UP --- 
# script_dir : Get the folder where this script is currently saved
# project_root : Go up one level to the main project folder "project root" 
# raw_dir : define raw_spectra directory relative to the "project root"
# processed_dir : define processed_dir directory relative to the "project root"
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
db_path = os.path.join(project_root, "PIXL_pipeline_registry.db")
processed_dir = os.path.join(project_root, "data", "processed")

# AUTOMATIC REFRESH 
# this step ensures that any new files in the folders are added to the DB before we start 
print("Refreshing file inventory ...")
scan_folders()

# DATABASE SEARCH 
# query database for files that are ready but not parsed 
def get_pending_tasks():
    conn = sqlite3.connect(db_path)
    query = """
    SELECT ps.sclk, inv.file_path
    FROM processing_status ps 
    JOIN file_inventory inv 
    ON ps.sclk = inv.sclk
    WHERE ps.raw_spectra_ready = 1
        AND ps.metadata_ready = 0
        AND inv.file_type = 'raw_spectra'
    """
    # Using pandas to read the SQL query results as a list of tasks 
    df_tasks = pd.read_sql_query(query, conn)
    conn.close()
    return df_tasks

tasks = get_pending_tasks()

if tasks.empty:
    print("No new raw spectra files pending processing.")
else: 
    print(f"Found {len(tasks)} new files to process.")

# Initialize a counter
processed_count = 0

# PROCESSING LOOP 
# Iterate through each file identified by the database 
for index, row in tasks.iterrows():
    sclk = row['sclk']
    csv_file = row['file_path']
    
    # Extract the prefix for naming output files (e.g., 'ps__0125_0678032243')
    file_name_prefix = os.path.basename(csv_file).split('rfs')[0].rstrip('_')

    # PARSING LOGIC 
    # Determine the column count to handle varying row lengths in  NASA RFS files 
    with open(csv_file, 'r') as temp_f:
        lines = temp_f.readlines()
        max_cols = max([len(l.split(",")) for l in lines])
    
    # Generate column names (names will be 0, 1, 2, ..., maximum columns - 1)
    column_names = [f'col_{i}' for i in range(max_cols)]
    df = pd.read_csv(csv_file, header=None, delimiter=',', names=column_names, engine='python');    
    
    #Get the base name without extension (.e.g, ps__0125_0678032243_000rfs__00417120483005510093___j02.csv)
    base_name = os.path.splitext(os.path.basename(csv_file))[0] 
    
    # Split by underscore. Double underscores will create empty strings in the list
    # Rejoin the first 4 parts to ensure we capture 'ps', '', '0125', and the SCLK (10-digit code)
    parts = base_name.split('_')
    file_name_prefix = '_'.join(parts[:4])    

    # Assign the first row as headers and reset index
    df.columns = df.iloc[0]
    df = df[1:]
    df.reset_index(drop=True, inplace=True)

    # Find all row indices where the headers appear 
    pmc_hits = df[df.iloc[:, 0] == 'PMC'].index.tolist()
    det_a_hits = df[df.iloc[:, 0] == 'A_1'].index.tolist()
    det_b_hits = df[df.iloc[:, 0] == 'B_1'].index.tolist()
    
    # Anchor to the first instance of each to capture the primary scan block 
    pmc_start = pmc_hits[0]
    det_a_start = det_a_hits[0]
    det_b_start = det_b_hits[0]
    
    # Extract metadata (everything from row 0 to the first PMC header)
    df_SCLK = df.loc[0 : pmc_start-1].copy()
    df_SCLK = df_SCLK.loc[:, :'OFFSET_B']
    
    # Extract PMC (from first PMC header to first DetA header)
    df_PMC = df.loc[pmc_start : det_a_start-1].copy()
    df_PMC.columns = df_PMC.iloc[0]
    df_PMC = df_PMC[1:].reset_index(drop=True)
    df_PMC = df_PMC.loc[:, :'z']
    
    # Extract DetA (from first DetA header to first DetB header)
    df_detA = df.loc[det_a_start : det_b_start-1].copy()
    df_detA.columns = df_detA.iloc[0]
    df_detA = df_detA[1:].reset_index(drop=True)
    
    # Extact DetB (symmetric length as detA, ignore appended footers)
    num_rows = len(df_detA)
    df_detB = df.loc[det_b_start : det_b_start + num_rows].copy()
    df_detB.columns = df_detB.iloc[0]
    df_detB = df_detB[1:].reset_index(drop=True)
    
    # Save as .csv
    df_SCLK.to_csv(os.path.join(processed_dir, f'{file_name_prefix}_metadata.csv'), index=False)
    df_PMC.to_csv(os.path.join(processed_dir, f'{file_name_prefix}_PMC.csv'), index=False)    
    df_detA.to_csv(os.path.join(processed_dir, f'{file_name_prefix}_DetA.csv'), index=False)
    df_detB.to_csv(os.path.join(processed_dir, f'{file_name_prefix}_DetB.csv'), index=False)    
    
    # Apply Normalization 
    
    # Ensure detector and livetime data are numeric to prevent NaN errors
    # errors='coerce' turns non-numbers into NaN, which we fill with 0
    df_detA_num = df_detA.apply(pd.to_numeric, errors='coerce').fillna(0)
    df_detB_num = df_detB.apply(pd.to_numeric, errors='coerce').fillna(0)
    
    livetime_A = pd.to_numeric(df_SCLK['live_time_A'], errors='coerce')
    livetime_B = pd.to_numeric(df_SCLK['live_time_B'], errors='coerce')
    
    # Calcualte CPS (count per second) using broadcasting 
    # divide each row by its corresponding livetime
    df_detA_cps = df_detA_num.div(livetime_A, axis=0)
    df_detB_cps = df_detB_num.div(livetime_B, axis=0)

    
    # Save the normalized CPS results to the processed directory
    df_detA_cps.to_csv(os.path.join(processed_dir, f'{file_name_prefix}_DetA_cps.csv'), index=False)
    df_detB_cps.to_csv(os.path.join(processed_dir, f'{file_name_prefix}_DetB_cps.csv'), index=False)
    
    # DATABASE BOOKKEEPING
    # Flip the metadata_read flag to 1 so this file is never processed again 
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE processing_status SET metadata_ready = 1 WHERE sclk = ?", (sclk,))
    conn.commit()
    conn.close()
    
    processed_count += 1 
    
    print(f"Successfully processed file {file_name_prefix} and updated database flags")
    
    
# Final completion message 
print('-' * 30)
print(f'COMPLETED: {processed_count} NASA RFS files processed.')
print(f"Output saved to: {processed_dir}")
print('-' * 30)
    