
# ===========================================================================================
# MATERIAL AND SECTION DEFINITIONS
# ===========================================================================================

# 1. CONCRETE MATERIALS FOR FIBER SECTION
concrete_materials = {
    'concrete_cover': {
        'elastic_modulus': 3600.0,  # ksi
        'poissons_ratio': 0.2,
        'density': 0.150,  # kcf
        'yield_strength': 4.0,  # ksi
        'color': '#dbb40c'  # gold/yellow
    },
    'concrete_core': {
        'elastic_modulus': 3600.0,  # ksi
        'poissons_ratio': 0.2,
        'density': 0.150,  # kcf
        'yield_strength': 5.0,  # ksi
        'color': '#88b378'  # green
    },
    'steel_rebar': {
        'elastic_modulus': 29000.0,  # ksi
        'poissons_ratio': 0.3,
        'density': 0.490,  # kcf
        'yield_strength': 60.0,  # ksi
        'color': 'black'
    }
}

# ===========================================================================================
# SECTION 1: RECTANGULAR COLUMN 2ft x 2ft WITH 4 REBARS (for columns A1, B1, A2)
# ===========================================================================================

column_rect_2x2_outline = [[-12.0, -12.0], [12.0, -12.0], [12.0, 12.0], [-12.0, 12.0]]
column_rect_2x2_cover = 1.5  # inches

column_rect_2x2_rebar = [{
    'type': 'points',
    'points': [
        [-10.5, -10.5],  # Bottom-left corner
        [10.5, -10.5],   # Bottom-right corner
        [10.5, 10.5],    # Top-right corner
        [-10.5, 10.5]    # Top-left corner
    ],
    'dia': 1.0,  # inches (#8 bar)
    'color': 'red',
    'group_name': 'Corner_Rebars'
}]

column_rect_2x2_mat_tags = {
    'cover': 1,
    'core': 2,
    'rebar': 3
}

# ===========================================================================================
# SECTION 2: RECTANGULAR COLUMN 2ft x 3ft WITH 6 REBARS (for columns C1, B2)
# ===========================================================================================

column_rect_2x3_outline = [[-12.0, -18.0], [12.0, -18.0], [12.0, 18.0], [-12.0, 18.0]]
column_rect_2x3_cover = 1.5  # inches

column_rect_2x3_rebar = [{
    'type': 'points',
    'points': [
        [-10.5, -16.5],  # Bottom-left
        [10.5, -16.5],   # Bottom-right
        [-10.5, 0.0],    # Middle-left
        [10.5, 0.0],     # Middle-right
        [-10.5, 16.5],   # Top-left
        [10.5, 16.5]     # Top-right
    ],
    'dia': 1.0,  # inches (#8 bar)
    'color': 'red',
    'group_name': 'Edge_Rebars'
}]

column_rect_2x3_mat_tags = {
    'cover': 4,
    'core': 5,
    'rebar': 6
}

# ===========================================================================================
# SECTION 3: CIRCULAR COLUMN (2ft diameter) WITH 8 REBARS (for columns A2, C2)
# ===========================================================================================

import opstool as opst
import numpy as np

from model_creation import build_model, generate_complete_model_file

column_circular_outline = opst.pre.section.create_circle_points(
    xo=[0.0, 0.0],
    radius=12.0,
    angles=(0, 360),
    n_sub=64
)

column_circular_cover = 1.5  # inches

column_circular_rebar = [{
    'type': 'circle',
    'xo': [0.0, 0.0],
    'radius': 10.5,
    'dia': 1.0,
    'n': 8,
    'angles': (0, 360),
    'color': 'red',
    'group_name': 'Circular_Rebars'
}]

column_circular_mat_tags = {
    'cover': 7,
    'core': 8,
    'rebar': 9
}

# ===========================================================================================
# SHEAR MODULUS AND UNIAXIAL MATERIALS
# ===========================================================================================

G_concrete = 1500.0  # ksi

