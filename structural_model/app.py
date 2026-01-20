"""
Structural Model Builder - Professional Streamlit App with Authentication
Clean, modern interface with example management and multi-user support
"""

import numpy as np
import streamlit as st
import os
import shutil
import zipfile
import json
import hashlib
from pathlib import Path
from io import BytesIO
from datetime import datetime


# ========================================================================================
# AUTHENTICATION FUNCTIONS
# ========================================================================================

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()


def save_users():
    """Save users to JSON file"""
    os.makedirs('auth_data', exist_ok=True)
    with open('auth_data/users.json', 'w') as f:
        json.dump(st.session_state.users, f)


def load_users():
    """Load users from JSON file"""
    if os.path.exists('auth_data/users.json'):
        with open('auth_data/users.json', 'r') as f:
            return json.load(f)
    return {}


def sign_up(username, email, password):
    """Handle user registration"""
    if username in st.session_state.users:
        return False, "Username already exists!"
    
    # Check if email already exists
    for user_data in st.session_state.users.values():
        if user_data['email'] == email:
            return False, "Email already registered!"
    
    # Store user data
    st.session_state.users[username] = {
        'email': email,
        'password_hash': hash_password(password),
        'models': [],
        'examples': {}
    }
    save_users()
    
    # Create user directory
    user_dir = f"./user_data/{username}"
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(f"{user_dir}/models", exist_ok=True)
    
    return True, "Registration successful!"


def sign_in(username, password):
    """Handle user login"""
    if username not in st.session_state.users:
        return False, "Username not found!"
    
    user_data = st.session_state.users[username]
    if user_data['password_hash'] != hash_password(password):
        return False, "Invalid password!"
    
    st.session_state.authenticated = True
    st.session_state.current_user = username
    return True, "Login successful!"


def sign_out():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.config_text = ""
    st.session_state.config_added = False
    st.session_state.model_built = False
    st.session_state.selected_example = None
    st.session_state.examples = {}


def get_user_models(username):
    """Get list of models for a specific user"""
    models_dir = f"./user_data/{username}/models"
    if not os.path.exists(models_dir):
        return []
    
    models = []
    for item in os.listdir(models_dir):
        model_path = os.path.join(models_dir, item)
        if os.path.isdir(model_path):
            # Read model metadata if exists
            meta_file = os.path.join(model_path, "metadata.json")
            if os.path.exists(meta_file):
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    models.append({
                        'name': item,
                        'created': metadata.get('created', 'Unknown'),
                        'description': metadata.get('description', '')
                    })
            else:
                models.append({
                    'name': item,
                    'created': 'Unknown',
                    'description': ''
                })
    
    return sorted(models, key=lambda x: x['created'], reverse=True)


def delete_user_model(username, model_name):
    """Delete a specific model for a user"""
    model_path = f"./user_data/{username}/models/{model_name}"
    
    if os.path.exists(model_path):
        shutil.rmtree(model_path)
        return True, f"Model '{model_name}' deleted successfully!"
    return False, f"Model '{model_name}' not found!"


def delete_account(username):
    """Delete user account and all associated data"""
    # Delete user directory
    user_dir = f"./user_data/{username}"
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    
    # Remove user from users dictionary
    if username in st.session_state.users:
        del st.session_state.users[username]
        save_users()
    
    return True, "Account deleted successfully!"


def save_user_examples(username):
    """Save user's examples"""
    if username in st.session_state.users:
        st.session_state.users[username]['examples'] = st.session_state.examples
        save_users()


def load_user_examples(username):
    """Load user's examples"""
    if username in st.session_state.users:
        user_examples = st.session_state.users[username].get('examples', {})
        if not user_examples:
            user_examples = get_default_examples()
            st.session_state.users[username]['examples'] = user_examples
            save_users()
        return user_examples
    return get_default_examples()


# ========================================================================================
# ORIGINAL HELPER FUNCTIONS (UNCHANGED)
# ========================================================================================

def create_regular_polygon_nodes(center_x, center_y, radius, n_sides, start_id, z=0.0):
    """Create regular polygon nodes dictionary"""
    angles = np.linspace(0, 2*np.pi, n_sides + 1)[:-1]
    nodes = {}
    for i, angle in enumerate(angles):
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        nodes[start_id + i] = (x, y, z)
    return nodes


def patch_gmsh():
    """Fix GMSH signal handling"""
    import signal as sig
    orig = sig.signal
    def dummy(sn, h):
        try:
            return orig(sn, h)
        except ValueError:
            return None
    sig.signal = dummy
    return orig


