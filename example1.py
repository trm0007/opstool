"""
Structural Model Builder - Streamlit App
Enhanced with multiple examples and dynamic configuration
"""

import numpy as np
import streamlit as st
import os
import shutil
from pathlib import Path
from io import BytesIO
import zipfile


def create_regular_polygon_nodes(center_x, center_y, radius, n_sides, start_id, z=0.0):
    """Create regular polygon nodes dictionary"""
    angles = np.linspace(0, 2*np.pi, n_sides + 1)[:-1]
    nodes = {}
    for i, angle in enumerate(angles):
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        nodes[start_id + i] = (x, y, z)
    return nodes


st.set_page_config(page_title="Model Builder", page_icon="🏗️", layout="wide")

st.markdown("""<style>
.main-header {font-size: 2.5rem; font-weight: 700; background: linear-gradient(120deg, #2196F3, #00BCD4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;}
.stButton>button {border-radius: 8px; font-weight: 600; height: 3rem;}
.config-box {background: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #2196F3; margin: 1rem 0;}
.error-box {background: #fee; padding: 1rem; border-radius: 10px; border-left: 4px solid #f44336; margin: 1rem 0;}
.example-card {padding: 1rem; border: 2px solid #e0e0e0; border-radius: 10px; cursor: pointer; transition: all 0.3s; margin-bottom: 1rem;}
.example-card:hover {border-color: #2196F3; background: #f5f9ff;}
.example-card.selected {border-color: #2196F3; background: #e3f2fd;}
.example-title {font-weight: 600; margin-bottom: 0.5rem; color: #1976D2;}
.example-desc {font-size: 0.9rem; color: #666;}
</style>""", unsafe_allow_html=True)

# Initialize session state
if 'config_text' not in st.session_state:
    st.session_state.config_text = ""
if 'config_added' not in st.session_state:
    st.session_state.config_added = False
if 'model_built' not in st.session_state:
    st.session_state.model_built = False
if 'output_dir' not in st.session_state:
    st.session_state.output_dir = "output"
if 'build_results' not in st.session_state:
    st.session_state.build_results = None
if 'selected_example' not in st.session_state:
    st.session_state.selected_example = None

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def patch_gmsh():
    """CRITICAL FIX: Patch signal handling before GMSH"""
    import signal as sig
    orig = sig.signal
    def dummy(sn, h):
        try:
            return orig(sn, h)
        except ValueError:
            return None
    sig.signal = dummy
    return orig