material_params = [
    # Section 1: Rect 2x2 (4 bars)
    ['Concrete01', 1, -4.0, -0.002, -0.8, -0.006],   # Cover
    ['Concrete01', 2, -5.0, -0.002, -1.0, -0.006],   # Core
    ['Steel01', 3, 60.0, 29000.0, 0.01],             # Rebar
    
    # Section 2: Rect 2x3 (6 bars)
    ['Concrete01', 4, -4.0, -0.002, -0.8, -0.006],   # Cover
    ['Concrete01', 5, -5.0, -0.002, -1.0, -0.006],   # Core
    ['Steel01', 6, 60.0, 29000.0, 0.01],             # Rebar
    
    # Section 3: Circular (8 bars)
    ['Concrete01', 7, -4.0, -0.002, -0.8, -0.006],   # Cover
    ['Concrete01', 8, -5.0, -0.002, -1.0, -0.006],   # Core
    ['Steel01', 9, 60.0, 29000.0, 0.01]              # Rebar
]

# ===========================================================================================
# NODE COORDINATES
# ===========================================================================================

node_coords_dict = {
    # Base nodes (z = 0 ft)
    1: (0.0, 0.0, 0.0),      # Column A1 base
    2: (20.0, 0.0, 0.0),     # Column B1 base
    3: (40.0, 0.0, 0.0),     # Column C1 base
    4: (0.0, 20.0, 0.0),     # Column A2 base
    5: (20.0, 20.0, 0.0),    # Column B2 base
    6: (40.0, 20.0, 0.0),    # Column C2 base
    
    # Top nodes (z = 10 ft)
    11: (0.0, 0.0, 10.0),    # Column A1 top
    12: (20.0, 0.0, 10.0),   # Column B1 top
    13: (40.0, 0.0, 10.0),   # Column C1 top
    14: (0.0, 20.0, 10.0),   # Column A2 top
    15: (20.0, 20.0, 10.0),  # Column B2 top
    16: (40.0, 20.0, 10.0)   # Column C2 top
}

element_mass_list = [
    # Columns
    {'tag': 1, 'density': 2.5, 'area': 4.0},    # Column 1: 2ft×2ft = 4 ft²
    {'tag': 2, 'density': 2.5, 'area': 4.0},    # Column 2
    {'tag': 3, 'density': 3.0, 'area': 6.0},    # Column 3: 2ft×3ft = 6 ft²
    {'tag': 4, 'density': 2.5, 'area': 3.14},   # Column 4: circular π×1² ft²
    {'tag': 5, 'density': 3.0, 'area': 6.0},    # Column 5
    {'tag': 6, 'density': 2.5, 'area': 3.14},   # Column 6
    
    # Beams (576 in² = 4 ft²)
    {'tag': 11, 'density': 1.0, 'area': 4.0},   # Beam 11
    {'tag': 12, 'density': 1.0, 'area': 4.0},   # Beam 12  
    {'tag': 13, 'density': 1.0, 'area': 4.0},   # Beam 13
    {'tag': 14, 'density': 1.0, 'area': 4.0},   # Beam 14
    {'tag': 15, 'density': 1.0, 'area': 4.0},   # Beam 15
    {'tag': 16, 'density': 1.0, 'area': 4.0},   # Beam 16
    {'tag': 17, 'density': 1.0, 'area': 4.0}    # Beam 17
]

nodal_mass_applied = [
    (1, 100.0),    # Node 1: 100 units
    (2, 150.0),    # Node 2: 150 units
    (3, 200.0)     # Node 3: 200 units
]

# ===========================================================================================
# BOUNDARY CONDITIONS
# ===========================================================================================

boundary_conditions_dict = {
    # Fix all DOFs for base nodes (1-6)
    1: [1, 1, 1, 1, 1, 1],
    2: [1, 1, 1, 1, 1, 1],
    3: [1, 1, 1, 1, 1, 1],
    4: [1, 1, 1, 1, 1, 1],
    5: [1, 1, 1, 1, 1, 1],
    6: [1, 1, 1, 1, 1, 1],
    
    # Top nodes (11-16) are free (for slab connection)
    11: [0, 0, 0, 0, 0, 0],
    12: [0, 0, 0, 0, 0, 0],
    13: [0, 0, 0, 0, 0, 0],
    14: [0, 0, 0, 0, 0, 0],
    15: [0, 0, 0, 0, 0, 0],
    16: [0, 0, 0, 0, 0, 0]
}

# ===========================================================================================
# ELEMENT CONFIGURATIONS
# ===========================================================================================

