

"1st part code"

"""
Minimal Dynamic GMSH Mesh Generator with Void Support
Simple and straightforward implementation
"""

import gmsh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection



import os
from math import sqrt
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Union

import numpy as np
import pandas as pd
import xarray as xr
import imageio.v2 as imageio
import matplotlib.pyplot as plt
import pickle

import openseespy.opensees as ops
import opstool as opst
import opstool.vis.pyvista as opsvis
import opstool.vis.plotly as opsvis_plotly

import gmsh



import opstool as opst




def generate_mesh(boundary_nodes, mesh_size, internal_points=None, voids=None,
                  py_file="model.py", png_file="mesh.png",
                  material_E=2e11, material_nu=0.3, material_rho=7850,
                  thickness=0.01, node_font_size=7, element_font_size=6, 
                  start_node_id=20000, start_element_id=20000):
    """
    Generate mesh - NO DUPLICATE NODES
    Internal points (100, 101) keep their original IDs
    """
    
    # Step 1: Create GMSH geometry
    gmsh.initialize()
    gmsh.model.add("mesh")
    
    # Sort boundary nodes by angle
    coords = np.array([boundary_nodes[nid] for nid in sorted(boundary_nodes.keys())])
    center = coords.mean(axis=0)
    angles = np.arctan2(coords[:, 1] - center[1], coords[:, 0] - center[0])
    sorted_indices = np.argsort(angles)
    sorted_ids = [sorted(boundary_nodes.keys())[i] for i in sorted_indices]
    
    # Create boundary points and lines
    point_map = {}
    for node_id in sorted_ids:
        x, y, z = boundary_nodes[node_id]
        pt = gmsh.model.geo.addPoint(x, y, z, mesh_size)
        point_map[node_id] = pt
    
    boundary_lines = []
    for i in range(len(sorted_ids)):
        start = sorted_ids[i]
        end = sorted_ids[(i + 1) % len(sorted_ids)]
        line = gmsh.model.geo.addLine(point_map[start], point_map[end])
        boundary_lines.append(line)
    
    outer_loop = gmsh.model.geo.addCurveLoop(boundary_lines)
    
    # Process voids
    void_loops = []
    if voids:
        print(f"\nProcessing {len(voids)} voids:")
        for void_idx, void_nodes in enumerate(voids):
            void_coords = np.array([void_nodes[nid] for nid in sorted(void_nodes.keys())])
            void_center = void_coords.mean(axis=0)
            void_angles = np.arctan2(void_coords[:, 1] - void_center[1], 
                                     void_coords[:, 0] - void_center[0])
            void_sorted_indices = np.argsort(void_angles)
            void_sorted_ids = [sorted(void_nodes.keys())[i] for i in void_sorted_indices]
            
            void_point_map = {}
            for node_id in void_sorted_ids:
                x, y, z = void_nodes[node_id]
                pt = gmsh.model.geo.addPoint(x, y, z, mesh_size)
                void_point_map[node_id] = pt
            
            void_lines = []
            for i in range(len(void_sorted_ids)):
                start = void_sorted_ids[i]
                end = void_sorted_ids[(i + 1) % len(void_sorted_ids)]
                line = gmsh.model.geo.addLine(void_point_map[start], void_point_map[end])
                void_lines.append(line)
            
            void_loop = gmsh.model.geo.addCurveLoop(void_lines)
            void_loops.append(void_loop)
    
    all_loops = [outer_loop] + void_loops
    surface = gmsh.model.geo.addPlaneSurface(all_loops)
    
    gmsh.model.geo.synchronize()
    
    # Embed internal points
    if internal_points:
        print(f"\nEmbedding {len(internal_points)} internal points:")
        for node_id, coord in internal_points.items():
            x, y, z = coord
            pt = gmsh.model.geo.addPoint(x, y, z, mesh_size)
            gmsh.model.geo.synchronize()
            try:
                gmsh.model.mesh.embed(0, [pt], 2, surface)
                print(f"   Embedded point {node_id}")
            except Exception as e:
                print(f"  ✗ Failed: {node_id}")
    
    # Generate mesh
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.RecombineAll", 1)
    gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size * 2)
    
    try:
        print(f"\nMeshing with Frontal-Delaunay...")
        gmsh.model.mesh.generate(2)
        print("   Success!")
    except:
        gmsh.model.mesh.clear()
        gmsh.option.setNumber("Mesh.Algorithm", 5)
        gmsh.option.setNumber("Mesh.RecombineAll", 0)
        gmsh.model.mesh.generate(2)
        print("   Success with Delaunay!")
    
    # Extract mesh (NO sequential remapping)
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    temp_nodes = {}
    for i, tag in enumerate(node_tags):
        temp_nodes[int(tag)] = (node_coords[3*i], node_coords[3*i+1], node_coords[3*i+2])

    # Get elements
    quad4_elems = []
    tri3_elems = []

    for elem_type in gmsh.model.mesh.getElementTypes(dim=2):
        elem_tags, elem_nodes = gmsh.model.mesh.getElementsByType(elem_type)
        
        if elem_type == 3:  # Quad4
            for i, tag in enumerate(elem_tags):
                nodes = [int(elem_nodes[i*4 + j]) for j in range(4)]
                quad4_elems.append({'tag': int(tag), 'nodes': nodes})
        elif elem_type == 2:  # Tri3
            for i, tag in enumerate(elem_tags):
                nodes = [int(elem_nodes[i*3 + j]) for j in range(3)]
                tri3_elems.append({'tag': int(tag), 'nodes': nodes})
    
    gmsh.finalize()
    
    # NODE MAPPING - PRESERVE SPECIAL IDs
    tolerance = mesh_size * 0.01
    node_map = {}
    final_nodes = {}
    used_ids = set()
    
    # Match boundary nodes
    for bnd_id, bnd_coord in boundary_nodes.items():
        best = None
        best_dist = float('inf')
        for gid, gcoord in temp_nodes.items():
            if gid in node_map:
                continue
            dist = np.linalg.norm(np.array(gcoord) - np.array(bnd_coord))
            if dist < tolerance and dist < best_dist:
                best = gid
                best_dist = dist
        if best:
            node_map[best] = bnd_id
            final_nodes[bnd_id] = bnd_coord
            used_ids.add(bnd_id)
    
    # Match void nodes
    if voids:
        for void_nodes in voids:
            for void_id, void_coord in void_nodes.items():
                best = None
                best_dist = float('inf')
                for gid, gcoord in temp_nodes.items():
                    if gid in node_map:
                        continue
                    dist = np.linalg.norm(np.array(gcoord) - np.array(void_coord))
                    if dist < tolerance and dist < best_dist:
                        best = gid
                        best_dist = dist
                if best:
                    node_map[best] = void_id
                    final_nodes[void_id] = void_coord
                    used_ids.add(void_id)
    
    # Match internal points - KEEP ORIGINAL IDs
    matched_internal = {}
    if internal_points:
        print(f"\nMatching internal points:")
        for int_id, int_coord in internal_points.items():
            best = None
            best_dist = float('inf')
            for gid, gcoord in temp_nodes.items():
                if gid in node_map:
                    continue
                dist = np.linalg.norm(np.array(gcoord) - np.array(int_coord))
                if dist < tolerance and dist < best_dist:
                    best = gid
                    best_dist = dist
            
            if best:
                node_map[best] = int_id  # USE ORIGINAL ID
                final_nodes[int_id] = int_coord
                used_ids.add(int_id)
                matched_internal[int_id] = int_id
                print(f"   {int_id} ← GMSH {best}")
    
    # Sequential numbering for remaining
    remaining = sorted([g for g in temp_nodes.keys() if g not in node_map])
    next_id = start_node_id
    for gid in remaining:
        while next_id in used_ids:
            next_id += 1
        node_map[gid] = next_id
        final_nodes[next_id] = temp_nodes[gid]
        used_ids.add(next_id)
        next_id += 1
    
    # Remap elements
    elem_id = start_element_id
    final_quad4 = []
    final_tri3 = []
    
    for elem in quad4_elems:
        nodes = [node_map[n] for n in elem['nodes']]
        final_quad4.append({'tag': elem_id, 'nodes': nodes})
        elem_id += 1
    
    for elem in tri3_elems:
        nodes = [node_map[n] for n in elem['nodes']]
        final_tri3.append({'tag': elem_id, 'nodes': nodes})
        elem_id += 1
    
    quad4_elems = final_quad4
    tri3_elems = final_tri3
    
    # Verify no duplicates
    print("\nVerification:")
    coord_map = {}
    for nid, coord in final_nodes.items():
        rc = tuple(round(c, 8) for c in coord)
        if rc not in coord_map:
            coord_map[rc] = []
        coord_map[rc].append(nid)
    
    dups = {c: ids for c, ids in coord_map.items() if len(ids) > 1}
    if dups:
        print(f"  ✗ {len(dups)} duplicates!")
    else:
        print(f"   No duplicates - {len(final_nodes)} unique nodes")
    
    # Visualization
    fig, ax = plt.subplots(figsize=(14, 12))
    
    for elem in quad4_elems:
        coords = np.array([final_nodes[n][:2] for n in elem['nodes']])
        ax.fill(coords[:, 0], coords[:, 1], fc='cyan', ec='blue', alpha=0.3, lw=1)
    for elem in tri3_elems:
        coords = np.array([final_nodes[n][:2] for n in elem['nodes']])
        ax.fill(coords[:, 0], coords[:, 1], fc='yellow', ec='orange', alpha=0.3, lw=1)
    
    bnd_ids = set(boundary_nodes.keys())
    void_ids = set()
    if voids:
        for v in voids:
            void_ids.update(v.keys())
    int_ids = set(matched_internal.keys())
    reg_ids = set(final_nodes.keys()) - bnd_ids - void_ids - int_ids
    
    if reg_ids:
        coords = np.array([final_nodes[n][:2] for n in reg_ids])
        ax.scatter(coords[:, 0], coords[:, 1], c='black', s=30, zorder=5)
    
    coords = np.array([boundary_nodes[n][:2] for n in boundary_nodes])
    ax.scatter(coords[:, 0], coords[:, 1], c='red', s=150, marker='s', 
               ec='black', lw=2, label='Boundary', zorder=6)
    
    if voids:
        for void_nodes in voids:
            coords = np.array([void_nodes[n][:2] for n in void_nodes])
            ax.scatter(coords[:, 0], coords[:, 1], c='purple', s=120, marker='o',
                       ec='black', lw=2, zorder=6)
    
    if int_ids:
        coords = np.array([final_nodes[n][:2] for n in int_ids])
        ax.scatter(coords[:, 0], coords[:, 1], c='lime', s=300, marker='^',
                   ec='darkgreen', lw=3, label='Internal', zorder=8)
    
    # Annotate internal points
    if int_ids:
        for nid in int_ids:
            coord = final_nodes[nid]
            ax.annotate(str(nid), (coord[0], coord[1]), xytext=(0, 20),
                       textcoords='offset points', fontsize=node_font_size+3,
                       ha='center', color='darkgreen', weight='bold',
                       bbox=dict(boxstyle='round,pad=0.5', fc='lime', ec='darkgreen', lw=2.5),
                       arrowprops=dict(arrowstyle='->', lw=1.5, color='darkgreen'),
                       zorder=11)
    
    for nid in bnd_ids:
        if nid in final_nodes:
            coord = final_nodes[nid]
            ax.annotate(str(nid), (coord[0], coord[1]), xytext=(0, -15),
                       textcoords='offset points', fontsize=node_font_size,
                       ha='center', color='darkred', weight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', fc='lightcoral', ec='darkred'),
                       zorder=9)
    
    for nid in reg_ids:
        coord = final_nodes[nid]
        ax.annotate(str(nid), (coord[0], coord[1]), fontsize=node_font_size-1,
                   ha='center', color='darkblue',
                   bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.6),
                   zorder=7)
    
    title = f'{len(final_nodes)} nodes, {len(quad4_elems)} quad4, {len(tri3_elems)} tri3'
    if int_ids:
        title += f', {len(int_ids)} internal'
    ax.set_title(title, fontsize=14, weight='bold')
    ax.legend()
    ax.axis('equal')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_file, dpi=200)
    plt.close()
    
    print(f"\n Complete: {len(final_nodes)} nodes")
    if matched_internal:
        print(f"  Internal: {sorted(matched_internal.keys())}")
    
    return {
        'nodes': final_nodes,
        'quad4': quad4_elems,
        'tri3': tri3_elems,
        'voids': voids if voids else [],
        'internal_points': matched_internal
    }