def validate_config(config_text):
    """Validate configuration syntax"""
    try:
        compile(config_text, '<string>', 'exec')
        return True, "Valid"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def get_default_examples():
    """Get default example configurations"""
    examples = {}
    
    examples['simple_building'] = {
        'name': 'Simple Building',
        'description': '2-column structure with fiber sections',
        'code': '''# Simple Building Example
import numpy as np
from test3 import build_model
materials = {
    'concrete_cover': {'elastic_modulus': 30e9, 'poissons_ratio': 0.2, 'density': 2400, 'color': '#dbb40c'},
    'concrete_core': {'elastic_modulus': 30e9, 'poissons_ratio': 0.2, 'density': 2400, 'color': '#88b378'},
    'steel_rebar': {'elastic_modulus': 200e9, 'poissons_ratio': 0.3, 'density': 7850, 'yield_strength': 500e6, 'color': 'black'}
}
outline = [[-0.3, -0.3], [0.3, -0.3], [0.3, 0.3], [-0.3, 0.3]]
rebar = [{'type': 'points', 'points': [[-0.25, -0.25], [0.25, -0.25], [0.25, 0.25], [-0.25, 0.25]], 
          'dia': 0.02, 'color': 'black', 'group_name': 'Main_Rebars'}]
node_coords = {1: (0, 0, 0), 2: (5, 0, 0), 3: (0, 0, 3), 4: (5, 0, 3)}
boundary_conditions = {1: [1, 1, 1, 1, 1, 1], 2: [1, 1, 1, 1, 1, 1]}
element_configs = {
    'transformations': [{'type': 'Linear', 'tag': 1, 'vecxz': [0, 1, 0]}],
    'integrations': [{'type': 'Lobatto', 'tag': 1, 'sec_tag': 1, 'np': 5}],
    'force_beam_columns': [
        {'tag': 1, 'node_i': 1, 'node_j': 3, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 2, 'node_i': 2, 'node_j': 4, 'transf_tag': 1, 'integ_tag': 1}
    ],
    'elastic_beam_columns': []
}
material_params = [
    ['Concrete01', 1, -30e6, -0.002, -6e6, -0.006],
    ['Concrete01', 2, -30e6, -0.002, -6e6, -0.006],
    ['Steel01', 3, 500e6, 200e9, 0.01]
]
results = build_model(
    model_params={'ndm': 3, 'ndf': 6},
    materials_list=[materials],
    outline_points_list=[outline],
    rebar_configs_list=[rebar],
    section_params_list=[{'cover': 0.05, 'mesh_size': 0.05, 'mat_tags': {'cover': 1, 'core': 2, 'rebar': 3},
                          'sec_tag': 1, 'G': 12.5e9, 'save_prefix': 'section_1', 'section_name': 'Column_Section'}],
    material_params=material_params,
    node_coords=node_coords,
    boundary_conditions=boundary_conditions,
    element_configs=element_configs,
    spring_configs=None,
    nodal_spring_configs=None,
    diaphragm_list=None,
    load_configs=None,
    mass_configs=None,
    visualize=True,
    output_dir="output",
    slab_configs=None,
    existing_frame_nodes=None
)
'''
    }
    
    examples['frame_springs'] = {
        'name': 'Frame with Springs',
        'description': 'Frame structure with zero-length spring supports',
        'code': '''# Frame with Springs Example
import numpy as np
from test3 import build_model
materials = {
    'concrete_cover': {'elastic_modulus': 30e9, 'poissons_ratio': 0.2, 'density': 2400, 'color': '#dbb40c'},
    'concrete_core': {'elastic_modulus': 30e9, 'poissons_ratio': 0.2, 'density': 2400, 'color': '#88b378'},
    'steel_rebar': {'elastic_modulus': 200e9, 'poissons_ratio': 0.3, 'density': 7850, 'yield_strength': 500e6, 'color': 'black'}
}
outline = [[-0.4, -0.4], [0.4, -0.4], [0.4, 0.4], [-0.4, 0.4]]
rebar = [{'type': 'points', 'points': [[-0.35, -0.35], [0.35, -0.35], [0.35, 0.35], [-0.35, 0.35]], 
          'dia': 0.025, 'color': 'black', 'group_name': 'Rebars'}]
node_coords = {1: (0, 0, 0), 2: (6, 0, 0), 3: (0, 0, 4), 4: (6, 0, 4)}
boundary_conditions = {}
element_configs = {
    'transformations': [{'type': 'Linear', 'tag': 1, 'vecxz': [0, 1, 0]}],
    'integrations': [{'type': 'Lobatto', 'tag': 1, 'sec_tag': 1, 'np': 5}],
    'force_beam_columns': [
        {'tag': 1, 'node_i': 1, 'node_j': 3, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 2, 'node_i': 2, 'node_j': 4, 'transf_tag': 1, 'integ_tag': 1}
    ],
    'elastic_beam_columns': [
        {'tag': 3, 'node_i': 3, 'node_j': 4, 'A': 0.64, 'E': 30e9, 'G': 12.5e9, 'J': 0.03413, 'Iy': 0.01365, 'Iz': 0.01365, 'transf_tag': 1}
    ]
}
material_params = [
    ['Concrete01', 1, -30e6, -0.002, -6e6, -0.006],
    ['Concrete01', 2, -30e6, -0.002, -6e6, -0.006],
    ['Steel01', 3, 500e6, 200e9, 0.01],
    ['Elastic', 4, 1e8]
]
nodal_spring_configs = {
    'material_props': {'id': 4, 'directions': [1, 2, 3], 'config': ['Elastic', 4, 1e8]},
    'node_list': [(1, 0, 0, 0), (2, 6, 0, 0)],
    'boundary_condition': [1, 1, 1, 1, 1, 1],
    'element_start_id': 100000,
    'spring_node_start_id': 10000000
}
results = build_model(
    model_params={'ndm': 3, 'ndf': 6},
    materials_list=[materials],
    outline_points_list=[outline],
    rebar_configs_list=[rebar],
    section_params_list=[{'cover': 0.05, 'mesh_size': 0.05, 'mat_tags': {'cover': 1, 'core': 2, 'rebar': 3},
                          'sec_tag': 1, 'G': 12.5e9, 'save_prefix': 'section_springs', 'section_name': 'Column_Springs'}],
    material_params=material_params,
    node_coords=node_coords,
    boundary_conditions=boundary_conditions,
    element_configs=element_configs,
    spring_configs=None,
    nodal_spring_configs=nodal_spring_configs,
    diaphragm_list=None,
    load_configs=None,
    mass_configs=None,
    visualize=True,
    output_dir="output",
    slab_configs=None,
    existing_frame_nodes=None
)
'''
    }

    examples['complex_structure'] = {
        'name': 'Complex Structure',
        'description': 'Complex structure with slabs, footings and springs',
        'code': r'''# ===========================================================================================
# MODEL CREATION SCRIPT - TRM007 COMPLETE
# ===========================================================================================
import numpy as np
import os
import opstool as opst
from test3 import build_model, generate_complete_model_file, create_regular_polygon_nodes
# ===========================================================================================
# STEP 1: MATERIAL DEFINITIONS
# ===========================================================================================
concrete_materials_trm007 = {
    'concrete_cover': {
        'elastic_modulus': 4000.0,
        'poissons_ratio': 0.2,
        'density': 0.150,
        'yield_strength': 4.5,
        'color': '#ffd700'
    },
    'concrete_core': {
        'elastic_modulus': 4500.0,
        'poissons_ratio': 0.2,
        'density': 0.155,
        'yield_strength': 6.0,
        'color': '#87ceeb'
    },
    'steel_rebar': {
        'elastic_modulus': 29000.0,
        'poissons_ratio': 0.3,
        'density': 0.490,
        'yield_strength': 75.0,
        'color': '#ff4500'
    },
    'hollow_core_material': {
        'elastic_modulus': 3500.0,
        'poissons_ratio': 0.2,
        'density': 0.140,
        'yield_strength': 3.5,
        'color': '#a9a9a9'
    }
}
# Section definitions
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
G_concrete = 1600.0
material_params_trm007 = [
    ['Concrete01', 101, -4.5, -0.002, -0.85, -0.006],
    ['Concrete01', 102, -6.0, -0.002, -0.9, -0.008],
    ['Steel01', 103, 75.0, 29000.0, 0.015],
    ['Concrete01', 104, -4.5, -0.002, -0.85, -0.006],
    ['Concrete01', 105, -6.0, -0.002, -0.9, -0.008],
    ['Steel01', 106, 75.0, 29000.0, 0.015],
    ['Concrete01', 107, -4.5, -0.002, -0.85, -0.006],
    ['Concrete01', 108, -6.0, -0.002, -0.9, -0.008],
    ['Steel01', 109, 75.0, 29000.0, 0.015],
    ['Concrete01', 110, -3.5, -0.002, -0.8, -0.005],
    ['ENT', 1001, 1e9],
    ['ENT', 1002, 1e8],
]
node_coords_trm007 = {
    1: (0.0, 0.0, 0.0), 2: (25.0, 0.0, 0.0), 3: (50.0, 0.0, 0.0),
    4: (0.0, 20.0, 0.0), 5: (25.0, 20.0, 0.0), 6: (50.0, 20.0, 0.0),
    7: (0.0, 0.0, 12.0), 8: (25.0, 0.0, 12.0), 9: (50.0, 0.0, 12.0),
    10: (0.0, 20.0, 12.0), 11: (25.0, 20.0, 12.0), 12: (50.0, 20.0, 12.0),
    13: (0.0, 0.0, 24.0), 14: (25.0, 0.0, 24.0), 15: (50.0, 0.0, 24.0),
    16: (0.0, 20.0, 24.0), 17: (25.0, 20.0, 24.0), 18: (50.0, 20.0, 24.0),
    19: (0.0, 0.0, 36.0), 20: (25.0, 0.0, 36.0), 21: (50.0, 0.0, 36.0),
    22: (0.0, 20.0, 36.0), 23: (25.0, 20.0, 36.0), 24: (50.0, 20.0, 36.0),
}
boundary_conditions_trm007 = {}
for nid in range(1, 25):
    boundary_conditions_trm007[nid] = [0, 0, 0, 0, 0, 0]
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
        {'tag': 1, 'node_i': 1, 'node_j': 7, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 2, 'node_i': 2, 'node_j': 8, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 3, 'node_i': 3, 'node_j': 9, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 4, 'node_i': 4, 'node_j': 10, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 5, 'node_i': 5, 'node_j': 11, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 6, 'node_i': 6, 'node_j': 12, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 7, 'node_i': 7, 'node_j': 13, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 8, 'node_i': 8, 'node_j': 14, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 9, 'node_i': 9, 'node_j': 15, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 10, 'node_i': 10, 'node_j': 16, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 11, 'node_i': 11, 'node_j': 17, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 12, 'node_i': 12, 'node_j': 18, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 13, 'node_i': 13, 'node_j': 19, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 14, 'node_i': 14, 'node_j': 20, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 15, 'node_i': 15, 'node_j': 21, 'transf_tag': 1, 'integ_tag': 3},
        {'tag': 16, 'node_i': 16, 'node_j': 22, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 17, 'node_i': 17, 'node_j': 23, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 18, 'node_i': 18, 'node_j': 24, 'transf_tag': 1, 'integ_tag': 3},
    ],
    'elastic_sections': [
        {'sec_tag': 200, 'E': 3600.0, 'A': 576.0, 'Iz': 27648.0, 'Iy': 27648.0, 'G': 1500.0, 'J': 44236.8}
    ],
    'elastic_beam_columns': [
        {'tag': 101, 'node_i': 7, 'node_j': 8, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 102, 'node_i': 8, 'node_j': 9, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 103, 'node_i': 10, 'node_j': 11, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 104, 'node_i': 11, 'node_j': 12, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 105, 'node_i': 7, 'node_j': 10, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 106, 'node_i': 9, 'node_j': 12, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 107, 'node_i': 13, 'node_j': 14, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 108, 'node_i': 14, 'node_j': 15, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 109, 'node_i': 16, 'node_j': 17, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 110, 'node_i': 17, 'node_j': 18, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 111, 'node_i': 13, 'node_j': 16, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 112, 'node_i': 15, 'node_j': 18, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 113, 'node_i': 19, 'node_j': 20, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 114, 'node_i': 20, 'node_j': 21, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 115, 'node_i': 22, 'node_j': 23, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 116, 'node_i': 23, 'node_j': 24, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 117, 'node_i': 19, 'node_j': 22, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 118, 'node_i': 21, 'node_j': 24, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
    ]
}
slab_configs_trm007 = []
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
    'node_font_size': 8, 
    'element_font_size': 6,  
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'zero_length_material_config': None,
    'zero_length_directions': None,
    'zero_length_boundary_conditions': None,
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
    'node_font_size': 8,  
    'element_font_size': 6, 
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'zero_length_material_config': None,
    'zero_length_directions': None,
    'zero_length_boundary_conditions': None,
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
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'zero_length_material_config': None,
    'zero_length_directions': None,
    'zero_length_boundary_conditions': None,
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
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
    'use_zero_length': False,
    'zero_length_material_config': None,
    'zero_length_directions': None,
    'zero_length_boundary_conditions': None,
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
footing_configs = []
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
    'internal_points': {1: (0.0, 0.0, -1.0)},
    'voids': None,
    'py_file': 'footing_1_rect.py',
    'png_file': 'footing_1_rect.png',
    'shell_material_config': ("ElasticIsotropic", 401, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
    'shell_section_config': ("PlateFiber", 401, 401, 2.0),
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],
    'zero_length_directions': [3],
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 50000,
    'spring_node_start_id': 2000000,
    'start_node_id': 500000,
    'start_element_id': 510000,
    'load_configs': None
})
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
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],
    'zero_length_directions': [3],
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 51000,
    'spring_node_start_id': 2100000,
    'start_node_id': 510000,
    'start_element_id': 520000,
    'load_configs': None
})
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
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],
    'zero_length_directions': [3],
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 52000,
    'spring_node_start_id': 2200000,
    'start_node_id': 520000,
    'start_element_id': 530000,
    'load_configs': None
})
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
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],
    'zero_length_directions': [3],
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 53000,
    'spring_node_start_id': 2300000,
    'start_node_id': 530000,
    'start_element_id': 540000,
    'load_configs': None
})
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
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],
    'zero_length_directions': [3],
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 54000,
    'spring_node_start_id': 2400000,
    'start_node_id': 540000,
    'start_element_id': 550000,
    'load_configs': None
})
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
    'node_font_size': 8,  
    'element_font_size': 6,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    'shell_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 1e9],
    'zero_length_directions': [3],
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],
    'element_start_id': 55000,
    'spring_node_start_id': 2500000,
    'start_node_id': 550000,
    'start_element_id': 560000,
    'load_configs': None
})
all_shell_configs = slab_configs_trm007 + footing_configs
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
    'shell_surface_loads': []
}
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
    diaphragm_list=None,  
    load_configs=load_configs,
    mass_configs=mass_configs,
    output_dir="output",
    slab_configs=all_shell_configs,
    existing_frame_nodes=node_coords_trm007,
    visualize=True
)
'''
    }
    
    examples['six_story_building'] = {
        'name': 'Six Story Building',
        'description': 'Six story building with rigid diaphragm',
        'code': r'''# ===========================================================================================
# 6-STORY BUILDING MODEL - 3 BAYS X-DIR, 2 BAYS Y-DIR
# ===========================================================================================
import numpy as np
import opstool as opst
from test3 import build_model
materials_6story = {
    'concrete_cover': {
        'elastic_modulus': 3600.0,
        'poissons_ratio': 0.2,
        'density': 0.150,
        'yield_strength': 4.0,
        'color': '#ffd700'
    },
    'concrete_core': {
        'elastic_modulus': 4000.0,
        'poissons_ratio': 0.2,
        'density': 0.155,
        'yield_strength': 5.0,
        'color': '#87ceeb'
    },
    'steel_rebar': {
        'elastic_modulus': 29000.0,
        'poissons_ratio': 0.3,
        'density': 0.490,
        'yield_strength': 60.0,
        'color': '#ff4500'
    }
}
col_12x18_outline = [[-6.0, -9.0], [6.0, -9.0], [6.0, 9.0], [-6.0, 9.0]]
col_12x18_cover = 1.5
col_12x18_rebar = [{
    'type': 'points',
    'points': [[-4.5, -7.5], [4.5, -7.5], [4.5, 7.5], [-4.5, 7.5], 
               [-4.5, 0.0], [4.5, 0.0], [0.0, -7.5], [0.0, 7.5]],
    'dia': 1.0,
    'color': 'red',
    'group_name': 'Col_12x18_Rebars'
}]
col_12x18_mat_tags = {'cover': 101, 'core': 102, 'rebar': 103}
col_12x24_outline = [[-6.0, -12.0], [6.0, -12.0], [6.0, 12.0], [-6.0, 12.0]]
col_12x24_cover = 1.5
col_12x24_rebar = [{
    'type': 'points',
    'points': [[-4.5, -10.5], [4.5, -10.5], [4.5, 10.5], [-4.5, 10.5],
               [-4.5, 0.0], [4.5, 0.0], [0.0, -10.5], [0.0, 0.0], [0.0, 10.5]],
    'dia': 1.0,
    'color': 'red',
    'group_name': 'Col_12x24_Rebars'
}]
col_12x24_mat_tags = {'cover': 104, 'core': 105, 'rebar': 106}
beam_10x16_outline = [[-5.0, -8.0], [5.0, -8.0], [5.0, 8.0], [-5.0, 8.0]]
beam_10x16_cover = 1.5
beam_10x16_rebar = [{
    'type': 'points',
    'points': [[-3.5, -6.5], [3.5, -6.5], [3.5, 6.5], [-3.5, 6.5],
               [0.0, -6.5], [0.0, 6.5]],
    'dia': 0.875,
    'color': 'blue',
    'group_name': 'Beam_10x16_Rebars'
}]
beam_10x16_mat_tags = {'cover': 107, 'core': 108, 'rebar': 109}
beam_10x21_outline = [[-5.0, -10.5], [5.0, -10.5], [5.0, 10.5], [-5.0, 10.5]]
beam_10x21_cover = 1.5
beam_10x21_rebar = [{
    'type': 'points',
    'points': [[-3.5, -9.0], [3.5, -9.0], [3.5, 9.0], [-3.5, 9.0],
               [-3.5, 0.0], [3.5, 0.0], [0.0, -9.0], [0.0, 9.0]],
    'dia': 0.875,
    'color': 'blue',
    'group_name': 'Beam_10x21_Rebars'
}]
beam_10x21_mat_tags = {'cover': 110, 'core': 111, 'rebar': 112}
G_concrete = 1600.0
material_params_6story = [
    ['Concrete01', 101, -4.0, -0.002, -0.8, -0.006],
    ['Concrete01', 102, -5.0, -0.002, -1.0, -0.008],
    ['Steel01', 103, 60.0, 29000.0, 0.015],
    ['Concrete01', 104, -4.0, -0.002, -0.8, -0.006],
    ['Concrete01', 105, -5.0, -0.002, -1.0, -0.008],
    ['Steel01', 106, 60.0, 29000.0, 0.015],
    ['Concrete01', 107, -4.0, -0.002, -0.8, -0.006],
    ['Concrete01', 108, -5.0, -0.002, -1.0, -0.008],
    ['Steel01', 109, 60.0, 29000.0, 0.015],
    ['Concrete01', 110, -4.0, -0.002, -0.8, -0.006],
    ['Concrete01', 111, -5.0, -0.002, -1.0, -0.008],
    ['Steel01', 112, 60.0, 29000.0, 0.015],
]
node_coords_6story = {
    1: (0.0, 0.0, 0.0), 2: (20.0, 0.0, 0.0), 3: (40.0, 0.0, 0.0), 4: (60.0, 0.0, 0.0),
    5: (0.0, 15.0, 0.0), 6: (20.0, 15.0, 0.0), 7: (40.0, 15.0, 0.0), 8: (60.0, 15.0, 0.0),
    9: (0.0, 30.0, 0.0), 10: (20.0, 30.0, 0.0), 11: (40.0, 30.0, 0.0), 12: (60.0, 30.0, 0.0),
    13: (0.0, 0.0, 12.0), 14: (20.0, 0.0, 12.0), 15: (40.0, 0.0, 12.0), 16: (60.0, 0.0, 12.0),
    17: (0.0, 15.0, 12.0), 18: (20.0, 15.0, 12.0), 19: (40.0, 15.0, 12.0), 20: (60.0, 15.0, 12.0),
    21: (0.0, 30.0, 12.0), 22: (20.0, 30.0, 12.0), 23: (40.0, 30.0, 12.0), 24: (60.0, 30.0, 12.0),
    25: (0.0, 0.0, 24.0), 26: (20.0, 0.0, 24.0), 27: (40.0, 0.0, 24.0), 28: (60.0, 0.0, 24.0),
    29: (0.0, 15.0, 24.0), 30: (20.0, 15.0, 24.0), 31: (40.0, 15.0, 24.0), 32: (60.0, 15.0, 24.0),
    33: (0.0, 30.0, 24.0), 34: (20.0, 30.0, 24.0), 35: (40.0, 30.0, 24.0), 36: (60.0, 30.0, 24.0),
    37: (0.0, 0.0, 36.0), 38: (20.0, 0.0, 36.0), 39: (40.0, 0.0, 36.0), 40: (60.0, 0.0, 36.0),
    41: (0.0, 15.0, 36.0), 42: (20.0, 15.0, 36.0), 43: (40.0, 15.0, 36.0), 44: (60.0, 15.0, 36.0),
    45: (0.0, 30.0, 36.0), 46: (20.0, 30.0, 36.0), 47: (40.0, 30.0, 36.0), 48: (60.0, 30.0, 36.0),
    49: (0.0, 0.0, 48.0), 50: (20.0, 0.0, 48.0), 51: (40.0, 0.0, 48.0), 52: (60.0, 0.0, 48.0),
    53: (0.0, 15.0, 48.0), 54: (20.0, 15.0, 48.0), 55: (40.0, 15.0, 48.0), 56: (60.0, 15.0, 48.0),
    57: (0.0, 30.0, 48.0), 58: (20.0, 30.0, 48.0), 59: (40.0, 30.0, 48.0), 60: (60.0, 30.0, 48.0),
    61: (0.0, 0.0, 60.0), 62: (20.0, 0.0, 60.0), 63: (40.0, 0.0, 60.0), 64: (60.0, 0.0, 60.0),
    65: (0.0, 15.0, 60.0), 66: (20.0, 15.0, 60.0), 67: (40.0, 15.0, 60.0), 68: (60.0, 15.0, 60.0),
    69: (0.0, 30.0, 60.0), 70: (20.0, 30.0, 60.0), 71: (40.0, 30.0, 60.0), 72: (60.0, 30.0, 60.0),
    73: (0.0, 0.0, 72.0), 74: (20.0, 0.0, 72.0), 75: (40.0, 0.0, 72.0), 76: (60.0, 0.0, 72.0),
    77: (0.0, 15.0, 72.0), 78: (20.0, 15.0, 72.0), 79: (40.0, 15.0, 72.0), 80: (60.0, 15.0, 72.0),
    81: (0.0, 30.0, 72.0), 82: (20.0, 30.0, 72.0), 83: (40.0, 30.0, 72.0), 84: (60.0, 30.0, 72.0),
}
boundary_conditions_6story = {
    1: [1, 1, 1, 1, 1, 1], 2: [1, 1, 1, 1, 1, 1], 3: [1, 1, 1, 1, 1, 1], 4: [1, 1, 1, 1, 1, 1],
    5: [1, 1, 1, 1, 1, 1], 6: [1, 1, 1, 1, 1, 1], 7: [1, 1, 1, 1, 1, 1], 8: [1, 1, 1, 1, 1, 1],
    9: [1, 1, 1, 1, 1, 1], 10: [1, 1, 1, 1, 1, 1], 11: [1, 1, 1, 1, 1, 1], 12: [1, 1, 1, 1, 1, 1],
}
element_configs_6story = {
    'transformations': [
        {'type': 'Linear', 'tag': 1, 'vecxz': [1, 0, 0]},
        {'type': 'Linear', 'tag': 2, 'vecxz': [0, 0, 1]},
        {'type': 'Linear', 'tag': 3, 'vecxz': [0, 0, 1]},
    ],
    'integrations': [
        {'type': 'Lobatto', 'tag': 1, 'sec_tag': 1, 'np': 5},
        {'type': 'Lobatto', 'tag': 2, 'sec_tag': 2, 'np': 5},
        {'type': 'Lobatto', 'tag': 3, 'sec_tag': 3, 'np': 5},
        {'type': 'Lobatto', 'tag': 4, 'sec_tag': 4, 'np': 5},
    ],
    'force_beam_columns': [
        {'tag': 1, 'node_i': 1, 'node_j': 13, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 2, 'node_i': 2, 'node_j': 14, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 3, 'node_i': 3, 'node_j': 15, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 4, 'node_i': 4, 'node_j': 16, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 5, 'node_i': 5, 'node_j': 17, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 6, 'node_i': 6, 'node_j': 18, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 7, 'node_i': 7, 'node_j': 19, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 8, 'node_i': 8, 'node_j': 20, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 9, 'node_i': 9, 'node_j': 21, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 10, 'node_i': 10, 'node_j': 22, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 11, 'node_i': 11, 'node_j': 23, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 12, 'node_i': 12, 'node_j': 24, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 13, 'node_i': 13, 'node_j': 25, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 14, 'node_i': 14, 'node_j': 26, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 15, 'node_i': 15, 'node_j': 27, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 16, 'node_i': 16, 'node_j': 28, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 17, 'node_i': 17, 'node_j': 29, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 18, 'node_i': 18, 'node_j': 30, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 19, 'node_i': 19, 'node_j': 31, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 20, 'node_i': 20, 'node_j': 32, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 21, 'node_i': 21, 'node_j': 33, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 22, 'node_i': 22, 'node_j': 34, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 23, 'node_i': 23, 'node_j': 35, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 24, 'node_i': 24, 'node_j': 36, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 25, 'node_i': 25, 'node_j': 37, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 26, 'node_i': 26, 'node_j': 38, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 27, 'node_i': 27, 'node_j': 39, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 28, 'node_i': 28, 'node_j': 40, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 29, 'node_i': 29, 'node_j': 41, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 30, 'node_i': 30, 'node_j': 42, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 31, 'node_i': 31, 'node_j': 43, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 32, 'node_i': 32, 'node_j': 44, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 33, 'node_i': 33, 'node_j': 45, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 34, 'node_i': 34, 'node_j': 46, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 35, 'node_i': 35, 'node_j': 47, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 36, 'node_i': 36, 'node_j': 48, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 37, 'node_i': 37, 'node_j': 49, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 38, 'node_i': 38, 'node_j': 50, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 39, 'node_i': 39, 'node_j': 51, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 40, 'node_i': 40, 'node_j': 52, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 41, 'node_i': 41, 'node_j': 53, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 42, 'node_i': 42, 'node_j': 54, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 43, 'node_i': 43, 'node_j': 55, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 44, 'node_i': 44, 'node_j': 56, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 45, 'node_i': 45, 'node_j': 57, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 46, 'node_i': 46, 'node_j': 58, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 47, 'node_i': 47, 'node_j': 59, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 48, 'node_i': 48, 'node_j': 60, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 49, 'node_i': 49, 'node_j': 61, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 50, 'node_i': 50, 'node_j': 62, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 51, 'node_i': 51, 'node_j': 63, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 52, 'node_i': 52, 'node_j': 64, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 53, 'node_i': 53, 'node_j': 65, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 54, 'node_i': 54, 'node_j': 66, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 55, 'node_i': 55, 'node_j': 67, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 56, 'node_i': 56, 'node_j': 68, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 57, 'node_i': 57, 'node_j': 69, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 58, 'node_i': 58, 'node_j': 70, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 59, 'node_i': 59, 'node_j': 71, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 60, 'node_i': 60, 'node_j': 72, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 61, 'node_i': 61, 'node_j': 73, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 62, 'node_i': 62, 'node_j': 74, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 63, 'node_i': 63, 'node_j': 75, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 64, 'node_i': 64, 'node_j': 76, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 65, 'node_i': 65, 'node_j': 77, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 66, 'node_i': 66, 'node_j': 78, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 67, 'node_i': 67, 'node_j': 79, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 68, 'node_i': 68, 'node_j': 80, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 69, 'node_i': 69, 'node_j': 81, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 70, 'node_i': 70, 'node_j': 82, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 71, 'node_i': 71, 'node_j': 83, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 72, 'node_i': 72, 'node_j': 84, 'transf_tag': 1, 'integ_tag': 1},
    ],
    'elastic_beam_columns': []
}
beam_elements = []
beam_tag = 1000
beam_elements.extend([
    {'tag': beam_tag, 'node_i': 13, 'node_j': 14, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+1, 'node_i': 14, 'node_j': 15, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+2, 'node_i': 15, 'node_j': 16, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+3, 'node_i': 17, 'node_j': 18, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+4, 'node_i': 18, 'node_j': 19, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+5, 'node_i': 19, 'node_j': 20, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+6, 'node_i': 21, 'node_j': 22, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+7, 'node_i': 22, 'node_j': 23, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+8, 'node_i': 23, 'node_j': 24, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
])
beam_tag += 9
beam_elements.extend([
    {'tag': beam_tag, 'node_i': 13, 'node_j': 17, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+1, 'node_i': 14, 'node_j': 18, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+2, 'node_i': 15, 'node_j': 19, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+3, 'node_i': 16, 'node_j': 20, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+4, 'node_i': 17, 'node_j': 21, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+5, 'node_i': 18, 'node_j': 22, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+6, 'node_i': 19, 'node_j': 23, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+7, 'node_i': 20, 'node_j': 24, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+8, 'node_i': 21, 'node_j': 24, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
])
beam_tag += 9
beam_elements.extend([
    {'tag': beam_tag, 'node_i': 25, 'node_j': 26, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+1, 'node_i': 26, 'node_j': 27, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+2, 'node_i': 27, 'node_j': 28, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+3, 'node_i': 29, 'node_j': 30, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+4, 'node_i': 30, 'node_j': 31, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+5, 'node_i': 31, 'node_j': 32, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+6, 'node_i': 33, 'node_j': 34, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+7, 'node_i': 34, 'node_j': 35, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+8, 'node_i': 35, 'node_j': 36, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+9, 'node_i': 25, 'node_j': 29, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+10, 'node_i': 26, 'node_j': 30, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+11, 'node_i': 27, 'node_j': 31, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+12, 'node_i': 28, 'node_j': 32, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+13, 'node_i': 29, 'node_j': 33, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+14, 'node_i': 30, 'node_j': 34, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+15, 'node_i': 31, 'node_j': 35, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+16, 'node_i': 32, 'node_j': 36, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+17, 'node_i': 33, 'node_j': 36, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
])
beam_tag += 18
beam_elements.extend([
    {'tag': beam_tag, 'node_i': 37, 'node_j': 38, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+1, 'node_i': 38, 'node_j': 39, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+2, 'node_i': 39, 'node_j': 40, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+3, 'node_i': 41, 'node_j': 42, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+4, 'node_i': 42, 'node_j': 43, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+5, 'node_i': 43, 'node_j': 44, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+6, 'node_i': 45, 'node_j': 46, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+7, 'node_i': 46, 'node_j': 47, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+8, 'node_i': 47, 'node_j': 48, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+9, 'node_i': 37, 'node_j': 41, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+10, 'node_i': 38, 'node_j': 42, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+11, 'node_i': 39, 'node_j': 43, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+12, 'node_i': 40, 'node_j': 44, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+13, 'node_i': 41, 'node_j': 45, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+14, 'node_i': 42, 'node_j': 46, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+15, 'node_i': 43, 'node_j': 47, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+16, 'node_i': 44, 'node_j': 48, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+17, 'node_i': 45, 'node_j': 48, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
])
beam_tag += 18
beam_elements.extend([
    {'tag': beam_tag, 'node_i': 49, 'node_j': 50, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+1, 'node_i': 50, 'node_j': 51, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+2, 'node_i': 51, 'node_j': 52, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+3, 'node_i': 53, 'node_j': 54, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+4, 'node_i': 54, 'node_j': 55, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+5, 'node_i': 55, 'node_j': 56, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+6, 'node_i': 57, 'node_j': 58, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+7, 'node_i': 58, 'node_j': 59, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+8, 'node_i': 59, 'node_j': 60, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+9, 'node_i': 49, 'node_j': 53, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+10, 'node_i': 50, 'node_j': 54, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+11, 'node_i': 51, 'node_j': 55, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+12, 'node_i': 52, 'node_j': 56, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+13, 'node_i': 53, 'node_j': 57, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+14, 'node_i': 54, 'node_j': 58, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+15, 'node_i': 55, 'node_j': 59, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+16, 'node_i': 56, 'node_j': 60, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+17, 'node_i': 57, 'node_j': 60, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
])
beam_tag += 18
beam_elements.extend([
    {'tag': beam_tag, 'node_i': 61, 'node_j': 62, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+1, 'node_i': 62, 'node_j': 63, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+2, 'node_i': 63, 'node_j': 64, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+3, 'node_i': 65, 'node_j': 66, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+4, 'node_i': 66, 'node_j': 67, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+5, 'node_i': 67, 'node_j': 68, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+6, 'node_i': 69, 'node_j': 70, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+7, 'node_i': 70, 'node_j': 71, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+8, 'node_i': 71, 'node_j': 72, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+9, 'node_i': 61, 'node_j': 65, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+10, 'node_i': 62, 'node_j': 66, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+11, 'node_i': 63, 'node_j': 67, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+12, 'node_i': 64, 'node_j': 68, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+13, 'node_i': 65, 'node_j': 69, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+14, 'node_i': 66, 'node_j': 70, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+15, 'node_i': 67, 'node_j': 71, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+16, 'node_i': 68, 'node_j': 72, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+17, 'node_i': 69, 'node_j': 72, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
])
beam_tag += 18
beam_elements.extend([
    {'tag': beam_tag, 'node_i': 73, 'node_j': 74, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+1, 'node_i': 74, 'node_j': 75, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+2, 'node_i': 75, 'node_j': 76, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+3, 'node_i': 77, 'node_j': 78, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+4, 'node_i': 78, 'node_j': 79, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+5, 'node_i': 79, 'node_j': 80, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+6, 'node_i': 81, 'node_j': 82, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+7, 'node_i': 82, 'node_j': 83, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+8, 'node_i': 83, 'node_j': 84, 'A': 210.0, 'E': 3600.0, 'G': 1600.0, 'J': 3675.0, 'Iy': 5880.0, 'Iz': 1750.0, 'transf_tag': 2},
    {'tag': beam_tag+9, 'node_i': 73, 'node_j': 77, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+10, 'node_i': 74, 'node_j': 78, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+11, 'node_i': 75, 'node_j': 79, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+12, 'node_i': 76, 'node_j': 80, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+13, 'node_i': 77, 'node_j': 81, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+14, 'node_i': 78, 'node_j': 82, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+15, 'node_i': 79, 'node_j': 83, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+16, 'node_i': 80, 'node_j': 84, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
    {'tag': beam_tag+17, 'node_i': 81, 'node_j': 84, 'A': 160.0, 'E': 3600.0, 'G': 1600.0, 'J': 2133.3, 'Iy': 2560.0, 'Iz': 1333.3, 'transf_tag': 3},
])
element_configs_6story['elastic_beam_columns'] = beam_elements
diaphragm_list_6story = [
    [3, 18, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24],
    [3, 30, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36],
    [3, 42, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48],
    [3, 54, 49, 50, 51, 52, 53, 55, 56, 57, 58, 59, 60],
    [3, 66, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 72],
    [3, 78, 73, 74, 75, 76, 77, 79, 80, 81, 82, 83, 84],
]
load_configs_6story = {
    'time_series': [{'tag': 1, 'type': 'Linear'}],
    'patterns': [{'tag': 1, 'type': 'Plain', 'ts_tag': 1}],
    'nodal_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                {'node': 18, 'forces': [0, 0, -180.0, 0, 0, 0]},
                {'node': 30, 'forces': [0, 0, -180.0, 0, 0, 0]},
                {'node': 42, 'forces': [0, 0, -180.0, 0, 0, 0]},
                {'node': 54, 'forces': [0, 0, -180.0, 0, 0, 0]},
                {'node': 66, 'forces': [0, 0, -180.0, 0, 0, 0]},
                {'node': 78, 'forces': [0, 0, -90.0, 0, 0, 0]},
            ]
        }
    ],
    'beam_uniform_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                {'elements': [1000, 1001, 1002], 'wy': 0, 'wz': -2.0},
                {'elements': [1018, 1019, 1020], 'wy': 0, 'wz': -2.0},
            ]
        }
    ],
}
mass_configs_6story = {
    'beam_column_mass': [
        {'tag': 1, 'density': 0.150, 'area': 216.0}, {'tag': 2, 'density': 0.150, 'area': 288.0},
        {'tag': 3, 'density': 0.150, 'area': 288.0}, {'tag': 4, 'density': 0.150, 'area': 216.0},
        {'tag': 5, 'density': 0.150, 'area': 216.0}, {'tag': 6, 'density': 0.150, 'area': 288.0},
        {'tag': 1000, 'density': 0.150, 'area': 210.0},
        {'tag': 1001, 'density': 0.150, 'area': 210.0},
        {'tag': 1002, 'density': 0.150, 'area': 210.0},
    ],
    'nodal_mass': [
        {'node': 18, 'mass': 150.0},
        {'node': 30, 'mass': 150.0},
        {'node': 42, 'mass': 150.0},
        {'node': 54, 'mass': 150.0},
        {'node': 66, 'mass': 150.0},
        {'node': 78, 'mass': 100.0},
    ],
}
results = build_model(
    model_params={'ndm': 3, 'ndf': 6},
    materials_list=[materials_6story, materials_6story, materials_6story, materials_6story],
    outline_points_list=[col_12x18_outline, col_12x24_outline, beam_10x16_outline, beam_10x21_outline],
    rebar_configs_list=[col_12x18_rebar, col_12x24_rebar, beam_10x16_rebar, beam_10x21_rebar],
    section_params_list=[
        {
            'cover': col_12x18_cover,
            'mesh_size': 3.0,
            'mat_tags': col_12x18_mat_tags,
            'sec_tag': 1,
            'G': G_concrete,
            'save_prefix': 'column_12x18',
            'section_name': 'Column_12x18'
        },
        {
            'cover': col_12x24_cover,
            'mesh_size': 3.0,
            'mat_tags': col_12x24_mat_tags,
            'sec_tag': 2,
            'G': G_concrete,
            'save_prefix': 'column_12x24',
            'section_name': 'Column_12x24'
        },
        {
            'cover': beam_10x16_cover,
            'mesh_size': 2.5,
            'mat_tags': beam_10x16_mat_tags,
            'sec_tag': 3,
            'G': G_concrete,
            'save_prefix': 'beam_10x16',
            'section_name': 'Beam_10x16'
        },
        {
            'cover': beam_10x21_cover,
            'mesh_size': 2.5,
            'mat_tags': beam_10x21_mat_tags,
            'sec_tag': 4,
            'G': G_concrete,
            'save_prefix': 'beam_10x21',
            'section_name': 'Beam_10x21'
        }
    ],
    material_params=material_params_6story,
    node_coords=node_coords_6story,
    boundary_conditions=boundary_conditions_6story,
    element_configs=element_configs_6story,
    spring_configs=None,
    nodal_spring_configs=None,
    diaphragm_list=diaphragm_list_6story,
    load_configs=load_configs_6story,
    mass_configs=mass_configs_6story,
    visualize=True,
    output_dir="output",
    slab_configs=None,
    existing_frame_nodes=None
)
'''
    }
    
    return examples


