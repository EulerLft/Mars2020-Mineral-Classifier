# -*- coding: utf-8 -*-
"""
Updated on Tues April 28 2026
@author: salva
"""

import pandas as pd
import numpy as np 
import os 
import sqlite3
from inventory_manager import scan_folders


# --- PATH SETUP ---
# Get the folder where this script is currently saved and the project root folder
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
db_path = os.path.join(project_root, "PIXL_pipeline_registry.db")

# Define paths relative to the project root 
refs_dir = os.path.join(project_root, "refs")
raw_abundances_dir = os.path.join(project_root, "data", "raw", "abundances")
processed_dir = os.path.join(project_root, "data", "processed")
molar_table_path = os.path.join(refs_dir, "molar_table.csv")

# AUTOMATIC REFRESH
print("Refreshing file inventory ...")
scan_folders()

def get_pending_abundances():
    """Query database for abundance files where molar is not yet ready"""
    conn = sqlite3.connect(db_path)
    query = """
    SELECT ps.sclk, inv.file_path, inv.file_name 
    FROM processing_status ps
    JOIN file_inventory inv
        ON ps.sclk = inv.sclk
    WHERE ps.raw_abundance_ready = 1
        AND metadata_ready = 1
        AND molar_ready = 0
        AND inv.file_type IN ('rqa', 'rqb', 'rqc')
    """
    df_tasks = pd.read_sql_query(query, conn)
    conn.close()
    return df_tasks

def run_molar_transform():
    # Load molar reference table 
    # Using iloc[:, 1:] if the table has unnamed index column 
    df_ref = pd.read_csv(molar_table_path)
    if 'Unnamed: 0' in df_ref.columns:
        df_ref = df_ref.drop(columns=['Unnamed: 0'])

    tasks = get_pending_abundances()

    if tasks.empty:
        print("No new abundance files pending molar transformation.")
        return 
    
    print(f"Found {len(tasks)} files to transform")
    
    for index, row in tasks.iterrows():
        sclk = row['sclk']
        raw_path = row['file_path']
        raw_name = row['file_name']
        
        print(f"Processing: {raw_name}")
        
        # Load the raw abundance data (PDS processed oxide/PIQUANT output)
        df_raw = pd.read_csv(raw_path)
        
        # Prepare the output molar DataFrame for results and copy the PMC column  
        df_molar = pd.DataFrame()
        df_molar['PMC'] = df_raw.iloc[:, 0]
        
        for _, row in df_ref.iterrows():
            oxide_name = row['element oxide']   # e.g., "SiO2_wt%"
            m_mass = row['molar (g/mol)']       # e.g., "60.1 g/mol"
            n_ratio = row['n_ratio']            # e.g., 1
            
            if oxide_name in df_raw.columns:
                # Vectorized math: (Weight % / Molar Mass) * n_ratio
                moles_col = oxide_name.replace('_wt%', ' (moles)')
                df_molar[moles_col] = (df_raw[oxide_name] / m_mass) * n_ratio
                
                # Look for corresponding error column
                error_col_name = f"{oxide_name}_err"
                if error_col_name in df_raw.columns:
                    moles_err_col = f"{moles_col}_err"
                    
                    # Apply linear transform to the absolute error 
                    df_molar[moles_err_col] = (df_raw[error_col_name] / m_mass) * n_ratio
         
        # Calculate Ratio (Fe/Mn) and propagate error 
        if 'FeO-T (moles)' in df_molar.columns and 'MnO (moles)' in df_molar.columns:
            df_molar['Fe/Mn'] = df_molar['FeO-T (moles)'] / df_molar['MnO (moles)']
            if 'FeO-T (moles)_err' in df_molar.columns and 'MnO (moles)_err' in df_molar.columns:
                df_molar['Fe/Mn_err'] = df_molar['Fe/Mn'] * np.sqrt(
                    (df_molar['FeO-T (moles)_err'] / df_molar['FeO-T (moles)'])**2 +
                    (df_molar['MnO (moles)_err'] / df_molar['MnO (moles)'])**2
                    )
                
        # Mafic Condition: (Fe + Mg + Ca)/Si
        # Check if columns exist to prevent crashes
        required_mafic = ['FeO-T (moles)', 'MgO (moles)', 'CaO (moles)', 'SiO2 (moles)']
        if all(col in df_molar.columns for col in required_mafic):
            sum_mafic = df_molar['FeO-T (moles)'] + df_molar['MgO (moles)'] + df_molar['CaO (moles)']
            df_molar['Mafic_Index'] = sum_mafic / df_molar['SiO2 (moles)']
            
        # Propagate error for Mafic Index 
        if all(f"{c}_err" in df_molar.columns for c in required_mafic):
            sum_mafic_err = np.sqrt(
                df_molar['FeO-T (moles)_err']**2 + 
                df_molar['MgO (moles)_err']**2 + 
                df_molar['CaO (moles)_err']**2
                )
            df_molar['Mafic_Index_err'] = df_molar['Mafic_Index'] * np.sqrt(
                (sum_mafic_err / sum_mafic)**2 +
                (df_molar['SiO2 (moles)_err'] / df_molar['SiO2 (moles)'])**2
                )
        
        # Split by underscore
        # Rejoin the first 4 parts to ensure we capture 'ps', '', '0125', and the SCLK (10-digit code)
        file_name_prefix = raw_name.split(str(sclk))[0] + str(sclk)
        
        # Determine which detector this is by checking the filename 
        detector = 'unknown'
        if "rqa" in raw_name.lower(): detector = "rqa"
        elif "rqb" in raw_name.lower(): detector = "rqb"
        elif "rqc" in raw_name.lower(): detector = "rqc"
        
        # Create a clean name: ps__0125_rqa_molar.csv
        output_name = f"{file_name_prefix}_{detector}_molar.csv"
        
        output_path = os.path.join(processed_dir, output_name)
        df_molar.to_csv(output_path, index=False)

        # DATABASE BOOKKEEPING 
        # Mark this specific SCLK as complete in the processing_status table 
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE processing_status SET molar_ready = 1 WHERE sclk = ?", (sclk,))
        
        # Register the new molar file in the file_inventory table
        cursor.execute("""
            INSERT OR REPLACE INTO file_inventory (sclk, file_name, file_type, file_path)
            VALUES (?, ?, ?, ?)
        """, (sclk, output_name, 'molar', output_path))        
        
        conn.commit()
        conn.close()
        
        print(f"Successfully transformed {raw_name} and updated database.")
                

if __name__ == "__main__":
    run_molar_transform()
