def get_default_examples():
    """Get default example configurations"""
    examples = {}
    
    examples['simple_building'] = {
        'name': 'Simple Building',
        'description': '2-column structure with fiber sections',
        'code': '''


import numpy as np
import openseespy.opensees as ops
import opstool as opst
# ==================================================
# STEP 1: DEFINE MODEL PARAMETERS
# ==================================================
model_params = {
    'ndm': 3,
    'ndf': 6
}
import os  # ADD THIS LINE
output_dir = "output"  # This will be replaced by the build process

# ==================================================
# STEP 2: DEFINE NODES
# ==================================================
floor_height = 12.0  # ft
bay_x = 20.0  # ft
bay_y = 20.0  # ft
node_coords = {
    # Ground floor nodes (z=0)
    1: (0.0, 0.0, 0.0),
    2: (20.0, 0.0, 0.0),
    3: (20.0, 20.0, 0.0),
    4: (0.0, 20.0, 0.0),
    
    # First floor nodes (z=12)
    11: (0.0, 0.0, 12.0),
    12: (20.0, 0.0, 12.0),
    13: (20.0, 20.0, 12.0),
    14: (0.0, 20.0, 12.0)
}
# ==================================================
# STEP 3: DEFINE UNIAXIAL MATERIALS
# ==================================================
material_params = [
    ('Concrete01', 1, -4.0, -0.002, -0.5, -0.005),
    ('Concrete01', 2, -5.0, -0.002, -0.5, -0.005),
    ('Steel02', 3, 60.0, 29000.0, 0.01, 18.0, 0.925, 0.15),
]
# ==================================================
# STEP 4: DEFINE MATERIALS FOR FIBER SECTIONS
# ==================================================
materials_col = {
    'concrete_core': {
        'elastic_modulus': 3600.0,
        'poissons_ratio': 0.2,
        'density': 0.0868,
        'color': '#88b378'
    },
    'concrete_cover': {
        'elastic_modulus': 3600.0,
        'poissons_ratio': 0.2,
        'density': 0.0868,
        'color': '#dbb40c'
    },
    'steel_rebar': {
        'elastic_modulus': 29000.0,
        'poissons_ratio': 0.3,
        'density': 0.490,
        'yield_strength': 60.0,
        'color': 'black'
    }
}
# ==================================================
# STEP 5: DEFINE COLUMN FIBER SECTIONS
# ==================================================
width_1 = 18.0 / 12.0
height_1 = 18.0 / 12.0
cover_1 = 1.5 / 12.0
outline_points_1 = [
    [-width_1/2, -height_1/2],
    [width_1/2, -height_1/2],
    [width_1/2, height_1/2],
    [-width_1/2, height_1/2]
]
rebar_configs_1 = [
    {
        'type': 'line',
        'points': [[-width_1/2 + cover_1, -height_1/2 + cover_1],
                   [width_1/2 - cover_1, -height_1/2 + cover_1]],
        'dia': 1.0 / 12.0,
        'n': 3,
        'gap': None,
        'color': 'black'
    },
    {
        'type': 'line',
        'points': [[-width_1/2 + cover_1, height_1/2 - cover_1],
                   [width_1/2 - cover_1, height_1/2 - cover_1]],
        'dia': 1.0 / 12.0,
        'n': 3,
        'gap': None,
        'color': 'black'
    },
    {
        'type': 'line',
        'points': [[-width_1/2 + cover_1, -height_1/2 + cover_1],
                   [-width_1/2 + cover_1, height_1/2 - cover_1]],
        'dia': 1.0 / 12.0,
        'n': 2,
        'gap': None,
        'color': 'black'
    },
    {
        'type': 'line',
        'points': [[width_1/2 - cover_1, -height_1/2 + cover_1],
                   [width_1/2 - cover_1, height_1/2 - cover_1]],
        'dia': 1.0 / 12.0,
        'n': 2,
        'gap': None,
        'color': 'black'
    }
]


fiber_config_1 = {
    'materials': materials_col,
    'outline_points': outline_points_1,
    'core_material': 'concrete_core',
    'mesh_sizes': 50,
    'ops_mat_tags': {
        'cover': 1,
        'core': 2,
        'rebar': 3
    },
    'cover_thickness': cover_1,
    'cover_material': 'concrete_cover',
    'rebar_configs': rebar_configs_1,
    'steel_material': 'steel_rebar',
    'sec_tag': 1,
    'G': 1500.0,
    'save_prefix': 'column_18x18',  # JUST FILENAME PREFIX
    'section_name': 'Column_18x18',
    'display_results': False,
    'plot_section': False
}

fiber_configs = [fiber_config_1]
# ==================================================
# STEP 6: DEFINE COLUMNS AND BEAMS
# ==================================================
element_configs = {
    'section': [
        {
            'type': 'Elastic',
            'secTag': 10,
            'E': 29000.0,
            'A': 17.9 / 144.0,
            'Iz': 800.0 / 1728.0,
            'Iy': 40.1 / 1728.0,
            'G': 11200.0,
            'J': 1.24 / 1728.0
        }
    ],
    'geomTransf': [
        {'type': 'PDelta', 'tag': 1, 'vecxz': [0, 1, 0]},
        {'type': 'Linear', 'tag': 2, 'vecxz': [0, 0, 1]}
    ],
    'element': [
        # Force beam columns (fiber sections)
        {
            'type': 'forceBeamColumn',
            'eleTag': 1,
            'eleNodes': [1, 11],
            'transfTag': 1,
            'integrationTag': 1
        },
        {
            'type': 'forceBeamColumn',
            'eleTag': 2,
            'eleNodes': [2, 12],
            'transfTag': 1,
            'integrationTag': 1
        },
        {
            'type': 'forceBeamColumn',
            'eleTag': 3,
            'eleNodes': [3, 13],
            'transfTag': 1,
            'integrationTag': 1
        },
        {
            'type': 'forceBeamColumn',
            'eleTag': 4,
            'eleNodes': [4, 14],
            'transfTag': 1,
            'integrationTag': 1
        },
        # Elastic beam columns
        {
            'type': 'elasticBeamColumn',
            'eleTag': 11,
            'eleNodes': [11, 12],
            'transfTag': 2,
            'Area': 17.9 / 144.0,
            'E': 29000.0,
            'G': 11200.0,
            'J': 1.24 / 1728.0,
            'Iy': 40.1 / 1728.0,
            'Iz': 800.0 / 1728.0
        },
        {
            'type': 'elasticBeamColumn',
            'eleTag': 12,
            'eleNodes': [12, 13],
            'transfTag': 2,
            'Area': 17.9 / 144.0,
            'E': 29000.0,
            'G': 11200.0,
            'J': 1.24 / 1728.0,
            'Iy': 40.1 / 1728.0,
            'Iz': 800.0 / 1728.0
        },
        {
            'type': 'elasticBeamColumn',
            'eleTag': 13,
            'eleNodes': [13, 14],
            'transfTag': 2,
            'Area': 17.9 / 144.0,
            'E': 29000.0,
            'G': 11200.0,
            'J': 1.24 / 1728.0,
            'Iy': 40.1 / 1728.0,
            'Iz': 800.0 / 1728.0
        },
        {
            'type': 'elasticBeamColumn',
            'eleTag': 14,
            'eleNodes': [14, 11],
            'transfTag': 2,
            'Area': 17.9 / 144.0,
            'E': 29000.0,
            'G': 11200.0,
            'J': 1.24 / 1728.0,
            'Iy': 40.1 / 1728.0,
            'Iz': 800.0 / 1728.0
        }
    ],
    'beamIntegration': [
        {'type': 'Lobatto', 'tag': 1, 'secTag': 1, 'N': 5}
    ]
}

# =========================================
# STEP 7: DEFINE SLAB - USE ONLY FILENAMES
# =========================================
slab_boundary_nodes = {
    11: (0.0, 0.0, 12.0),
    12: (20.0, 0.0, 12.0),
    13: (20.0, 20.0, 12.0),
    14: (0.0, 20.0, 12.0)
}

slab_configs = [
    {
        'name': 'Floor_Slab',
        'boundary_nodes': slab_boundary_nodes,
        'mesh_size': 10.0,
        'internal_points': None,
        'voids': None,
        'py_file': 'floor_slab_mesh.py',  # JUST FILENAME
        'png_file': 'floor_slab_mesh.png',  # JUST FILENAME
        'shell_material_config': ('ElasticIsotropic', 100, 3600.0, 0.2, 0.0868),
        'shell_section_config': ('PlateFiber', 100, 'ShellMITC4', 0.6666666666666666),
        'node_font_size': 8,
        'element_font_size': 6,
        'ops_ele_type1': 'ShellMITC4',
        'ops_ele_type2': 'ShellNLDKGT',
        'shell_boundary_conditions': None,
        'spring_configs': None,
        'load_configs': {
            'time_series': [{'tag': 1, 'type': 'Linear'}],
            'patterns': [{'tag': 1, 'ts_tag': 1}],
            'shell_surface_loads': [{
                'pattern': 1,
                'loads': [{
                    'pressure': -0.050,
                    'elements': None
                }]
            }],
            'nodal_loads': [{
                'pattern': 1,
                'loads': [
                    {'node': 11, 'forces': (0, 0, -2.0, 0, 0, 0)},
                    {'node': 13, 'forces': (0, 0, -2.0, 0, 0, 0)}
                ]
            }]
        },
        'mass_configs': {
            'shell_element_mass': [{
                'mass_per_area': 0.030,
                'elements': None,
                'description': 'SDL'
            }],
            'nodal_mass': [
                {'node': 12, 'mass': 0.5},
                {'node': 14, 'mass': 0.5}
            ]
        },
        'start_node_id': 100000,
        'start_element_id': 100000
    }
]
# =========================================
# STEP 8: BOUNDARY CONDITIONS
# =========================================
boundary_conditions = {
    1: (1, 1, 1, 1, 1, 1),
    2: (1, 1, 1, 1, 1, 1),
    3: (1, 1, 1, 1, 1, 1),
    4: (1, 1, 1, 1, 1, 1)
}
# =========================================
# STEP 9: NODAL SPRINGS
# =========================================
nodal_spring_configs = [
    {
        "node1": (1, 0.0, 0.0, 0.0),
        "spring_id": 5001,
        "direction": 3,
        "material": ("Elastic", 6001, 10000.0),
        "boundary_condition": (1, 1, 1, 1, 1, 1)
    },
    {
        "node1": (2, bay_x, 0.0, 0.0),
        "spring_id": 5002,
        "direction": 3,
        "material": ("Elastic", 6002, 10000.0),
        "boundary_condition": (1, 1, 1, 1, 1, 1)
    },
    {
        "node1": (3, bay_x, bay_y, 0.0),
        "spring_id": 5003,
        "direction": 3,
        "material": ("Elastic", 6003, 10000.0),
        "boundary_condition": (1, 1, 1, 1, 1, 1)
    },
    {
        "node1": (4, 0.0, bay_y, 0.0),
        "spring_id": 5004,
        "direction": 3,
        "material": ("Elastic", 6004, 10000.0),
        "boundary_condition": (1, 1, 1, 1, 1, 1)
    }
]
# =========================================
# STEP 10: RIGID DIAPHRAGM
# =========================================
diaphragm_list = [
    (3, 11, 12, 13, 14)
]
# =========================================================
# STEP 11: LOADS AND MASSES FOR BEAMS AND COLUMNS
# NOTE: Use DIFFERENT tags than slab 
# =========================================================
load_configs = {
    'time_series': [],  # EMPTY - slab already creates timeSeries 1
    'patterns': [],     # EMPTY - slab already creates pattern 1
    
    'beam_uniform_loads': [{
        'pattern': 1,  # Use existing pattern 1 from slab
        'loads': [
            {'elements': [11, 12, 13, 14], 'wy': 0.0, 'wz': -0.5}
        ]
    }],
    
    'nodal_loads': [{
        'pattern': 1,  # Use existing pattern 1 from slab
        'loads': [
            {'node': 11, 'forces': (0, 0, -5.0, 0, 0, 0)},
            {'node': 12, 'forces': (0, 0, -5.0, 0, 0, 0)},
            {'node': 13, 'forces': (0, 0, -5.0, 0, 0, 0)},
            {'node': 14, 'forces': (0, 0, -5.0, 0, 0, 0)}
        ]
    }]
}
mass_configs = {
    'beam_column_mass': [
        {'tag': 1, 'density': 0.0868, 'area': 2.25},
        {'tag': 2, 'density': 0.0868, 'area': 2.25},
        {'tag': 3, 'density': 0.0868, 'area': 2.25},
        {'tag': 4, 'density': 0.0868, 'area': 2.25}
    ],
    'beam_additional_mass': [{
        'element_tags': [11, 12, 13, 14],
        'mass_per_length': 0.050,
        'description': 'Steel beam self-weight'
    }],
    'nodal_mass': [
        {'node': 11, 'mass': 1.0},
        {'node': 12, 'mass': 1.0},
        {'node': 13, 'mass': 1.0},
        {'node': 14, 'mass': 1.0}
    ]
}
# =================================================
# STEP 12: BUILD MODEL
# =================================================
if __name__ == "__main__":
    
    
    # Call build_model
    results = build_model(
        model_params=model_params,
        fiber_configs=fiber_configs,
        material_params=material_params,
        node_coords=node_coords,
        boundary_conditions=boundary_conditions,
        element_configs=element_configs,
        nodal_spring_configs=nodal_spring_configs,
        diaphragm_list=diaphragm_list,
        load_configs=load_configs,
        mass_configs=mass_configs,
        visualize=True,
        output_dir=output_dir,
        slab_configs=slab_configs
    )

    print(results['all_file_paths'])
    


'''
    }
    


    
    return examples