# def zero_element_boundary_condition(material_props, sections, node_list, boundary_condition, 
#                                     element_start_id, spring_node_start_id):
#     """
#     Create zero-length elements at specified nodes for boundary condition modeling
#     """
#     import openseespy.opensees as ops
    
#     node_mapping = {}
#     element_ids = []
#     current_elem_id = element_start_id
#     current_spring_node_id = spring_node_start_id
    
#     ops.uniaxialMaterial(*material_props['config'])
    
#     for node_id, x, y, z in node_list:
#         spring_node_id = current_spring_node_id
        
#         ops.node(spring_node_id, x, y, z)
#         ops.fix(spring_node_id, *boundary_condition)
        
#         ops.element("zeroLength", current_elem_id, 
#                    node_id, spring_node_id, 
#                    "-mat", material_props['id'], 
#                    "-dir", *material_props['directions'])
        
#         node_mapping[node_id] = {
#             'spring_node': spring_node_id,
#             'element_id': current_elem_id,
#             'main_coords': (x, y, z),
#             'spring_coords': (x, y, z)
#         }
        
#         element_ids.append(current_elem_id)
#         current_elem_id += 1
#         current_spring_node_id += 1
    
#     return {
#         'node_mapping': node_mapping,
#         'element_ids': element_ids,
#         'spring_node_ids': list(range(spring_node_start_id, current_spring_node_id)),
#         'total_elements': len(element_ids)
#     }


def zero_element_boundary_condition(material_props, sections, node_list, 
                                    boundary_condition, 
                                    element_start_id, spring_node_start_id):
    """
    Create zero-length elements at specified nodes for boundary condition modeling
    """
    import openseespy.opensees as ops
    
    node_mapping = {}
    element_ids = []
    current_elem_id = element_start_id
    current_spring_node_id = spring_node_start_id
    
    # Try to create material (skip if already exists)
    try:
        ops.uniaxialMaterial(*material_props['config'])
    except:
        pass  # Material already exists, skip
    
    for node_id, x, y, z in node_list:
        spring_node_id = current_spring_node_id
        
        ops.node(spring_node_id, x, y, z)
        ops.fix(spring_node_id, *boundary_condition)
        
        ops.element("zeroLength", current_elem_id, 
                   node_id, spring_node_id, 
                   "-mat", material_props['id'], 
                   "-dir", *material_props['directions'])
        
        node_mapping[node_id] = {
            'spring_node': spring_node_id,
            'element_id': current_elem_id,
            'main_coords': (x, y, z),
            'spring_coords': (x, y, z)
        }
        
        element_ids.append(current_elem_id)
        current_elem_id += 1
        current_spring_node_id += 1
    
    return {
        'node_mapping': node_mapping,
        'element_ids': element_ids,
        'spring_node_ids': list(range(spring_node_start_id, current_spring_node_id)),
        'total_elements': len(element_ids)
    }


def create_slab(boundary_nodes, mesh_size, internal_points=None,existing_frame_nodes= None, voids=None,
                py_file="slab_model.py", png_file="slab_mesh.png",
                shell_material_config=("ElasticIsotropic", 1, 2e11, 0.3, 7850),
                shell_section_config=("PlateFiber", 1, 1, 0.01),
                node_font_size=14, element_font_size=14,
                ops_ele_type1="ShellMITC4", ops_ele_type2="ASDShellT3",
                shell_boundary_conditions=[1, 1, 1, 1, 1, 1],
                
                assign_to_ops=False,
                use_zero_length=False,
                zero_length_material_config=None,
                zero_length_directions=[3],
                zero_length_boundary_conditions=[1, 1, 1, 1, 1, 1],
                element_start_id=10000,
                spring_node_start_id=1000000,
                load_configs=None, 
                start_node_id = 20000, 
                start_element_id=20000):
    """
    Create slab with mesh generation and OpenSeesPy assignment.
    Supports voids (holes) in the mesh.
    """
    
    # Extract shell material and section info
    material_E = shell_material_config[2] if len(shell_material_config) > 2 else 2e11
    material_nu = shell_material_config[3] if len(shell_material_config) > 3 else 0.3
    material_rho = shell_material_config[4] if len(shell_material_config) > 4 else 7850
    thickness = shell_section_config[3] if len(shell_section_config) > 3 else 0.01
    
    mesh = generate_mesh(
        boundary_nodes=boundary_nodes,
        mesh_size=mesh_size,
        internal_points=internal_points,
        # existing_nodes=existing_frame_nodes,  # ✅ PASS THIS

        voids=voids,  
        py_file=py_file,
        png_file=png_file,
        material_E=material_E,
        material_nu=material_nu,
        material_rho=material_rho,
        thickness=thickness,
        node_font_size=node_font_size,
        element_font_size=element_font_size,
        start_node_id=start_node_id,  # ADD
        start_element_id=start_element_id  # ADD
    )
    
    if assign_to_ops:
        import openseespy.opensees as ops
        
        # ops.wipe()
        ops.model("basic", "-ndm", 3, "-ndf", 6)
        
        # Apply shell material and section
        ops.nDMaterial(*shell_material_config)
        ops.section(*shell_section_config)
        
        # Create ALL nodes first
        for nid, coord in mesh['nodes'].items():
            ops.node(nid, coord[0], coord[1], coord[2])
        
        # Create shell elements
        section_tag = shell_section_config[1]
        for elem in mesh['quad4']:
            ops.element(ops_ele_type1, elem['tag'], *elem['nodes'], section_tag)
        
        for elem in mesh['tri3']:
            ops.element(ops_ele_type2, elem['tag'], *elem['nodes'], section_tag)

        # Apply surface loads if requested
        # if load_configs is not None and 'pressure' in load_configs:
        #     apply_surface_load(mesh=mesh, load_configs=load_configs)

        # Apply boundary conditions
        if use_zero_length and zero_length_material_config:
            # Zero-length boundary conditions
            zero_mat_tag = zero_length_material_config[1]
            zero_length_material = {
                'id': zero_mat_tag,
                'directions': zero_length_directions,
                'config': zero_length_material_config
            }
            
            node_list = [(nid, float(mesh['nodes'][nid][0]), 
                               float(mesh['nodes'][nid][1]), 
                               float(mesh['nodes'][nid][2])) 
                               for nid in mesh['nodes'].keys()]
            
            zero_result = zero_element_boundary_condition(
                material_props=zero_length_material,
                sections={},
                node_list=node_list,
                boundary_condition=zero_length_boundary_conditions,
                element_start_id=element_start_id,
                spring_node_start_id=spring_node_start_id
            )
            mesh['zero_length'] = zero_result
        else:
            # Standard boundary conditions - apply only to outer boundary
            for nid in boundary_nodes.keys():
                if nid in mesh['nodes']:
                    ops.fix(nid, *shell_boundary_conditions)
    
    # Create final.py file
    if assign_to_ops:
        with open(py_file, 'w') as f:
            f.write("# OpenSeesPy Model Generated by GMSH Mesh Generator\n")
            f.write("import openseespy.opensees as ops\n\n")
            f.write("# Clear existing model\n")
            f.write("ops.wipe()\n")
            f.write("ops.model('basic', '-ndm', 3, '-ndf', 6)\n\n")
            
            # Write shell material
            mat_args = ", ".join([repr(arg) for arg in shell_material_config])
            f.write(f"# Shell material\n")
            f.write(f"ops.nDMaterial({mat_args})\n\n")
            
            # Write shell section
            sec_args = ", ".join([repr(arg) for arg in shell_section_config])
            f.write(f"# Shell section\n")
            f.write(f"ops.section({sec_args})\n\n")
            
            # Write nodes
            f.write(f"# Nodes ({len(mesh['nodes'])} total)\n")
            for nid, coord in mesh['nodes'].items():
                x, y, z = float(coord[0]), float(coord[1]), float(coord[2])
                f.write(f"ops.node({nid}, {x}, {y}, {z})\n")
            f.write("\n")
            
            # Write shell elements
            f.write(f"# Shell elements ({len(mesh['quad4']) + len(mesh['tri3'])} total)\n")
            for elem in mesh['quad4']:
                node_str = ", ".join([str(n) for n in elem['nodes']])
                f.write(f"ops.element('{ops_ele_type1}', {elem['tag']}, {node_str}, {shell_section_config[1]})\n")
            
            for elem in mesh['tri3']:
                node_str = ", ".join([str(n) for n in elem['nodes']])
                f.write(f"ops.element('{ops_ele_type2}', {elem['tag']}, {node_str}, {shell_section_config[1]})\n")
            
            f.write("\n")
            
            f.write("\n")
            
            # Write surface loads if applied (BEFORE boundary conditions)
            print(100*"-")
            print("load configs started")
            if load_configs is not None and 'pressure' in load_configs:
                print("load_configs1250000:")
                print(load_configs)
                f.write("# Surface loads\n")
                f.write("try:\n")
                f.write("    import opstool as opst\n")
                
                time_series_tag = load_configs['time_series_tag']
                pattern_tag = load_configs['pattern_tag']
                load_pressure = load_configs['pressure']
                element_tags = load_configs.get('element_tags')
                
                f.write(f"    ops.timeSeries('Linear', {time_series_tag})\n")
                f.write(f"    ops.pattern('Plain', {pattern_tag}, {time_series_tag})\n")
                
                if element_tags is None:
                    all_elem_tags = [elem['tag'] for elem in mesh['quad4']]
                    all_elem_tags += [elem['tag'] for elem in mesh['tri3']]
                    elem_str = str(all_elem_tags)
                else:
                    elem_str = str(element_tags)
                
                f.write(f"    opst.pre.transform_surface_uniform_load(ele_tags={elem_str}, p={load_pressure})\n")
                f.write(f"    print('Surface load applied: pressure={load_pressure}')\n")
                f.write("except ImportError:\n")
                f.write("    print('WARNING: opstool not installed. Surface loads not applied.')\n")
                f.write("    print('Install with: pip install opstool')\n\n")
            
            # Write boundary conditions
            # if not use_zero_length:

            
            # Write boundary conditions
            if not use_zero_length:
                f.write("# Standard boundary conditions (outer boundary only)\n")
                for nid in boundary_nodes.keys():
                    if nid in mesh['nodes']:
                        bc_str = ", ".join([str(bc) for bc in shell_boundary_conditions])
                        f.write(f"ops.fix({nid}, {bc_str})\n")
            else:
                if zero_length_material_config and 'zero_length' in mesh:
                    f.write("# Zero-length boundary conditions\n")
                    zl_mat_args = ", ".join([repr(arg) for arg in zero_length_material_config])
                    f.write(f"ops.uniaxialMaterial({zl_mat_args})\n\n")
                    
                    zero_data = mesh['zero_length']
                    f.write("# Spring nodes (fixed boundary)\n")
                    for node_info in zero_data['node_mapping'].values():
                        spring_node = node_info['spring_node']
                        x, y, z = node_info['spring_coords']
                        bc_str = ", ".join([str(bc) for bc in zero_length_boundary_conditions])
                        f.write(f"ops.node({spring_node}, {x}, {y}, {z})\n")
                        f.write(f"ops.fix({spring_node}, {bc_str})\n")
                    
                    f.write("\n# Zero-length elements\n")
                    for main_node_id, node_info in zero_data['node_mapping'].items():
                        spring_node_id = node_info['spring_node']
                        elem_id = node_info['element_id']
                        dir_str = ", ".join([str(d) for d in zero_length_directions])
                        f.write(f"ops.element('zeroLength', {elem_id}, "
                               f"{main_node_id}, {spring_node_id}, "
                               f"'-mat', {zero_length_material_config[1]}, "
                               f"'-dir', {dir_str})\n")
                    f.write("\n")
            
            f.write("\n# Model setup complete\n")
            void_info = f" with {len(voids)} voids" if voids else ""
            f.write(f"print('Model created successfully{void_info}: {{}} nodes and {{}} elements'.format(")
            f.write(f"{len(mesh['nodes'])}, {len(mesh['quad4']) + len(mesh['tri3'])}))\n")
        
        # print(f"Python model file created: {py_file}")
    
    return mesh





