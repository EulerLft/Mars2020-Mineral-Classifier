# -*- coding: utf-8 -*-

"""
Updated on Fri May 01 2026
@author: salva
"""
import pandas as pd
import sqlite3
import os
import json

# --- PATH SETUP --- 
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
geochem_dir = os.path.join(project_root, "data", "processed")
analysis_dir = os.path.join(project_root, "data", "analysis")
db_path = os.path.join(project_root, "PIXL_pipeline_registry.db")

def get_mineral_rules():
    """Fetch and organize rules from DB by rank and group"""
    conn = sqlite3.connect(db_path)
    query = """
    SELECT d.mineral_id, d.mineral_name, d.priority_rank, r.group_id, r.parameter, r.min_val, r.max_val
    FROM classification_definitions d
    JOIN mineral_rules r
        ON d.mineral_id = r.mineral_id
    ORDER BY d.priority_rank ASC
    """
    df_rules = pd.read_sql_query(query, conn)
    conn.close()
    
    # Organize into a nested dictionary for fast look-up
    # {rank {name: {group: [(param, min, max,), ...]}}}
    hierarchy = {}
    for _, row in df_rules.iterrows():
        rank = row['priority_rank']
        name = row['mineral_name']
        if rank not in hierarchy:
            hierarchy[rank] = {'name': name, 'id': row['mineral_id'], 'groups': {}}
        
        group = row['group_id']
        if group not in hierarchy[rank]['groups']:
            hierarchy[rank]['groups'][group] = []
            
        hierarchy[rank]['groups'][group].append((row['parameter'], row['min_val'], row['max_val']))
    return hierarchy

def get_sample_metadata(sclk_id, conn):
    """Fetch metadata from sample_registry for a specific SCLK"""
    query = """
    SELECT sample_name, target_id, nominal_sol, scan_type
    FROM sample_registry 
    WHERE sclk = ?
    """
    cursor = conn.cursor()
    cursor.execute(query, (sclk_id,))
    result = cursor.fetchone()
    
    if result:
        return {
            "sample_name": result[0],
            "target_id": result[1],
            "nominal_sol": result[2],
            "scan_type": result[3]
        }
    return {
        "sample_name": "Unknown",
        "target_id": "Unknown",
        "nominal_sol": None,
        "scan_type": "Unknown"
    }

def classify_pmc(row, hierarchy):
    """Apply the tiered funnel logic to a single row (one PMC) in a scan"""
    for rank in sorted(hierarchy.keys()):
        mineral_name = hierarchy[rank]['name']
        mineral_id = hierarchy[rank]['id']
        groups = hierarchy[rank]['groups']
        
        # Check each group (e.g., Group A, Group B)
        for group_id, conditions in groups.items():
            match = True
            for param, min_val, max_val in conditions:
                val = row.get(param)
                # All conditions in a group must be true (AND)
                if val is None or not (min_val <= val <= max_val):
                    match = False
                    break 
            
            # If any group matches the mineral is identifed (OR)
            if match:
                return mineral_name, mineral_id
    
    return "Other", 7

def get_parent_category(mineral_name):
    """Group minerals into four broader categories"""
    mafic_minerals = ['Olivine', 'Pyroxene', 'Alt. Mafic']
    alteration_minerals = ['Alteration', 'High Alteration']
    
    if mineral_name in mafic_minerals:
        return "Mafic"
    elif mineral_name in alteration_minerals:
        return "Alteration"
    elif mineral_name == 'Felsic':
        return "Felsic"
    else:
        return "Other"