def create_default_examples():
    """Create minimal default examples"""
    examples = {}
    
    # Example 1: Simple Building
    examples['simple_building'] = '''...'''  # This one is probably fine
    
    # Example 2: Frame with Springs
    examples['frame_springs'] = '''...'''  # This one is probably fine


    # Example 3: Complex Structure - WITH IMPORT STATEMENTS
    
        # Example 3: Complex Structure - WITH IMPORT STATEMENTS
        # Example 3: Complex Structure - WITH IMPORT STATEMENTS
    examples['complex_structure'] = r'''# ===========================================================================================
# MODEL CREATION SCRIPT - TRM007 COMPLETE
# ===========================================================================================
# This script creates a 3-story building with:
# 1. Three different fiber sections (Rectangular, Circular, L-shaped with hollow core)
# 2. 24 nodes (4 stories × 6 columns) - manually defined
# 3. 4 slabs (2 on 1st floor, 2 on 2nd floor)
# 4. 6 footings (rectangular and circular shapes)
# 5. Zero-length springs at all footing mesh nodes
# 6. Loads and masses on all structural components
# 7. Both fiber section elements and elastic elements
# ===========================================================================================

import numpy as np
import os
import opstool as opst
from model_creation import build_model, generate_complete_model_file

# ===========================================================================================
# STEP 1: MATERIAL DEFINITIONS
# ===========================================================================================

concrete_materials_trm007 = {
    'concrete_cover': {
        'elastic_modulus': 4000.0,  # ksi
        'poissons_ratio': 0.2,
        'density': 0.150,  # kcf
        'yield_strength': 4.5,  # ksi
        'color': '#ffd700'
    },
    'concrete_core': {
        'elastic_modulus': 4500.0,  # ksi
        'poissons_ratio': 0.2,
        'density': 0.155,  # kcf
        'yield_strength': 6.0,  # ksi
        'color': '#87ceeb'
    },
    'steel_rebar': {
        'elastic_modulus': 29000.0,  # ksi
        'poissons_ratio': 0.3,
        'density': 0.490,  # kcf
        'yield_strength': 75.0,  # ksi
        'color': '#ff4500'
    },
    'hollow_core_material': {
        'elastic_modulus': 3500.0,  # ksi
        'poissons_ratio': 0.2,
        'density': 0.140,  # kcf
        'yield_strength': 3.5,  # ksi
        'color': '#a9a9a9'
    }
}

# ===========================================================================================
# STEP 2: FIBER SECTION DEFINITIONS
# ===========================================================================================

# 1. RECTANGULAR SECTION (24" × 18")
section_rect_outline = [[-12.0, -9.0], [12.0, -9.0], [12.0, 9.0], [-12.0, 9.0]]
section_rect_cover = 2.0

section_rect_rebar = [{
    'type': 'points',
    'points': [
        [-10.0, -7.0], [10.0, -7.0], [10.0, 7.0], [-10.0, 7.0],
        [-10.0, 0.0], [10.0, 0.0]
    ],
    'dia': 1.128,
    'color': 'red',
    'group_name': 'Rectangular_Rebars'
}]

section_rect_mat_tags = {'cover': 101, 'core': 102, 'rebar': 103}

# 2. CIRCULAR SECTION (20" diameter)
section_circular_outline = opst.pre.section.create_circle_points(
    xo=[0.0, 0.0], radius=10.0, angles=(0, 360), n_sub=48
)
section_circular_cover = 2.0

section_circular_rebar = [{
    'type': 'circle',
    'xo': [0.0, 0.0],
    'radius': 8.0,
    'dia': 1.0,
    'n': 8,
    'angles': (0, 360),
    'color': 'blue',
    'group_name': 'Circular_Rebars'
}]

section_circular_mat_tags = {'cover': 104, 'core': 105, 'rebar': 106}

# 3. L-SHAPED SECTION WITH HOLLOW CORE
section_l_outline = [
    [-12.0, -12.0], [12.0, -12.0], [12.0, 0.0],
    [0.0, 0.0], [0.0, 12.0], [-12.0, 12.0]
]

section_l_hole = [
    [-10.0, -10.0], [10.0, -10.0], [10.0, -2.0],
    [-2.0, -2.0], [-2.0, 10.0], [-10.0, 10.0]
]

section_l_cover = 2.0

section_l_rebar = [{
    'type': 'points',
    'points': [
        [-10.0, -10.0], [10.0, -10.0], [10.0, -2.0], [5.0, -5.0],
        [-2.0, -2.0], [-2.0, 10.0], [-5.0, 5.0], [-10.0, 10.0]
    ],
    'dia': 1.27,
    'color': 'green',
    'group_name': 'L_Section_Rebars'
}]

section_l_mat_tags = {'cover': 107, 'core': 108, 'rebar': 109, 'hollow': 110}

# ===========================================================================================
# STEP 3: UNIAXIAL MATERIALS
# ===========================================================================================

G_concrete = 1600.0  # ksi

material_params_trm007 = [
    # Rectangular section materials
    ['Concrete01', 101, -4.5, -0.002, -0.85, -0.006],
    ['Concrete01', 102, -6.0, -0.002, -0.9, -0.008],
    ['Steel01', 103, 75.0, 29000.0, 0.015],
    
    # Circular section materials
    ['Concrete01', 104, -4.5, -0.002, -0.85, -0.006],
    ['Concrete01', 105, -6.0, -0.002, -0.9, -0.008],
    ['Steel01', 106, 75.0, 29000.0, 0.015],
    
    # L-shaped section materials
    ['Concrete01', 107, -4.5, -0.002, -0.85, -0.006],
    ['Concrete01', 108, -6.0, -0.002, -0.9, -0.008],
    ['Steel01', 109, 75.0, 29000.0, 0.015],
    ['Concrete01', 110, -3.5, -0.002, -0.8, -0.005],
    
    # Spring materials
    ['ENT', 1001, 1e9],
    ['ENT', 1002, 1e8],
]

# ===========================================================================================
# STEP 4: NODE COORDINATES (MANUALLY DEFINED)
# ===========================================================================================

node_coords_trm007 = {
    # Ground floor (Z=0)
    1: (0.0, 0.0, 0.0),
    2: (25.0, 0.0, 0.0),
    3: (50.0, 0.0, 0.0),
    4: (0.0, 20.0, 0.0),
    5: (25.0, 20.0, 0.0),
    6: (50.0, 20.0, 0.0),
    
    # 1st floor (Z=12)
    7: (0.0, 0.0, 12.0),
    8: (25.0, 0.0, 12.0),
    9: (50.0, 0.0, 12.0),
    10: (0.0, 20.0, 12.0),
    11: (25.0, 20.0, 12.0),
    12: (50.0, 20.0, 12.0),
    
    # 2nd floor (Z=24)
    13: (0.0, 0.0, 24.0),
    14: (25.0, 0.0, 24.0),
    15: (50.0, 0.0, 24.0),
    16: (0.0, 20.0, 24.0),
    17: (25.0, 20.0, 24.0),
    18: (50.0, 20.0, 24.0),
    
    # 3rd floor (Z=36)
    19: (0.0, 0.0, 36.0),
    20: (25.0, 0.0, 36.0),
    21: (50.0, 0.0, 36.0),
    22: (0.0, 20.0, 36.0),
    23: (25.0, 20.0, 36.0),
    24: (50.0, 20.0, 36.0),
}

# ===========================================================================================
# STEP 5: BOUNDARY CONDITIONS
# ===========================================================================================

boundary_conditions_trm007 = {}

# All nodes free (springs will handle foundation)
for nid in range(1, 25):
    boundary_conditions_trm007[nid] = [0, 0, 0, 0, 0, 0]

# ===========================================================================================
# STEP 6: ELEMENT CONFIGURATIONS
# ===========================================================================================

element_configs_trm007 = {
    'transformations': [
        {'type': 'Linear', 'tag': 1, 'vecxz': [1, 0, 0]},
        {'type': 'Linear', 'tag': 2, 'vecxz': [0, 0, 1]}
    ],
    
    'integrations': [
        {'type': 'Lobatto', 'tag': 1, 'sec_tag': 101, 'np': 7},
        {'type': 'Lobatto', 'tag': 2, 'sec_tag': 102, 'np': 7},
        {'type': 'Lobatto', 'tag': 3, 'sec_tag': 103, 'np': 7}
    ],
    
    'force_beam_columns': [
        # Ground to 1st floor columns (Fiber sections)
        {'tag': 1, 'node_i': 1, 'node_j': 7, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 2, 'node_i': 2, 'node_j': 8, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 3, 'node_i': 3, 'node_j': 9, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 4, 'node_i': 4, 'node_j': 10, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 5, 'node_i': 5, 'node_j': 11, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 6, 'node_i': 6, 'node_j': 12, 'transf_tag': 1, 'integ_tag': 3},
        
        # 1st to 2nd floor columns (Fiber sections)
        {'tag': 7, 'node_i': 7, 'node_j': 13, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 8, 'node_i': 8, 'node_j': 14, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 9, 'node_i': 9, 'node_j': 15, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 10, 'node_i': 10, 'node_j': 16, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 11, 'node_i': 11, 'node_j': 17, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 12, 'node_i': 12, 'node_j': 18, 'transf_tag': 1, 'integ_tag': 3},
        
        # 2nd to 3rd floor columns (Fiber sections)
        {'tag': 13, 'node_i': 13, 'node_j': 19, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 14, 'node_i': 14, 'node_j': 20, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 15, 'node_i': 15, 'node_j': 21, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 16, 'node_i': 16, 'node_j': 22, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 17, 'node_i': 17, 'node_j': 23, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 18, 'node_i': 18, 'node_j': 24, 'transf_tag': 1, 'integ_tag': 3},
    ],
    
    # Elastic sections for beams
    'elastic_sections': [
        {'sec_tag': 200, 'E': 3600.0, 'A': 576.0, 'Iz': 27648.0, 'Iy': 27648.0, 'G': 1500.0, 'J': 44236.8}
    ],
    
    # Elastic beam-column elements
    'elastic_beam_columns': [
        # 1st floor beams
        {'tag': 101, 'node_i': 7, 'node_j': 8, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 102, 'node_i': 8, 'node_j': 9, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 103, 'node_i': 10, 'node_j': 11, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 104, 'node_i': 11, 'node_j': 12, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 105, 'node_i': 7, 'node_j': 10, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 106, 'node_i': 9, 'node_j': 12, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        
        # 2nd floor beams
        {'tag': 107, 'node_i': 13, 'node_j': 14, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 108, 'node_i': 14, 'node_j': 15, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 109, 'node_i': 16, 'node_j': 17, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 110, 'node_i': 17, 'node_j': 18, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 111, 'node_i': 13, 'node_j': 16, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 112, 'node_i': 15, 'node_j': 18, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        
        # 3rd floor beams
        {'tag': 113, 'node_i': 19, 'node_j': 20, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 114, 'node_i': 20, 'node_j': 21, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 115, 'node_i': 22, 'node_j': 23, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 116, 'node_i': 23, 'node_j': 24, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 117, 'node_i': 19, 'node_j': 22, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 118, 'node_i': 21, 'node_j': 24, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
    ]
}

# ===========================================================================================
# STEP 7: SLAB CONFIGURATIONS (4 slabs total - 2 per floor)
# ===========================================================================================

slab_configs_trm007 = []

# 1st Floor Slabs (Z=12)
# Slab 1: Left half (0-25, 0-20)
slab_configs_trm007.append({
    'name': 'Slab_1st_Left',
    'type': 'slab',
    'boundary_nodes': {
        7: (0.0, 0.0, 12.0),
        8: (25.0, 0.0, 12.0),
        11: (25.0, 20.0, 12.0),
        10: (0.0, 20.0, 12.0)
    },
    'mesh_size': 4.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'slab_1st_left.py',
    'png_file': 'slab_1st_left.png',
    'shell_material_config': ("ElasticIsotropic", 301, 3600.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 301, 301, 8.0 / 12.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'element_start_id': 10000,
    'spring_node_start_id': 1000000,
    'start_node_id': 100000,
    'start_element_id': 110000,
    'load_configs': {
        'pressure': -150.0,
        'time_series_tag': 101,
        'pattern_tag': 201,
        'element_tags': None
    }
})

# Slab 2: Right half (25-50, 0-20)
slab_configs_trm007.append({
    'name': 'Slab_1st_Right',
    'type': 'slab',
    'boundary_nodes': {
        8: (25.0, 0.0, 12.0),
        9: (50.0, 0.0, 12.0),
        12: (50.0, 20.0, 12.0),
        11: (25.0, 20.0, 12.0)
    },
    'mesh_size': 4.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'slab_1st_right.py',
    'png_file': 'slab_1st_right.png',
    'shell_material_config': ("ElasticIsotropic", 302, 3600.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 302, 302, 8.0 / 12.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'element_start_id': 20000,
    'spring_node_start_id': 1100000,
    'start_node_id': 200000,
    'start_element_id': 210000,
    'load_configs': {
        'pressure': -150.0,
        'time_series_tag': 102,
        'pattern_tag': 202,
        'element_tags': None
    }
})

# 2nd Floor Slabs (Z=24)
# Slab 3: Left half (0-25, 0-20)
slab_configs_trm007.append({
    'name': 'Slab_2nd_Left',
    'type': 'slab',
    'boundary_nodes': {
        13: (0.0, 0.0, 24.0),
        14: (25.0, 0.0, 24.0),
        17: (25.0, 20.0, 24.0),
        16: (0.0, 20.0, 24.0)
    },
    'mesh_size': 4.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'slab_2nd_left.py',
    'png_file': 'slab_2nd_left.png',
    'shell_material_config': ("ElasticIsotropic", 303, 3600.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 303, 303, 8.0 / 12.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'element_start_id': 30000,
    'spring_node_start_id': 1200000,
    'start_node_id': 300000,
    'start_element_id': 310000,
    'load_configs': {
        'pressure': -150.0,
        'time_series_tag': 103,
        'pattern_tag': 203,
        'element_tags': None
    }
})

# Slab 4: Right half (25-50, 0-20)
slab_configs_trm007.append({
    'name': 'Slab_2nd_Right',
    'type': 'slab',
    'boundary_nodes': {
        14: (25.0, 0.0, 24.0),
        15: (50.0, 0.0, 24.0),
        18: (50.0, 20.0, 24.0),
        17: (25.0, 20.0, 24.0)
    },
    'mesh_size': 4.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'slab_2nd_right.py',
    'png_file': 'slab_2nd_right.png',
    'shell_material_config': ("ElasticIsotropic", 304, 3600.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 304, 304, 8.0 / 12.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'element_start_id': 40000,
    'spring_node_start_id': 1300000,
    'start_node_id': 400000,
    'start_element_id': 410000,
    'load_configs': {
        'pressure': -150.0,
        'time_series_tag': 104,
        'pattern_tag': 204,
        'element_tags': None
    }
})

# ===========================================================================================
# STEP 8: FOOTING CONFIGURATIONS (6 footings - alternating shapes)
# ===========================================================================================

footing_configs = []

# Footing 1 (Node 1): Rectangular
footing_configs.append({
    'name': 'Footing_1_Rect',
    'type': 'footing',
    'boundary_nodes': {
        5001: (-4.0, -4.0, -1.0),
        5002: (4.0, -4.0, -1.0),
        5003: (4.0, 4.0, -1.0),
        5004: (-4.0, 4.0, -1.0)
    },
    'mesh_size': 2.0,
    'internal_points': {1: (0.0, 0.0, -1.0)},  # Column base node 1
    'voids': None,
    'py_file': 'footing_1_rect.py',
    'png_file': 'footing_1_rect.png',
    'shell_material_config': ("ElasticIsotropic", 401, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 401, 401, 2.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],  # Complete material definition
    'zero_length_directions': [3],  # Vertical direction
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 50000,
    'spring_node_start_id': 2000000,
    'start_node_id': 500000,
    'start_element_id': 510000,
    'load_configs': None
})


  
    

# Footing 2 (Node 2): Circular
footing_configs.append({
    'name': 'Footing_2_Circ',
    'type': 'footing',
    'boundary_nodes': create_regular_polygon_nodes(25.0, 0.0, 3.5, 12, 5101, -1.0),
    'mesh_size': 2.0,
    'internal_points': {2: (25.0, 0.0, -1.0)},
    'voids': None,
    'py_file': 'footing_2_circ.py',
    'png_file': 'footing_2_circ.png',
    'shell_material_config': ("ElasticIsotropic", 402, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 402, 402, 2.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],  # Complete material definition
    'zero_length_directions': [3],  # Vertical direction
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 51000,
    'spring_node_start_id': 2100000,
    'start_node_id': 510000,
    'start_element_id': 520000,
    'load_configs': None
})

# Footing 3 (Node 3): Rectangular
footing_configs.append({
    'name': 'Footing_3_Rect',
    'type': 'footing',
    'boundary_nodes': {
        5201: (50.0 - 4.0, -4.0, -1.0),
        5202: (50.0 + 4.0, -4.0, -1.0),
        5203: (50.0 + 4.0, 4.0, -1.0),
        5204: (50.0 - 4.0, 4.0, -1.0)
    },
    'mesh_size': 2.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'footing_3_rect.py',
    'png_file': 'footing_3_rect.png',
    'shell_material_config': ("ElasticIsotropic", 403, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 403, 403, 2.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],  # Complete material definition
    'zero_length_directions': [3],  # Vertical direction
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 52000,
    'spring_node_start_id': 2200000,
    'start_node_id': 520000,
    'start_element_id': 530000,
    'load_configs': None
})

# Footing 4 (Node 4): Circular
footing_configs.append({
    'name': 'Footing_4_Circ',
    'type': 'footing',
    'boundary_nodes': {
        5301 + i: (0.0 + 4.0 * np.cos(i * 2 * np.pi / 16), 20.0 + 4.0 * np.sin(i * 2 * np.pi / 16), -1.0)
        for i in range(16)
    },
    'mesh_size': 2.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'footing_4_circ.py',
    'png_file': 'footing_4_circ.png',
    'shell_material_config': ("ElasticIsotropic", 404, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 404, 404, 2.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],  # Complete material definition
    'zero_length_directions': [3],  # Vertical direction
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 53000,
    'spring_node_start_id': 2300000,
    'start_node_id': 530000,
    'start_element_id': 540000,
    'load_configs': None
})

# Footing 5 (Node 5): Rectangular
footing_configs.append({
    'name': 'Footing_5_Rect',
    'type': 'footing',
    'boundary_nodes': {
        5401: (25.0 - 4.0, 20.0 - 4.0, -1.0),
        5402: (25.0 + 4.0, 20.0 - 4.0, -1.0),
        5403: (25.0 + 4.0, 20.0 + 4.0, -1.0),
        5404: (25.0 - 4.0, 20.0 + 4.0, -1.0)
    },
    'mesh_size': 2.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'footing_5_rect.py',
    'png_file': 'footing_5_rect.png',
    'shell_material_config': ("ElasticIsotropic", 405, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 405, 405, 2.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],  # Complete material definition
    'zero_length_directions': [3],  # Vertical direction
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 54000,
    'spring_node_start_id': 2400000,
    'start_node_id': 540000,
    'start_element_id': 550000,
    'load_configs': None
})

# Footing 6 (Node 6): Circular
footing_configs.append({
    'name': 'Footing_6_Circ',
    'type': 'footing',
    'boundary_nodes': {
        5501 + i: (50.0 + 4.0 * np.cos(i * 2 * np.pi / 16), 20.0 + 4.0 * np.sin(i * 2 * np.pi / 16), -1.0)
        for i in range(16)
    },
    'mesh_size': 2.0,
    'internal_points': None,
    'voids': None,
    'py_file': 'footing_6_circ.py',
    'png_file': 'footing_6_circ.png',
    'shell_material_config': ("ElasticIsotropic", 406, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 406, 406, 2.0),
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],  # Complete material definition
    'zero_length_directions': [3],  # Vertical direction
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 55000,
    'spring_node_start_id': 2500000,
    'start_node_id': 550000,
    'start_element_id': 560000,
    'load_configs': None
})

# Combine all shell configurations
all_shell_configs = slab_configs_trm007 + footing_configs

# ===========================================================================================
# STEP 9: LOAD CONFIGURATIONS
# ===========================================================================================

load_configs = {
    'time_series': [
        {'tag': 1, 'type': 'Linear'},
        {'tag': 101, 'type': 'Linear'},
        {'tag': 102, 'type': 'Linear'},
        {'tag': 103, 'type': 'Linear'},
        {'tag': 104, 'type': 'Linear'}
    ],
    
    'patterns': [
        {'tag': 1, 'type': 'Plain', 'ts_tag': 1},
        {'tag': 201, 'type': 'Plain', 'ts_tag': 101},
        {'tag': 202, 'type': 'Plain', 'ts_tag': 102},
        {'tag': 203, 'type': 'Plain', 'ts_tag': 103},
        {'tag': 204, 'type': 'Plain', 'ts_tag': 104}
    ],
    
    # Nodal point loads
    'nodal_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                {'node': 19, 'forces': [50, 0, -300, 0, 0, 0]},
                {'node': 20, 'forces': [0, 50, -400, 0, 0, 0]},
                {'node': 21, 'forces': [-50, 0, -300, 0, 0, 0]},
                {'node': 22, 'forces': [0, -50, -400, 0, 0, 0]},
                {'node': 23, 'forces': [75, 75, -500, 0, 0, 0]},
                {'node': 24, 'forces': [-75, -75, -500, 0, 0, 0]}
            ]
        }
    ],
    
    # Beam uniform loads
    'beam_uniform_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                {'elements': [101, 102, 103, 104], 'wy': 0, 'wz': -15.0},
                {'elements': [107, 108, 109, 110], 'wy': 0, 'wz': -15.0},
                {'elements': [113, 114, 115, 116], 'wy': 0, 'wz': -12.0}
            ]
        }
    ],
    
    # Shell surface loads (defined in slab configs)
    'shell_surface_loads': []
}

# ===========================================================================================
# STEP 10: MASS CONFIGURATIONS
# ===========================================================================================

mass_configs = {
    'beam_column_mass': [
        {'tag': 101, 'density': 0.150, 'area': 576.0},
        {'tag': 102, 'density': 0.150, 'area': 576.0},
        {'tag': 107, 'density': 0.150, 'area': 576.0},
        {'tag': 113, 'density': 0.150, 'area': 576.0}
    ],
    
    'nodal_mass': [
        {'node': 19, 'mass': 100.0},
        {'node': 20, 'mass': 120.0},
        {'node': 21, 'mass': 100.0},
        {'node': 22, 'mass': 120.0},
        {'node': 23, 'mass': 150.0},
        {'node': 24, 'mass': 150.0}
    ],
    
    'shell_mass': {
        'calculate': True,
        'exclude': [],
        'scale': 1.0
    }
}

# ===========================================================================================
# STEP 11: BUILD THE MODEL
# ===========================================================================================

print("\n" + "="*80)
print("BUILDING TRM007 COMPLETE MODEL")
print("="*80)

materials_list_trm007 = [
    concrete_materials_trm007,
    concrete_materials_trm007,
    concrete_materials_trm007
]

results = build_model(
    model_params={'ndm': 3, 'ndf': 6},
    materials_list=materials_list_trm007,
    outline_points_list=[section_rect_outline, section_circular_outline, section_l_outline],
    rebar_configs_list=[section_rect_rebar, section_circular_rebar, section_l_rebar],
    section_params_list=[
        {
            'cover': section_rect_cover,
            'mesh_size': 4.0,
            'mat_tags': section_rect_mat_tags,
            'sec_tag': 101,
            'G': G_concrete,
            'save_prefix': 'section_rectangular_24x18',
            'section_name': 'Rectangular_24x18'
        },
        {
            'cover': section_circular_cover,
            'mesh_size': 4.0,
            'mat_tags': section_circular_mat_tags,
            'sec_tag': 102,
            'G': G_concrete,
            'save_prefix': 'section_circular_20dia',
            'section_name': 'Circular_20dia'
        },
        {
            'cover': section_l_cover,
            'mesh_size': 4.0,
            'mat_tags': section_l_mat_tags,
            'sec_tag': 103,
            'G': G_concrete,
            'save_prefix': 'section_l_shaped_hollow',
            'section_name': 'L_Shaped_Hollow',
            'core_holes': [section_l_hole]
        }
    ],
    material_params=material_params_trm007,
    node_coords=node_coords_trm007,
    boundary_conditions=boundary_conditions_trm007,
    element_configs=element_configs_trm007,
    spring_configs=None,
    nodal_spring_configs=None,
    load_configs=load_configs,
    mass_configs=mass_configs,
    output_dir="output",
    slab_configs=all_shell_configs,
    existing_frame_nodes=node_coords_trm007,
    visualize=True
)

# ===========================================================================================
# STEP 12: GENERATE COMPLETE MODEL FILE
# ===========================================================================================


print("\n" + "="*80)
print("MODEL GENERATION COMPLETE!")
print("="*80)
'''

    return examples