def create_dynamic_composite_section(
    materials: Dict[str, Dict[str, float]],
    outline_points: List[List[float]],
    core_material: str,
    mesh_sizes: Dict[str, float],
    ops_mat_tags: Dict[str, int],
    cover_thickness: Optional[float] = None,
    cover_material: Optional[str] = None,
    core_holes: Optional[List[List[List[float]]]] = None,
    voids: Optional[List[Dict]] = None,
    bone_geometry: Optional[Dict] = None,
    additional_patches: Optional[List[Dict]] = None,
    rebar_configs: Optional[List[Dict]] = None,
    steel_material: Optional[str] = None,
    sec_tag: Optional[int] = None,
    save_txt_path: Optional[str] = None,
    save_png_path: Optional[str] = None,
    save_pkl_path: Optional[str] = None,
    G: Optional[float] = None,
    section_name: str = "Section",
    display_results: bool = False,
    plot_section: bool = False
) -> opst.pre.section.FiberSecMesh:
    """
    Create dynamic composite section with multiple materials.
    All material properties must be specified by user - no defaults.
    """
    
    # Create materials - NO DEFAULTS, raise error if not provided
    mat_objects = {}
    for name, props in materials.items():
        if 'elastic_modulus' not in props:
            raise ValueError(f"Material '{name}': 'elastic_modulus' is required!")
        if 'poissons_ratio' not in props:
            raise ValueError(f"Material '{name}': 'poissons_ratio' is required!")
        if 'density' not in props:
            raise ValueError(f"Material '{name}': 'density' is required!")
        
        mat_objects[name] = opst.pre.section.create_material(
            name=name,
            elastic_modulus=props['elastic_modulus'],
            poissons_ratio=props['poissons_ratio'],
            density=props['density'],
            yield_strength=props.get('yield_strength', 1.0),
            color=props.get('color', 'gray')
        )
    
    # Process voids
    all_voids = []
    if voids:
        for v in voids:
            if v['type'] == 'polygon':
                all_voids.append(v['points'])
            elif v['type'] == 'circle':
                pts = opst.pre.section.create_circle_points(
                    v['xo'], v['radius'], 
                    v.get('angles', (0, 360)), 
                    v.get('n_sub', 40)
                )
                all_voids.append(pts)
    
    combined_holes = (core_holes or []) + all_voids
    
    # Create patches
    patches = {}
    
    if cover_thickness and cover_material:
        coverlines = opst.pre.section.offset(outline_points, d=cover_thickness)
        patches['cover'] = opst.pre.section.create_polygon_patch(
            outline_points, 
            holes=[coverlines], 
            material=mat_objects[cover_material]
        )
    else:
        coverlines = outline_points
    
    if not cover_thickness:
        patches['core'] = opst.pre.section.create_polygon_patch(
            outline_points, 
            holes=combined_holes or None, 
            material=mat_objects[core_material]
        )
    else:
        patches['core'] = opst.pre.section.create_polygon_patch(
            coverlines, 
            holes=combined_holes or None, 
            material=mat_objects[core_material]
        )
    
    if bone_geometry:
        patches['bone'] = opst.pre.section.create_polygon_patch(
            bone_geometry['points'], 
            holes=bone_geometry.get('holes'),
            material=mat_objects[bone_geometry['material']]
        )
    
    if additional_patches:
        for p in additional_patches:
            patches[p['name']] = opst.pre.section.create_polygon_patch(
                p['points'], 
                holes=p.get('holes'), 
                material=mat_objects[p['material']]
            )
    
    # Create section
    SEC = opst.pre.section.FiberSecMesh(sec_name=section_name)
    SEC.add_patch_group(patches)
    SEC.set_mesh_size(mesh_sizes)
    
    color_map = {}
    if 'cover' in patches:
        color_map['cover'] = materials.get(cover_material, {}).get('color', '#dbb40c')
    if 'core' in patches:
        color_map['core'] = materials.get(core_material, {}).get('color', '#88b378')
    if 'bone' in patches:
        color_map['bone'] = materials.get(bone_geometry['material'], {}).get('color', '#ffc168')
    for p in (additional_patches or []):
        color_map[p['name']] = materials.get(p['material'], {}).get('color', 'gray')
    SEC.set_mesh_color(color_map)
    
    # Set OpenSees material tags only for patches (not rebar)
    patch_mat_tags = {k: v for k, v in ops_mat_tags.items() if k in patches}
    SEC.set_ops_mat_tag(patch_mat_tags)
    SEC.mesh()
    
    # Add rebars
    if rebar_configs and steel_material:
        rebar_tag = ops_mat_tags.get('rebar')
        for i, cfg in enumerate(rebar_configs):
            t = cfg.get('type', 'line')
            if t == 'line':
                SEC.add_rebar_line(
                    cfg['points'], cfg['dia'], 
                    cfg.get('gap', 0.1), 
                    cfg.get('n'),
                    cfg.get('closure', False), 
                    rebar_tag, 
                    cfg.get('color', 'black'),
                    cfg.get('group_name', f'Rebar_{i+1}')
                )
            elif t == 'circle':
                SEC.add_rebar_circle(
                    cfg['xo'], cfg['radius'], cfg['dia'], 
                    cfg.get('gap', 0.1),
                    cfg.get('n'), 
                    cfg.get('angles', (0, 360)), 
                    rebar_tag,
                    cfg.get('color', 'black'), 
                    cfg.get('group_name', f'Rebar_{i+1}')
                )
            elif t == 'points':
                SEC.add_rebar_points(
                    cfg['points'], cfg['dia'], rebar_tag,
                    cfg.get('color', 'black'), 
                    cfg.get('group_name', f'Rebar_{i+1}')
                )
    
    SEC.centring()
    
    if display_results:
        SEC.get_frame_props(display_results=True)
    
    # Save files
    if save_txt_path and sec_tag is not None:
        if G is None:
            raise ValueError("G value must be provided!")
        GJ = G * SEC.get_j()  # ✅ Calculate GJ from G
        print("GJ calculated:", GJ)
        
        SEC.to_file(save_txt_path, secTag=sec_tag, GJ=GJ, fmt=":.6E")
        print(f"Commands saved to: {save_txt_path}")

        # NEW: Save section tag and GJ values to another file
        if save_txt_path.endswith('.py'):
            params_file = save_txt_path.replace('.py', '_params.txt')
        else:
            params_file = save_txt_path + '_params.txt'
            
        with open(params_file, 'w') as f:
            f.write(f"section_tag = {sec_tag}\n")
            f.write(f"GJ = {GJ:.6E}\n")
            f.write(f"section_name = '{section_name}'\n")
        print(f"Section parameters saved to: {params_file}")

    
    if save_png_path:
        fig, ax = plt.subplots(figsize=(8, 8))
        SEC.view(fill=True, show_legend=True, ax=ax)
        ax.set_aspect("equal", "box")
        plt.tight_layout()
        plt.savefig(save_png_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to: {save_png_path}")
        if not plot_section:
            plt.close(fig)
    
    if save_pkl_path:
        with open(save_pkl_path, 'wb') as f:
            pickle.dump(SEC, f)
        print(f"Section object saved to: {save_pkl_path}")
    
    if plot_section and not save_png_path:
        SEC.view(fill=True, show_legend=True)
        plt.show()
    
    
    return SEC, sec_tag, save_txt_path, save_png_path, save_pkl_path, params_file

def load_saved_section(
    txt_path: Optional[str] = None,
    png_path: Optional[str] = None,
    pkl_path: Optional[str] = None,
    display_commands: bool = False,
    display_image: bool = False,
    return_section_object: bool = True
) -> Tuple[Optional[str], Optional[plt.Figure], Optional[opst.pre.section.FiberSecMesh], Optional[int], Optional[float], Dict[str, str]]:
    """Load saved section files (.txt, .png, .pkl)."""
    
    commands, fig, section = None, None, None
    section_id = None
    GJ_value = None
    file_paths = {'txt': txt_path, 'png': png_path, 'pkl': pkl_path}
    
    if txt_path:
        if txt_path.endswith('.py'):
            params_file = txt_path.replace('.py', '_params.txt')
        else:
            params_file = txt_path + '_params.txt'
        
        try:
            with open(params_file, 'r') as f:
                for line in f:
                    if line.startswith('section_tag'):
                        section_id = int(line.split('=')[1].strip())
                    elif line.startswith('GJ'):
                        GJ_value = float(line.split('=')[1].strip())
        except:
            pass
    
    if txt_path:
        try:
            with open(txt_path, 'r') as f:
                commands = f.read()
            if display_commands:
                print(commands)
        except Exception as e:
            print(f"Error loading {txt_path}: {e}")
    
    if png_path and display_image:
        try:
            img = plt.imread(png_path)
            fig, ax = plt.subplots(figsize=(10, 10))
            ax.imshow(img)
            ax.axis('off')
            ax.set_title(f'Loaded from: {png_path}', fontsize=12)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"Error loading {png_path}: {e}")
    
    if pkl_path and return_section_object:
        try:
            with open(pkl_path, 'rb') as f:
                section = pickle.load(f)
        except Exception as e:
            print(f"Error loading {pkl_path}: {e}")
    
    return commands, fig, section, section_id, GJ_value, file_paths


def create_fiber_section(materials, outline_points, cover, rebar_configs, mesh_size, 
                         mat_tags, sec_tag, G, save_prefix, section_name):
    """Create and save fiber section"""
    SEC, sec_id, txt_path, png_path, pkl_path, params_path = create_dynamic_composite_section(
        materials=materials,
        outline_points=outline_points,
        cover_thickness=cover,
        cover_material='concrete_cover',
        core_material='concrete_core',
        mesh_sizes={'cover': mesh_size, 'core': mesh_size},
        ops_mat_tags=mat_tags,
        rebar_configs=rebar_configs,
        steel_material='steel_rebar',
        sec_tag=sec_tag,
        G=G,
        save_txt_path=f'{save_prefix}_commands.py',
        save_png_path=f'{save_prefix}_figure.png',
        save_pkl_path=f'{save_prefix}_object.pkl',
        section_name=section_name,
        display_results=False,
        plot_section=False
    )
    return sec_id, txt_path, png_path, pkl_path



def define_uniaxial_materials(material_params):
    """Define OpenSees uniaxial materials"""
    for param in material_params:
        ops.uniaxialMaterial(*param)


def create_nodes(node_coords):
    """Create nodes"""
    for node_id, coords in node_coords.items():
        ops.node(node_id, *coords)

def apply_boundary_conditions(boundary_conditions):
    """Apply boundary conditions"""
    for node_id, dofs in boundary_conditions.items():
        ops.fix(node_id, *dofs)


def create_rigid_diaphragms(diaphragm_list):
    """Create rigid diaphragm constraints"""
    for perp_dir, ret_node, *constr_nodes in diaphragm_list:
        ops.rigidDiaphragm(perp_dir, ret_node, *constr_nodes)

def create_elements(element_configs):
    """Create transformations, integrations, elastic sections, and elements
    NOTE: Fiber sections are created separately by build_model()"""
    
    for transf in element_configs.get('transformations', []):
        ops.geomTransf(transf['type'], transf['tag'], *transf['vecxz'])
    
    for integ in element_configs.get('integrations', []):
        ops.beamIntegration(integ['type'], integ['tag'], integ['sec_tag'], integ['np'])
    
    for elastic_sec in element_configs.get('elastic_sections', []):
        ops.section("Elastic", elastic_sec['sec_tag'], elastic_sec['E'],
                   elastic_sec['A'], elastic_sec['Iz'], elastic_sec['Iy'],
                   elastic_sec['G'], elastic_sec['J'])
    
    for col in element_configs.get('force_beam_columns', []):
        ops.element("forceBeamColumn", col['tag'], col['node_i'], col['node_j'], 
                    col['transf_tag'], col['integ_tag'])
    
    for beam in element_configs.get('elastic_beam_columns', []):
        ops.element("elasticBeamColumn", beam['tag'], beam['node_i'], beam['node_j'],
                    beam['A'], beam['E'], beam['G'], beam['J'], 
                    beam['Iy'], beam['Iz'], beam['transf_tag'])

