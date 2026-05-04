# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 10:37:55 2026
@author: salva
"""

import sqlite3
import os 

# --- PATH SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
db_path = os.path.join(project_root, "PIXL_pipeline_registry.db")

def seed_mineral_logic(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear tables to ensure a clean start
    cursor.execute("DELETE FROM mineral_rules")
    cursor.execute("DELETE FROM classification_definitions")
    
    # Define the 6-tier hierarchy
    minerals = [
        ('Pyroxene', 1),
        ('Olivine', 2),
        ('Alt. Mafic', 3),
        ('Felsic', 4),
        ('High Alteration', 5),
        ('Alteration', 6)
    ]
    
    mineral_id_map = {}
    for name, rank in minerals:
        cursor.execute(
            "INSERT INTO classification_definitions (mineral_name, priority_rank) VALUES (?, ?)",
            (name, rank)
        )
        mineral_id_map[name] = cursor.lastrowid
        
    # Define the thresholds matching master file (*geochem*) column names 
    rules_data = [        
        # Pyroxene (rank 1)
        (mineral_id_map['Pyroxene'], 'A', 'mafic_score', 0.85, 1),
        (mineral_id_map['Pyroxene'], 'A', 'Mafic_Index', 0.75, 1.25), 
        (mineral_id_map['Pyroxene'], 'B', 'mafic_score', 0.85, 1),
        (mineral_id_map['Pyroxene'], 'B', 'Fe/Mn', 25, 40),

        # Olivine (rank 2)
        (mineral_id_map['Olivine'], 'A', 'mafic_score', 0.85, 1),
        (mineral_id_map['Olivine'], 'A', 'Mafic_Index', 1.6, 2.3),
        (mineral_id_map['Olivine'], 'B', 'mafic_score', 0.85, 1),
        (mineral_id_map['Olivine'], 'B', 'Fe/Mn', 40.1, 70.0), 

        
        # Alt. Mafic (rank 3)
        (mineral_id_map['Alt. Mafic'], 'A', 'mafic_score', 0.7, 1.0),
        (mineral_id_map['Alt. Mafic'], 'A', 'Mafic_Index', 0.8, 2.2),
        (mineral_id_map['Alt. Mafic'], 'A', 'Fe/Mn', 80.0, 1000.0),
        
        # Felsic (rank 4)
        (mineral_id_map['Felsic'], 'A', 'felsic_score', 0.65, 1.0),
        
        # High Alteration (rank 5)
        (mineral_id_map['High Alteration'], 'A', 'silica_score', 0.0, 0.10),
        (mineral_id_map['High Alteration'], 'B', 'SO3_wt%_Cl_wt%_sum', 25.0, 100.0),
        
        # Alteration (Rank 6)
        (mineral_id_map['Alteration'], 'A', 'silica_score', 0.0, 0.20),
        (mineral_id_map['Alteration'], 'B', 'SO3_wt%_Cl_wt%_sum', 10.0, 100.0)
    ]
    
    cursor.executemany(
        "INSERT INTO mineral_rules (mineral_id, group_id, parameter, min_val, max_val) VALUES (?, ?, ?, ?, ?)",
        rules_data
    )
    
    conn.commit()
    conn.close()
    print("Database seeded successfully.")
    
if __name__ == "__main__":
    seed_mineral_logic(db_path)
    