def validate_config(config_text):
    """Validate configuration syntax and structure"""
    try:
        compile(config_text, '<string>', 'exec')
        return True, "Syntax is valid"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Configuration error: {e}"

# Load examples
available_examples = create_default_examples()

# ============================================================
# MAIN APP LAYOUT
# ============================================================

st.markdown('<p class="main-header">🏗️ Structural Model Builder</p>', unsafe_allow_html=True)

# Example selection section
st.markdown("## 📚 Select an Example")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏢 Simple Building", use_container_width=True,
                type="primary" if st.session_state.selected_example == "simple_building" else "secondary"):
        st.session_state.selected_example = "simple_building"
        st.session_state.config_text = available_examples["simple_building"]
        st.session_state.config_added = False
        st.rerun()

with col2:
    if st.button("🔩 Frame with Springs", use_container_width=True,
                type="primary" if st.session_state.selected_example == "frame_springs" else "secondary"):
        st.session_state.selected_example = "frame_springs"
        st.session_state.config_text = available_examples["frame_springs"]
        st.session_state.config_added = False
        st.rerun()

with col3:
    if st.button("🏗️ Complex Structure", use_container_width=True,
                type="primary" if st.session_state.selected_example == "complex_structure" else "secondary"):
        st.session_state.selected_example = "complex_structure"
        st.session_state.config_text = available_examples["complex_structure"]
        st.session_state.config_added = False
        st.rerun()

