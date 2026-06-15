# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 16:18:12
@author: salva

Description:
    An Object-Oriented data engineering and analysis engine designed to automate
    the classification of Martian mineral phases from NASA's Mars 2020 PIXL 
    instrument. This class encapsulates database connectivity, in-memory rule 
    caching to eliminate query overhead, coordinate transformations, and the 
    generation of multi-format downstream data payloads (CSV and JSON).
"""

import pandas as pd
import sqlite3
import os
import json

class MineralClassifierEngine:
    def __init__(self, db_path=None):
        """
        Initializes the classification engine, establishes directory paths, 
        and pre-loads the mineral rules hierarchy into memory.
        
        Parameters:
            db_path (str, optional): Custom path to the SQLite tracking database.
                                     Defaults to 'PIXL_pipeline_registry.db'.
        """
        # Establish base directory paths relative to this script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
        
        self.geochem_dir = os.path.join(project_root, "data", "processed")
        self.analysis_dir = os.path.join(project_root, "data", "analysis")
        self.db_path = db_path or os.path.join(project_root, "PIXL_pipeline_registry.db")
        
        # Performance Optimization: Query the database ONCE during initialization.
        # This keeps the nested hierarchy dict in memory and prevents hitting the 
        # database repeatedly for every single data row or sample file.
        self.hierarchy = self._load_mineral_rules()

    def _load_mineral_rules(self):
        """
        Queries the SQLite database to fetch classification 
        thresholds and organizes them into a nested dictionary structured by 
        priority rank and conditional groups.
        
        Returns:
            dict: A nested lookup structure mapping priority ranks to mineral rules.
        """
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT d.mineral_id, d.mineral_name, d.priority_rank, r.group_id, r.parameter, r.min_val, r.max_val
        FROM classification_definitions d
        JOIN mineral_rules r
            ON d.mineral_id = r.mineral_id
        ORDER BY d.priority_rank ASC
        """
        df_rules = pd.read_sql_query(query, conn)
        conn.close()
        
        # Build the nested hierarchy: {rank: {name, id, groups: {group_id: [(param, min, max)]}}}
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

    def _get_sample_metadata(self, sclk_id, conn):
        """
        Retrieves contextual metadata for a specific spacecraft 
        clock (SCLK) ID from the sample registry table.
        
        Parameters:
            sclk_id (int/str): The unique clock time identifier for the sample run.
            conn (sqlite3.Connection): An active SQLite database connection object.
            
        Returns:
            dict: Target sample names, sol IDs, and scan categories.
        """
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

    def _classify_pmc(self, row):
        """
        Evaluates a single target point (PMC) against the 
        pre-loaded rule hierarchy using deterministic, tiered funnel logic.
        
        Parameters:
            row (pd.Series): A single row of geochemical weight-percent abundances.
            
        Returns:
            tuple: (mineral_name, mineral_id) mapping the successful match.
        """
        # Iterate through rules sequentially based on priority rank
        for rank in sorted(self.hierarchy.keys()):
            mineral_name = self.hierarchy[rank]['name']
            mineral_id = self.hierarchy[rank]['id']
            groups = self.hierarchy[rank]['groups']
            
            # Evaluate distinct conditional groups (Implements OR logic between groups)
            for group_id, conditions in groups.items():
                match = True
                # Evaluate individual parameters within a group (Implements AND logic)
                for param, min_val, max_val in conditions:
                    val = row.get(param)
                    if val is None or not (min_val <= val <= max_val):
                        match = False
                        break # Break current group evaluation if a condition fails
                
                # If all conditions within any group pass, the mineral is identified
                if match:
                    return mineral_name, mineral_id
                    
        # Default fallback classification if no predefined mineral rules are matched
        return "Other", 7

    def _get_parent_category(self, mineral_name):
        """
        Maps granular, specialized mineral classifications into 
        four macro-level geologic parent categories.
        
        Parameters:
            mineral_name (str): The granular mineral name string.
            
        Returns:
            str: The broader geologic parent category label.
        """
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

    def process_pending_analysis(self):
        """
        Identifies unprocessed scans via the pipeline 
        registry database, executes data cleansing and mathematical transformations, 
        and exports structured mapping CSVs and master JSON summaries.
        """
        conn = sqlite3.connect(self.db_path)
        
        # Locate files that have successfully finished preprocessing but lack analysis
        query = """
        SELECT sclk FROM processing_status 
        WHERE is_processed = 1 AND analysis_ready = 0
        """
        tasks = pd.read_sql_query(query, conn)
        
        if tasks.empty:
            print('No new files to analyze.')
            conn.close()
            return 
        
        # Process every pending file identified in the tracking directory
        for sclk_id in tasks['sclk']:
            reg_info = self._get_sample_metadata(sclk_id, conn)
            
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT file_path, file_name FROM file_inventory 
                           WHERE sclk=? AND file_type LIKE "%geochem"
                           """, (sclk_id,))
            file_list = cursor.fetchall()
            
            for path, name in file_list:
                print(f"Analyzing {name} - Target: {reg_info['sample_name']}")
                df = pd.read_csv(path)
                
                # --- Step 1: Execute Granular Mineral Classification ---
                # Applies the core tiered funnel logic row-by-row across the dataframe
                res = df.apply(lambda row: self._classify_pmc(row), axis=1)
                df['classification'] = [x[0] for x in res]
                df['mineral_id'] = [x[1] for x in res]
                
                # --- Step 2: Apply Macro Geologic Groupings ---
                df['parent_category'] = df['classification'].apply(self._get_parent_category) 
                
                # --- Step 3: Handle Mathematical Boundary Anomalies ---
                # Replaces division-by-zero infinity values with a standard upper bound limit
                df['fe_mn_ratio'] = df['Fe/Mn'].replace([float('inf'), float('-inf')], 200.0).fillna(0).round(2)
                
                # --- Step 4: Unit Conversion (Meters to Millimeters) ---
                df['x_mm'] = (df['x'] * 1000).round(2)
                df['y_mm'] = (df['y'] * 1000).round(2)
                df['z_mm'] = (df['z'] * 1000).round(2)
                         
                # --- Step 5: Generate Executive Statistical Summary ---
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
                
                # --- Step 6: Export Downstream Spatial Mapping CSV ---
                map_name = name.replace("geochem.csv", "mapping.csv")
                map_path = os.path.join(self.analysis_dir, map_name)
                export_cols = ['PMC', 'x', 'y', 'z', 'x_mm', 'y_mm', 'z_mm', 'mineral_id', 'classification', 'parent_category']
                df[export_cols].to_csv(map_path, index=False)
                
                # --- Step 7: Export Nested JSON Master Payload for UI / Web Layer ---
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
                json_path = os.path.join(self.analysis_dir, json_name)
                with open(json_path, 'w') as f:
                    json.dump(json_output, f, indent=4)
                    
                # --- Step 8: Update Pipeline Registry Tracking & Commit Transaction ---
                cursor.execute("UPDATE processing_status SET analysis_ready = 1 WHERE sclk = ?", (sclk_id,))
                cursor.execute("INSERT INTO file_inventory (sclk, file_name, file_type, file_path) VALUES (?, ?, ?, ?)",
                               (sclk_id, map_name, "mapping_csv", map_path))
                cursor.execute("INSERT INTO file_inventory (sclk, file_name, file_type, file_path) VALUES (?, ?, ?, ?)",
                               (sclk_id, json_name, "summary_json", json_path))
                conn.commit()
        
        conn.close()                   

if __name__ == "__main__":
    # Instantiate the engine object and execute the pending file pipeline processing framework
    engine = MineralClassifierEngine()
    engine.process_pending_analysis()