from collections import defaultdict


"""
UNIFIED LOAD AND MASS APPLICATION FUNCTION - NO DEFAULTS
=========================================================
Single function to handle all loads and masses.
User MUST provide all parameters explicitly.
"""


"""
UNIFIED LOAD AND MASS APPLICATION FUNCTION - NO DEFAULTS
=========================================================
Single function to handle all loads and masses.
User MUST provide all parameters explicitly.
"""

import numpy as np
import openseespy.opensees as ops
from collections import defaultdict

def apply_loads_and_masses(
    load_configs,        # REQUIRED: Load configurations
    mass_configs,        # REQUIRED: Mass configurations
    shell_meshes,        # REQUIRED: Shell mesh data
    slab_configs,        # REQUIRED: Shell configurations
    element_configs,     # REQUIRED: Element connectivity
    node_coords          # REQUIRED: Node coordinates
):
    """
    Unified function to apply ALL loads and masses to OpenSees model.
    
    ALL PARAMETERS ARE REQUIRED - NO DEFAULTS PROVIDED.
    
    Parameters
    ----------
    load_configs : dict or None
        If None: No loads applied
        If dict: Must contain load definitions:
        {
            'time_series': [
                {'tag': 1, 'type': 'Linear'},
                {'tag': 2, 'type': 'Constant'},
            ],
            
            'patterns': [
                {'tag': 1, 'type': 'Plain', 'ts_tag': 1},
            ],
            
            'nodal_loads': [
                {
                    'pattern_tag': 1,
                    'loads': [
                        {'node': 1, 'forces': [Fx, Fy, Fz, Mx, My, Mz]},
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
            
            'beam_point_loads': [
                {
                    'pattern_tag': 1,
                    'loads': [
                        {'element': 11, 'py': 0, 'pz': -50, 'xl': 0.5},
                    ]
                }
            ],
            
            'shell_surface_loads': [
                {
                    'pattern_tag': 2,
                    'loads': [
                        {'mesh_name': 'Slab_1', 'pressure': -100.0, 'elements': None},
                    ]
                }
            ]
        }
    
    mass_configs : dict or None
        If None: No masses applied
        If dict: Must contain mass definitions:
        {
            'beam_column_mass': [
                {'tag': 11, 'density': 1.0, 'area': 4.0},
            ],
            
            'nodal_mass': [
                {'node': 1, 'mass': 100.0},
            ],
            
            'shell_mass': {
                'calculate': True,
                'exclude': ['Footing_1'],  # Can be empty list []
                'scale': 1.0
            }
        }
    
    shell_meshes : list
        List of shell mesh dictionaries from create_slab()
        Can be empty list [] if no shells
    
    slab_configs : list
        List of shell configuration dictionaries
        Can be empty list [] if no shells
    
    element_configs : dict
        Element connectivity dictionary
        Must have keys: 'force_beam_columns', 'elastic_beam_columns'
    
    node_coords : dict
        Node coordinates dictionary {node_id: (x, y, z)}
    
    Returns
    -------
    results : dict
        {
            'nodal_masses': dict,
            'load_summary': dict,
            'mass_summary': dict
        }
    """
    
    # Validate required parameters
    if load_configs is None and mass_configs is None:
        raise ValueError("Both load_configs and mass_configs are None. Nothing to do!")
    
    if element_configs is None:
        raise ValueError("element_configs is required!")
    
    if node_coords is None:
        raise ValueError("node_coords is required!")
    
    # Import opstool if available
    try:
        import opstool as opst
        has_opstool = True
    except ImportError:
        print("WARNING: opstool not installed. Some features may not work.")
        opst = None
        has_opstool = False
    
    results = {
        'nodal_masses': {},
        'load_summary': {},
        'mass_summary': {}
    }
    
    # ========================================================================
    # PART 1: APPLY LOADS
    # ========================================================================
    
    if load_configs is not None:
        print("\n" + "="*70)
        print("APPLYING LOADS")
        print("="*70)
        
        # ----------------------------------------------------------------
        # 1.1: CREATE TIME SERIES
        # ----------------------------------------------------------------
        if 'time_series' in load_configs:
            print("\n1. Creating Time Series:")
            for ts in load_configs['time_series']:
                tag = ts['tag']
                ts_type = ts['type']
                
                if ts_type == 'Linear':
                    ops.timeSeries('Linear', tag)
                elif ts_type == 'Constant':
                    ops.timeSeries('Constant', tag)
                elif ts_type == 'Trig':
                    ops.timeSeries('Trig', tag, ts['tStart'], ts['tEnd'], ts['period'])
                else:
                    raise ValueError(f"Unknown time series type: {ts_type}")
                
                print(f"   Time Series {tag}: {ts_type}")
            
            results['load_summary']['time_series'] = len(load_configs['time_series'])
        
        # ----------------------------------------------------------------
        # 1.2: CREATE LOAD PATTERNS
        # ----------------------------------------------------------------
        if 'patterns' in load_configs:
            print("\n2. Creating Load Patterns:")
            for pattern in load_configs['patterns']:
                tag = pattern['tag']
                pattern_type = pattern['type']
                ts_tag = pattern['ts_tag']
                
                if pattern_type != 'Plain':
                    raise ValueError(f"Unknown pattern type: {pattern_type}. Only 'Plain' supported.")
                
                ops.pattern('Plain', tag, ts_tag)
                print(f"   Pattern {tag}: {pattern_type} (TimeSeries {ts_tag})")
            
            results['load_summary']['patterns'] = len(load_configs['patterns'])
        
        # ----------------------------------------------------------------
        # 1.3: APPLY NODAL LOADS
        # ----------------------------------------------------------------
        if 'nodal_loads' in load_configs:
            print("\n3. Applying Nodal Loads:")
            total_nodal_loads = 0
            
            for load_group in load_configs['nodal_loads']:
                pattern_tag = load_group['pattern_tag']
                # DON'T create pattern again - it's already created in step 1.2!
                # Just apply loads to the existing pattern
                
                for load in load_group['loads']:
                    node_id = load['node']
                    forces = load['forces']
                    
                    if len(forces) != 6:
                        raise ValueError(f"forces must have 6 values [Fx,Fy,Fz,Mx,My,Mz], got {len(forces)}")
                    
                    ops.load(node_id, *forces)
                    total_nodal_loads += 1
                    print(f"   Node {node_id}: F={forces[:3]} (Pattern {pattern_tag})")
            
            results['load_summary']['nodal_loads'] = total_nodal_loads
        
        # ----------------------------------------------------------------
        # 1.4: APPLY BEAM UNIFORM LOADS
        # ----------------------------------------------------------------
        if 'beam_uniform_loads' in load_configs:
            if not has_opstool:
                raise ImportError("opstool required for beam_uniform_loads")
            
            print("\n4. Applying Beam Uniform Loads:")
            total_beam_uniform = 0
            
            for load_group in load_configs['beam_uniform_loads']:
                pattern_tag = load_group['pattern_tag']
                # Pattern already created in step 1.2 - don't create again!
                
                for load in load_group['loads']:
                    elements = load['elements']
                    wy = load['wy']
                    wz = load['wz']
                    
                    opst.pre.transform_beam_uniform_load(elements, wy=wy, wz=wz)
                    total_beam_uniform += len(elements)
                    print(f"   Elements {elements}: wy={wy}, wz={wz} (Pattern {pattern_tag})")
            
            results['load_summary']['beam_uniform_loads'] = total_beam_uniform
        
        # ----------------------------------------------------------------
        # 1.5: APPLY BEAM POINT LOADS
        # ----------------------------------------------------------------
        if 'beam_point_loads' in load_configs:
            if not has_opstool:
                raise ImportError("opstool required for beam_point_loads")
            
            print("\n5. Applying Beam Point Loads:")
            total_beam_point = 0
            
            for load_group in load_configs['beam_point_loads']:
                pattern_tag = load_group['pattern_tag']
                # Pattern already created in step 1.2 - don't create again!
                
                for load in load_group['loads']:
                    element = load['element']
                    py = load['py']
                    pz = load['pz']
                    xl = load['xl']
                    
                    opst.pre.transform_beam_point_load([element], py=py, pz=pz, xl=xl)
                    total_beam_point += 1
                    print(f"   Element {element}: py={py}, pz={pz}, xl={xl} (Pattern {pattern_tag})")
            
            results['load_summary']['beam_point_loads'] = total_beam_point
        
        # ----------------------------------------------------------------
        # 1.6: APPLY SHELL SURFACE LOADS
        # ----------------------------------------------------------------
        if 'shell_surface_loads' in load_configs:
            if not has_opstool:
                raise ImportError("opstool required for shell_surface_loads")
            
            if not shell_meshes:
                raise ValueError("shell_meshes cannot be empty for shell_surface_loads")
            
            print("\n6. Applying Shell Surface Loads:")
            total_shell_loads = 0
            
            for load_group in load_configs['shell_surface_loads']:
                pattern_tag = load_group['pattern_tag']
                # Pattern already created in step 1.2 - don't create again!
                
                for load in load_group['loads']:
                    mesh_name = load['mesh_name']
                    pressure = load['pressure']
                    specific_elements = load['elements']
                    
                    # Find mesh
                    target_mesh = None
                    for mesh in shell_meshes:
                        if mesh.get('config_name') == mesh_name:
                            target_mesh = mesh
                            break
                    
                    if target_mesh is None:
                        raise ValueError(f"Mesh '{mesh_name}' not found in shell_meshes")
                    
                    # Get element tags
                    if specific_elements is None:
                        element_tags = [elem['tag'] for elem in target_mesh['quad4']]
                        element_tags += [elem['tag'] for elem in target_mesh['tri3']]
                    else:
                        element_tags = specific_elements
                    
                    # Apply load
                    opst.pre.transform_surface_uniform_load(ele_tags=element_tags, p=pressure)
                    total_shell_loads += len(element_tags)
                    print(f"   {mesh_name}: pressure={pressure}, {len(element_tags)} elements (Pattern {pattern_tag})")
            
            results['load_summary']['shell_surface_loads'] = total_shell_loads
    
    # ========================================================================
    # PART 2: APPLY MASSES
    # ========================================================================
    
    # ========================================================================
    # PART 2: APPLY MASSES
    # ========================================================================
    
    if mass_configs is not None:
        print("\n" + "="*70)
        print("APPLYING MASSES")
        print("="*70)
        
        # ================================================================
        # INITIALIZE NODAL MASS DICTIONARY WITH ALL NODES
        # ================================================================
        # Start with frame nodes from node_coords
        nodal_masses = {node_id: 0.0 for node_id in node_coords.keys()}
        
        # Add all shell mesh nodes
        if shell_meshes:
            for shell_mesh in shell_meshes:
                for node_id in shell_mesh['nodes'].keys():
                    if node_id not in nodal_masses:
                        nodal_masses[node_id] = 0.0
        
        print(f"\nInitialized mass dictionary with {len(nodal_masses)} nodes")
        
        # ----------------------------------------------------------------
        # 2.1: BEAM/COLUMN MASS
        # ----------------------------------------------------------------
        if 'beam_column_mass' in mass_configs:
            print("\n1. Calculating Beam/Column Masses:")
            
            beam_col_mass_applied = 0
            
            for item in mass_configs['beam_column_mass']:
                tag = item['tag']
                density = item['density']
                area = item['area']
                
                # Find element in force beam columns
                element_found = False
                node_i, node_j = None, None
                
                for col in element_configs['force_beam_columns']:
                    if col['tag'] == tag:
                        node_i, node_j = col['node_i'], col['node_j']
                        element_found = True
                        break
                
                # If not found, search in elastic beam columns
                if not element_found:
                    for beam in element_configs['elastic_beam_columns']:
                        if beam['tag'] == tag:
                            node_i, node_j = beam['node_i'], beam['node_j']
                            element_found = True
                            break
                
                if not element_found:
                    raise ValueError(f"Element {tag} not found in element_configs")
                
                # Calculate element length
                xi, yi, zi = node_coords[node_i]
                xj, yj, zj = node_coords[node_j]
                length = ((xj-xi)**2 + (yj-yi)**2 + (zj-zi)**2)**0.5
                
                # Calculate element mass
                mass = density * area * length
                half_mass = mass / 2.0
                
                # Ensure nodes exist in dictionary (safety check)
                if node_i not in nodal_masses:
                    nodal_masses[node_i] = 0.0
                if node_j not in nodal_masses:
                    nodal_masses[node_j] = 0.0
                
                # Add mass to nodes
                nodal_masses[node_i] += half_mass
                nodal_masses[node_j] += half_mass
                
                beam_col_mass_applied += mass
            
            print(f"   Processed {len(mass_configs['beam_column_mass'])} beam/column elements")
            print(f"   Total beam/column mass: {beam_col_mass_applied:.2f}")
            results['mass_summary']['beam_column_count'] = len(mass_configs['beam_column_mass'])
            results['mass_summary']['beam_column_mass'] = beam_col_mass_applied
        
        # ----------------------------------------------------------------
        # 2.2: NODAL MASS (with automatic summation at common nodes)
        # ----------------------------------------------------------------
        if 'nodal_mass' in mass_configs:
            print("\n2. Applying Nodal Masses:")
            
            # Group by node to show summation
            node_mass_groups = defaultdict(list)
            for item in mass_configs['nodal_mass']:
                node_id = item['node']
                mass_value = item['mass']
                node_mass_groups[node_id].append(mass_value)
            
            total_nodal_mass_applied = 0.0
            
            for node_id, mass_list in node_mass_groups.items():
                total_mass = sum(mass_list)
                
                # Ensure node exists in dictionary (safety check)
                if node_id not in nodal_masses:
                    nodal_masses[node_id] = 0.0
                
                # Add mass to node
                nodal_masses[node_id] += total_mass
                total_nodal_mass_applied += total_mass
                
                # Show summation if multiple entries for same node
                if len(mass_list) > 1:
                    mass_str = ' + '.join([f'{m:.2f}' for m in mass_list])
                    print(f"   Node {node_id}: {mass_str} = {total_mass:.2f} (summed)")
                else:
                    print(f"   Node {node_id}: {total_mass:.2f}")
            
            print(f"   Total nodal mass: {total_nodal_mass_applied:.2f}")
            results['mass_summary']['nodal_mass_count'] = len(mass_configs['nodal_mass'])
            results['mass_summary']['nodal_mass_total'] = total_nodal_mass_applied
        
        # ----------------------------------------------------------------
        # 2.3: SHELL MASS (calculated from element areas)
        # ----------------------------------------------------------------
        if 'shell_mass' in mass_configs:
            shell_config = mass_configs['shell_mass']
            
            if shell_config['calculate']:
                if not has_opstool:
                    raise ImportError("opstool required for shell mass calculation")
                
                if not shell_meshes:
                    raise ValueError("shell_meshes cannot be empty when calculate=True")
                
                if not slab_configs:
                    raise ValueError("slab_configs cannot be empty when calculate=True")
                
                print("\n3. Calculating Shell Masses:")
                
                exclude_list = shell_config['exclude']
                scale_factor = shell_config['scale']
                
                total_shell_elements = 0
                total_shell_mass_applied = 0.0
                
                for shell_mesh in shell_meshes:
                    config_name = shell_mesh.get('config_name', 'Unknown')
                    
                    # Check if excluded
                    if config_name in exclude_list:
                        print(f"  ⊘ {config_name}: EXCLUDED from mass calculation")
                        continue
                    
                    # Find density and thickness from slab_configs
                    density = None
                    thickness = None
                    
                    for cfg in slab_configs:
                        if cfg.get('name') == config_name:
                            mat_config = cfg['shell_material_config']
                            density = mat_config[4] * scale_factor
                            
                            sec_config = cfg['shell_section_config']
                            thickness = sec_config[3]
                            break
                    
                    if density is None or thickness is None:
                        raise ValueError(f"Could not find density/thickness for {config_name}")
                    
                    # Get all shell element tags
                    shell_ele_tags = [elem['tag'] for elem in shell_mesh['quad4'] + shell_mesh['tri3']]
                    
                    # Calculate masses from element areas
                    shell_nodal_masses = _calculate_shell_mass_from_areas(
                        ele_tags=shell_ele_tags,
                        density=density,
                        thickness=thickness,
                        opst=opst
                    )
                    
                    # Add to total nodal masses (with safety check)
                    mesh_total_mass = 0.0
                    for node_id, shell_mass in shell_nodal_masses.items():
                        if node_id not in nodal_masses:
                            nodal_masses[node_id] = 0.0
                        
                        nodal_masses[node_id] += shell_mass
                        mesh_total_mass += shell_mass
                    
                    total_shell_elements += len(shell_ele_tags)
                    total_shell_mass_applied += mesh_total_mass
                    
                    print(f"   {config_name}: {len(shell_ele_tags)} elements, mass={mesh_total_mass:.2f}")
                
                print(f"   Total shell mass: {total_shell_mass_applied:.2f}")
                results['mass_summary']['shell_elements'] = total_shell_elements
                results['mass_summary']['shell_mass_total'] = total_shell_mass_applied
        
        # ----------------------------------------------------------------
        # 2.4: APPLY MASSES TO OPENSEES MODEL
        # ----------------------------------------------------------------
        print("\n4. Applying Masses to OpenSees Model:")
        
        nodes_with_mass = 0
        total_mass_applied = 0.0
        
        for node_id, mass_value in nodal_masses.items():
            if mass_value > 0:
                # Apply mass to translational DOFs (X, Y, Z)
                # Rotational inertias set to 0
                ops.mass(node_id, mass_value, mass_value, mass_value, 0.0, 0.0, 0.0)
                nodes_with_mass += 1
                total_mass_applied += mass_value
        
        print(f"   Applied mass to {nodes_with_mass} nodes")
        print(f"   Total mass in model: {total_mass_applied:.4f}")
        
        # Store results
        results['nodal_masses'] = nodal_masses
        results['mass_summary']['nodes_with_mass'] = nodes_with_mass
        results['mass_summary']['total_mass'] = total_mass_applied
        
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print("\n" + "="*70)
    print("LOAD AND MASS APPLICATION COMPLETE")
    print("="*70)
    
    if load_configs:
        print("\nLoads Applied:")
        for key, value in results['load_summary'].items():
            print(f"  - {key}: {value}")
    
    if mass_configs:
        print("\nMasses Applied:")
        for key, value in results['mass_summary'].items():
            print(f"  - {key}: {value}")
    
    print("="*70)
    
    return results



