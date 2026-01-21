# ===========================================================================================
# SIMPLE FOOTING SLAB WITH ZERO-LENGTH SPRINGS
# ===========================================================================================
import numpy as np
import opstool as opst
from test3 import build_model, create_regular_polygon_nodes

# ===========================================================================================
# MATERIAL DEFINITIONS
# ===========================================================================================
footing_materials = {
    'concrete_cover': {
        'elastic_modulus': 3600.0,
        'poissons_ratio': 0.2,
        'density': 0.150,
        'yield_strength': 4.0,
        'color': '#dbb40c'
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
# MATERIAL PARAMETERS
# ===========================================================================================
material_params_footing = [
    # Spring material (ENT - Elastic No Tension for soil)
    ['ENT', 1001, 5000.0],  # Soil spring stiffness = 5000 kip/ft
]

# ===========================================================================================
# NODE COORDINATES (Empty - nodes will be created by mesh)
# ===========================================================================================
node_coords_footing = {}

# ===========================================================================================
# BOUNDARY CONDITIONS (Empty - will be applied through zero-length springs)
# ===========================================================================================
boundary_conditions_footing = {}

# ===========================================================================================
# ELEMENT CONFIGURATIONS (Empty - no beam/column elements)
# ===========================================================================================
element_configs_footing = {
    'transformations': [],
    'integrations': [],
    'force_beam_columns': [],
    'elastic_beam_columns': []
}

# ===========================================================================================
# FOOTING SLAB CONFIGURATION
# Rectangular footing: 20 ft × 15 ft × 2 ft thick
# At Z = 0 elevation
# Coarse mesh size = 2.5 ft
# ===========================================================================================
footing_config = {
    'name': 'Simple_Footing',
    'type': 'footing',
    'boundary_nodes': {
        1: (-10.0, -7.5, 0.0),
        2: (10.0, -7.5, 0.0),
        3: (10.0, 7.5, 0.0),
        4: (-10.0, 7.5, 0.0)
    },
    'mesh_size': 2.5,  # Coarse mesh
    'internal_points': None,
    'voids': None,
    'py_file': 'simple_footing.py',
    'png_file': 'simple_footing.png',
    
    # Shell material: Elastic Isotropic
    # E = 3600 ksi, nu = 0.2, rho = 0.150 kcf
    'shell_material_config': ("ElasticIsotropic", 501, 3600.0 * 144.0, 0.2, 0.150 * 1000.0),
    
    # Shell section: Plate Fiber
    # Thickness = 2.0 ft = 24 inches
    'shell_section_config': ("PlateFiber", 501, 501, 2.0),
    
    'node_font_size': 10,
    'element_font_size': 8,
    'ops_ele_type1': "ShellMITC4",
    'ops_ele_type2': "ASDShellT3",
    
    # Shell nodes will have zero-length springs attached
    'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],  # Free initially
    
    # Enable zero-length springs for soil support
    'use_zero_length': True,
    'zero_length_material_config': ['ENT', 1001, 5000.0],  # Soil spring
    'zero_length_directions': [3],  # Vertical direction only (Z)
    'zero_length_boundary_conditions': [1, 1, 1, 1, 1, 1],  # Fixed spring nodes
    
    'element_start_id': 10000,
    'spring_node_start_id': 1000000,
    'start_node_id': 100000,
    'start_element_id': 110000,
    
    'load_configs': None  # Will define separately
}

# ===========================================================================================
# LOAD CONFIGURATIONS
# ===========================================================================================
# Point loads at three locations on the footing
# Point 1: (-5, 0, 0) - 100 kips downward
# Point 2: (0, 0, 0) - 150 kips downward (center)
# Point 3: (5, 0, 0) - 100 kips downward

# Downward soil pressure: 10 psf = 10/144 ksi on footing bottom (negative = downward)
# Self-weight of footing: 2 ft thick × 0.150 kcf = 0.3 ksf downward

load_configs_footing = {
    'time_series': [
        {'tag': 1, 'type': 'Linear'},
        {'tag': 2, 'type': 'Linear'},
        {'tag': 3, 'type': 'Linear'}
    ],
    'patterns': [
        {'tag': 1, 'type': 'Plain', 'ts_tag': 1},
        {'tag': 2, 'type': 'Plain', 'ts_tag': 2},
        {'tag': 3, 'type': 'Plain', 'ts_tag': 3}
    ],
    'nodal_loads': [
        {
            'pattern_tag': 1,
            'loads': [
                # Point loads will be applied to nearest nodes after mesh generation
                # We'll identify these nodes manually after checking mesh output
                # For now, we'll use approximate node IDs
                # Assuming coarse mesh creates nodes near these coordinates
                
                # Point load 1: at (-5, 0, 0) - 100 kips downward
                {'node': 100001, 'forces': [0, 0, -100.0, 0, 0, 0]},
                
                # Point load 2: at (0, 0, 0) center - 150 kips downward
                {'node': 100002, 'forces': [0, 0, -150.0, 0, 0, 0]},
                
                # Point load 3: at (5, 0, 0) - 100 kips downward
                {'node': 100003, 'forces': [0, 0, -100.0, 0, 0, 0]},
            ]
        }
    ],
    'shell_surface_loads': [
        {
            'pattern_tag': 2,
            'loads': [
                {
                    'mesh_name': 'Simple_Footing',
                    'pressure': -10.0 / 144.0,  # Downward soil bearing pressure (negative = downward)
                    'elements': None  # Apply to all elements
                }
            ]
        },
        {
            'pattern_tag': 3,
            'loads': [
                {
                    'mesh_name': 'Simple_Footing',
                    'pressure': -0.3 / 144.0,  # Self-weight downward (negative = downward)
                    'elements': None  # Apply to all elements
                }
            ]
        }
    ]
}

# ===========================================================================================
# MASS CONFIGURATIONS
# ===========================================================================================
mass_configs_footing = {
    'shell_mass': {
        'calculate': True,
        'exclude': [],
        'scale': 1.0  # Full self-weight mass (for dynamic analysis)
    }
}

# ===========================================================================================
# BUILD MODEL
# ===========================================================================================
print("\n" + "="*80)
print("BUILDING SIMPLE FOOTING MODEL")
print("="*80)
print("\nFooting Dimensions: 20 ft × 15 ft × 2 ft thick")
print("Mesh Size: 2.5 ft (coarse)")
print("Soil Spring Stiffness: 5000 kip/ft")
print("\nLoads:")
print("  - Point Load 1: 100 kips DOWNWARD at (-5, 0, 0)")
print("  - Point Load 2: 150 kips DOWNWARD at (0, 0, 0)")
print("  - Point Load 3: 100 kips DOWNWARD at (5, 0, 0)")
print("  - Soil Bearing Pressure: 10 psf DOWNWARD")
print("  - Self-weight: 0.3 ksf DOWNWARD")
print("  - Total Downward Load: ~420 kips")
print("  - Support: Zero-length springs (5000 kip/ft) at all nodes")
print("="*80)

results = build_model(
    model_params={'ndm': 3, 'ndf': 6},
    materials_list=[],  # No fiber sections
    outline_points_list=[],
    rebar_configs_list=[],
    section_params_list=[],
    material_params=material_params_footing,
    node_coords=node_coords_footing,
    boundary_conditions=boundary_conditions_footing,
    element_configs=element_configs_footing,
    spring_configs=None,
    nodal_spring_configs=None,
    diaphragm_list=None,
    load_configs=load_configs_footing,
    mass_configs=mass_configs_footing,
    visualize=True,
    output_dir="output_footing",
    slab_configs=[footing_config],
    existing_frame_nodes=None
)

print("\n" + "="*80)
print("SIMPLE FOOTING MODEL COMPLETE")
print("="*80)
print("\nNext Steps:")
print("1. Check 'output_footing/simple_footing.png' for node numbering")
print("2. Update node IDs in load_configs_footing for accurate point loads")
print("3. Re-run the model with correct node IDs")
print("\nNote: The model is ready to run. Point load nodes may need adjustment")
print("      based on actual mesh node locations.")
print("="*80)

# ===========================================================================================
# ADDITIONAL NOTES
# ===========================================================================================
"""
EXPLANATION OF MODEL COMPONENTS:

1. FOOTING SLAB (20 ft × 15 ft × 2 ft):
   - Shell elements with coarse mesh (2.5 ft)
   - Material: Concrete E=3600 ksi, nu=0.2, rho=0.150 kcf
   - Thickness: 2 ft (24 inches)

2. ZERO-LENGTH SPRINGS:
   - Attached to every shell node in vertical (Z) direction
   - Stiffness: 5000 kip/ft (ENT material - Elastic No Tension)
   - Simulates soil support
   - Spring nodes fixed [1,1,1,1,1,1]

3. LOADS:
   a) Point Loads (Pattern 1):
      - Three concentrated loads at different locations
      - Total: 350 kips downward
   
   b) Soil Pressure (Pattern 2):
      - Upward pressure: 10 psf on bottom surface
      - Applied using shell_surface_loads
   
   c) Self-Weight:
      - Applied as additional mass load
      - 2 ft × 0.150 kcf = 0.3 ksf

4. MASSES:
   - Shell self-weight mass calculated from density
   - Additional mass for self-weight included
   - Important for dynamic analysis

5. BOUNDARY CONDITIONS:
   - Shell nodes are free initially [0,0,0,0,0,0]
   - Support provided through zero-length springs
   - Spring base nodes fixed [1,1,1,1,1,1]

OUTPUT FILES:
- output_footing/simple_footing.py - Mesh generation commands
- output_footing/simple_footing.png - Mesh visualization with node numbers
- output_footing/complete_model.html - 3D interactive model
- output_footing/final_complete_model.py - Complete OpenSees script

TO REFINE POINT LOADS:
1. Open simple_footing.png
2. Identify node numbers closest to:
   - (-5, 0, 0)
   - (0, 0, 0)
   - (5, 0, 0)
3. Update load_configs_footing['nodal_loads'][0]['loads']
4. Re-run the script
"""