def run_analysis():
    conn = sqlite3.connect(db_path)
    # Find the files that are ready for analysis 
    query = """
    SELECT sclk FROM processing_status 
    WHERE is_processed = 1 AND analysis_ready = 0
    """
    tasks = pd.read_sql_query(query, conn)
    
    if tasks.empty:
        print('No new files to analyze.')
        conn.close()
        return 
    
    hierarchy = get_mineral_rules()
    
    for sclk_id in tasks['sclk']:
        # Fetch registry info for the current scan
        reg_info = get_sample_metadata(sclk_id, conn)
        
        # Find the geochem file in inventory
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT file_path, file_name FROM file_inventory WHERE sclk=? AND file_type LIKE "%geochem"
                       """, (sclk_id,))
        file_list = cursor.fetchall()
        
        for path, name in file_list:
            print(f"Analyzing {name} - Target: {reg_info['sample_name']}")
            df = pd.read_csv(path)
            
            # --- Perform classification ---
            #Upack the tuple (name and id) into two columns 
            res = df.apply(lambda row: classify_pmc(row, hierarchy), axis=1)
            df['classification'] = [x[0] for x in res]
            df['mineral_id'] = [x[1] for x in res]
            
            df['parent_category'] = df['classification'].apply(get_parent_category) 
            df['fe_mn_ratio'] = df['Fe/Mn'].replace([float('inf'), float('-inf')], 200.0).fillna(0).round(2)
            
            # --- Convert MM coordinantes ---
            df['x_mm'] = (df['x'] * 1000).round(2)
            df['y_mm'] = (df['y'] * 1000).round(2)
            df['z_mm'] = (df['z'] * 1000).round(2)
                     
            # --- CALCULATE EXECUTIVE SUMMARY ---
            total_shots = len(df)
            counts = df['classification'].value_counts()
            bulk_fe_mn = round(df['fe_mn_ratio'].mean(), 1) if 'fe_mn_ratio' in df else 0
            
            summary_stats = {
                "pyroxene_pct": round((counts.get('Pyroxene', 0) / total_shots) * 100, 1), 
                "olivine_pct": round((counts.get('Olivine', 0) / total_shots) * 100, 1),
                "alt_mafic_pct": round((counts.get('Alt. Mafic', 0) / total_shots) * 100, 1),
                "felsic_pct": round((counts.get('Felsic', 0) / total_shots) * 100, 1),
                "high_alt_pct": round((counts.get('High Alteration', 0) / total_shots) * 100, 1),
                "alteration_pct": round((counts.get('Alteration', 0) / total_shots) * 100, 1),
                "other_pct": round((counts.get('Other', 0) / total_shots) * 100, 1),
                "bulk_fe_mn_ratio": bulk_fe_mn
                }
            
            # Export 1: Mapping CSV --- 
            map_name = name.replace("geochem.csv", "mapping.csv")
            map_path = os.path.join(analysis_dir, map_name)
            df[['PMC', 'x', 'y', 'z', 'x_mm', 'y_mm', 'z_mm', 'mineral_id', 'classification', 'parent_category']].to_csv(map_path, index=False)
            
            # Export 2: JSON Master (Two-Part Structure) --- 
            counts = df['classification'].value_counts(normalize=True).to_dict()
            core_six = ['SiO2_wt%', 'MgO_wt%', 'Al2O3_wt%', 'FeO-T_wt%', 'SO3_wt%', 'Cl_wt%']
            
            json_output = {
                "metadata": {
                    "nominal_id": reg_info['nominal_sol'],
                    "sclk" : sclk_id, 
                    "sample_name": reg_info['sample_name'],
                    "target_id": reg_info['target_id'],
                    "scan_type": reg_info['scan_type'],                    
                    "source_file" : name, 
                    "total_pmcs" : total_shots
                    },
                "executive_summary" : summary_stats,
                "shot_by_shot": df[['PMC', 'x_mm', 'y_mm', 'classification', 'parent_category', 'fe_mn_ratio'] + core_six].to_dict(orient='records')
                }
            
            json_name = name.replace("geochem.csv", "summary.json")
            json_path = os.path.join(analysis_dir, json_name)
            with open (json_path, 'w') as f:
                json.dump(json_output, f, indent=4)
                
            # --- UPDATE DATABASE ---
            cursor.execute("UPDATE processing_status SET analysis_ready = 1 WHERE sclk = ?", (sclk_id,))
            cursor.execute("INSERT INTO file_inventory (sclk, file_name, file_type, file_path) VALUES (?, ?, ?, ?)",
                           (sclk_id, map_name, "mapping_csv", map_path))
            cursor.execute("INSERT INTO file_inventory (sclk, file_name, file_type, file_path) VALUES (?, ?, ?, ?)",
                           (sclk_id, json_name, "summary_json", json_path))
            conn.commit()
    
    conn.close()                   

if __name__ == "__main__":
    run_analysis()
           
            
            