def _compute_tri_area_and_normal(vertices):
    """
    Compute the area and normal vector of a triangular element.

    Parameters
    ----------
    vertices : numpy.ndarray
        Coordinates of the triangle's vertices, shape (3, 3).

    Returns
    -------
    area : float
        Area of the triangle.
    normal : numpy.ndarray
        Unit normal vector of the triangle, shape (3,).
    """
    # Edges: IJ and JK
    edge_ij = vertices[1] - vertices[0]
    edge_jk = vertices[2] - vertices[1]

    # Compute cross product
    cross_product = np.cross(edge_ij, edge_jk)
    norm = np.linalg.norm(cross_product)
    area = 0.5 * norm
    # Normalize the normal vector
    normal = cross_product / norm
    return area, normal


def _compute_quad_area_and_normal(vertices):
    """
    Compute the area and normal vector of a quadrilateral element.

    Parameters
    ----------
    vertices : numpy.ndarray
        Coordinates of the quadrilateral's vertices, shape (4, 3).

    Returns
    -------
    area : float
        Area of the quadrilateral.
    normal : numpy.ndarray
        Unit normal vector of the quadrilateral, shape (3,).
    """
    # Divide quadrilateral into two triangles
    triangle1 = vertices[:3]
    triangle2 = np.array([vertices[0], vertices[2], vertices[3]])

    # Compute areas and normals
    area1, normal1 = _compute_tri_area_and_normal(triangle1)
    area2, normal2 = _compute_tri_area_and_normal(triangle2)

    # Average the normals and normalize
    normal = (normal1 + normal2) / 2.0
    # normal = normal / np.linalg.norm(normal)
    return area1 + area2, normal

# ============================================================================
# HELPER FUNCTION: Shell Mass Calculation
# ============================================================================

def _calculate_shell_mass_from_areas(ele_tags, density, thickness, opst):
    """Calculate shell element mass from areas (internal helper function)"""
    
    ele_tags = [int(tag) for tag in ele_tags]
    nodal_masses = defaultdict(float)
    
    for etag in ele_tags:
        node_ids = ops.eleNodes(etag)
        vertices = np.array([ops.nodeCoord(node_id) for node_id in node_ids])
        
        # Calculate area
        if len(node_ids) == 3:
            area, _ = _compute_tri_area_and_normal(vertices)
        elif len(node_ids) == 4:
            area, _ = _compute_quad_area_and_normal(vertices)
        else:
            raise ValueError(f"Unsupported element with {len(node_ids)} nodes")
        
        # Calculate and distribute mass
        element_mass = density * area * thickness
        mass_per_node = element_mass / len(node_ids)
        
        for node_id in node_ids:
            nodal_masses[node_id] += mass_per_node
    
    return dict(nodal_masses)

