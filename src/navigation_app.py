# -*- coding: utf-8 -*-
"""
Updated on Fri May 02 2026
@author: salva
"""
import os 
import json
import pandas as pd
import streamlit as st 
import matplotlib.pyplot as plt
from mapping_tools import MineralMapper

TARGET_LOOKUP = {
    "Dourbes": {
        "257": {"id": "0689790785", "type": "rqc"},
        "269": {"id": "0690861528", "type": "rqc"}
    },
    "Quartier": {
        "293": {"id": "0692986818", "type": "rqc"},
        "300": {"id": "0693593437", "type": "rqc"}
    },
    "Bellegarde": {
        "186": {"id": "0683484569", "type": "rqc"}
    },
    "Montpezat": {
        "349": {"id": "0697957949", "type": "rqc"}
    },
    "Alfalfa": {
        "369": {"id": "0699719245", "type": "rqc"}
    }
}

# Set up paths relative to this script in PIXL_2/src
# Ensures we find the existing asset folder 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
DATA_DIR = os.path.join(PROJECT_DIR, "data", "analysis")

# Initialize session state for the "Navigation" memory
if "view" not in st.session_state:
    st.session_state.view = 'wide'
if "selected_sample" not in st.session_state:
    st.session_state.selected_sample = None
if "sol" not in st.session_state:
    st.session_state.sol = None

# Navigation Helper Functions
def reset_to_home():
    st.session_state.view = 'wide'
    st.session_state.selected_sample = None
    st.session_state.sol = None
    
def reset_to_crater():
    st.session_state.view = 'crater'
    
def reset_to_formation():
    # Helper to return to the specific formation view from the map
    # Logic handles both Séítah and Máaz target lists
    seitah_samples = ["Dourbes", "Quartier"]
    maaz_samples = ["Bellegarde", "Montpezat", "Alfalfa"]
    if st.session_state.selected_sample in seitah_samples:
        st.session_state.view = 'seitah'
    elif st.session_state.selected_sample in maaz_samples:
        st.session_state.view = 'maaz'
    else:
        # Default fallback if no sample was active
        st.session_state.view = 'crater'
    st.session_state.selected_sample = None
    st.session_state.sol = None
    
def load_markdown(filename):
    """Helper to safely load markdown content from the assets folder."""
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Description coming soon..."

def get_mineral_summary(target, sol):
    """Fetch high-level geochemistry from executive_summary for dropdown table"""
    target_info = TARGET_LOOKUP[target][sol]
    sol_padded = sol.zfill(4)
    json_file = f"ps__{sol_padded}_{target_info['id']}_{target_info['type']}_summary.json"
    json_path = os.path.join(DATA_DIR, json_file)
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            exec_sum = data.get("executive_summary", {})
            metadata = data.get("metadata", {})
            
            st.markdown("""
                    <style>
                    th {text-align: center !important;}
                    td {text-align: center !important;}
                    </style>
                    """, unsafe_allow_html=True)
                    
            # Mapping specific keys to human-readable labels 
            met_data = {"Metric": ["Target Type", "Scan Type", "Total Shots", "Bulk Fe/Mn"],
                        "Value": [metadata.get("target_id"), metadata.get("scan_type"), 
                                  f'{metadata.get("total_pmcs", 0):,.0f}', f"{exec_sum.get('bulk_fe_mn_ratio', 0):.0f}"]
                        }
            
            summary_data = {
                "Mineral": ["Olivine", "Pyroxene", "Alt Mafic", "Felsic", 
                           "High Alt.", "Alteration", "Other"],
                "Abundance": [
                    f"{exec_sum.get('olivine_pct', 0):.0f}%",
                    f"{exec_sum.get('pyroxene_pct', 0):.0f}%",
                    f"{exec_sum.get('alt_mafic_pct', 0):.0f}%",
                    f"{exec_sum.get('felsic_pct', 0):.0f}%",
                    f"{exec_sum.get('high_alt_pct', 0):.0f}%",
                    f"{exec_sum.get('alteration_pct', 0):.0f}%",
                    f"{exec_sum.get('other_pct', 0):.0f}%"
                    ]
                }
            df_summary = pd.DataFrame(summary_data)
            df_metadata = pd.DataFrame(met_data)
            return df_summary, df_metadata
    return None
    
# UI Headers
st.set_page_config(page_title='Jezero Crater Navigation', layout='wide')

st.markdown("""
    <style>
           .block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
                margin-top: 0rem;
            }
    </style>
    """, unsafe_allow_html=True)
    
st.markdown("<h1 style='text-align: center; font-size: 60px;'>Mars2020 - Perseverance Rover</h1>", unsafe_allow_html=True)