# Custom configuration upload
st.markdown("---")
st.markdown("## 📤 Upload Your Own Configuration")

uploaded_file = st.file_uploader("Choose a Python configuration file", type=['py'])
if uploaded_file is not None:
    try:
        content = uploaded_file.read().decode('utf-8')
        st.session_state.config_text = content
        st.session_state.selected_example = "custom_upload"
        st.session_state.config_added = False
        st.success("✅ Configuration loaded from file!")
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")

# Configuration editor section
st.markdown("---")
st.markdown("## ✏️ Configuration Editor")

if st.session_state.config_text:
    # Show which example is selected
    if st.session_state.selected_example and st.session_state.selected_example in available_examples:
        example_name = st.session_state.selected_example.replace('_', ' ').title()
        st.info(f"Currently editing: **{example_name}**")
    
    # Configuration editor
    edited_config = st.text_area("Edit your configuration code below:", 
                               value=st.session_state.config_text, 
                               height=400,
                               key="config_editor")
    
    if edited_config != st.session_state.config_text:
        st.session_state.config_text = edited_config
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Validate & Prepare", type="primary", use_container_width=True):
            is_valid, msg = validate_config(st.session_state.config_text)
            if is_valid:
                st.session_state.config_added = True
                st.success("✅ Configuration is valid and ready to build!")
            else:
                st.error(f"❌ {msg}")
    
    with col2:
        if st.button("🔄 Reset Example", use_container_width=True):
            if st.session_state.selected_example and st.session_state.selected_example in available_examples:
                st.session_state.config_text = available_examples[st.session_state.selected_example]
                st.rerun()
    
    with col3:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.config_text = ""
            st.session_state.selected_example = None
            st.session_state.config_added = False
            st.session_state.model_built = False
            st.rerun()