def create_zip_archive(output_dir):
    """Create ZIP archive of output directory"""
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_dir)
                z.write(file_path, arcname)
    buf.seek(0)
    return buf.getvalue()


# ========================================================================================
# SESSION STATE INITIALIZATION
# ========================================================================================

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'users' not in st.session_state:
    st.session_state.users = load_users()
if 'examples' not in st.session_state:
    st.session_state.examples = {}
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


# ========================================================================================
# PAGE CONFIG
# ========================================================================================

st.set_page_config(
    page_title="Structural Model Builder",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ========================================================================================
# PROFESSIONAL STYLES (UNCHANGED FROM ORIGINAL)
# ========================================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* {
    font-family: 'Inter', sans-serif;
}
.main-title {
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
    text-align: center;
}
.subtitle {
    text-align: center;
    color: #6b7280;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}
.stButton>button {
    width: 100%;
    border-radius: 12px;
    font-weight: 600;
    height: 3.5rem;
    border: 2px solid transparent;
    transition: all 0.3s ease;
    font-size: 1rem;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
}
.example-card {
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
    cursor: pointer;
}
.example-card:hover {
    border-color: #667eea;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
    transform: translateY(-4px);
}
.example-card.selected {
    border-color: #667eea;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
}
.example-title {
    font-weight: 600;
    font-size: 1.2rem;
    color: #1f2937;
    margin-bottom: 0.5rem;
}
.example-desc {
    color: #6b7280;
    font-size: 0.95rem;
}
.metric-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 1.5rem;
    color: white;
    text-align: center;
}
.metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}
.metric-label {
    font-size: 0.9rem;
    opacity: 0.9;
}
.section-header {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1f2937;
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e5e7eb;
}
.stTextArea textarea {
    border-radius: 12px;
    border: 2px solid #e5e7eb;
    font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}