element_configs_dict = {
    'transformations': [
        {
            'type': 'Linear',
            'tag': 1,
            'vecxz': [1, 0, 0]  # For columns
        },
        {
            'type': 'Linear',
            'tag': 2,
            'vecxz': [0, 0, 1]  # For beams
        }
    ],
    
    'integrations': [
        # Integration for Section 1 (2x2 rect)
        {
            'type': 'Lobatto',
            'tag': 1,
            'sec_tag': 1,
            'np': 5
        },
        # Integration for Section 2 (2x3 rect)
        {
            'type': 'Lobatto',
            'tag': 2,
            'sec_tag': 2,
            'np': 5
        },
        # Integration for Section 3 (circular)
        {
            'type': 'Lobatto',
            'tag': 3,
            'sec_tag': 3,
            'np': 5
        }
    ],
    
    'fiber_sections': [],  # Will be populated by build_model function
    
    'force_beam_columns': [
        # SECTION ASSIGNMENT:
        # A1, B1: Section 1 (2x2 rect, 4 bars) - integ_tag = 1
        # C1, B2: Section 2 (2x3 rect, 6 bars) - integ_tag = 2
        # A2, C2: Section 3 (circular, 8 bars) - integ_tag = 3
        
        {'tag': 1, 'node_i': 1, 'node_j': 11, 'transf_tag': 1, 'integ_tag': 1},  # A1: Rect 2x2
        {'tag': 2, 'node_i': 2, 'node_j': 12, 'transf_tag': 1, 'integ_tag': 1},  # B1: Rect 2x2
        {'tag': 3, 'node_i': 3, 'node_j': 13, 'transf_tag': 1, 'integ_tag': 2},  # C1: Rect 2x3
        {'tag': 4, 'node_i': 4, 'node_j': 14, 'transf_tag': 1, 'integ_tag': 3},  # A2: Circular
        {'tag': 5, 'node_i': 5, 'node_j': 15, 'transf_tag': 1, 'integ_tag': 2},  # B2: Rect 2x3
        {'tag': 6, 'node_i': 6, 'node_j': 16, 'transf_tag': 1, 'integ_tag': 3}   # C2: Circular
    ],
    
    'elastic_sections': [
        {
            'sec_tag': 100,
            'E': 3600.0,
            'A': 576.0,
            'Iz': 27648.0,
            'Iy': 27648.0,
            'G': 1500.0,
            'J': 44236.8
        }
    ],
    
    'elastic_beam_columns': [
        # Beams in X-direction
        {'tag': 11, 'node_i': 11, 'node_j': 12, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 
         'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 12, 'node_i': 12, 'node_j': 13, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 
         'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 13, 'node_i': 14, 'node_j': 15, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 
         'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 14, 'node_i': 15, 'node_j': 16, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 
         'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        
        # Beams in Y-direction
        {'tag': 15, 'node_i': 11, 'node_j': 14, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 
         'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        {'tag': 16, 'node_i': 13, 'node_j': 16, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 
         'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2},
        
        # Diagonal beam
        {'tag': 17, 'node_i': 12, 'node_j': 15, 'A': 576.0, 'E': 3600.0, 'G': 1500.0, 
         'J': 44236.8, 'Iy': 27648.0, 'Iz': 27648.0, 'transf_tag': 2}
    ]
}

# ===========================================================================================
# MODEL PARAMETERS
# ===========================================================================================

model_params = {
    'ndm': 3,
    'ndf': 6
}

# ===========================================================================================
# SPRING CONFIGURATIONS
# ===========================================================================================

K = 1e8  # Spring stiffness

spring_configs = [
    {
        'node_i': 1,
        'mat_tag': 101,
        'dirs': [3],
        'spring_type': 'ENT',
        'stiffness': K
    },
    {
        'node_i': 2,
        'mat_tag': 102,
        'dirs': [3],
        'spring_type': 'ENT',
        'stiffness': K
    },
    {
        'node_i': 3,
        'mat_tag': 103,
        'dirs': [3],
        'spring_type': 'ENT',
        'stiffness': K
    },
    {
        'node_i': 4,
        'mat_tag': 104,
        'dirs': [3],
        'spring_type': 'ENT',
        'stiffness': K
    },
    {
        'node_i': 5,
        'mat_tag': 105,
        'dirs': [3],
        'spring_type': 'ENT',
        'stiffness': K
    },
    {
        'node_i': 6,
        'mat_tag': 106,
        'dirs': [3],
        'spring_type': 'ENT',
        'stiffness': K
    }
]

# # User defines nodal_spring_configs
# nodal_spring_configs = {
#     'material_props': {
#         'id': 101,
#         'directions': [3],
#         'config': ['ENT', 101, 1e8]
#     },
#     'sections': {},  # Empty dict, not used for springs
#     'node_list': [
#         (1, 0.0, 0.0, 0.0),
#         (2, 20.0, 0.0, 0.0),
#         (3, 40.0, 0.0, 0.0),
#         (4, 0.0, 20.0, 0.0),
#         (5, 20.0, 20.0, 0.0),
#         (6, 40.0, 20.0, 0.0)
#     ],
#     'boundary_condition': [1, 1, 1, 1, 1, 1],
#     'element_start_id': 10000000,
#     'spring_node_start_id': 11000000
# }

nodal_spring_configs = None
# ===========================================================================================
# PREPARE SHELL CONFIGURATIONS (SLABS AND FOOTINGS)
# ===========================================================================================

# Helper function for regular polygons
def create_regular_polygon_nodes(center_x, center_y, radius, n_sides, start_id, z=0.0):
    """Create regular polygon nodes dictionary"""
    angles = np.linspace(0, 2*np.pi, n_sides + 1)[:-1]
    nodes = {}
    for i, angle in enumerate(angles):
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        nodes[start_id + i] = (x, y, z)
    return nodes


# ===========================================================================================
# INTERNAL POINTS FOR FOOTINGS - ALIGNED WITH COLUMN BASE NODES
# ===========================================================================================

# Footing 1: Square footing under Column A1 (node 1)
# Center at (0, 0, 0) - matches column A1 base
footing1_internal_points = {
    1: (0.0, 0.0, 0.0)  # Column A1 base location
}

# Footing 2: Hexagon footing under Column B1 (node 2)
# Center at (20, 0, 0) - matches column B1 base
footing2_internal_points = {
    2: (20.0, 0.0, 0.0)  # Column B1 base location
}

# Footing 3: Octagon footing under Column C1 (node 3)
# Center at (40, 0, 0) - matches column C1 base
footing3_internal_points = {
    3: (40.0, 0.0, 0.0)  # Column C1 base location
}

# Footing 4: Triangle footing under Column A2 (node 4)
# Centroid near (0, 20, 0) - matches column A2 base
footing4_internal_points = {
    4: (0.0, 20.0, 0.0)  # Column A2 base location
}

# Footing 5: Circle footing under Column B2 (node 5)
# Center at (20, 20, 0) - matches column B2 base
footing5_internal_points = {
    5: (20.0, 20.0, 0.0)  # Column B2 base location
}

# Footing 6: L-Shaped footing under Column C2 (node 6)
# Point at (40, 20, 0) - matches column C2 base
footing6_internal_points = {
    6: (40.0, 20.0, 0.0)  # Column C2 base location
}


# Single unified configuration list for all shell structures
slab_configs = [
    # ============================================================
    # SLABS
    # ============================================================
    {
        'name': 'Slab_1',
        'type': 'slab',
        'boundary_nodes': {
            11: (0.0, 0.0, 10.0),
            12: (20.0, 0.0, 10.0),
            15: (20.0, 20.0, 10.0),
            14: (0.0, 20.0, 10.0)
        },
        'mesh_size': 5.0,
        'internal_points': None,  # ✓ Column A1 base

        'internal_points': None,
        'voids': None,
                # ADD VOID (e.g., for drainage hole):
        # 'voids': [
            # {
        #         30001: (-0.5, -0.5, 0.0),
        #         30002: (0.5, -0.5, 0.0),
        #         30003: (0.5, 0.5, 0.0),
        #         30004: (-0.5, 0.5, 0.0)
        #     }
        # ],
        
        # # FONT SIZES:
        'node_font_size': 9,      # Larger for footings
        'element_font_size': 8,

        'py_file': 'slab1_model.py',
        'png_file': 'slab1_mesh.png',
        'shell_material_config': ("ElasticIsotropic", 10, 3600.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 10, 10, 8.0 / 12.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 10000,
        'spring_node_start_id': 1000000,
        'start_node_id': 100000,      # Slab 1 mesh nodes start at 100000
        
        'start_element_id': 110000,   # Slab 1 mesh elements start at 110000
        'load_configs': {
            'pressure': -100.0,
            'time_series_tag': 101,
            'pattern_tag': 201,
            'element_tags': None
        }
    },
    {
        'name': 'Slab_2',
        'type': 'slab',
        'boundary_nodes': {
            12: (20.0, 0.0, 10.0),
            13: (40.0, 0.0, 10.0),
            16: (40.0, 20.0, 10.0),
            15: (20.0, 20.0, 10.0)
        },
        'mesh_size': 5.0,
        'internal_points': None,  # ✓ Column A1 base

        'internal_points': None,
        'voids': None,
        'py_file': 'slab2_model.py',
        'png_file': 'slab2_mesh.png',
        'shell_material_config': ("ElasticIsotropic", 11, 3600.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 11, 11, 8.0 / 12.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 20000,
        'spring_node_start_id': 1100000,
        'start_node_id': 200000,      # Slab 2 mesh nodes start at 120000
        'start_element_id': 130000,   # Slab 2 mesh elements start at 130000
        'load_configs': {
            'pressure': -100.0,
            'time_series_tag': 102,
            'pattern_tag': 202,
            'element_tags': None
        }
    },
    
    # ============================================================
    # FOOTINGS
    # ============================================================
    {
        'name': 'Footing_1_Square',
        'type': 'footing',
        'boundary_nodes': {
            3001: (-3.0, -3.0, 0.0),
            3002: (3.0, -3.0, 0.0),
            3003: (3.0, 3.0, 0.0),
            3004: (-3.0, 3.0, 0.0)
        },
        'mesh_size': 5.0,
        'internal_points': footing1_internal_points,  # ✓ Column A1 base

        'voids': None,
        'py_file': 'footing1_square.py',
        'png_file': 'footing1_square.png',
        'shell_material_config': ("ElasticIsotropic", 21, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 21, 21, 1.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 30000,
        'spring_node_start_id': 1200000,
        'start_node_id': 300000,      # Footing 1 mesh nodes start at 140000
        'start_element_id': 150000,   # Footing 1 mesh elements start at 150000
        'load_configs': {
            'pressure': -200.0,
            'time_series_tag': 301,
            'pattern_tag': 401,
            'element_tags': None
        }
    },
    {
        'name': 'Footing_2_Hexagon',
        'type': 'footing',
        'boundary_nodes': create_regular_polygon_nodes(20.0, 0.0, 3.5, 6, 4001, 0.0),
        'mesh_size': 5.0,
        # 'internal_points': None,
        'internal_points': footing2_internal_points,  # ✓ Column A1 base

        'voids': None,
        'py_file': 'footing2_hexagon.py',
        'png_file': 'footing2_hexagon.png',
        'shell_material_config': ("ElasticIsotropic", 22, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 22, 22, 1.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 40000,
        'spring_node_start_id': 1300000,
        'start_node_id': 400000,      # Footing 2 mesh nodes start at 160000
        'start_element_id': 170000,   # Footing 2 mesh elements start at 170000
        'load_configs': {
            'pressure': -200.0,
            'time_series_tag': 302,
            'pattern_tag': 402,
            'element_tags': None
        }
    },
    {
        'name': 'Footing_3_Octagon',
        'type': 'footing',
        'boundary_nodes': create_regular_polygon_nodes(40.0, 0.0, 3.5, 8, 5001, 0.0),
        'mesh_size': 5.0,
        # 'internal_points': None,
        'internal_points': footing3_internal_points,  # ✓ Column A1 base

        'voids': None,
        'py_file': 'footing3_octagon.py',
        'png_file': 'footing3_octagon.png',
        'shell_material_config': ("ElasticIsotropic", 23, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 23, 23, 1.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 50000,
        'spring_node_start_id': 1400000,
        'start_node_id': 500000,      # Footing 3 mesh nodes start at 180000
        'start_element_id': 190000,   # Footing 3 mesh elements start at 190000
        'load_configs': {
            'pressure': -200.0,
            'time_series_tag': 303,
            'pattern_tag': 403,
            'element_tags': None
        }
    },
    {
        'name': 'Footing_4_Triangle',
        'type': 'footing',
        'boundary_nodes': {
            6001: (-2.5, 17.0, 0.0),
            6002: (2.5, 17.0, 0.0),
            6003: (0.0, 23.0, 0.0)
        },
        'mesh_size': 5.0,
        # 'internal_points': None,
        'internal_points': footing4_internal_points,  # ✓ Column A1 base

        'voids': None,
        'py_file': 'footing4_triangle.py',
        'png_file': 'footing4_triangle.png',
        'shell_material_config': ("ElasticIsotropic", 24, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 24, 24, 1.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 60000,
        'spring_node_start_id': 1500000,
        'start_node_id': 600000,      # Footing 4 mesh nodes start at 200000
        'start_element_id': 210000,   # Footing 4 mesh elements start at 210000
        'load_configs': {
            'pressure': -200.0,
            'time_series_tag': 304,
            'pattern_tag': 404,
            'element_tags': None
        }
    },
    {
        'name': 'Footing_5_Circle',
        'type': 'footing',
        'boundary_nodes': create_regular_polygon_nodes(20.0, 20.0, 3.5, 12, 7001, 0.0),
        'mesh_size': 6.0,
        # 'internal_points': None,
        'internal_points': footing5_internal_points,  # ✓ Column A1 base

        'voids': None,
                # ADD VOID (e.g., for drainage hole):
        # 'voids': [
        #     {
        #         30001: (-0.5, -0.5, 0.0),
        #         30002: (0.5, -0.5, 0.0),
        #         30003: (0.5, 0.5, 0.0),
        #         30004: (-0.5, 0.5, 0.0)
        #     }
        # ],
        
        # # FONT SIZES:
        # 'node_font_size': 9,      # Larger for footings
        # 'element_font_size': 8,

        'py_file': 'footing6_circle.py',
        'png_file': 'footing5_circle.png',
        'shell_material_config': ("ElasticIsotropic", 25, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 25, 25, 1.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 70000,
        'spring_node_start_id': 1600000,
        'start_node_id': 700000,      # Footing 5 mesh nodes start at 220000
        'start_element_id': 230000,   # Footing 5 mesh elements start at 230000
        'load_configs': {
            'pressure': -200.0,
            'time_series_tag': 305,
            'pattern_tag': 405,
            'element_tags': None
        }
    },
    
    {
        'name': 'Footing_6_L_Shaped',
        'type': 'footing',
        'boundary_nodes': {
            8001: (37.0, 17.0, 0.0),
            8002: (43.0, 17.0, 0.0),
            8003: (43.0, 20.0, 0.0),
            8004: (40.0, 20.0, 0.0),
            8005: (40.0, 23.0, 0.0),
            8006: (37.0, 23.0, 0.0)
        },
        'mesh_size': 5.0,
        'internal_points': None,
        'voids': None,
        'py_file': 'footing6_lshaped.py',
        'png_file': 'footing6_lshaped.png',
        'shell_material_config': ("ElasticIsotropic", 26, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 26, 26, 1.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 80000,
        'spring_node_start_id': 1700000,
        'start_node_id': 800000,      # Footing 6 mesh nodes start at 240000
        'start_element_id': 250000,   # Footing 6 mesh elements start at 250000
        'load_configs': {
            'pressure': -200.0,
            'time_series_tag': 306,
            'pattern_tag': 406,
            'element_tags': None
        }
    }
]

# Define loads
load_configs = {
    'time_series': [
        {'tag': 1, 'type': 'Linear'},
    ],
    'patterns': [
        {'tag': 1, 'type': 'Plain', 'ts_tag': 1},
    ],
    'nodal_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                {'node': 11, 'forces': [100, 0, -500, 0, 0, 0]},
            ]
        }
    ],
    'beam_uniform_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                {'elements': [11, 12], 'wy': 0, 'wz': -10},
            ]
        }
    ],
    'shell_surface_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                {'mesh_name': 'Slab_1', 'pressure': -100.0, 'elements': None},
            ]
        }
    ]
}

# Define masses
mass_configs = {
    'beam_column_mass': [
        {'tag': 11, 'density': 1.0, 'area': 4.0},
        {'tag': 12, 'density': 1.0, 'area': 4.0},
    ],
    'nodal_mass': [
        {'node': 11, 'mass': 50.0},
        {'node': 12, 'mass': 75.0},
    ],
    'shell_mass': {
        'calculate': True,
        'exclude': [],  # Or ['Footing_1', 'Footing_2']
        'scale': 1.0
    }
}

# start_node_id=start_node_id,  # ADD
# start_element_id=start_element_id  # ADD
# ===========================================================================================
# BUILD MODEL WITH MULTIPLE SECTIONS
# ===========================================================================================

results = build_model(
    model_params=model_params,
    
    # Pass all 3 fiber sections
    materials_list=[
        concrete_materials,  # Section 1 (2x2 rect, 4 bars)
        concrete_materials,  # Section 2 (2x3 rect, 6 bars)
        concrete_materials   # Section 3 (circular, 8 bars)
    ],
    
    outline_points_list=[
        column_rect_2x2_outline,
        column_rect_2x3_outline,
        column_circular_outline
    ],
    
    rebar_configs_list=[
        column_rect_2x2_rebar,
        column_rect_2x3_rebar,
        column_circular_rebar
    ],
    
    section_params_list=[
        {
            'cover': column_rect_2x2_cover,
            'mesh_size': 5.0,
            'mat_tags': column_rect_2x2_mat_tags,
            'sec_tag': 1,
            'G': G_concrete,
            'save_prefix': 'column_rect_2x2_4bars',
            'section_name': 'Rect_2x2_4bars'
        },
        {
            'cover': column_rect_2x3_cover,
            'mesh_size': 5.0,
            'mat_tags': column_rect_2x3_mat_tags,
            'sec_tag': 2,
            'G': G_concrete,
            'save_prefix': 'column_rect_2x3_6bars',
            'section_name': 'Rect_2x3_6bars'
        },
        {
            'cover': column_circular_cover,
            'mesh_size': 5.0,
            'mat_tags': column_circular_mat_tags,
            'sec_tag': 3,
            'G': G_concrete,
            'save_prefix': 'column_circular_8bars',
            'section_name': 'Circular_2ft_8bars'
        }
    ],
    
    material_params=material_params,
    node_coords=node_coords_dict,
    boundary_conditions=boundary_conditions_dict,
    element_configs=element_configs_dict,
    spring_configs=spring_configs,
    nodal_spring_configs=nodal_spring_configs,
    load_configs=load_configs,      # NEW
    mass_configs=mass_configs,      # NEW
    output_dir="output",
    
    # NEW: Single unified parameter for all shell structures (slabs, footings, walls, etc.)
    slab_configs=slab_configs,
    existing_frame_nodes = node_coords_dict,
    # element_mass_list=element_mass_list,
    # nodal_mass_applied = nodal_mass_applied, 
    
    visualize=True
)


"""
COMPLETE FINAL MODEL FILE GENERATOR
====================================
Generates a complete standalone OpenSeesPy script with everything included
"""



# ============================================================================
# HOW TO USE THIS FUNCTION
# ============================================================================



# Now generate the complete standalone model file:
generate_complete_model_file(
    output_filepath='output/final_complete_model.py',
    model_params=model_params,
    fiber_section_info=results['fiber_sections'],
    material_params=material_params,
    node_coords=node_coords_dict,
    shell_meshes=results['shell_meshes'],
    slab_configs=slab_configs,
    boundary_conditions=boundary_conditions_dict,
    element_configs=element_configs_dict,
    nodal_spring_configs=nodal_spring_configs,
    load_configs=load_configs,
    mass_configs=mass_configs
)

# This creates a standalone .py file that can be run independently:
# python final_complete_model.py


print("\n" + "="*80)
print("MODEL GENERATION COMPLETE!")
print("="*80)
print(f"\nResults Summary:")
print(f"  - Fiber Sections: {len(results['fiber_sections'])}")
print(f"  - Shell Meshes: {len(results['shell_meshes'])}")
print(f"  - Total Nodes: {results['total_nodes']}")
print(f"  - Total Elements: {results['total_elements']}")
print("\nShell Meshes Created:")
for i, mesh in enumerate(results['shell_meshes'], 1):
    print(f"  {i}. {mesh['config_name']}: {len(mesh['nodes'])} nodes, "
          f"{len(mesh['quad4']) + len(mesh['tri3'])} elements")
    

