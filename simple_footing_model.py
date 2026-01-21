# ===========================================================================================
# 6-STORY BUILDING MODEL - 3 BAYS X-DIR, 2 BAYS Y-DIR
# 72 Columns (12 columns x 6 floors) + 90 Beams (15 beams x 6 floors)
# ===========================================================================================
import numpy as np
import opstool as opst
from test3 import build_model

# ===========================================================================================
# MATERIAL DEFINITIONS
# ===========================================================================================
materials_building = {
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

# ===========================================================================================
# SECTION 1: COLUMN 18x18 (Exterior columns)
# ===========================================================================================
col_18x18_outline = [[-9.0, -9.0], [9.0, -9.0], [9.0, 9.0], [-9.0, 9.0]]
col_18x18_cover = 1.5
col_18x18_rebar = [{
    'type': 'points',
    'points': [
        [-7.5, -7.5], [0.0, -7.5], [7.5, -7.5],
        [-7.5, 0.0], [7.5, 0.0],
        [-7.5, 7.5], [0.0, 7.5], [7.5, 7.5]
    ],
    'dia': 1.0,
    'color': 'red',
    'group_name': 'Col_18x18_Rebars'
}]
col_18x18_mat_tags = {'cover': 101, 'core': 102, 'rebar': 103}

# ===========================================================================================
# SECTION 2: COLUMN 24x24 (Interior columns)
# ===========================================================================================
col_24x24_outline = [[-12.0, -12.0], [12.0, -12.0], [12.0, 12.0], [-12.0, 12.0]]
col_24x24_cover = 1.5
col_24x24_rebar = [{
    'type': 'points',
    'points': [
        [-10.5, -10.5], [-3.5, -10.5], [3.5, -10.5], [10.5, -10.5],
        [-10.5, -3.5], [10.5, -3.5],
        [-10.5, 3.5], [10.5, 3.5],
        [-10.5, 10.5], [-3.5, 10.5], [3.5, 10.5], [10.5, 10.5]
    ],
    'dia': 1.128,
    'color': 'red',
    'group_name': 'Col_24x24_Rebars'
}]
col_24x24_mat_tags = {'cover': 104, 'core': 105, 'rebar': 106}

# ===========================================================================================
# MATERIAL PARAMETERS
# ===========================================================================================
G_concrete = 1600.0
material_params_building = [
    # Column 18x18 materials
    ['Concrete01', 101, -4.0, -0.002, -0.8, -0.006],
    ['Concrete01', 102, -5.0, -0.002, -1.0, -0.008],
    ['Steel01', 103, 60.0, 29000.0, 0.015],
    # Column 24x24 materials
    ['Concrete01', 104, -4.0, -0.002, -0.8, -0.006],
    ['Concrete01', 105, -5.0, -0.002, -1.0, -0.008],
    ['Steel01', 106, 60.0, 29000.0, 0.015],
]

# ===========================================================================================
# NODE COORDINATES (4 columns x 3 bays X x 2 bays Y = 12 columns per floor, 7 levels)
# Bay spacing: 25 ft in X, 20 ft in Y
# Heights: Base=0, Ground=5, then 10 ft per floor
# ===========================================================================================
node_coords_building = {
    # LEVEL 0 (Base - 0 ft)
    1: (0.0, 0.0, 0.0), 2: (25.0, 0.0, 0.0), 3: (50.0, 0.0, 0.0), 4: (75.0, 0.0, 0.0),
    5: (0.0, 20.0, 0.0), 6: (25.0, 20.0, 0.0), 7: (50.0, 20.0, 0.0), 8: (75.0, 20.0, 0.0),
    9: (0.0, 40.0, 0.0), 10: (25.0, 40.0, 0.0), 11: (50.0, 40.0, 0.0), 12: (75.0, 40.0, 0.0),
    
    # LEVEL 1 (Ground floor - 5 ft)
    13: (0.0, 0.0, 5.0), 14: (25.0, 0.0, 5.0), 15: (50.0, 0.0, 5.0), 16: (75.0, 0.0, 5.0),
    17: (0.0, 20.0, 5.0), 18: (25.0, 20.0, 5.0), 19: (50.0, 20.0, 5.0), 20: (75.0, 20.0, 5.0),
    21: (0.0, 40.0, 5.0), 22: (25.0, 40.0, 5.0), 23: (50.0, 40.0, 5.0), 24: (75.0, 40.0, 5.0),
    
    # LEVEL 2 (1st floor - 15 ft)
    25: (0.0, 0.0, 15.0), 26: (25.0, 0.0, 15.0), 27: (50.0, 0.0, 15.0), 28: (75.0, 0.0, 15.0),
    29: (0.0, 20.0, 15.0), 30: (25.0, 20.0, 15.0), 31: (50.0, 20.0, 15.0), 32: (75.0, 20.0, 15.0),
    33: (0.0, 40.0, 15.0), 34: (25.0, 40.0, 15.0), 35: (50.0, 40.0, 15.0), 36: (75.0, 40.0, 15.0),
    
    # LEVEL 3 (2nd floor - 25 ft)
    37: (0.0, 0.0, 25.0), 38: (25.0, 0.0, 25.0), 39: (50.0, 0.0, 25.0), 40: (75.0, 0.0, 25.0),
    41: (0.0, 20.0, 25.0), 42: (25.0, 20.0, 25.0), 43: (50.0, 20.0, 25.0), 44: (75.0, 20.0, 25.0),
    45: (0.0, 40.0, 25.0), 46: (25.0, 40.0, 25.0), 47: (50.0, 40.0, 25.0), 48: (75.0, 40.0, 25.0),
    
    # LEVEL 4 (3rd floor - 35 ft)
    49: (0.0, 0.0, 35.0), 50: (25.0, 0.0, 35.0), 51: (50.0, 0.0, 35.0), 52: (75.0, 0.0, 35.0),
    53: (0.0, 20.0, 35.0), 54: (25.0, 20.0, 35.0), 55: (50.0, 20.0, 35.0), 56: (75.0, 20.0, 35.0),
    57: (0.0, 40.0, 35.0), 58: (25.0, 40.0, 35.0), 59: (50.0, 40.0, 35.0), 60: (75.0, 40.0, 35.0),
    
    # LEVEL 5 (4th floor - 45 ft)
    61: (0.0, 0.0, 45.0), 62: (25.0, 0.0, 45.0), 63: (50.0, 0.0, 45.0), 64: (75.0, 0.0, 45.0),
    65: (0.0, 20.0, 45.0), 66: (25.0, 20.0, 45.0), 67: (50.0, 20.0, 45.0), 68: (75.0, 20.0, 45.0),
    69: (0.0, 40.0, 45.0), 70: (25.0, 40.0, 45.0), 71: (50.0, 40.0, 45.0), 72: (75.0, 40.0, 45.0),
    
    # LEVEL 6 (5th floor - 55 ft)
    73: (0.0, 0.0, 55.0), 74: (25.0, 0.0, 55.0), 75: (50.0, 0.0, 55.0), 76: (75.0, 0.0, 55.0),
    77: (0.0, 20.0, 55.0), 78: (25.0, 20.0, 55.0), 79: (50.0, 20.0, 55.0), 80: (75.0, 20.0, 55.0),
    81: (0.0, 40.0, 55.0), 82: (25.0, 40.0, 55.0), 83: (50.0, 40.0, 55.0), 84: (75.0, 40.0, 55.0),
}

# ===========================================================================================
# BOUNDARY CONDITIONS (Fixed at base nodes)
# ===========================================================================================
boundary_conditions_building = {
    1: [1, 1, 1, 1, 1, 1], 2: [1, 1, 1, 1, 1, 1], 3: [1, 1, 1, 1, 1, 1], 4: [1, 1, 1, 1, 1, 1],
    5: [1, 1, 1, 1, 1, 1], 6: [1, 1, 1, 1, 1, 1], 7: [1, 1, 1, 1, 1, 1], 8: [1, 1, 1, 1, 1, 1],
    9: [1, 1, 1, 1, 1, 1], 10: [1, 1, 1, 1, 1, 1], 11: [1, 1, 1, 1, 1, 1], 12: [1, 1, 1, 1, 1, 1],
}

# ===========================================================================================
# ELEMENT CONFIGURATIONS
# ===========================================================================================
element_configs_building = {
    'transformations': [
        {'type': 'Linear', 'tag': 1, 'vecxz': [1, 0, 0]},  # For columns
        {'type': 'Linear', 'tag': 2, 'vecxz': [0, 0, 1]},  # For beams in X
        {'type': 'Linear', 'tag': 3, 'vecxz': [0, 0, 1]},  # For beams in Y
    ],
    'integrations': [
        {'type': 'Lobatto', 'tag': 1, 'sec_tag': 1, 'np': 5},  # Col 18x18
        {'type': 'Lobatto', 'tag': 2, 'sec_tag': 2, 'np': 5},  # Col 24x24
    ],
    'force_beam_columns': [
        # ===== COLUMNS (72 total) =====
        # Ground floor columns (Base to Level 1: 0 to 5 ft)
        # Exterior columns (18x18)
        {'tag': 1, 'node_i': 1, 'node_j': 13, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 2, 'node_i': 4, 'node_j': 16, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 3, 'node_i': 9, 'node_j': 21, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 4, 'node_i': 12, 'node_j': 24, 'transf_tag': 1, 'integ_tag': 1},
        # Interior/edge columns (24x24)
        {'tag': 5, 'node_i': 2, 'node_j': 14, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 6, 'node_i': 3, 'node_j': 15, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 7, 'node_i': 5, 'node_j': 17, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 8, 'node_i': 6, 'node_j': 18, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 9, 'node_i': 7, 'node_j': 19, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 10, 'node_i': 8, 'node_j': 20, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 11, 'node_i': 10, 'node_j': 22, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 12, 'node_i': 11, 'node_j': 23, 'transf_tag': 1, 'integ_tag': 2},
        
        # 1st floor columns (Level 1 to Level 2: 5 to 15 ft)
        {'tag': 13, 'node_i': 13, 'node_j': 25, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 14, 'node_i': 16, 'node_j': 28, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 15, 'node_i': 21, 'node_j': 33, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 16, 'node_i': 24, 'node_j': 36, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 17, 'node_i': 14, 'node_j': 26, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 18, 'node_i': 15, 'node_j': 27, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 19, 'node_i': 17, 'node_j': 29, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 20, 'node_i': 18, 'node_j': 30, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 21, 'node_i': 19, 'node_j': 31, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 22, 'node_i': 20, 'node_j': 32, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 23, 'node_i': 22, 'node_j': 34, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 24, 'node_i': 23, 'node_j': 35, 'transf_tag': 1, 'integ_tag': 2},
        
        # 2nd floor columns (Level 2 to Level 3: 15 to 25 ft)
        {'tag': 25, 'node_i': 25, 'node_j': 37, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 26, 'node_i': 28, 'node_j': 40, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 27, 'node_i': 33, 'node_j': 45, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 28, 'node_i': 36, 'node_j': 48, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 29, 'node_i': 26, 'node_j': 38, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 30, 'node_i': 27, 'node_j': 39, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 31, 'node_i': 29, 'node_j': 41, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 32, 'node_i': 30, 'node_j': 42, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 33, 'node_i': 31, 'node_j': 43, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 34, 'node_i': 32, 'node_j': 44, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 35, 'node_i': 34, 'node_j': 46, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 36, 'node_i': 35, 'node_j': 47, 'transf_tag': 1, 'integ_tag': 2},
        
        # 3rd floor columns (Level 3 to Level 4: 25 to 35 ft)
        {'tag': 37, 'node_i': 37, 'node_j': 49, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 38, 'node_i': 40, 'node_j': 52, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 39, 'node_i': 45, 'node_j': 57, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 40, 'node_i': 48, 'node_j': 60, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 41, 'node_i': 38, 'node_j': 50, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 42, 'node_i': 39, 'node_j': 51, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 43, 'node_i': 41, 'node_j': 53, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 44, 'node_i': 42, 'node_j': 54, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 45, 'node_i': 43, 'node_j': 55, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 46, 'node_i': 44, 'node_j': 56, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 47, 'node_i': 46, 'node_j': 58, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 48, 'node_i': 47, 'node_j': 59, 'transf_tag': 1, 'integ_tag': 2},
        
        # 4th floor columns (Level 4 to Level 5: 35 to 45 ft)
        {'tag': 49, 'node_i': 49, 'node_j': 61, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 50, 'node_i': 52, 'node_j': 64, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 51, 'node_i': 57, 'node_j': 69, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 52, 'node_i': 60, 'node_j': 72, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 53, 'node_i': 50, 'node_j': 62, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 54, 'node_i': 51, 'node_j': 63, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 55, 'node_i': 53, 'node_j': 65, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 56, 'node_i': 54, 'node_j': 66, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 57, 'node_i': 55, 'node_j': 67, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 58, 'node_i': 56, 'node_j': 68, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 59, 'node_i': 58, 'node_j': 70, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 60, 'node_i': 59, 'node_j': 71, 'transf_tag': 1, 'integ_tag': 2},
        
        # 5th floor columns (Level 5 to Level 6: 45 to 55 ft)
        {'tag': 61, 'node_i': 61, 'node_j': 73, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 62, 'node_i': 64, 'node_j': 76, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 63, 'node_i': 69, 'node_j': 81, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 64, 'node_i': 72, 'node_j': 84, 'transf_tag': 1, 'integ_tag': 1},
        {'tag': 65, 'node_i': 62, 'node_j': 74, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 66, 'node_i': 63, 'node_j': 75, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 67, 'node_i': 65, 'node_j': 77, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 68, 'node_i': 66, 'node_j': 78, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 69, 'node_i': 67, 'node_j': 79, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 70, 'node_i': 68, 'node_j': 80, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 71, 'node_i': 70, 'node_j': 82, 'transf_tag': 1, 'integ_tag': 2},
        {'tag': 72, 'node_i': 71, 'node_j': 83, 'transf_tag': 1, 'integ_tag': 2},
    ],
    'elastic_beam_columns': [
        # ===== BEAMS (90 total = 15 beams/floor x 6 floors) =====
        # Beam properties: 12"x24" beam
        # A = 288 in², E = 3600 ksi, G = 1600 ksi
        # J = 13824 in⁴, Iy = 13824 in⁴ (strong axis), Iz = 3456 in⁴ (weak axis)
        
        # === LEVEL 1 BEAMS (Ground floor - 5 ft) ===
        # X-direction beams (9 beams)
        {'tag': 1001, 'node_i': 13, 'node_j': 14, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1002, 'node_i': 14, 'node_j': 15, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1003, 'node_i': 15, 'node_j': 16, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1004, 'node_i': 17, 'node_j': 18, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1005, 'node_i': 18, 'node_j': 19, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1006, 'node_i': 19, 'node_j': 20, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1007, 'node_i': 21, 'node_j': 22, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1008, 'node_i': 22, 'node_j': 23, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 1009, 'node_i': 23, 'node_j': 24, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        # Y-direction beams (6 beams)
        {'tag': 1010, 'node_i': 13, 'node_j': 17, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 1011, 'node_i': 14, 'node_j': 18, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 1012, 'node_i': 15, 'node_j': 19, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 1013, 'node_i': 16, 'node_j': 20, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 1014, 'node_i': 17, 'node_j': 21, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 1015, 'node_i': 18, 'node_j': 22, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 1016, 'node_i': 19, 'node_j': 23, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 1017, 'node_i': 20, 'node_j': 24, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        
        # === LEVEL 2 BEAMS (1st floor - 15 ft) ===
        # X-direction beams (9 beams)
        {'tag': 2001, 'node_i': 25, 'node_j': 26, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2002, 'node_i': 26, 'node_j': 27, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2003, 'node_i': 27, 'node_j': 28, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2004, 'node_i': 29, 'node_j': 30, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2005, 'node_i': 30, 'node_j': 31, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2006, 'node_i': 31, 'node_j': 32, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2007, 'node_i': 33, 'node_j': 34, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2008, 'node_i': 34, 'node_j': 35, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 2009, 'node_i': 35, 'node_j': 36, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        # Y-direction beams (6 beams)
        {'tag': 2010, 'node_i': 25, 'node_j': 29, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 2011, 'node_i': 26, 'node_j': 30, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 2012, 'node_i': 27, 'node_j': 31, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 2013, 'node_i': 28, 'node_j': 32, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 2014, 'node_i': 29, 'node_j': 33, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 2015, 'node_i': 30, 'node_j': 34, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 2016, 'node_i': 31, 'node_j': 35, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 2017, 'node_i': 32, 'node_j': 36, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        
        # === LEVEL 3 BEAMS (2nd floor - 25 ft) ===
        # X-direction beams (9 beams)
        {'tag': 3001, 'node_i': 37, 'node_j': 38, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3002, 'node_i': 38, 'node_j': 39, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3003, 'node_i': 39, 'node_j': 40, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3004, 'node_i': 41, 'node_j': 42, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3005, 'node_i': 42, 'node_j': 43, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3006, 'node_i': 43, 'node_j': 44, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3007, 'node_i': 45, 'node_j': 46, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3008, 'node_i': 46, 'node_j': 47, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 3009, 'node_i': 47, 'node_j': 48, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        # Y-direction beams (6 beams)
        {'tag': 3010, 'node_i': 37, 'node_j': 41, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 3011, 'node_i': 38, 'node_j': 42, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 3012, 'node_i': 39, 'node_j': 43, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 3013, 'node_i': 40, 'node_j': 44, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 3014, 'node_i': 41, 'node_j': 45, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 3015, 'node_i': 42, 'node_j': 46, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 3016, 'node_i': 43, 'node_j': 47, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 3017, 'node_i': 44, 'node_j': 48, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        
        # === LEVEL 4 BEAMS (3rd floor - 35 ft) ===
        # X-direction beams (9 beams)
        {'tag': 4001, 'node_i': 49, 'node_j': 50, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4002, 'node_i': 50, 'node_j': 51, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4003, 'node_i': 51, 'node_j': 52, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4004, 'node_i': 53, 'node_j': 54, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4005, 'node_i': 54, 'node_j': 55, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4006, 'node_i': 55, 'node_j': 56, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4007, 'node_i': 57, 'node_j': 58, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4008, 'node_i': 58, 'node_j': 59, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 4009, 'node_i': 59, 'node_j': 60, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        # Y-direction beams (6 beams)
        {'tag': 4010, 'node_i': 49, 'node_j': 53, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 4011, 'node_i': 50, 'node_j': 54, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 4012, 'node_i': 51, 'node_j': 55, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 4013, 'node_i': 52, 'node_j': 56, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 4014, 'node_i': 53, 'node_j': 57, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 4015, 'node_i': 54, 'node_j': 58, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 4016, 'node_i': 55, 'node_j': 59, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 4017, 'node_i': 56, 'node_j': 60, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        
        # === LEVEL 5 BEAMS (4th floor - 45 ft) ===
        # X-direction beams (9 beams)
        {'tag': 5001, 'node_i': 61, 'node_j': 62, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5002, 'node_i': 62, 'node_j': 63, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5003, 'node_i': 63, 'node_j': 64, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5004, 'node_i': 65, 'node_j': 66, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5005, 'node_i': 66, 'node_j': 67, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5006, 'node_i': 67, 'node_j': 68, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5007, 'node_i': 69, 'node_j': 70, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5008, 'node_i': 70, 'node_j': 71, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 5009, 'node_i': 71, 'node_j': 72, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        # Y-direction beams (6 beams)
        {'tag': 5010, 'node_i': 61, 'node_j': 65, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 5011, 'node_i': 62, 'node_j': 66, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 5012, 'node_i': 63, 'node_j': 67, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 5013, 'node_i': 64, 'node_j': 68, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 5014, 'node_i': 65, 'node_j': 69, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 5015, 'node_i': 66, 'node_j': 70, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 5016, 'node_i': 67, 'node_j': 71, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 5017, 'node_i': 68, 'node_j': 72, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        
        # === LEVEL 6 BEAMS (5th floor - 55 ft) ===
        # X-direction beams (9 beams)
        {'tag': 6001, 'node_i': 73, 'node_j': 74, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6002, 'node_i': 74, 'node_j': 75, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6003, 'node_i': 75, 'node_j': 76, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6004, 'node_i': 77, 'node_j': 78, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6005, 'node_i': 78, 'node_j': 79, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6006, 'node_i': 79, 'node_j': 80, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6007, 'node_i': 81, 'node_j': 82, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6008, 'node_i': 82, 'node_j': 83, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        {'tag': 6009, 'node_i': 83, 'node_j': 84, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 13824.0, 'Iz': 3456.0, 'transf_tag': 2},
        # Y-direction beams (6 beams)
        {'tag': 6010, 'node_i': 73, 'node_j': 77, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 6011, 'node_i': 74, 'node_j': 78, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 6012, 'node_i': 75, 'node_j': 79, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 6013, 'node_i': 76, 'node_j': 80, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 6014, 'node_i': 77, 'node_j': 81, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 6015, 'node_i': 78, 'node_j': 82, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 6016, 'node_i': 79, 'node_j': 83, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
        {'tag': 6017, 'node_i': 80, 'node_j': 84, 'A': 288.0, 'E': 3600.0, 'G': 1600.0, 'J': 13824.0, 'Iy': 3456.0, 'Iz': 13824.0, 'transf_tag': 3},
    ]
}

# ===========================================================================================
# DIAPHRAGM CONSTRAINTS (Rigid diaphragm at each floor level)
# Format: [perpendicular_direction, retained_node, constrained_nodes...]
# perpendicular_direction = 3 means diaphragm in XY plane (perpendicular to Z)
# ===========================================================================================
diaphragm_list_building = [
    [3, 18, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24],  # Level 1 (Ground floor)
    [3, 30, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36],  # Level 2 (1st floor)
    [3, 42, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48],  # Level 3 (2nd floor)
    [3, 54, 49, 50, 51, 52, 53, 55, 56, 57, 58, 59, 60],  # Level 4 (3rd floor)
    [3, 66, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 72],  # Level 5 (4th floor)
    [3, 78, 73, 74, 75, 76, 77, 79, 80, 81, 82, 83, 84],  # Level 6 (5th floor)
]

# ===========================================================================================
# CALCULATE CENTER OF MASS FOR EACH FLOOR (Average of node coordinates)
# ===========================================================================================
# Level 1 center: (37.5, 20.0, 5.0)
# Level 2 center: (37.5, 20.0, 15.0)
# Level 3 center: (37.5, 20.0, 25.0)
# Level 4 center: (37.5, 20.0, 35.0)
# Level 5 center: (37.5, 20.0, 45.0)
# Level 6 center: (37.5, 20.0, 55.0)

# ===========================================================================================
# LOAD CONFIGURATIONS
# Apply loads at center of mass of each diaphragm (retained nodes)
# Self-weight UDL on all beams
# Self-weight loads on columns as nodal loads
# ===========================================================================================

# Calculate column self-weight loads
# 18x18 column: 324 in² × 0.150 kcf = 0.0337 kip/ft
# 24x24 column: 576 in² × 0.150 kcf = 0.06 kip/ft
# Ground floor height: 5 ft, Other floors: 10 ft

col_18x18_sw_ground = 0.0337 * 5.0 / 2.0  # Half to top, half to bottom = 0.084 kip
col_24x24_sw_ground = 0.06 * 5.0 / 2.0  # = 0.15 kip
col_18x18_sw_typical = 0.0337 * 10.0 / 2.0  # = 0.169 kip
col_24x24_sw_typical = 0.06 * 10.0 / 2.0  # = 0.3 kip

load_configs_building = {
    'time_series': [{'tag': 1, 'type': 'Linear'}],
    'patterns': [{'tag': 1, 'type': 'Plain', 'ts_tag': 1}],
    'nodal_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                # Dead + Live loads at center of mass (retained node of each diaphragm)
                {'node': 18, 'forces': [0, 0, -200.0, 0, 0, 0]},  # Level 1
                {'node': 30, 'forces': [0, 0, -200.0, 0, 0, 0]},  # Level 2
                {'node': 42, 'forces': [0, 0, -200.0, 0, 0, 0]},  # Level 3
                {'node': 54, 'forces': [0, 0, -200.0, 0, 0, 0]},  # Level 4
                {'node': 66, 'forces': [0, 0, -200.0, 0, 0, 0]},  # Level 5
                {'node': 78, 'forces': [0, 0, -100.0, 0, 0, 0]},  # Level 6 (Roof - reduced)
                
                # Column self-weight loads - Ground floor (Base to Level 1)
                # 18x18 exterior columns
                {'node': 1, 'forces': [0, 0, -0.084, 0, 0, 0]},
                {'node': 13, 'forces': [0, 0, -0.084, 0, 0, 0]},
                {'node': 4, 'forces': [0, 0, -0.084, 0, 0, 0]},
                {'node': 16, 'forces': [0, 0, -0.084, 0, 0, 0]},
                {'node': 9, 'forces': [0, 0, -0.084, 0, 0, 0]},
                {'node': 21, 'forces': [0, 0, -0.084, 0, 0, 0]},
                {'node': 12, 'forces': [0, 0, -0.084, 0, 0, 0]},
                {'node': 24, 'forces': [0, 0, -0.084, 0, 0, 0]},
                # 24x24 interior columns
                {'node': 2, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 14, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 3, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 15, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 5, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 17, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 6, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 18, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 7, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 19, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 8, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 20, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 10, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 22, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 11, 'forces': [0, 0, -0.15, 0, 0, 0]},
                {'node': 23, 'forces': [0, 0, -0.15, 0, 0, 0]},
                
                # Column self-weight loads - 1st floor (Level 1 to Level 2)
                # 18x18 exterior columns
                {'node': 13, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 25, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 16, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 28, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 21, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 33, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 24, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 36, 'forces': [0, 0, -0.169, 0, 0, 0]},
                # 24x24 interior columns
                {'node': 14, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 26, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 15, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 27, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 17, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 29, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 18, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 30, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 19, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 31, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 20, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 32, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 22, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 34, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 23, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 35, 'forces': [0, 0, -0.3, 0, 0, 0]},
                
                # Column self-weight loads - 2nd floor (Level 2 to Level 3)
                {'node': 25, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 37, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 28, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 40, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 33, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 45, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 36, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 48, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 26, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 38, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 27, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 39, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 29, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 41, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 30, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 42, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 31, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 43, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 32, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 44, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 34, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 46, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 35, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 47, 'forces': [0, 0, -0.3, 0, 0, 0]},
                
                # Column self-weight loads - 3rd floor (Level 3 to Level 4)
                {'node': 37, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 49, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 40, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 52, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 45, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 57, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 48, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 60, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 38, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 50, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 39, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 51, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 41, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 53, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 42, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 54, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 43, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 55, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 44, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 56, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 46, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 58, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 47, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 59, 'forces': [0, 0, -0.3, 0, 0, 0]},
                
                # Column self-weight loads - 4th floor (Level 4 to Level 5)
                {'node': 49, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 61, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 52, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 64, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 57, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 69, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 60, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 72, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 50, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 62, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 51, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 63, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 53, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 65, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 54, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 66, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 55, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 67, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 56, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 68, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 58, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 70, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 59, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 71, 'forces': [0, 0, -0.3, 0, 0, 0]},
                
                # Column self-weight loads - 5th floor (Level 5 to Level 6)
                {'node': 61, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 73, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 64, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 76, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 69, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 81, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 72, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 84, 'forces': [0, 0, -0.169, 0, 0, 0]},
                {'node': 62, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 74, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 63, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 75, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 65, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 77, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 66, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 78, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 67, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 79, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 68, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 80, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 70, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 82, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 71, 'forces': [0, 0, -0.3, 0, 0, 0]},
                {'node': 83, 'forces': [0, 0, -0.3, 0, 0, 0]},
            ]
        }
    ],
    'beam_uniform_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                # Self-weight UDL on all beams (12"x24" beam: 288 in² × 0.150 kcf = 0.3 kip/ft)
                # Level 1 beams
                {'elements': [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009], 'wy': 0, 'wz': -0.3},
                {'elements': [1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017], 'wx': 0, 'wz': -0.3},
                # Level 2 beams
                {'elements': [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009], 'wy': 0, 'wz': -0.3},
                {'elements': [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017], 'wx': 0, 'wz': -0.3},
                # Level 3 beams
                {'elements': [3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009], 'wy': 0, 'wz': -0.3},
                {'elements': [3010, 3011, 3012, 3013, 3014, 3015, 3016, 3017], 'wx': 0, 'wz': -0.3},
                # Level 4 beams
                {'elements': [4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 4009], 'wy': 0, 'wz': -0.3},
                {'elements': [4010, 4011, 4012, 4013, 4014, 4015, 4016, 4017], 'wx': 0, 'wz': -0.3},
                # Level 5 beams
                {'elements': [5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009], 'wy': 0, 'wz': -0.3},
                {'elements': [5010, 5011, 5012, 5013, 5014, 5015, 5016, 5017], 'wx': 0, 'wz': -0.3},
                # Level 6 beams
                {'elements': [6001, 6002, 6003, 6004, 6005, 6006, 6007, 6008, 6009], 'wy': 0, 'wz': -0.3},
                {'elements': [6010, 6011, 6012, 6013, 6014, 6015, 6016, 6017], 'wx': 0, 'wz': -0.3},
            ]
        }
    ],
}

# ===========================================================================================
# MASS CONFIGURATIONS
# Apply self-weight mass to all beams and columns
# ===========================================================================================
mass_configs_building = {
    'beam_column_mass': [
        # Column masses (18x18 = 324 in², 24x24 = 576 in²)
        # 18x18 exterior columns
        {'tag': 1, 'density': 0.150, 'area': 324.0}, {'tag': 2, 'density': 0.150, 'area': 324.0},
        {'tag': 3, 'density': 0.150, 'area': 324.0}, {'tag': 4, 'density': 0.150, 'area': 324.0},
        {'tag': 13, 'density': 0.150, 'area': 324.0}, {'tag': 14, 'density': 0.150, 'area': 324.0},
        {'tag': 15, 'density': 0.150, 'area': 324.0}, {'tag': 16, 'density': 0.150, 'area': 324.0},
        {'tag': 25, 'density': 0.150, 'area': 324.0}, {'tag': 26, 'density': 0.150, 'area': 324.0},
        {'tag': 27, 'density': 0.150, 'area': 324.0}, {'tag': 28, 'density': 0.150, 'area': 324.0},
        {'tag': 37, 'density': 0.150, 'area': 324.0}, {'tag': 38, 'density': 0.150, 'area': 324.0},
        {'tag': 39, 'density': 0.150, 'area': 324.0}, {'tag': 40, 'density': 0.150, 'area': 324.0},
        {'tag': 49, 'density': 0.150, 'area': 324.0}, {'tag': 50, 'density': 0.150, 'area': 324.0},
        {'tag': 51, 'density': 0.150, 'area': 324.0}, {'tag': 52, 'density': 0.150, 'area': 324.0},
        {'tag': 61, 'density': 0.150, 'area': 324.0}, {'tag': 62, 'density': 0.150, 'area': 324.0},
        {'tag': 63, 'density': 0.150, 'area': 324.0}, {'tag': 64, 'density': 0.150, 'area': 324.0},
        # 24x24 interior columns
        {'tag': 5, 'density': 0.150, 'area': 576.0}, {'tag': 6, 'density': 0.150, 'area': 576.0},
        {'tag': 7, 'density': 0.150, 'area': 576.0}, {'tag': 8, 'density': 0.150, 'area': 576.0},
        {'tag': 9, 'density': 0.150, 'area': 576.0}, {'tag': 10, 'density': 0.150, 'area': 576.0},
        {'tag': 11, 'density': 0.150, 'area': 576.0}, {'tag': 12, 'density': 0.150, 'area': 576.0},
        {'tag': 17, 'density': 0.150, 'area': 576.0}, {'tag': 18, 'density': 0.150, 'area': 576.0},
        {'tag': 19, 'density': 0.150, 'area': 576.0}, {'tag': 20, 'density': 0.150, 'area': 576.0},
        {'tag': 21, 'density': 0.150, 'area': 576.0}, {'tag': 22, 'density': 0.150, 'area': 576.0},
        {'tag': 23, 'density': 0.150, 'area': 576.0}, {'tag': 24, 'density': 0.150, 'area': 576.0},
        {'tag': 29, 'density': 0.150, 'area': 576.0}, {'tag': 30, 'density': 0.150, 'area': 576.0},
        {'tag': 31, 'density': 0.150, 'area': 576.0}, {'tag': 32, 'density': 0.150, 'area': 576.0},
        {'tag': 33, 'density': 0.150, 'area': 576.0}, {'tag': 34, 'density': 0.150, 'area': 576.0},
        {'tag': 35, 'density': 0.150, 'area': 576.0}, {'tag': 36, 'density': 0.150, 'area': 576.0},
        {'tag': 41, 'density': 0.150, 'area': 576.0}, {'tag': 42, 'density': 0.150, 'area': 576.0},
        {'tag': 43, 'density': 0.150, 'area': 576.0}, {'tag': 44, 'density': 0.150, 'area': 576.0},
        {'tag': 45, 'density': 0.150, 'area': 576.0}, {'tag': 46, 'density': 0.150, 'area': 576.0},
        {'tag': 47, 'density': 0.150, 'area': 576.0}, {'tag': 48, 'density': 0.150, 'area': 576.0},
        {'tag': 53, 'density': 0.150, 'area': 576.0}, {'tag': 54, 'density': 0.150, 'area': 576.0},
        {'tag': 55, 'density': 0.150, 'area': 576.0}, {'tag': 56, 'density': 0.150, 'area': 576.0},
        {'tag': 57, 'density': 0.150, 'area': 576.0}, {'tag': 58, 'density': 0.150, 'area': 576.0},
        {'tag': 59, 'density': 0.150, 'area': 576.0}, {'tag': 60, 'density': 0.150, 'area': 576.0},
        {'tag': 65, 'density': 0.150, 'area': 576.0}, {'tag': 66, 'density': 0.150, 'area': 576.0},
        {'tag': 67, 'density': 0.150, 'area': 576.0}, {'tag': 68, 'density': 0.150, 'area': 576.0},
        {'tag': 69, 'density': 0.150, 'area': 576.0}, {'tag': 70, 'density': 0.150, 'area': 576.0},
        {'tag': 71, 'density': 0.150, 'area': 576.0}, {'tag': 72, 'density': 0.150, 'area': 576.0},
        # Beam masses (all beams: 288 in²)
        {'tag': 1001, 'density': 0.150, 'area': 288.0}, {'tag': 1002, 'density': 0.150, 'area': 288.0},
        {'tag': 1003, 'density': 0.150, 'area': 288.0}, {'tag': 1004, 'density': 0.150, 'area': 288.0},
        {'tag': 1005, 'density': 0.150, 'area': 288.0}, {'tag': 1006, 'density': 0.150, 'area': 288.0},
        {'tag': 1007, 'density': 0.150, 'area': 288.0}, {'tag': 1008, 'density': 0.150, 'area': 288.0},
        {'tag': 1009, 'density': 0.150, 'area': 288.0},
    ],
    'nodal_mass': [
        # Additional floor masses at center of mass (retained nodes)
        {'node': 18, 'mass': 150.0},
        {'node': 30, 'mass': 150.0},
        {'node': 42, 'mass': 150.0},
        {'node': 54, 'mass': 150.0},
        {'node': 66, 'mass': 150.0},
        {'node': 78, 'mass': 100.0},  # Roof
    ],
}

# ===========================================================================================
# BUILD MODEL
# ===========================================================================================
results = build_model(
    model_params={'ndm': 3, 'ndf': 6},
    materials_list=[materials_building, materials_building],
    outline_points_list=[col_18x18_outline, col_24x24_outline],
    rebar_configs_list=[col_18x18_rebar, col_24x24_rebar],
    section_params_list=[
        {
            'cover': col_18x18_cover,
            'mesh_size': 3.0,
            'mat_tags': col_18x18_mat_tags,
            'sec_tag': 1,
            'G': G_concrete,
            'save_prefix': 'column_18x18',
            'section_name': 'Column_18x18'
        },
        {
            'cover': col_24x24_cover,
            'mesh_size': 3.0,
            'mat_tags': col_24x24_mat_tags,
            'sec_tag': 2,
            'G': G_concrete,
            'save_prefix': 'column_24x24',
            'section_name': 'Column_24x24'
        }
    ],
    material_params=material_params_building,
    node_coords=node_coords_building,
    boundary_conditions=boundary_conditions_building,
    element_configs=element_configs_building,
    spring_configs=None,
    nodal_spring_configs=None,
    diaphragm_list=diaphragm_list_building,
    load_configs=load_configs_building,
    mass_configs=mass_configs_building,
    visualize=True,
    output_dir="output",
    slab_configs=None,
    existing_frame_nodes=None
)

print("=" * 80)
print("6-STORY BUILDING MODEL COMPLETE")
print("=" * 80)
print(f"Total Columns: 72 (12 per floor × 6 floors)")
print(f"Total Beams: 90 (15 per floor × 6 floors)")
print(f"Total Nodes: 84 (12 per level × 7 levels)")
print(f"Column Sections: 2 fiber sections (18x18 and 24x24)")
print(f"Beam Sections: Elastic (12x24)")
print(f"Diaphragm Constraints: 6 rigid diaphragms")
print(f"Self-weight loads applied to all beams and columns")
print(f"Nodal loads applied at center of mass of each floor")
print("=" * 80)
