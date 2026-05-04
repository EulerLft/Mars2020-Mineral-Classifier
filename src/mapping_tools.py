# -*- coding: utf-8 -*-
"""
Created on Thu Apr 30 17:51:34 2026
@author: salva
"""

from pathlib import Path 
import matplotlib.pyplot as plt
import pandas as pd 
import json 
from matplotlib.colors import ListedColormap

class MineralMapper:
    def __init__(self, csv_path, json_path):
        self.csv_path = Path(csv_path)
        self.json_path = Path(json_path)
        self.df = None
        self.metadata = None 
        self.bounds = {}
        
        # Define the custom colour map for consistency across all plots 
        self.colors = [
            '#b02271',         # Pyroxene
            '#d8a4cf',         # Olivine
            '#8259ad',         # Altered Mafic
            '#40826D',        # Felsic
            'tab:orange',      # High Alt
            '#ffbf00',         # Alteration
            '#FDF5E6'          # Other
        ]
        self.cmap = ListedColormap(self.colors)
        
        # Legend mapping for consistency with classification IDs
        self.mineral_labels = [
            "Pyroxene", "Olivine", "Altered Mafic", 
            'Felsic', 'High Alt.', 'Alteration', 'Other'
            ]
        
        # Calculate midpoints for the 7 categories
        self.midpoints = [1.45, 2.255, 3.10, 4.00, 4.75, 5.65, 6.5]
        
    def load_data(self):
        # Load the mapping CSV into a DataFrame 
        self.df = pd.read_csv(self.csv_path)
        
        # Load the summary JSON 
        with open(self.json_path, 'r') as f:
            # Save the entire JSON object to self.metadata to access nested keys later
            self.metadata = json.load(f)
            
        # Calculate and store spatial bounds for plotting 
        self.bounds = {
            'x_min': self.df['x_mm'].min(),
            'x_max': self.df['x_mm'].max(),
            'y_min': self.df['y_mm'].min(),
            'y_max': self.df['y_mm'].max()
            }
    
    def plot_mineral_map(self, title='Mineral Composition Map'):
        """
        Generates a 2D spatial plot of the mineral distribution based on spatial coordinates. 
        """
        if self.df is None or self.metadata is None:
            self.load_data()
        
        # Dynamic title generation from metadata
        sample = self.metadata['metadata']['sample_name']
        scan = self.metadata['metadata']['scan_type']
        sol = self.metadata['metadata']['nominal_id']
        dynamic_title = f"{sample} ({scan})"
        
        fig, ax = plt.subplots(figsize=(12, 8))
 
        # Scatter plot using the numerical mineral_id to map to the ListedColormap 
        sc = ax.scatter(
            self.df['x_mm'], 
            self.df['y_mm'], 
            c=self.df['mineral_id'],
            cmap=self.cmap, 
            s=25, 
            marker='o', 
            edgecolors='none')
        
        ax.set_aspect('equal')
        
        # Color bar setup 
        colorbar = plt.colorbar(sc, ax=ax, ticks=self.midpoints)
        colorbar.ax.set_yticklabels(self.mineral_labels, size=12, color='#ced4da')
        
        # Set face colour 
        ax.set_facecolor('#212529')
        fig.patch.set_facecolor('#212529')
         
        # Axes limits with dynamic padding 
        x_min, x_max = self.df['x_mm'].min(), self.df['x_mm'].max()
        y_min, y_max = self.df['y_mm'].min(), self.df['y_mm'].max()
        
        buffer = 4.0  # 4mm padding on all sides

        ax.set_xlim(x_max + buffer, x_min - buffer)
        ax.set_ylim(y_min - buffer, y_max + buffer)
        
        # Set all text to soft gray 
        ax.tick_params(axis='both', colors='#ced4da', labelsize=12)
        ax.xaxis.label.set_color('#ced4da')
        ax.yaxis.label.set_color('#ced4da')

        # Measurement bars 
        length = x_max - x_min
        scale_y = y_min - (buffer * 0.55) # Places bar halfway into the bottom buffer zone

        ax.hlines(y=scale_y, xmin=x_min, xmax=x_max, linewidth=2.5, alpha=0.8, color='#ced4da')
        ax.text(x_min + (length * 0.5), scale_y + 0.1, f"{length.round(1)}mm", 
        color='#ced4da', size=12, ha='center', va='bottom')
        
        # Axes labels 
        plt.xlabel('x coordinate [mm]', size=15, labelpad=20);
        plt.ylabel('y coordinate [mm]', size=15, labelpad=20);

        # Updated Title with dynamic formatting
        ax.set_title(
            dynamic_title, 
            fontsize=15, 
            bbox=dict(boxstyle='round', facecolor='#ced4da', alpha=0.8), 
            pad=15
            );
        
        plt.tight_layout()
        plt.show()
        
        
        