def build_model(
    model_params,
    materials_list,
    outline_points_list,
    rebar_configs_list,
    section_params_list,
    material_params,
    node_coords,
    boundary_conditions,
    element_configs,
    spring_configs=None,
    nodal_spring_configs=None,
    start_base_node_id=10000000,
    diaphragm_list=None,
    start_node_id=20000,  # ADD
    start_element_id=20000,  # ADD
    # element_mass_list=None,
    # nodal_mass_applied=None,
    # load_configs=None,      # NEW: Unified load config
    # mass_configs=None,      # NEW: Unified mass config (or keep old params)
    load_configs=None,      # NEW: Unified load config
    mass_configs=None,      # NEW: Unified mass config

    visualize=True,
    output_dir="output",
    
    # NEW: Single parameter for all create_slab() configurations
    slab_configs=None,  # List of dicts with create_slab() parameters (for slabs, footings, etc.)
    existing_frame_nodes=None
): 
    """
    Build complete OpenSeesPy 3D frame model with integrated fiber section creation,
    shell meshes (slabs, footings, etc.), and springs.
    """
    
    import os
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # ===================================================================
    # STEP 1: CREATE FIBER SECTIONS
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 1: CREATING FIBER SECTIONS")
    print("="*80)
    
    fiber_section_info = []
    for i, (materials, outline_points, rebar_configs, section_params) in enumerate(
        zip(materials_list, outline_points_list, rebar_configs_list, section_params_list)):
        
        # Use create_fiber_section function
        sec_id, txt_path, png_path, pkl_path = create_fiber_section(
            materials=materials,
            outline_points=outline_points,
            cover=section_params['cover'],
            rebar_configs=rebar_configs,
            mesh_size=section_params['mesh_size'],
            mat_tags=section_params['mat_tags'],
            sec_tag=section_params['sec_tag'],
            G=section_params['G'],
            save_prefix=os.path.join(output_dir, section_params['save_prefix']),
            section_name=section_params['section_name']
        )
        
        fiber_section_info.append({
            'sec_tag': section_params['sec_tag'],
            'txt_path': txt_path,
            'png_path': png_path,
            'pkl_path': pkl_path,
            'GJ': section_params['G']  # Will be updated after section creation
        })
    
    # ===================================================================
    # STEP 2: INITIALIZE MODEL AND DEFINE MATERIALS
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 2: INITIALIZING MODEL AND DEFINING MATERIALS")
    print("="*80)
    
    # Initialize OpenSees model
    ops.wipe()
    ops.model("basic", "-ndm", model_params['ndm'], "-ndf", model_params['ndf'])
    
    # Define uniaxial materials (only uniaxial materials, NOT fiber sections)
    for mat_param in material_params:
        ops.uniaxialMaterial(*mat_param)
    
    print(" Defined uniaxial materials")
    
    # ===================================================================
    # STEP 3: CREATE ALL SHELL MESHES USING create_slab() (IF SPECIFIED)
    # ===================================================================

    shell_results = []
    if slab_configs:
        print("\n" + "="*80)
        print("STEP 3: CREATING SHELL MESHES WITH create_slab()")
        print("="*80)
        
        for i, config in enumerate(slab_configs, start=1):
            config_name = config.get('name', f'Shell_{i}')
            print(f"\nGenerating {config_name}...")
            
            # Call create_slab() with the config parameters
            mesh = create_slab(
                boundary_nodes=config['boundary_nodes'],
                mesh_size=config.get('mesh_size', 1.0),
                internal_points=config.get('internal_points', None),
                existing_frame_nodes=existing_frame_nodes,
                voids=config.get('voids', None),
                py_file=os.path.join(output_dir, config.get('py_file', f'shell{i}_model.py')),
                png_file=os.path.join(output_dir, config.get('png_file', f'shell{i}_mesh.png')),
                shell_material_config=config['shell_material_config'],
                shell_section_config=config['shell_section_config'],
                
                node_font_size=config.get('node_font_size', 7),
                element_font_size=config.get('element_font_size', 6),
                ops_ele_type1=config.get('ops_ele_type1', "ShellMITC4"),
                ops_ele_type2=config.get('ops_ele_type2', "ASDShellT3"),
                shell_boundary_conditions=config.get('shell_boundary_conditions', [0, 0, 0, 0, 0, 0]),
                # assign_to_ops=True,
                use_zero_length=config.get('use_zero_length', False),
                zero_length_material_config=config.get('zero_length_material_config', None),
                zero_length_directions=config.get('zero_length_directions', [3]),
                zero_length_boundary_conditions=config.get('zero_length_boundary_conditions', [1, 1, 1, 1, 1, 1]),
                element_start_id=config.get('element_start_id', 10000 + i*1000),
                spring_node_start_id=config.get('spring_node_start_id', 1000000 + i*10000),
                load_configs=config.get('load_configs', None),
                start_node_id=config.get('start_node_id', start_node_id),          # Use config-specific or global
                start_element_id=config.get('start_element_id', start_element_id)  # Use config-specific or global

            )
            
            # Store the mesh with its name
            mesh['config_name'] = config_name
            shell_results.append(mesh)
            
            print(f" {config_name}: {len(mesh['nodes'])} nodes, "
                  f"{len(mesh['quad4']) + len(mesh['tri3'])} elements")

        print(f"\n  Total: {len(shell_results)} shell meshes created")

    # ===================================================================
    # STEP 4: CREATE ALL NODES
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 4: CREATING ALL NODES")
    print("="*80)
    
    all_nodes_created = set()
    
    # Create frame nodes
    for node_id, coords in node_coords.items():
        ops.node(node_id, *coords)
        all_nodes_created.add(node_id)
    
    # Create shell nodes (from all shell meshes)
    if shell_results:
        for shell_mesh in shell_results:
            for nid, coords in shell_mesh['nodes'].items():
                if nid not in all_nodes_created:
                    ops.node(nid, coords[0], coords[1], coords[2])
                    all_nodes_created.add(nid)
    
    print(f" Created {len(all_nodes_created)} unique nodes")
    
    # ===================================================================
    # STEP 5: APPLY BOUNDARY CONDITIONS
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 5: APPLYING BOUNDARY CONDITIONS")
    print("="*80)
    
    for node_id, dofs in boundary_conditions.items():
        ops.fix(node_id, *dofs)
    
    print(f" Applied boundary conditions to {len(boundary_conditions)} nodes")
    
    # ===================================================================
    # STEP 6: CREATE FIBER SECTIONS IN OPENSEES
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 6: CREATING FIBER SECTIONS IN MODEL")
    print("="*80)
    
    # Load and create fiber sections in OpenSees
    for fiber_sec in fiber_section_info:
        commands, figure, loaded_section, loaded_sec_id, loaded_GJ, file_paths = load_saved_section(
            txt_path=fiber_sec['txt_path'],
            png_path=fiber_sec['png_path'],
            pkl_path=fiber_sec['pkl_path'],
            display_commands=False,
            display_image=False,
            return_section_object=True
        )
        
        # Update GJ value from saved parameters
        if loaded_GJ is not None:
            fiber_sec['GJ'] = loaded_GJ
        
        # Execute the commands to create the fiber section
        exec(commands)
        print(f" Created fiber section with tag {fiber_sec['sec_tag']}")
    
    # ===================================================================
    # STEP 7: CREATE SPRINGS (IF SPECIFIED)
    # ===================================================================
    
    if nodal_spring_configs:
        print("\n" + "="*80)
        print("STEP 7: CREATING SUPPORT SPRINGS")
        print("="*80)
        
        zero_element_boundary_condition(
            material_props=nodal_spring_configs['material_props'],
            sections=nodal_spring_configs.get('sections', {}),
            node_list=nodal_spring_configs['node_list'],
            boundary_condition=nodal_spring_configs.get('boundary_condition', [1, 1, 1, 1, 1, 1]),
            element_start_id=nodal_spring_configs.get('element_start_id', start_base_node_id),
            spring_node_start_id=nodal_spring_configs.get('spring_node_start_id', start_base_node_id + 1000000)
        )
    
    print(f" Created zero-length springs")

    # ===================================================================
    # STEP 8: CREATE RIGID DIAPHRAGMS (IF SPECIFIED)
    # ===================================================================
    
    if diaphragm_list:
        print("\n" + "="*80)
        print("STEP 8: CREATING RIGID DIAPHRAGMS")
        print("="*80)
        
        for perp_dir, ret_node, *constr_nodes in diaphragm_list:
            ops.rigidDiaphragm(perp_dir, ret_node, *constr_nodes)
        
        print(f" Created {len(diaphragm_list)} rigid diaphragms")
    
    # ===================================================================
    # STEP 9: CREATE TRANSFORMATIONS, INTEGRATIONS, AND BEAM ELEMENTS
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 9: CREATING BEAM ELEMENTS")
    print("="*80)
    
    # Create transformations
    for transf in element_configs.get('transformations', []):
        ops.geomTransf(transf['type'], transf['tag'], *transf['vecxz'])
    
    # Create integrations
    for integ in element_configs.get('integrations', []):
        ops.beamIntegration(integ['type'], integ['tag'], integ['sec_tag'], integ['np'])
    
    # Create elastic sections
    for elastic_sec in element_configs.get('elastic_sections', []):
        ops.section("Elastic", elastic_sec['sec_tag'], elastic_sec['E'],
                   elastic_sec['A'], elastic_sec['Iz'], elastic_sec['Iy'],
                   elastic_sec['G'], elastic_sec['J'])
    
    # Create force beam columns
    col_count = 0
    for col in element_configs.get('force_beam_columns', []):
        ops.element("forceBeamColumn", col['tag'], col['node_i'], col['node_j'], 
                    col['transf_tag'], col['integ_tag'])
        col_count += 1
    
    # Create elastic beam columns
    beam_count = 0
    for beam in element_configs.get('elastic_beam_columns', []):
        ops.element("elasticBeamColumn", beam['tag'], beam['node_i'], beam['node_j'],
                    beam['A'], beam['E'], beam['G'], beam['J'], 
                    beam['Iy'], beam['Iz'], beam['transf_tag'])
        beam_count += 1
    
    print(f" Created {col_count} columns and {beam_count} beams")
    

    

    # ===================================================================
    # STEP 10: CREATE SHELL ELEMENTS
    # ===================================================================

    # print("\n" + "="*80)
    # print("STEP 10: CREATING SHELL ELEMENTS")
    # print("="*80)

    # shell_ele_count = 0
    # if shell_results:
    #     for shell_mesh in shell_results:
    #         config_name = shell_mesh.get('config_name', 'Unknown')
            
    #         # Get material and section configs from the original slab_configs
    #         # Find the matching config
    #         shell_mat_config = None
    #         shell_sec_config = None
            
    #         for config in slab_configs:
    #             if config.get('name') == config_name:
    #                 shell_mat_config = config['shell_material_config']
    #                 shell_sec_config = config['shell_section_config']
    #                 break
            
    #         if shell_mat_config is None or shell_sec_config is None:
    #             print(f"  WARNING: Could not find config for {config_name}, skipping...")
    #             continue
            
    #         # Get section tag from shell_section_config
    #         sec_tag = shell_sec_config[1]
            
    #         # Define nDMaterial and section if not already defined
    #         try:
    #             ops.nDMaterial(shell_mat_config[0], shell_mat_config[1], 
    #                         shell_mat_config[2], shell_mat_config[3], shell_mat_config[4])
    #         except:
    #             pass  # Material might already exist
            
    #         try:
    #             ops.section(shell_sec_config[0], shell_sec_config[1], 
    #                     shell_sec_config[2], shell_sec_config[3])
    #         except:
    #             pass  # Section might already exist
            
    #         # Create quad4 elements
    #         for elem in shell_mesh['quad4']:
    #             ops.element("ShellMITC4", elem['tag'], *elem['nodes'], sec_tag)
    #             shell_ele_count += 1
            
    #         # Create tri3 elements
    #         for elem in shell_mesh['tri3']:
    #             ops.element("ASDShellT3", elem['tag'], *elem['nodes'], sec_tag)
    #             shell_ele_count += 1
            
    #         print(f"  {config_name}: {len(shell_mesh['quad4']) + len(shell_mesh['tri3'])} elements")

    # print(f" Created {shell_ele_count} total shell elements")


    # ===================================================================
    # STEP 10: CREATE SHELL ELEMENTS
    # ===================================================================

    print("\n" + "="*80)
    print("STEP 10: CREATING SHELL ELEMENTS")
    print("="*80)

    shell_ele_count = 0
    if shell_results:
        for shell_mesh in shell_results:
            config_name = shell_mesh.get('config_name', 'Unknown')
            
            # Find matching config
            shell_mat_config = None
            shell_sec_config = None
            use_zero_length = False
            zero_length_config = None
            
            for config in slab_configs:
                if config.get('name') == config_name:
                    shell_mat_config = config['shell_material_config']
                    shell_sec_config = config['shell_section_config']
                    use_zero_length = config.get('use_zero_length', False)
                    if use_zero_length:
                        zero_length_config = {
                            'material_config': config.get('zero_length_material_config'),
                            'directions': config.get('zero_length_directions', [3]),
                            'boundary_conditions': config.get('zero_length_boundary_conditions', [1,1,1,1,1,1]),
                            'element_start_id': config.get('element_start_id', 10000),
                            'spring_node_start_id': config.get('spring_node_start_id', 1000000)
                        }
                    break
            
            if shell_mat_config is None or shell_sec_config is None:
                print(f"  WARNING: Could not find config for {config_name}, skipping...")
                continue
            
            # Get section tag
            sec_tag = shell_sec_config[1]
            
            # Define nDMaterial and section
            try:
                ops.nDMaterial(shell_mat_config[0], shell_mat_config[1], 
                            shell_mat_config[2], shell_mat_config[3], shell_mat_config[4])
            except:
                pass
            
            try:
                ops.section(shell_sec_config[0], shell_sec_config[1], 
                        shell_sec_config[2], shell_sec_config[3])
            except:
                pass
            
            # Create quad4 elements
            for elem in shell_mesh['quad4']:
                ops.element("ShellMITC4", elem['tag'], *elem['nodes'], sec_tag)
                shell_ele_count += 1
            
            # Create tri3 elements
            for elem in shell_mesh['tri3']:
                ops.element("ASDShellT3", elem['tag'], *elem['nodes'], sec_tag)
                shell_ele_count += 1
            
            print(f"  {config_name}: {len(shell_mesh['quad4']) + len(shell_mesh['tri3'])} elements")
            
            # ===== ADD ZERO-LENGTH SPRINGS =====
            if use_zero_length and zero_length_config and zero_length_config['material_config']:
                print(f"  Creating zero-length springs for {config_name}...")
                
                # Prepare material properties
                zero_mat_tag = zero_length_config['material_config'][1]
                zero_length_material = {
                    'id': zero_mat_tag,
                    'directions': zero_length_config['directions'],
                    'config': zero_length_config['material_config']
                }
                
                # Create node list from ALL mesh nodes
                node_list = [(nid, float(shell_mesh['nodes'][nid][0]), 
                                float(shell_mesh['nodes'][nid][1]), 
                                float(shell_mesh['nodes'][nid][2])) 
                                for nid in shell_mesh['nodes'].keys()]
                
                # Create zero-length springs
                zero_result = zero_element_boundary_condition(
                    material_props=zero_length_material,
                    sections={},
                    node_list=node_list,
                    boundary_condition=zero_length_config['boundary_conditions'],
                    element_start_id=zero_length_config['element_start_id'],
                    spring_node_start_id=zero_length_config['spring_node_start_id']
                )
                
                print(f"   Created {zero_result['total_elements']} zero-length springs")
                shell_mesh['zero_length'] = zero_result

    print(f" Created {shell_ele_count} total shell elements")

    # ===================================================================
    # # STEP 11: CREATE ELEMENT MASS
    # # ===================================================================
    
    # print("\n" + "="*80)
    # print("STEP 11: CALCULATING AND APPLYING MASSES")
    # print("="*80)
    
    # if element_mass_list:
    #     nodal_masses= calculate_and_apply_all_masses(
    #         element_mass_list=element_mass_list,
    #         shell_meshes=shell_results,
    #         slab_configs=slab_configs,
    #         element_configs=element_configs,
    #         node_coords=node_coords,
    #         nodal_mass_applied=nodal_mass_applied  # NEW!
    #     )
    # else:
    #     print("No beam/column masses defined")

    # ===================================================================
    # STEP 11: APPLY LOADS AND MASSES
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 11: APPLYING LOADS AND MASSES")
    print("="*80)
    
    # Prepare load configs (if any)
    load_configs_to_apply = load_configs if load_configs else None
    
    # Prepare mass configs (if any) - SIMPLIFY THIS
    mass_configs_to_apply = mass_configs if mass_configs else None

    
    # Apply loads and masses using unified function
    if load_configs_to_apply or mass_configs_to_apply:
        results = apply_loads_and_masses(
            load_configs=load_configs_to_apply,
            mass_configs=mass_configs_to_apply,
            shell_meshes=shell_results,
            slab_configs=slab_configs,
            element_configs=element_configs,
            node_coords=node_coords
        )
    else:
        print("No loads or masses defined")
    
    # ===================================================================
    # STEP 12: VISUALIZATION
    # ===================================================================
    
    if visualize:
        print("\n" + "="*80)
        print("STEP 12: CREATING VISUALIZATION")
        print("="*80)
        
        try:
            fig = opst.vis.plotly.plot_model(
                show_node_numbering=False,
                show_ele_numbering=False,
                show_ele_hover=True,
                style="surface",
                show_bc=True,
                bc_scale=0.5,
                show_outline=True
            )
            
            output_path = os.path.join(output_dir, "complete_model.html")
            fig.write_html(output_path)
            print(f" Visualization saved to: {output_path}")
            
        except Exception as e:
            print(f"Visualization error: {e}")
    
    # ===================================================================
    # STEP 13: SUMMARY
    # ===================================================================
    
    print("\n" + "="*80)
    print("MODEL BUILD COMPLETE")
    print("="*80)
    
    all_node_tags = ops.getNodeTags()
    all_ele_tags = ops.getEleTags()
    
    print(f"\nTotal Nodes: {len(all_node_tags)}")
    print(f"Total Elements: {len(all_ele_tags)}")
    print(f"  - Columns: {col_count}")
    print(f"  - Beams: {beam_count}")
    print(f"  - Shell elements: {shell_ele_count} (from {len(shell_results) if shell_results else 0} shell meshes)")
    print(f"  - Springs: {len(spring_configs) if spring_configs else 0}")
    
    print("\n" + "="*80)
    print("SUCCESS!")
    print("="*80)

    
    # In the build_model() function, modify the call to generate_complete_model_file():

    # Find spring configurations from shell meshes
    nodal_spring_configs_to_pass = None
    for shell_mesh in shell_results:
        if 'zero_length' in shell_mesh:
            # Find the corresponding slab config
            config_name = shell_mesh.get('config_name', '')
            for slab_config in slab_configs:
                if slab_config.get('name') == config_name:
                    if slab_config.get('use_zero_length', False):
                        zero_mat_config = slab_config.get('zero_length_material_config')
                        if zero_mat_config:
                            nodal_spring_configs_to_pass = {
                                'material_props': {
                                    'id': zero_mat_config[1],
                                    'directions': slab_config['zero_length_directions'],
                                    'config': zero_mat_config
                                },
                                'node_list': [(nid, shell_mesh['nodes'][nid][0], 
                                            shell_mesh['nodes'][nid][1], 
                                            shell_mesh['nodes'][nid][2]) 
                                            for nid in shell_mesh['nodes'].keys()],
                                'boundary_condition': slab_config['zero_length_boundary_conditions'],
                                'element_start_id': slab_config['element_start_id'],
                                'spring_node_start_id': slab_config['spring_node_start_id']
                            }
                    break

    # Call generate_complete_model_file() with the actual parameters
    generate_complete_model_file(
        output_filepath=os.path.join(output_dir, "complete_model.py"),
        model_params=model_params,
        fiber_section_info=fiber_section_info,
        material_params=material_params,  # This is defined in build_model()
        node_coords=node_coords,  # This is defined in build_model()
        shell_meshes=shell_results,  # This is defined in build_model()
        slab_configs=slab_configs,  # This is defined in build_model()
        boundary_conditions=boundary_conditions,  # This is defined in build_model()
        element_configs=element_configs,  # This is defined in build_model()
        nodal_spring_configs=nodal_spring_configs_to_pass,  # Pass extracted config or None
        load_configs=load_configs,  # This is defined in build_model()
        mass_configs=mass_configs  # This is defined in build_model()
    )

    
    return {
        'fiber_sections': fiber_section_info,
        'shell_meshes': shell_results,
        'total_nodes': len(all_node_tags),
        'total_elements': len(all_ele_tags)
    }

