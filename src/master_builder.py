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
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
processed_dir = os.path.join(project_root, "data", "processed")
raw_abundances_dir = os.path.join(project_root, "data", "raw", "abundances")
db_path = os.path.join(project_root, "PIXL_pipeline_registry.db")

# AUTOMATIC REFRESH 
print("Refreshing file inventory ...")
scan_folders()

def get_grouped_files():
    """Query database for molar files that haven't been merged into master yet"""
    conn = sqlite3.connect(db_path)
    query = """
    SELECT ps.sclk, fi.file_type, fi.file_path
    FROM processing_status as ps
    JOIN file_inventory fi
        ON ps.sclk = fi.sclk
    WHERE ps.molar_ready = 1
        AND ps.is_processed = 0
        AND fi.file_type IN ('metadata', 'PMC', 'rqa', 'rqb', 'rqc', 'rqa_molar', 'rqb_molar', 'rqc_molar')
        ORDER BY ps.sclk;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Group by sclk and map file_type to its path 
    grouped = {}
    for sclk, group in df.groupby('sclk'):
        grouped[sclk] = dict(zip(group['file_type'], group['file_path']))
    return grouped


def run_master_builder():
    tasks = get_grouped_files()
    
    for sclk_id, files in tasks.items():
        # Identify which detectors are available for this SCLK
        detectors = [d for d in ['rqa', 'rqb', 'rqc'] if d in files]
        
        for detector in detectors:
            # Extract '0125' from 'ps__0125_0678032243_metadata.csv'
            meta_path = files.get('metadata')
            raw_meta_name = os.path.basename(meta_path)
            
            # split name "ps__0125_0678032243_metadata.csv"
            name_parts = raw_meta_name.split('_')
            sol_num = name_parts[2]
            
            # Reconstruct with the double underscore and the clean sol number
            file_id = f"ps__{sol_num}_{str(sclk_id).zfill(10)}_{detector}"
            
            # Retrieve paths for the database dictionary
            pmc_path = files.get('PMC')
            ox_path = files.get(detector)
            molar_path = files.get(f"{detector}_molar")
            
            if all([pmc_path, meta_path, ox_path, molar_path]):
                print(f"Building master: {file_id} (linked via SCLK ID: {sclk_id})")
                
                # Load datasets
                df_pmc = pd.read_csv(pmc_path)[['PMC', 'x', 'y', 'z']]
                df_meta = pd.read_csv(meta_path)[['live_time_A', 'live_time_B']]
                df_ox = pd.read_csv(ox_path).drop(columns=['PMC'], errors='ignore')
                
                # Filter molar file to keep only actual molar columns (avoiding oxide/PMC overlap)
                df_molar_full = pd.read_csv(molar_path)
                molar_cols = [c for c in df_molar_full.columns if '(moles)' in c]
                df_molar = df_molar_full[molar_cols]
                
                # Specific ratios from the end of the molar file
                ratio_cols = ['Fe/Mn', 'Fe/Mn_err', 'Mafic_Index', 'Mafic_Index_err']
                df_ratios = df_molar_full[[c for c in ratio_cols if c in df_molar_full.columns]]
    
                # --- CALCULATE GEOLOGICAL SCORES & PROPAGATED ERRORS ---
                df_predictors = pd.DataFrame()    
    
                # Sum of Oxides and its Errors (Sum in Quadrature)
                # Assuming first 16 columns are wt% and the next 16 columns at wt%_err
                oxide_cols = [
                    'Na2O_wt%', 'MgO_wt%', 'Al2O3_wt%', 'SiO2_wt%', 'P2O5_wt%', 
                    'SO3_wt%', 'Cl_wt%', 'K2O_wt%', 'CaO_wt%', 'TiO2_wt%', 
                    'Cr2O3_wt%', 'MnO_wt%', 'FeO-T_wt%', 'NiO_wt%', 'ZnO_wt%', 'Br_wt%'
                ]
                oxide_cols = [c for c in oxide_cols if c in df_ox.columns]
                error_cols = [f"{c}_err" for c in oxide_cols]
        
                total_ox = df_ox[oxide_cols].sum(axis=1)
                total_ox_err = np.sqrt(df_ox[error_cols]**2).sum(axis=1)
        
                df_predictors['Sum_ox%'] = total_ox
                df_predictors['Sum_ox%_err'] = total_ox_err
            
                # Mafic Score & Error    
                mafic_elements = ['MgO_wt%', 'CaO_wt%', 'SiO2_wt%', 'FeO-T_wt%']
                mafic_errors = [f"{c}_err" for c in mafic_elements]
                
                mafic_num = df_ox[mafic_elements].sum(axis=1)
                mafic_num_err = np.sqrt((df_ox[mafic_errors]**2).sum(axis=1))
                
                df_predictors['mafic_score'] = mafic_num / total_ox
                df_predictors['mafic_score_err'] = df_predictors['mafic_score'] * np.sqrt(
                    (mafic_num_err / mafic_num)**2 + (total_ox_err / total_ox)**2
                    )
                
                # Felsic Score & Error
                felsic_elements = ['K2O_wt%', 'Na2O_wt%', 'Al2O3_wt%', 'CaO_wt%', 'SiO2_wt%']
                felsic_errors = [f"{c}_err" for c in felsic_elements]
                
                felsic_num = df_ox[felsic_elements].sum(axis=1)
                felsic_num_err = np.sqrt((df_ox[felsic_errors]**2).sum(axis=1))
                
                df_predictors['felsic_score'] = felsic_num / total_ox
                df_predictors['felsic_score_err'] = df_predictors['felsic_score'] * np.sqrt(
                    (felsic_num_err / felsic_num)**2 + (total_ox_err / total_ox)**2
                    ) 
                
                # buSilica Score & Error            
                df_predictors['silica_score'] = df_ox['SiO2_wt%'] / total_ox
                df_predictors['silica_score_error'] = df_predictors['silica_score'] * np.sqrt(
                    (df_ox['SiO2_wt%_err'] / df_ox['SiO2_wt%'])**2 + (total_ox_err / total_ox)**2
                    )
                df_predictors['SO3_wt%_Cl_wt%_sum'] = df_ox['SO3_wt%'] + df_ox['Cl_wt%']
                
                
                # --- MERGE EVERYTHING ---
                df_master = pd.concat([df_pmc, df_meta, df_ox, df_molar, df_ratios, df_predictors], axis=1)
                
                # Save final master file
                output_name = f"{file_id}_geochem.csv"
                df_master.to_csv(os.path.join(processed_dir, output_name), index=False)
        
                # --- UPDATE DATABASE STATUS --- 
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Mark the SCLK as fully processed 
                cursor.execute("Update processing_status SET is_processed = 1 where sclk = ?", (sclk_id,))
                
                # Register the new geochem file in the inventory
                cursor.execute("""
                               INSERT OR REPLACE INTO file_inventory (sclk, file_name, file_type, file_path)
                               VALUES (?, ?, ?, ?)
                               """, (sclk_id, output_name, f"{detector}_geochem", os.path.join(processed_dir, output_name))
                    )
                
                conn.commit()
                conn.close()

if __name__ == "__main__":
    run_master_builder()