# --- LAYER 1: Global View --- 
if st.session_state.view == 'wide':
    st.write("## Jezero Crater - Overview Map")
    
    # Create two columns: one for the interactive map and one for the info box \
    col_map, col_info = st.columns([2, 1])
    
    with col_map: 
        st.info("##### Select a Mission Campaign below to explore the campaign site.") 
        # Navigation buttons at the bottom 
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            if st.button("Explore Delta Front", use_container_width=True):
                st.session_state.view = 'delta'
                st.rerun()
                
        with c2:
            if st.button("Explore Crater Floor", use_container_width=True):
                st.session_state.view = 'crater'
                st.rerun()
        
        with c3: 
            if st.button("Explore Upper Fan", use_container_width=True):
                st.toast("Upper Fan data is currently being processed.", icon="🚀")
                
        with c4:
            if st.button("Explore Creater Rim", use_container_width=True):
                st.toast("Creater Rin analysis is in progress.", icon="🛰️")

        img_path = os.path.join(ASSETS_DIR, "nav_01_jezero_crater_wide.JPG")
        st.image(img_path, use_container_width=True)

        st.write("##### Composition Summary")
    
        # Adding a small table for bulk composition
        
        st.markdown("""
                    <style>
                    th {text-align: center !important;}
                    td {text-align: center !important;}
                    </style>
                    """, unsafe_allow_html=True)
        
        comp_data = {
            "Region": ["Crater Floor", "Delta Front"],
            "Mafic": ['56%', '30%'],
            "Felsic": ['28%', '9%'],
            "Alteration": ['9%', '43%'],
            "Other ": ['7%', '18%']
            
            }
        # Create DataFrame and apply centering style
        df = pd.DataFrame(comp_data).astype(str)
        st.table(df)    


    with col_info: 
        st.write("## Mission Overview")
    
        # Load and display the mission_overview.md contents
        content = load_markdown("mission_overview.md")
        st.markdown(content)
        
        st.divider()


# --- LAYER 2: Campaign View ---

# --- Delta Front Campaign --- 
elif st.session_state.view == "delta":
    st.button("Back to Wide View", on_click=reset_to_home)
    st.write("### Delta Front Campaign View")
    col_map, col_pad, col_info = st.columns([1.5, 0.25, 1])
    
    with col_map:
        st.info("Select a formation to explore specific geological targets.")
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button("Explore Shanandoah", use_container_width=True):
                st.toast("Shenandoah Formation data is currently being processed.", icon="🚀")
        with c2:
            if st.button("Explore Wildcat Ridge", use_container_width=True):
                st.toast("Wildcat Ridge Formation data is currently being processed.", icon="🚀")
        with c3:
            if st.button("Explore Skinner Ridge", use_container_width=True):
                st.toast("Skinner Ridge Formation data is currently being processed.", icon="🚀")
        img_path_delta = os.path.join(ASSETS_DIR, "nav_03_delta_front_campaign.JPG")
        st.image(img_path_delta, width=950)
        
    with col_info:
        st.write("## Delta Front Campaign Overview")
        # Load and display the crater_floor_campaign_overview
        content = load_markdown("delta_front_overview.md")
        st.markdown(content)
    
# --- Crater Floor Campaign --- 
elif st.session_state.view == 'crater':
    st.button('Back to Wide View', on_click = reset_to_home)    
    st.write("## Crater Floor Campaign")
    col_map, col_pad, col_info = st.columns([1.5, 0.25, 1])
    
    with col_map:
        st.info("Select a formation to explore specific geological targets.")
        c1, c2 = st.columns(2)        
        with c1:
            if st.button("Explore Séítah Formation", use_container_width=True):
                st.session_state.view = 'seitah'
                st.rerun()
        with c2:
            if st.button("Explore Máaz Fromation", use_container_width=True):
                st.session_state.view = 'maaz'
                st.rerun()
        img_path_crater = os.path.join(ASSETS_DIR, "nav_02_crater_floor_campaign.JPG")
        st.image(img_path_crater, width=950)
        
    with col_info:
        st.write("## Crater Floor Campaign Overview")
        # Load and display the crater_floor_campaign_overview
        content = load_markdown("crater_floor_overview.md")
        st.markdown(content)
        
# --- LAYER 3: Formation Zoom View --- 

# --- Seitah Formation --- 
elif st.session_state.view == 'seitah':
    st.button('Back to Crater Floor', on_click=reset_to_crater)    
    
    col_ctrl, col_pad, col_map = st.columns([1.2, 0.35, 2])
    
    with col_ctrl:
        st.write("### Target Selection")
        st.info("Select a geological target to begin analysis.")   
        
        # First Level -- Target Drop-Down
        for target in ["Dourbes", "Quartier"]:                        
            with st.expander(f"{target}", expanded=False):
                
                # Second level -- Sol Drop-Down
                for sol_val in TARGET_LOOKUP[target].keys():
                    with st.expander(f"Sol {sol_val}", expanded=False):
                                               
                        # 1. Action Button to Trigger Shot-by-Shot analysis
                        if st.button(f"Analyze Sol {sol_val}", key=f"btn_{target}_{sol_val}", use_container_width=True):
                            st.session_state.selected_sample = target
                            st.session_state.sol = sol_val
                            st.session_state.view = "run_map"
                            st.rerun()
                    
                        st.write("**Compositional Overview**")
                        # 2. Display Mineral Table 
                        metadata_df = get_mineral_summary(target, sol_val)[1]
                        st.table(metadata_df)

                        summary_df = get_mineral_summary(target, sol_val)[0]
                        if summary_df is not None:
                            st.table(summary_df)
                        else:
                            st.caption("Summary data not available.")
                    
        st.divider()
        
    with col_map:
        st.write("### Séítah Formation")
        # Show map image for context 
        img_path_seitah = os.path.join(ASSETS_DIR, "nav_02a_seitah_zoom.JPG")
        st.image(img_path_seitah, use_container_width=True)