else:
    st.info("👆 Select an example above or upload your own configuration file to get started.")

# ============================================================
# BUILD SECTION
# ============================================================

if st.session_state.config_added:
    st.markdown("---")
    st.markdown("## 🚀 Build Model")
    
    with st.expander("📋 Configuration Preview", expanded=False):
        st.code(st.session_state.config_text, language='python')
    
    if st.button("🔨 Build Model Now", type="primary", use_container_width=True):
        with st.spinner("Building model..."):
            try:
                # Clean output directory
                od = st.session_state.output_dir
                if os.path.exists(od):
                    shutil.rmtree(od)
                os.makedirs(od, exist_ok=True)
                
                # Patch GMSH
                patch_gmsh()
                
                # Import required functions
                from model_creation import build_model, generate_complete_model_file
                from shell_design import create_regular_polygon_nodes
                # Prepare execution namespace with the required functions
                eg = {
                    'build_model': build_model,
                    'generate_complete_model_file': generate_complete_model_file,
                    'np': __import__('numpy'),
                    'opst': __import__('opstool'),
                    'create_regular_polygon_nodes': create_regular_polygon_nodes

                }
                
                # Execute user's ENTIRE configuration script
                # This includes all variable definitions AND the build_model() call
                exec(st.session_state.config_text, eg)
                
                # Try to get results from execution
                if 'results' in eg:
                    st.session_state.build_results = eg['results']
                else:
                    # Look for any variable with 'results' in the name
                    results_var = next((v for k, v in eg.items() if 'result' in k.lower()), None)
                    if results_var:
                        st.session_state.build_results = results_var
                
                st.session_state.model_built = True
                st.success("✅ Model built successfully!")
                st.rerun()
                
            except NameError as e:
                if "'build_model' is not defined" in str(e):
                    st.error("❌ The configuration must import build_model from model_creation")
                    st.info("Add this at the top of your configuration: `from model_creation import build_model, generate_complete_model_file`")
                else:
                    st.error(f"❌ Name error: {e}")
            except ModuleNotFoundError as e:
                st.error(f"❌ Module not found: {e}")
                st.info("Make sure you have installed all required packages.")
            except SyntaxError as e:
                st.error(f"❌ Syntax error in configuration: {e}")
            except Exception as e:
                st.error(f"❌ Error building model: {e}")
                import traceback
                with st.expander("Detailed Error Traceback"):
                    st.code(traceback.format_exc(), language='bash')

