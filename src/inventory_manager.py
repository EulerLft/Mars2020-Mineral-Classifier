# -*- coding: utf-8 -*-
"""
Edited on Tues Apr 28 13:00:34 2026

@author: salva
"""

import sqlite3
import os 
import glob

# --- PATH SETUP --- 
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
db_path = os.path.join(project_root, "PIXL_pipeline_registry.db")
processed_dir = os.path.join(project_root, "data", "processed")
raw_spectra_dir = os.path.join(project_root, "data", "raw", "spectra")
raw_abundance_dir = os.path.join(project_root, "data", "raw", "abundances")

# --- FILE CLASSIFICATION SETUP ---
# Maps a string found in the filename to a clean "file_type" for the DB 
FILE_TYPE_MAP ={
    'rfs': 'raw_spectra',
    'DetA_cps': 'DetA_cps',
    'DetB_cps': 'DetB_cps',
    'DetA': 'DetA', 
    'DetB': 'DetB',
    'PMC': 'PMC',
    'metadata': 'metadata',
    'rqa_molar': 'rqa_molar',
    'rqb_molar': 'rqb_molar',
    'rqc_molar': 'rqc_molar',
    'rqa': 'rqa',
    'rqb': 'rqb',
    'rqc': 'rqc'}

def get_file_details(filename):
    # Standard PIXL format is prefix_sol_sclk_type.csv
    # We remove the extension and split by underscore 
    parts = filename.replace(".csv", "").split("_")
    
    try: 
        # Sol is typically the second element (index 2)
        sol = int(parts[2])
        
        # SCLK is typically the fourth element (index 4)
        sclk = int(parts[3])
        
        # Check filename against our map to determine the type 
        f_type = "unknown"
        for key in FILE_TYPE_MAP:
            if key in filename:
                f_type = FILE_TYPE_MAP[key]
                break # STOP at the first match to respect priority
        return sclk, sol, f_type
    except (IndexError, ValueError):
        # This handles cases where the filename doesn't match the expected pattern 
        return None, None, "unknown"

def scan_folders():
    # Connect to the database 
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Gather every .csv file from all three directories 
    all_files = glob.glob(os.path.join(raw_spectra_dir, "*.csv")) + \
                glob.glob(os.path.join(raw_abundance_dir, "*.csv")) + \
                glob.glob(os.path.join(processed_dir, "*.csv"))
                
    print(f"Found {len(all_files)} total files across all directories...")
    
    for f_path in all_files:
        f_name = os.path.basename(f_path)
        sclk, nominal_sol, f_type = get_file_details(f_name)
        
        # Debugging print statement 
        print(f"Checking: {f_name} -> SCLK: {sclk}, Type: {f_type}")
        
        if sclk and f_type != "unknown":
            # Update the 'file_inventory' table
            cursor.execute("""
                           INSERT OR REPLACE INTO file_inventory (sclk, file_name, file_type, file_path)
                           VALUES (?, ?, ?, ?)
            """, (sclk, f_name, f_type, f_path))
            
            # Initialize the status row if it doesn't exist
            cursor.execute("INSERT OR IGNORE INTO processing_status (sclk) VALUES(?)", (sclk,))
            
            # Flip the flag based on the file type found 
            if f_type == "raw_spectra":
                cursor.execute("UPDATE processing_status SET raw_spectra_ready = 1 WHERE sclk = ?", (sclk,))
            elif f_type in ['rqa', 'rqb', 'rqc']:
                cursor.execute("UPDATE processing_status SET raw_abundance_ready = 1 WHERE sclk =?", (sclk,))
            elif f_type in ['rqa_molar', 'rqb_molar', 'rqc_molar']:
                cursor.execute("UPDATE processing_status SET molar_ready = 1 WHERE sclk=?", (sclk,))
            
            cursor.execute("""
                           INSERT OR IGNORE INTO sample_registry (sclk, nominal_sol)
                           VALUES (?, ?)
                           """, (sclk, nominal_sol))
            
    # Commit changes and close 
    conn.commit()
    conn.close()
    print("Database sync complete. Inventory and Status tables updated.")
    
# Run function when executed
if __name__ == "__main__":
    scan_folders()
            
            