.css-1d391kg {
    background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
}
.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 12px;
    padding: 1rem;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
}
.stImage {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.streamlit-expanderHeader {
    background: #f9fafb;
    border-radius: 12px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ========================================================================================
# AUTHENTICATION UI
# ========================================================================================

st.markdown('<h1 class="main-title">🏗️ Structural Model Builder</h1>', unsafe_allow_html=True)

if not st.session_state.authenticated:
    st.markdown('<p class="subtitle">Advanced Finite Element Analysis Platform</p>', unsafe_allow_html=True)
    st.info("Please sign in or sign up to start building structural models")
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    # with tab1:
    #     st.subheader("Sign In")
        
    #     with st.form("signin_form"):
    #         login_username = st.text_input("Username", key="login_user")
    #         login_password = st.text_input("Password", type="password", key="login_pass")
    #         login_submit = st.form_submit_button("Sign In", type="primary")
            
    #         if login_submit:
    #             if login_username and login_password:
    #                 success, message = sign_in(login_username, login_password)
    #                 if success:
    #                     st.session_state.examples = load_user_examples(login_username)
    #                     st.session_state.output_dir = f"./user_data/{login_username}/output"
    #                     st.success(message)
    #                     st.rerun()
    #                 else:
    #                     st.error(message)
    #             else:
    #                 st.warning("Please fill all fields")

    with tab1:
        st.subheader("Sign In")
        
        with st.form("signin_form"):
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            login_submit = st.form_submit_button("Sign In", type="primary")
            
            if login_submit:
                if login_username and login_password:
                    success, message = sign_in(login_username, login_password)
                    if success:
                        # FORCE LOAD DEFAULT EXAMPLES ALWAYS
                        st.session_state.examples = get_default_examples()
                        st.session_state.output_dir = f"./user_data/{login_username}/output"
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all fields")
    
    with tab2:
        st.subheader("Sign Up")
        
        with st.form("signup_form"):
            reg_username = st.text_input("Username", key="reg_user", help="Choose a unique username")
            reg_email = st.text_input("Email", key="reg_email", help="Enter your email address")
            reg_password = st.text_input("Password", type="password", key="reg_pass", help="Minimum 6 characters")
            reg_submit = st.form_submit_button("Sign Up", type="primary")
            
            if reg_submit:
                if reg_username and reg_email and reg_password:
                    if "@" not in reg_email or "." not in reg_email:
                        st.error("Please enter a valid email address")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters")
                    elif " " in reg_username:
                        st.error("Username cannot contain spaces")
                    else:
                        success, message = sign_up(reg_username, reg_email, reg_password)
                        if success:
                            st.success(message)
                            st.info("Now you can sign in with your credentials")
                        else:
                            st.error(message)
                else:
                    st.warning("Please fill all fields")
    
    st.stop()


# ========================================================================================
# AUTHENTICATED USER INTERFACE - SIDEBAR
# ========================================================================================

with st.sidebar:
    st.success(f"👤 Logged in as: **{st.session_state.current_user}**")
    if st.button("🚪 Sign Out", use_container_width=True):
        sign_out()
        st.rerun()
    
    st.divider()
    # ENSURE EXAMPLES ARE ALWAYS LOADED
    if not st.session_state.examples:
        st.session_state.examples = get_default_examples()
    
    # Display user's models
    st.subheader("📁 Your Models")
    user_models = get_user_models(st.session_state.current_user)
    
    if user_models:
        for model in user_models:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• **{model['name']}**")
                if model['description']:
                    st.caption(model['description'])
            with col2:
                if st.button("🗑️", key=f"del_model_{model['name']}", help=f"Delete {model['name']}"):
                    success, message = delete_user_model(st.session_state.current_user, model['name'])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("No models created yet")
    
    st.divider()
    
    # Example Library
    st.markdown("### 📚 Example Library")
    
    if st.session_state.examples:
        for key, example in st.session_state.examples.items():
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"📄 {example['name']}", 
                        key=f"load_{key}",
                        use_container_width=True,
                        type="primary" if st.session_state.selected_example == key else "secondary"
                    ):
                        st.session_state.selected_example = key
                        st.session_state.config_text = example['code']
                        st.session_state.config_added = False
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"del_{key}", help="Delete example"):
                        del st.session_state.examples[key]
                        save_user_examples(st.session_state.current_user)
                        if st.session_state.selected_example == key:
                            st.session_state.selected_example = None
                            st.session_state.config_text = ""
                        st.rerun()
    else:
        st.info("No examples available. Add one below!")
    
    st.markdown("---")
    
    # Add new example
    st.markdown("### ➕ Add New Example")
    
    with st.form("add_example_form"):
        new_name = st.text_input("Example Name", placeholder="My Custom Model")
        new_desc = st.text_input("Description", placeholder="Brief description...")
        new_code = st.text_area("Code", height=200, placeholder="Paste your Python code here...")
        
        if st.form_submit_button("Add Example", use_container_width=True):
            if new_name and new_code:
                key = new_name.lower().replace(' ', '_')
                st.session_state.examples[key] = {
                    'name': new_name,
                    'description': new_desc or "Custom example",
                    'code': new_code
                }
                save_user_examples(st.session_state.current_user)
                st.success(f"✅ Added: {new_name}")
                st.rerun()
            else:
                st.error("Name and code are required!")
    
    st.markdown("---")
    
    # Import/Export examples
    st.markdown("### 💾 Import/Export")
    
    if st.session_state.examples:
        examples_json = json.dumps(st.session_state.examples, indent=2)
        st.download_button(
            "📥 Export Examples",
            examples_json,
            "examples.json",
            "application/json",
            use_container_width=True
        )
    
    uploaded_examples = st.file_uploader("📤 Import Examples", type=['json'])
    if uploaded_examples:
        try:
            imported = json.loads(uploaded_examples.read().decode('utf-8'))
            st.session_state.examples.update(imported)
            save_user_examples(st.session_state.current_user)
            st.success("✅ Examples imported!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Import failed: {e}")
    
    st.markdown("---")
    
    # Profile Button
    if st.button("👤 Profile", use_container_width=True):
        st.session_state.show_profile = True