def generate_complete_model_file(
    output_filepath,
    model_params,
    fiber_section_info,
    material_params,
    node_coords,
    shell_meshes,
    slab_configs,
    boundary_conditions,
    element_configs,
    nodal_spring_configs,
    load_configs,
    mass_configs
):
    """
    Generate a complete standalone OpenSeesPy model file (.py)
    
    Parameters
    ----------
    output_filepath : str
        Path to output .py file (e.g., 'final_model.py')
    
    model_params : dict
        {'ndm': 3, 'ndf': 6}
    
    fiber_section_info : list
        List of fiber section dictionaries with 'txt_path' for commands
    
    material_params : list
        List of uniaxial material parameters
    
    node_coords : dict
        Frame node coordinates {node_id: (x, y, z)}
    
    shell_meshes : list
        List of shell mesh dictionaries from create_slab()
    
    slab_configs : list
        List of shell configuration dictionaries
    
    boundary_conditions : dict
        Boundary conditions {node_id: [dof1, dof2, ...]}
    
    element_configs : dict
        Element connectivity and properties
    
    nodal_spring_configs : dict or None
        Zero-length spring configurations
    
    load_configs : dict or None
        Load configurations
    
    mass_configs : dict or None
        Mass configurations
    """
    
    with open(output_filepath, 'w') as f:
        
        # ================================================================
        # HEADER
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# COMPLETE OPENSEESPY MODEL - AUTO-GENERATED\n")
        f.write("# " + "="*70 + "\n")
        f.write("# This file contains the complete structural model including:\n")
        f.write("# - Fiber section columns\n")
        f.write("# - Elastic beam elements\n")
        f.write("# - Shell elements (slabs, footings, etc.)\n")
        f.write("# - Boundary conditions\n")
        f.write("# - Zero-length springs (if applicable)\n")
        f.write("# - Loads and masses\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("import openseespy.opensees as ops\n")
        f.write("import opstool as opst\n")
        f.write("import numpy as np\n\n")
        
        # ================================================================
        # SECTION 1: MODEL INITIALIZATION
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 1: MODEL INITIALIZATION\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('Initializing OpenSees model...')\n")
        f.write("ops.wipe()\n")
        f.write(f"ops.model('basic', '-ndm', {model_params['ndm']}, '-ndf', {model_params['ndf']})\n")
        # f.write("print(' Model initialized')\n\n")
        f.write("print(' Model initialized')\n\n")

        
        # ================================================================
        # SECTION 2: UNIAXIAL MATERIALS
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 2: UNIAXIAL MATERIALS\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\nDefining uniaxial materials...')\n")
        for mat_param in material_params:
            mat_str = ", ".join([repr(p) for p in mat_param])
            f.write(f"ops.uniaxialMaterial({mat_str})\n")
        f.write(f"print(' Defined {len(material_params)} uniaxial materials')\n\n")
        
        # ================================================================
        # SECTION 3: FIBER SECTIONS
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 3: FIBER SECTIONS\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\nCreating fiber sections...')\n")
        for fiber_sec in fiber_section_info:
            # Read fiber section commands from saved file
            with open(fiber_sec['txt_path'], 'r') as sec_file:
                sec_commands = sec_file.read()
            
            # Write the section commands
            f.write(f"\n# Fiber Section {fiber_sec['sec_tag']}\n")
            f.write(sec_commands)
            f.write("\n")
        
        f.write(f"print(' Created {len(fiber_section_info)} fiber sections')\n\n")
        
        # ================================================================
        # SECTION 4: NODES
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 4: NODES\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\nCreating nodes...')\n\n")
        
        # Frame nodes
        f.write("# Frame nodes\n")
        for node_id, coords in sorted(node_coords.items()):
            x, y, z = coords
            f.write(f"ops.node({node_id}, {x}, {y}, {z})\n")
        
        f.write(f"\n# Created {len(node_coords)} frame nodes\n\n")
        
        # Shell nodes
        if shell_meshes:
            f.write("# Shell mesh nodes\n")
            total_shell_nodes = 0
            for shell_mesh in shell_meshes:
                config_name = shell_mesh.get('config_name', 'Unknown')
                f.write(f"\n# Nodes for {config_name}\n")
                
                for node_id, coords in sorted(shell_mesh['nodes'].items()):
                    x, y, z = coords
                    f.write(f"ops.node({node_id}, {x}, {y}, {z})\n")
                
                total_shell_nodes += len(shell_mesh['nodes'])
            
            f.write(f"\n# Created {total_shell_nodes} shell nodes\n\n")
        
        f.write(f"print(' Created {len(node_coords) + total_shell_nodes} total nodes')\n\n")
        
        # ================================================================
        # SECTION 5: BOUNDARY CONDITIONS
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 5: BOUNDARY CONDITIONS\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\nApplying boundary conditions...')\n\n")
        
        for node_id, dofs in sorted(boundary_conditions.items()):
            dof_str = ", ".join([str(d) for d in dofs])
            f.write(f"ops.fix({node_id}, {dof_str})\n")
        
        f.write(f"\nprint(' Applied boundary conditions to {len(boundary_conditions)} nodes')\n\n")
        
        # ================================================================
        # SECTION 6: GEOMETRIC TRANSFORMATIONS
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 6: GEOMETRIC TRANSFORMATIONS\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\nDefining geometric transformations...')\n\n")
        
        for transf in element_configs.get('transformations', []):
            vecxz_str = ", ".join([str(v) for v in transf['vecxz']])
            f.write(f"ops.geomTransf('{transf['type']}', {transf['tag']}, {vecxz_str})\n")
        
        f.write(f"\nprint(' Created {len(element_configs.get('transformations', []))} transformations')\n\n")
        
        # ================================================================
        # SECTION 7: BEAM INTEGRATIONS
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 7: BEAM INTEGRATIONS\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\nDefining beam integrations...')\n\n")
        
        for integ in element_configs.get('integrations', []):
            f.write(f"ops.beamIntegration('{integ['type']}', {integ['tag']}, "
                   f"{integ['sec_tag']}, {integ['np']})\n")
        
        f.write(f"\nprint(' Created {len(element_configs.get('integrations', []))} integrations')\n\n")
        
        # ================================================================
        # SECTION 8: ELASTIC SECTIONS
        # ================================================================
        if element_configs.get('elastic_sections'):
            f.write("# " + "="*70 + "\n")
            f.write("# SECTION 8: ELASTIC SECTIONS\n")
            f.write("# " + "="*70 + "\n\n")
            
            f.write("print('\\nDefining elastic sections...')\n\n")
            
            for elastic_sec in element_configs.get('elastic_sections', []):
                f.write(f"ops.section('Elastic', {elastic_sec['sec_tag']}, "
                       f"{elastic_sec['E']}, {elastic_sec['A']}, "
                       f"{elastic_sec['Iz']}, {elastic_sec['Iy']}, "
                       f"{elastic_sec['G']}, {elastic_sec['J']})\n")
            
            f.write(f"\nprint(' Created {len(element_configs.get('elastic_sections', []))} elastic sections')\n\n")
        
        # ================================================================
        # SECTION 9: BEAM/COLUMN ELEMENTS
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# SECTION 9: BEAM/COLUMN ELEMENTS\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\nCreating beam/column elements...')\n\n")
        
        # Force beam columns (fiber sections)
        f.write("# Force beam columns (fiber sections)\n")
        for col in element_configs.get('force_beam_columns', []):
            f.write(f"ops.element('forceBeamColumn', {col['tag']}, "
                   f"{col['node_i']}, {col['node_j']}, "
                   f"{col['transf_tag']}, {col['integ_tag']})\n")
        
        col_count = len(element_configs.get('force_beam_columns', []))
        f.write(f"\n# Created {col_count} fiber section columns\n\n")
        
        # Elastic beam columns
        f.write("# Elastic beam columns\n")
        for beam in element_configs.get('elastic_beam_columns', []):
            f.write(f"ops.element('elasticBeamColumn', {beam['tag']}, "
                   f"{beam['node_i']}, {beam['node_j']}, "
                   f"{beam['A']}, {beam['E']}, {beam['G']}, {beam['J']}, "
                   f"{beam['Iy']}, {beam['Iz']}, {beam['transf_tag']})\n")
        
        beam_count = len(element_configs.get('elastic_beam_columns', []))
        f.write(f"\n# Created {beam_count} elastic beams\n")
        f.write(f"\nprint(' Created {col_count + beam_count} beam/column elements')\n\n")
        
        # ================================================================
        # SECTION 10: SHELL ELEMENTS
        # ================================================================
        if shell_meshes:
            f.write("# " + "="*70 + "\n")
            f.write("# SECTION 10: SHELL ELEMENTS\n")
            f.write("# " + "="*70 + "\n\n")
            
            f.write("print('\\nCreating shell elements...')\n\n")
            
            total_shell_elements = 0
            
            for shell_mesh in shell_meshes:
                config_name = shell_mesh.get('config_name', 'Unknown')
                
                # Find matching config
                shell_mat_config = None
                shell_sec_config = None
                
                for config in slab_configs:
                    if config.get('name') == config_name:
                        shell_mat_config = config['shell_material_config']
                        shell_sec_config = config['shell_section_config']
                        break
                
                if shell_mat_config is None or shell_sec_config is None:
                    continue
                
                # Write material and section
                f.write(f"# Shell material and section for {config_name}\n")
                
                mat_str = ", ".join([repr(p) for p in shell_mat_config])
                f.write(f"ops.nDMaterial({mat_str})\n")
                
                sec_str = ", ".join([repr(p) for p in shell_sec_config])
                f.write(f"ops.section({sec_str})\n\n")
                
                sec_tag = shell_sec_config[1]
                
                # Write quad4 elements
                f.write(f"# Quad4 elements for {config_name}\n")
                for elem in shell_mesh['quad4']:
                    node_str = ", ".join([str(n) for n in elem['nodes']])
                    f.write(f"ops.element('ShellMITC4', {elem['tag']}, {node_str}, {sec_tag})\n")
                
                # Write tri3 elements
                if shell_mesh['tri3']:
                    f.write(f"\n# Tri3 elements for {config_name}\n")
                    for elem in shell_mesh['tri3']:
                        node_str = ", ".join([str(n) for n in elem['nodes']])
                        f.write(f"ops.element('ASDShellT3', {elem['tag']}, {node_str}, {sec_tag})\n")
                
                elem_count = len(shell_mesh['quad4']) + len(shell_mesh['tri3'])
                total_shell_elements += elem_count
                f.write(f"\n# Created {elem_count} elements for {config_name}\n\n")
            
            f.write(f"print(' Created {total_shell_elements} shell elements')\n\n")
        
        # ================================================================
        # SECTION 11: ZERO-LENGTH SPRINGS
        # ================================================================
        if nodal_spring_configs:
            f.write("# " + "="*70 + "\n")
            f.write("# SECTION 11: ZERO-LENGTH SPRINGS\n")
            f.write("# " + "="*70 + "\n\n")
            
            f.write("print('\\nCreating zero-length springs...')\n\n")
            
            # Write spring material
            mat_config = nodal_spring_configs['material_props']['config']
            mat_str = ", ".join([repr(p) for p in mat_config])
            f.write(f"# Spring material\n")
            f.write(f"ops.uniaxialMaterial({mat_str})\n\n")
            
            # Write spring nodes and elements
            mat_id = nodal_spring_configs['material_props']['id']
            directions = nodal_spring_configs['material_props']['directions']
            boundary_condition = nodal_spring_configs['boundary_condition']
            element_start_id = nodal_spring_configs['element_start_id']
            spring_node_start_id = nodal_spring_configs['spring_node_start_id']
            
            f.write("# Spring nodes and elements\n")
            
            spring_count = 0
            for i, (node_id, x, y, z) in enumerate(nodal_spring_configs['node_list']):
                spring_node_id = spring_node_start_id + i
                elem_id = element_start_id + i
                
                bc_str = ", ".join([str(d) for d in boundary_condition])
                dir_str = ", ".join([str(d) for d in directions])
                
                f.write(f"\n# Spring at node {node_id}\n")
                f.write(f"ops.node({spring_node_id}, {x}, {y}, {z})\n")
                f.write(f"ops.fix({spring_node_id}, {bc_str})\n")
                f.write(f"ops.element('zeroLength', {elem_id}, {node_id}, {spring_node_id}, "
                       f"'-mat', {mat_id}, '-dir', {dir_str})\n")
                
                spring_count += 1
            
            f.write(f"\nprint(' Created {spring_count} zero-length springs')\n\n")
        
        # ================================================================
        # SECTION 12: LOADS
        # ================================================================
        if load_configs:
            f.write("# " + "="*70 + "\n")
            f.write("# SECTION 12: LOADS\n")
            f.write("# " + "="*70 + "\n\n")
            
            f.write("print('\\nApplying loads...')\n\n")
            
            # Time series
            if 'time_series' in load_configs:
                f.write("# Time series\n")
                for ts in load_configs['time_series']:
                    if ts['type'] == 'Linear':
                        f.write(f"ops.timeSeries('Linear', {ts['tag']})\n")
                    elif ts['type'] == 'Constant':
                        f.write(f"ops.timeSeries('Constant', {ts['tag']})\n")
                f.write("\n")
            
            # Patterns
            if 'patterns' in load_configs:
                f.write("# Load patterns\n")
                for pattern in load_configs['patterns']:
                    f.write(f"ops.pattern('Plain', {pattern['tag']}, {pattern['ts_tag']})\n")
                f.write("\n")
            
            # Nodal loads
            if 'nodal_loads' in load_configs:
                f.write("# Nodal loads\n")
                for load_group in load_configs['nodal_loads']:
                    for load in load_group['loads']:
                        force_str = ", ".join([str(f) for f in load['forces']])
                        f.write(f"ops.load({load['node']}, {force_str})\n")
                f.write("\n")
            
            # Beam uniform loads
            if 'beam_uniform_loads' in load_configs:
                f.write("# Beam uniform loads\n")
                for load_group in load_configs['beam_uniform_loads']:
                    for load in load_group['loads']:
                        elem_str = str(load['elements'])
                        f.write(f"opst.pre.transform_beam_uniform_load({elem_str}, "
                               f"wy={load['wy']}, wz={load['wz']})\n")
                f.write("\n")
            
            # Beam point loads
            if 'beam_point_loads' in load_configs:
                f.write("# Beam point loads\n")
                for load_group in load_configs['beam_point_loads']:
                    for load in load_group['loads']:
                        f.write(f"opst.pre.transform_beam_point_load([{load['element']}], "
                               f"py={load['py']}, pz={load['pz']}, xl={load['xl']})\n")
                f.write("\n")
            
            # Shell surface loads
            if 'shell_surface_loads' in load_configs:
                f.write("# Shell surface loads\n")
                for load_group in load_configs['shell_surface_loads']:
                    for load in load_group['loads']:
                        # Find mesh
                        for shell_mesh in shell_meshes:
                            if shell_mesh.get('config_name') == load['mesh_name']:
                                if load['elements'] is None:
                                    element_tags = [elem['tag'] for elem in shell_mesh['quad4']]
                                    element_tags += [elem['tag'] for elem in shell_mesh['tri3']]
                                else:
                                    element_tags = load['elements']
                                
                                f.write(f"# Surface load on {load['mesh_name']}\n")
                                f.write(f"opst.pre.transform_surface_uniform_load("
                                       f"ele_tags={element_tags}, p={load['pressure']})\n")
                                break
                f.write("\n")
            
            f.write("print(' Loads applied')\n\n")
        
        # ================================================================
        # SECTION 13: MASSES
        # ================================================================
        if mass_configs:
            f.write("# " + "="*70 + "\n")
            f.write("# SECTION 13: MASSES\n")
            f.write("# " + "="*70 + "\n\n")
            
            f.write("print('\\nApplying masses...')\n\n")
            
            # Initialize mass dictionary
            f.write("# Initialize nodal masses\n")
            f.write("nodal_masses = {}\n\n")
            
            # Beam/column masses
            if 'beam_column_mass' in mass_configs:
                f.write("# Beam/column masses\n")
                f.write("node_coords = {\n")
                for node_id, coords in sorted(node_coords.items()):
                    f.write(f"    {node_id}: {coords},\n")
                f.write("}\n\n")
                
                for item in mass_configs['beam_column_mass']:
                    tag = item['tag']
                    density = item['density']
                    area = item['area']
                    
                    # Find nodes (simplified - assumes user knows node_i, node_j)
                    f.write(f"\n# Element {tag}\n")
                    f.write(f"# Calculate and add mass for element {tag}\n")
                    f.write(f"# density={density}, area={area}\n")
                
                f.write("\n")
            
            # Nodal masses
            if 'nodal_mass' in mass_configs:
                f.write("# Direct nodal masses\n")
                for item in mass_configs['nodal_mass']:
                    node_id = item['node']
                    mass_value = item['mass']
                    f.write(f"if {node_id} not in nodal_masses:\n")
                    f.write(f"    nodal_masses[{node_id}] = 0.0\n")
                    f.write(f"nodal_masses[{node_id}] += {mass_value}\n")
                f.write("\n")
            
            # Apply masses
            f.write("# Apply masses to OpenSees model\n")
            f.write("for node_id, mass_value in nodal_masses.items():\n")
            f.write("    if mass_value > 0:\n")
            f.write("        ops.mass(node_id, mass_value, mass_value, mass_value, 0.0, 0.0, 0.0)\n\n")
            
            f.write("print(' Masses applied')\n\n")
        
        # ================================================================
        # FOOTER
        # ================================================================
        f.write("# " + "="*70 + "\n")
        f.write("# MODEL CREATION COMPLETE\n")
        f.write("# " + "="*70 + "\n\n")
        
        f.write("print('\\n' + '='*70)\n")
        f.write("print('MODEL CREATION COMPLETE')\n")
        f.write("print('='*70)\n")
        f.write("print(f'Total nodes: {len(ops.getNodeTags())}')\n")
        f.write("print(f'Total elements: {len(ops.getEleTags())}')\n")
        f.write("print('='*70)\n")
    
    print(f"\n{'='*70}")
    print(f"COMPLETE MODEL FILE GENERATED")
    print(f"{'='*70}")
    print(f"File saved to: {output_filepath}")
    print(f"{'='*70}\n")


def create_regular_polygon_nodes(center_x, center_y, radius, n_sides, start_id, z=0.0):
    """Create regular polygon nodes dictionary"""
    angles = np.linspace(0, 2*np.pi, n_sides + 1)[:-1]
    nodes = {}
    for i, angle in enumerate(angles):
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        nodes[start_id + i] = (x, y, z)
    return nodes