# --- Maaz Formation ---- 
elif st.session_state.view == 'maaz':
    st.button('Back to Crater Floor', on_click=reset_to_crater)
    
    col_ctrl, col_pad, col_map = st.columns([1.2, 0.35, 2])
    with col_ctrl:
        st.write("### Target Selection")
        st.info("Select a geological target to begin analysis.")
        
        # First Level -- Target Drop-Down
        for target in ["Bellegarde", "Montpezat", "Alfalfa"]:
            with st.expander(f"{target}", expanded=False):
                
                for sol_val in TARGET_LOOKUP[target].keys():
                    with st.expander(f"Sol {sol_val}", expanded=False):
                        
                        # 1. Action Button to Trigger Shot-by-Shot analysis
                        if st.button(f"Analyze Sol {sol_val}", key=f"{target}_{sol_val}", use_container_width=True):
                            st.session_state.selected_sample = target
                            st.session_state.sol = sol_val
                            st.session_state.view = 'run_map'
                            st.rerun()
                        
                        st.write("**Compositional Overview**")
                        # 2. Display Mineral Table 
                        metadata_df = get_mineral_summary(target, sol_val)[1]
                        st.table(metadata_df)
                        
                        summary_df = get_mineral_summary(target, sol_val)[0]
                        if summary_df is not None:
                            st.table(summary_df)
                        else:
                            st.caption("Summary data not available.")
        st.divider()
        
    with col_map:
        st.write("### Máaz Formation")
        # Show map image for context
        img_path_maaz = os.path.join(ASSETS_DIR, "nav_02b_maaz_zoom.JPG")
        st.image(img_path_maaz, width=950)
    

# --- LAYER 4: Run MineralMapper ---
elif st.session_state.view == 'run_map':
    st.button("Return to Target Selection", on_click=reset_to_formation)
    st.write(f"### {st.session_state.selected_sample} (Sol {st.session_state.sol})")
    
    col_ref, col_scan = st.columns(2)
    
    # Retrieve the specific NASA IDs from lookup 
    target_info = TARGET_LOOKUP[st.session_state.selected_sample][st.session_state.sol]
    prod_id = target_info['id']
    prod_type = target_info['type']
    sol_padded = st.session_state.sol.zfill(4)
    
    # Reference Image Logic (Left Column)
    with col_ref:
        # Construct filename: [target]_[sol].jpg
        target_lower = st.session_state.selected_sample.lower()
        ref_img_name = f"{target_lower}_{st.session_state.sol}.jpg"
        ref_img_path = os.path.join(ASSETS_DIR, ref_img_name)
        
        if os.path.exists(ref_img_path):
            st.image(ref_img_path, use_container_width=True)
        else: 
            st.warning(f"Reference image {ref_img_name} not found in assets.")
            
        # Display Info Table 
        metadata_df = get_mineral_summary(st.session_state.selected_sample, st.session_state.sol)[1]
        st.table(metadata_df)
        
        
    # Mineral Scan Logic (Right Column)
    with col_scan:
        csv_file = f"ps__{sol_padded}_{prod_id}_{prod_type}_mapping.csv"
        json_file = f"ps__{sol_padded}_{prod_id}_{prod_type}_summary.json"
            
        csv_path = os.path.join(DATA_DIR, csv_file)
        json_path = os.path.join(DATA_DIR, json_file)
    
        if os.path.exists(csv_path) and os.path.exists(json_path):
            try:
                mapper = MineralMapper(csv_path, json_path)
                mapper.load_data()
                
                fig, ax = plt.subplots(figsize=(7,7))
                mapper.plot_mineral_map()
                
                fig = plt.gcf()
                fig.tight_layout(pad=1.0)
                st.pyplot(fig, width=1110)
            except Exception as e:
                st.error(f"Error during mapping: {e}")
        else: 
            st.error(f"File Not Found: Expected {csv_file}")
            st.info(f"Check directory: {DATA_DIR}")
        
        # Display Mineral Table 
        summary_df = get_mineral_summary(st.session_state.selected_sample, st.session_state.sol)[0]
        if summary_df is not None:
            st.table(summary_df)
        else:
            st.caption("Summary data not available.")
    
    st.divider()    
            