# Show Profile Modal
if st.session_state.get('show_profile', False):
    st.markdown("---")
    st.subheader("👤 User Profile")
    
    user_data = st.session_state.users.get(st.session_state.current_user, {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Personal Details")
        st.info(f"""
        **Username:** {st.session_state.current_user}
        
        **Email:** {user_data.get('email', 'N/A')}
        
        **Account Status:** Active ✅
        """)
    
    with col2:
        st.markdown("### Statistics")
        user_models = get_user_models(st.session_state.current_user)
        st.metric("Total Models", len(user_models))
        st.metric("Total Examples", len(st.session_state.examples))
    
    st.markdown("---")
    st.warning("⚠️ **Danger Zone**")
    st.write("Deleting your account will permanently remove:")
    st.write(f"- All {len(user_models)} model(s)")
    st.write("- All examples and configurations")
    st.write("- Account information")
    
    confirm_delete = st.checkbox("I understand that this action is irreversible", key="confirm_delete_profile")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Delete Account", type="secondary", disabled=not confirm_delete, use_container_width=True):
            if confirm_delete:
                username = st.session_state.current_user
                success, message = delete_account(username)
                if success:
                    st.success(message)
                    sign_out()
                    st.rerun()
                else:
                    st.error(message)
    
    with col_btn2:
        if st.button("Close Profile", use_container_width=True):
            st.session_state.show_profile = False
            st.rerun()


# ========================================================================================
# MAIN APPLICATION (UNCHANGED FROM ORIGINAL)
# ========================================================================================

st.markdown('<p class="subtitle">Advanced Finite Element Analysis Platform</p>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 Editor", "🚀 Build & Results"])

# TAB 1: EDITOR
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="section-header">Configuration Editor</div>', unsafe_allow_html=True)
        
        if st.session_state.config_text:
            if st.session_state.selected_example:
                example_data = st.session_state.examples.get(st.session_state.selected_example)
                if example_data:
                    st.info(f"📝 Editing: **{example_data['name']}** - {example_data['description']}")
            
            edited_config = st.text_area(
                "Edit your configuration:",
                value=st.session_state.config_text,
                height=500,
                key="config_editor"
            )
            
            if edited_config != st.session_state.config_text:
                st.session_state.config_text = edited_config
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("✅ Validate", type="primary", use_container_width=True):
                    is_valid, msg = validate_config(st.session_state.config_text)
                    if is_valid:
                        st.session_state.config_added = True
                        st.success("✅ Configuration is valid!")
                    else:
                        st.error(f"❌ {msg}")
            
            with col_b:
                if st.button("🔄 Reset", use_container_width=True):
                    if st.session_state.selected_example and st.session_state.selected_example in st.session_state.examples:
                        st.session_state.config_text = st.session_state.examples[st.session_state.selected_example]['code']
                        st.rerun()
            
            with col_c:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state.config_text = ""
                    st.session_state.selected_example = None
                    st.session_state.config_added = False
                    st.rerun()
        
        else:
            st.info("👈 Select an example from the sidebar to get started!")
            
            with st.expander("📖 Show Code Template"):
                st.code('''# Basic Template
import numpy as np
from test3 import build_model

# Define your materials, nodes, elements...
# Then call build_model(...)

results = build_model(
    model_params={'ndm': 3, 'ndf': 6},
    # ... other parameters
)
''', language='python')
    
    with col2:
        st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("📤 Upload Python File", type=['py'])
        if uploaded_file:
            try:
                content = uploaded_file.read().decode('utf-8')
                st.session_state.config_text = content
                st.session_state.selected_example = "custom_upload"
                st.session_state.config_added = False
                st.success("✅ File loaded!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
        
        if st.session_state.config_text:
            st.download_button(
                "💾 Download Configuration",
                st.session_state.config_text.encode('utf-8'),
                f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py",
                "text/x-python",
                use_container_width=True
            )
        
        with st.expander("❓ Quick Guide"):
            st.markdown("""
            **Steps:**
            1. Select example from sidebar
            2. Edit configuration as needed
            3. Click 'Validate'
            4. Go to 'Build & Results' tab
            5. Click 'Build Model'
            
            **Requirements:**
            - Import `build_model` from `test3`
            - Define all required parameters
            - Call `build_model(...)`
            """)


# TAB 2: BUILD & RESULTS
with tab2:
    if st.session_state.config_added:
        st.markdown('<div class="section-header">Build Model</div>', unsafe_allow_html=True)
        
        col_name1, col_name2 = st.columns([2, 1])
        with col_name1:
            model_name = st.text_input(
                "Model Name", 
                value=f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                help="Enter a unique name for this model"
            )
        with col_name2:
            user_models = get_user_models(st.session_state.current_user)
            existing_names = [m['name'] for m in user_models]
            if model_name in existing_names:
                st.warning("⚠️ Name exists!")
            else:
                st.success("✓ Available")
        
        model_description = st.text_input("Description (optional)", placeholder="Brief description of the model")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            with st.expander("📋 Configuration Preview"):
                st.code(st.session_state.config_text, language='python', line_numbers=True)
        
        with col2:
            build_disabled = model_name in existing_names
            if st.button("🔨 Build Model", type="primary", use_container_width=True, disabled=build_disabled):
                if build_disabled:
                    st.error("Please choose a different model name")
                    st.stop()
                
                with st.spinner("Building model..."):
                    try:
                        user_dir = f"./user_data/{st.session_state.current_user}/models/{model_name}"
                        os.makedirs(user_dir, exist_ok=True)
                        
                        metadata = {
                            'name': model_name,
                            'description': model_description,
                            'created': datetime.now().isoformat(),
                            'username': st.session_state.current_user
                        }
                        with open(f"{user_dir}/metadata.json", 'w') as f:
                            json.dump(metadata, f, indent=2)
                        
                        with open(f"{user_dir}/config.py", 'w') as f:
                            f.write(st.session_state.config_text)
                        
                        # Create absolute path for output directory
                        od = os.path.abspath(f"{user_dir}/output")
                        if os.path.exists(od):
                            shutil.rmtree(od)
                        os.makedirs(od, exist_ok=True)
                        
                        st.session_state.output_dir = od
                        
                        # Change working directory to output directory
                        original_cwd = os.getcwd()
                        os.chdir(od)
                        
                        patch_gmsh()
                        
                        from test3 import build_model, generate_complete_model_file
                        
                        # Modify config_text to use current directory as output
                        modified_config = st.session_state.config_text.replace(
                            'output_dir="output"', 
                            'output_dir="."'
                        ).replace(
                            "output_dir='output'", 
                            "output_dir='.'"
                        )
                        
                        eg = {
                            'build_model': build_model,
                            'generate_complete_model_file': generate_complete_model_file,
                            'create_regular_polygon_nodes': create_regular_polygon_nodes,
                            'np': __import__('numpy'),
                            'opst': __import__('opstool'),
                            'os': os,
                        }
                        
                        exec(modified_config, eg)
                        
                        # Change back to original directory
                        os.chdir(original_cwd)
                        
                        if 'results' in eg:
                            st.session_state.build_results = eg['results']
                            with open(f"{user_dir}/results.json", 'w') as f:
                                json.dump(eg['results'], f, indent=2)
                        
                        st.session_state.model_built = True
                        st.success("✅ Model built successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        # Make sure to change back to original directory on error
                        try:
                            os.chdir(original_cwd)
                        except:
                            pass
                        st.error(f"❌ Build error: {e}")
                        import traceback
                        with st.expander("🔍 Error Details"):
                            st.code(traceback.format_exc(), language='bash')
    else:
        st.info("⚠️ Please validate your configuration in the Editor tab first!")
    
    # Results section
    if st.session_state.model_built and os.path.exists(st.session_state.output_dir):
        st.markdown("---")
        st.markdown('<div class="section-header">Build Results</div>', unsafe_allow_html=True)
        
        files = list(Path(st.session_state.output_dir).rglob("*"))
        imgs = [f for f in files if f.suffix.lower() in ['.png', '.jpg', '.jpeg'] and f.is_file()]
        pys = [f for f in files if f.suffix == '.py' and f.is_file()]
        htmls = [f for f in files if f.suffix == '.html' and f.is_file()]
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{st.session_state.build_results.get('total_nodes', 'N/A') if st.session_state.build_results else '✓'}</div>
                <div class="metric-label">Nodes</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{st.session_state.build_results.get('total_elements', 'N/A') if st.session_state.build_results else '✓'}</div>
                <div class="metric-label">Elements</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{len(imgs)}</div>
                <div class="metric-label">Images</div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col4:
            st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{len(pys) + len(htmls)}</div>
                <div class="metric-label">Files</div>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Images
        if imgs:
            st.markdown("### 🖼️ Generated Images")
            cols = st.columns(2)
            for i, img in enumerate(sorted(imgs)):
                with cols[i % 2]:
                    st.image(str(img), caption=img.name, use_column_width=True)
                    with open(img, 'rb') as f:
                        st.download_button(
                            f"⬇️ {img.name}",
                            f.read(),
                            img.name,
                            key=f"img_{i}",
                            use_container_width=True
                        )
        
        # 3D Visualizations
        if htmls:
            st.markdown("### 🌐 3D Visualizations")
            for i, h in enumerate(sorted(htmls)):
                with st.expander(f"📈 {h.name}", expanded=(i == 0)):
                    with open(h, encoding='utf-8') as f:
                        st.components.v1.html(f.read(), height=600, scrolling=True)
                    
                    with open(h, 'rb') as f:
                        st.download_button(
                            f"⬇️ Download {h.name}",
                            f.read(),
                            h.name,
                            key=f"html_{i}",
                            use_container_width=True
                        )
        
        # Python Files
        if pys:
            st.markdown("### 🐍 Python Files")
            for i, p in enumerate(sorted(pys)):
                with st.expander(f"📄 {p.name}"):
                    with open(p) as f:
                        st.code(f.read(), language='python', line_numbers=True)
                    
                    with open(p, 'rb') as f:
                        st.download_button(
                            f"⬇️ Download {p.name}",
                            f.read(),
                            p.name,
                            key=f"py_{i}",
                            use_container_width=True
                        )
        
        st.markdown("---")
        
        # Download all
        col1, col2 = st.columns(2)
        with col1:
            zip_data = create_zip_archive(st.session_state.output_dir)
            st.download_button(
                "📦 Download All Files (ZIP)",
                zip_data,
                f"model_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                "application/zip",
                use_container_width=True
            )
        
        with col2:
            if st.button("🗑️ Clean Output Directory", use_container_width=True):
                if os.path.exists(st.session_state.output_dir):
                    shutil.rmtree(st.session_state.output_dir)
                st.session_state.model_built = False
                st.session_state.build_results = None
                st.success("✅ Output directory cleaned!")
                st.rerun()


# ========================================================================================
# FOOTER
# ========================================================================================

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; padding: 2rem 0;'>
    <p style='color: #6b7280; font-size: 0.9rem; margin-bottom: 0.5rem;'>
        🏗️ <strong>Structural Model Builder</strong> | User: {st.session_state.current_user}
    </p>
    <p style='color: #9ca3af; font-size: 0.8rem;'>
        Advanced Finite Element Analysis Platform
    </p>
</div>
""", unsafe_allow_html=True)