# ============================================================
# RESULTS SECTION
# ============================================================

if st.session_state.model_built and os.path.exists(st.session_state.output_dir):
    st.markdown("---")
    st.markdown("## 📊 Build Results")
    
    # Count files
    files = list(Path(st.session_state.output_dir).rglob("*"))
    imgs = [f for f in files if f.suffix.lower() in ['.png', '.jpg', '.jpeg'] and f.is_file()]
    pys = [f for f in files if f.suffix == '.py' and f.is_file()]
    htmls = [f for f in files if f.suffix == '.html' and f.is_file()]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.session_state.build_results:
            if isinstance(st.session_state.build_results, dict) and 'total_nodes' in st.session_state.build_results:
                st.metric("📊 Nodes", st.session_state.build_results.get('total_nodes', 'N/A'))
            else:
                st.metric("📊 Nodes", "Built")
        else:
            st.metric("📊 Nodes", "Built")
    with col2:
        if st.session_state.build_results:
            if isinstance(st.session_state.build_results, dict) and 'total_elements' in st.session_state.build_results:
                st.metric("🔧 Elements", st.session_state.build_results.get('total_elements', 'N/A'))
            else:
                st.metric("🔧 Elements", "Built")
        else:
            st.metric("🔧 Elements", "Built")
    with col3:
        st.metric("🖼️ Images", len(imgs))
    with col4:
        st.metric("📁 Files", len(pys) + len(htmls))
    
    # Display images
    if imgs:
        st.markdown("### 🖼️ Generated Images")
        cols = st.columns(2)
        for i, img in enumerate(sorted(imgs)):
            with cols[i % 2]:
                st.image(str(img), caption=img.name, use_container_width=True)
                with open(img, 'rb') as f:
                    st.download_button(f"⬇️ {img.name}", f.read(), img.name, key=f"img_{i}")
    
    # Display 3D models
    if htmls:
        st.markdown("### 🌐 3D Visualizations")
        for i, h in enumerate(sorted(htmls)):
            with st.expander(f"📈 {h.name}", expanded=(i == 0)):
                with open(h, encoding='utf-8') as f:
                    html_content = f.read()
                    st.components.v1.html(html_content, height=600)
                
                with open(h, 'rb') as f:
                    st.download_button(f"⬇️ {h.name}", f.read(), h.name, key=f"html_{i}")
    
    # Display Python files
    if pys:
        st.markdown("### 🐍 Python Files")
        for i, p in enumerate(sorted(pys)):
            with st.expander(f"📄 {p.name}"):
                with open(p) as f:
                    st.code(f.read(), language='python', line_numbers=True)
                
                with open(p, 'rb') as f:
                    st.download_button(f"⬇️ {p.name}", f.read(), p.name, key=f"py_{i}")
    
    # Download all files as ZIP
    st.markdown("### 📦 Download All Files")
    
    def create_zip_archive():
        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(st.session_state.output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, st.session_state.output_dir)
                    z.write(file_path, arcname)
        buf.seek(0)
        return buf.getvalue()
    
    zip_data = create_zip_archive()
    st.download_button(
        label="📥 Download as ZIP",
        data=zip_data,
        file_name="model_output.zip",
        mime="application/zip",
        use_container_width=True
    )
    
    # Cleanup button
    if st.button("🗑️ Clean Output Directory", type="secondary", use_container_width=True):
        if os.path.exists(st.session_state.output_dir):
            shutil.rmtree(st.session_state.output_dir)
        st.session_state.model_built = False
        st.session_state.build_results = None
        st.rerun()

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    # Output directory
    new_output_dir = st.text_input("Output Directory", value=st.session_state.output_dir)
    if new_output_dir != st.session_state.output_dir:
        st.session_state.output_dir = new_output_dir
    
    st.markdown("---")
    st.markdown("### 💾 Save/Load")
    
    # Save configuration
    if st.session_state.config_text:
        config_bytes = st.session_state.config_text.encode('utf-8')
        st.download_button(
            label="💾 Save Configuration",
            data=config_bytes,
            file_name="my_configuration.py",
            mime="text/x-python",
            use_container_width=True
        )
    
    st.markdown("---")
    st.markdown("### ℹ️ Help")
    st.info("""
    **How to use:**
    1. Select an example from above
    2. Modify the configuration as needed
    3. Click 'Validate & Prepare'
    4. Click 'Build Model Now'
    
    **Your configuration must include:**
    ```python
    from model_creation import build_model, generate_complete_model_file
    
    # Define your variables...
    
    results = build_model(...)
    
    generate_complete_model_file(...)
    ```
    """)

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.9rem;'>"
    "🏗️ Structural Model Builder | Powered by Streamlit"
    "</div>",
    unsafe_allow_html=True
)

