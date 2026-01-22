"""
Minimal Dynamic GMSH Mesh Generator
Clean implementation with no defaults - all parameters required
"""

import os
import pickle
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
import gmsh

import openseespy.opensees as ops
import opstool as opst
import opstool.vis.pyvista as opsvis
import opstool.vis.plotly as opsvis_plotly


"""
Shell Design Helper Functions
"""

import numpy as np


def create_regular_polygon_nodes(center_x, center_y, radius, n_sides, start_id, z=0.0):
    """
    Create regular polygon nodes dictionary
    
    Parameters
    ----------
    center_x : float
        X coordinate of center
    center_y : float
        Y coordinate of center
    radius : float
        Radius of polygon
    n_sides : int
        Number of sides
    start_id : int
        Starting node ID
    z : float
        Z coordinate (elevation)
    
    Returns
    -------
    dict
        Node dictionary {node_id: (x, y, z)}
    """
    angles = np.linspace(0, 2*np.pi, n_sides + 1)[:-1]
    nodes = {}
    for i, angle in enumerate(angles):
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        nodes[start_id + i] = (x, y, z)
    return nodes

def generate_mesh(boundary_nodes, mesh_size, internal_points, voids,
                  py_file, png_file, material_E, material_nu, material_rho,
                  thickness, node_font_size, element_font_size, 
                  start_node_id, start_element_id):
    """Generate mesh with boundary nodes, internal points, and voids"""
    
    gmsh.initialize()
    gmsh.model.add("mesh")
    
    # Sort boundary nodes by angle
    coords = np.array([boundary_nodes[nid] for nid in sorted(boundary_nodes.keys())])
    center = coords.mean(axis=0)
    angles = np.arctan2(coords[:, 1] - center[1], coords[:, 0] - center[0])
    sorted_indices = np.argsort(angles)
    sorted_ids = [sorted(boundary_nodes.keys())[i] for i in sorted_indices]
    
    # Create boundary
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
        for void_nodes in voids:
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
        for node_id, coord in internal_points.items():
            x, y, z = coord
            pt = gmsh.model.geo.addPoint(x, y, z, mesh_size)
            gmsh.model.geo.synchronize()
            try:
                gmsh.model.mesh.embed(0, [pt], 2, surface)
            except:
                pass
    
    # Generate mesh
    gmsh.option.setNumber("Mesh.Algorithm", 6)
    gmsh.option.setNumber("Mesh.RecombineAll", 1)
    gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size * 2)
    
    try:
        gmsh.model.mesh.generate(2)
    except:
        gmsh.model.mesh.clear()
        gmsh.option.setNumber("Mesh.Algorithm", 5)
        gmsh.option.setNumber("Mesh.RecombineAll", 0)
        gmsh.model.mesh.generate(2)
    
    # Extract mesh
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    temp_nodes = {}
    for i, tag in enumerate(node_tags):
        temp_nodes[int(tag)] = (node_coords[3*i], node_coords[3*i+1], node_coords[3*i+2])

    quad4_elems = []
    tri3_elems = []

    for elem_type in gmsh.model.mesh.getElementTypes(dim=2):
        elem_tags, elem_nodes = gmsh.model.mesh.getElementsByType(elem_type)
        
        if elem_type == 3:
            for i, tag in enumerate(elem_tags):
                nodes = [int(elem_nodes[i*4 + j]) for j in range(4)]
                quad4_elems.append({'tag': int(tag), 'nodes': nodes})
        elif elem_type == 2:
            for i, tag in enumerate(elem_tags):
                nodes = [int(elem_nodes[i*3 + j]) for j in range(3)]
                tri3_elems.append({'tag': int(tag), 'nodes': nodes})
    
    gmsh.finalize()
    
    # Node mapping - preserve special IDs
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
    
    # Match internal points - keep original IDs
    matched_internal = {}
    if internal_points:
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
                node_map[best] = int_id
                final_nodes[int_id] = int_coord
                used_ids.add(int_id)
                matched_internal[int_id] = int_id
    
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
    
    # Visualization
    fig, ax = plt.subplots(figsize=(14, 12))
    
    for elem in final_quad4:
        coords = np.array([final_nodes[n][:2] for n in elem['nodes']])
        ax.fill(coords[:, 0], coords[:, 1], fc='cyan', ec='blue', alpha=0.3, lw=1)
    for elem in final_tri3:
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
    
    title = f'{len(final_nodes)} nodes, {len(final_quad4)} quad4, {len(final_tri3)} tri3'
    if int_ids:
        title += f', {len(int_ids)} internal'
    ax.set_title(title, fontsize=14, weight='bold')
    ax.legend()
    ax.axis('equal')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_file, dpi=200)
    plt.close()
    
    print(f"Mesh: {len(final_nodes)} nodes, {len(final_quad4)} quad4, {len(final_tri3)} tri3")
    
    return {
        'nodes': final_nodes,
        'quad4': final_quad4,
        'tri3': final_tri3,
        'voids': voids if voids else [],
        'internal_points': matched_internal
    }


def create_spring(spring_config):
    import openseespy.opensees as ops
    
    results = []
    
    for config in spring_config:
        node1_tuple = config["node1"]
        spring_id = config["spring_id"]
        direction = config["direction"]
        material_type, mat_tag, K = config["material"]
        boundary_condition = config["boundary_condition"]
        
        node1_tag, x, y, z = node1_tuple
        spring_node = 100000 + spring_id
        
        ops.node(spring_node, x, y, z)
        ops.fix(spring_node, *boundary_condition)
        
        ops.uniaxialMaterial(material_type, mat_tag, K)
        ops.element("zeroLength", spring_id,
                    node1_tag, spring_node,
                    "-mat", mat_tag, "-dir", direction)
        
        results.append({"spring_id": spring_id, 
                       "spring_node": spring_node, 
                       "material_id": mat_tag})
    
    return results




def create_slab(slab_configs):
    """Create multiple slabs with mesh, springs, loads, masses, boundary conditions"""
    
    all_meshes = []
    all_springs = []
    all_file_paths = {}
    all_ops_commands = []  # NEW: Initialize command list
    
    for config in slab_configs:
        slab_name = config['name']
        
        # Extract material properties
        material_E = config['shell_material_config'][2]
        material_nu = config['shell_material_config'][3]
        material_rho = config['shell_material_config'][4]
        thickness = config['shell_section_config'][3]
        
        # Generate mesh
        mesh = generate_mesh(
            boundary_nodes=config['boundary_nodes'],
            mesh_size=config['mesh_size'],
            internal_points=config.get('internal_points'),
            voids=config.get('voids'),
            py_file=config['py_file'],
            png_file=config['png_file'],
            material_E=material_E,
            material_nu=material_nu,
            material_rho=material_rho,
            thickness=thickness,
            node_font_size=config['node_font_size'],
            element_font_size=config['element_font_size'],
            start_node_id=config['start_node_id'],
            start_element_id=config['start_element_id']
        )
        
        mesh['config_name'] = slab_name
        all_meshes.append(mesh)
        all_file_paths[slab_name] = {'py_file': config['py_file'], 'png_file': config['png_file']}
        
        # Track all nodes and elements
        all_node_ids = list(mesh['nodes'].keys())
        quad4_element_tags = [elem['tag'] for elem in mesh['quad4']]
        tri3_element_tags = [elem['tag'] for elem in mesh['tri3']]
        
        # Create OpenSees nodes
        # node_coords = {}
        # for node_id, coords in mesh['nodes'].items():
        #     ops.node(node_id, *coords)
        #     all_ops_commands.append(f"ops.node({node_id}, {coords[0]}, {coords[1]}, {coords[2]})")  # NEW
        #     node_coords[node_id] = coords
        # Create OpenSees nodes (skip if already exist)
        node_coords = {}
        existing_nodes = set(ops.getNodeTags())
        for node_id, coords in mesh['nodes'].items():
            if node_id not in existing_nodes:
                ops.node(node_id, *coords)
                all_ops_commands.append(f"ops.node({node_id}, {coords[0]}, {coords[1]}, {coords[2]})")
            node_coords[node_id] = coords
        
        # Apply boundary conditions to ALL nodes
        if config.get('shell_boundary_conditions'):
            bc_dofs = config['shell_boundary_conditions']
            for node_id in all_node_ids:
                ops.fix(node_id, *bc_dofs)
                all_ops_commands.append(f"ops.fix({node_id}, {', '.join(map(str, bc_dofs))})")  # NEW
        
        # Create springs for ALL nodes
        if config.get('spring_configs'):
            for spring_cfg in config['spring_configs']:
                spring_id_start = spring_cfg['spring_id']
                direction = spring_cfg['direction']
                material_type, mat_tag, K = spring_cfg['material']
                bc = spring_cfg['boundary_condition']
                
                spring_results = []
                for i, node_id in enumerate(all_node_ids):
                    x, y, z = mesh['nodes'][node_id]
                    spring_node_id = spring_id_start + 100000 + i
                    spring_elem_id = spring_id_start + i
                    
                    ops.node(spring_node_id, x, y, z)
                    all_ops_commands.append(f"ops.node({spring_node_id}, {x}, {y}, {z})")  # NEW
                    
                    ops.fix(spring_node_id, *bc)
                    all_ops_commands.append(f"ops.fix({spring_node_id}, {', '.join(map(str, bc))})")  # NEW
                    
                    ops.uniaxialMaterial(material_type, mat_tag + i, K)
                    all_ops_commands.append(f"ops.uniaxialMaterial('{material_type}', {mat_tag + i}, {K})")  # NEW
                    
                    ops.element("zeroLength", spring_elem_id, node_id, spring_node_id, 
                               "-mat", mat_tag + i, "-dir", direction)
                    all_ops_commands.append(f"ops.element('zeroLength', {spring_elem_id}, {node_id}, {spring_node_id}, '-mat', {mat_tag + i}, '-dir', {direction})")  # NEW
                    
                    spring_results.append({
                        'spring_id': spring_elem_id,
                        'spring_node': spring_node_id,
                        'material_id': mat_tag + i,
                        'main_node': node_id
                    })
                
                all_springs.extend(spring_results)
        
        # Create shell material and section
        mat_id = config['shell_material_config'][1]
        sec_id = config['shell_section_config'][1]
        ops.nDMaterial('ElasticIsotropic', mat_id, material_E, material_nu, material_rho)
        all_ops_commands.append(f"ops.nDMaterial('ElasticIsotropic', {mat_id}, {material_E}, {material_nu}, {material_rho})")  # NEW
        
        ops.section('PlateFiber', sec_id, mat_id, thickness)
        all_ops_commands.append(f"ops.section('PlateFiber', {sec_id}, {mat_id}, {thickness})")  # NEW
        
        # Create shell elements
        for elem in mesh['quad4']:
            ops.element(config['ops_ele_type1'], elem['tag'], *elem['nodes'], sec_id)
            all_ops_commands.append(f"ops.element('{config['ops_ele_type1']}', {elem['tag']}, {', '.join(map(str, elem['nodes']))}, {sec_id})")  # NEW
        for elem in mesh['tri3']:
            ops.element(config['ops_ele_type2'], elem['tag'], *elem['nodes'], sec_id)
            all_ops_commands.append(f"ops.element('{config['ops_ele_type2']}', {elem['tag']}, {', '.join(map(str, elem['nodes']))}, {sec_id})")  # NEW
        
        # Apply loads to tracked elements
        if config.get('load_configs'):
            load_configs = config['load_configs']
            
            if 'time_series' in load_configs:
                for ts in load_configs['time_series']:
                    ops.timeSeries(ts['type'], ts['tag'])
                    all_ops_commands.append(f"ops.timeSeries('{ts['type']}', {ts['tag']})")  # NEW
            
            if 'patterns' in load_configs:
                for pattern in load_configs['patterns']:
                    ops.pattern('Plain', pattern['tag'], pattern['ts_tag'])
                    all_ops_commands.append(f"ops.pattern('Plain', {pattern['tag']}, {pattern['ts_tag']})")  # NEW
            
            if 'nodal_loads' in load_configs:
                for load_group in load_configs['nodal_loads']:
                    for load in load_group['loads']:
                        ops.load(load['node'], *load['forces'])
                        all_ops_commands.append(f"ops.load({load['node']}, {', '.join(map(str, load['forces']))})")  # NEW
            
            if 'shell_surface_loads' in load_configs:
                for load_group in load_configs['shell_surface_loads']:
                    for load in load_group['loads']:
                        pressure = load['pressure']
                        element_tags = load.get('elements')
                        
                        if element_tags is None:
                            element_tags = quad4_element_tags + tri3_element_tags
                        
                        for etag in element_tags:
                            opst.pre.transform_surface_uniform_load(ele_tags=[etag], p=pressure)
                            all_ops_commands.append(f"opst.pre.transform_surface_uniform_load(ele_tags=[{etag}], p={pressure})")  # NEW
        
        # Apply masses to tracked elements
        if config.get('mass_configs'):
            mass_configs = config['mass_configs']
            nodal_masses = {node_id: 0.0 for node_id in all_node_ids}
            
            if 'nodal_mass' in mass_configs:
                for item in mass_configs['nodal_mass']:
                    node_id = item['node']
                    mass = item['mass']
                    if node_id in nodal_masses:
                        nodal_masses[node_id] += mass
            
            if 'shell_element_mass' in mass_configs:
                for item in mass_configs['shell_element_mass']:
                    element_tags = item.get('elements')
                    mass_per_area = item['mass_per_area']
                    
                    if element_tags is None:
                        element_tags = quad4_element_tags + tri3_element_tags
                    
                    shell_nodal_masses = _calculate_shell_mass_from_areas(
                        ele_tags=element_tags,
                        density=mass_per_area,
                        thickness=1.0,
                        opst=opst
                    )
                    
                    for node_id, shell_mass in shell_nodal_masses.items():
                        if node_id in nodal_masses:
                            nodal_masses[node_id] += shell_mass
            
            # for node_id, mass_value in nodal_masses.items():
            #     if mass_value > 0:
            #         ops.mass(node_id, mass_value, mass_value, mass_value, 0.0, 0.0, 0.0)
            #         all_ops_commands.append(f"ops.mass({node_id}, {mass_value}, {mass_value}, {mass_value}, 0.0, 0.0, 0.0)")  # NEW
    
    return {
        'meshes': all_meshes,
        'springs': all_springs,
        'file_paths': all_file_paths,
        'ops_commands': all_ops_commands  # NEW: Return commands
    }



def load_saved_section(txt_path, png_path, pkl_path, display_commands, 
                      display_image, return_section_object):
    """Load saved section files"""
    
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



def create_dynamic_composite_section(
    materials, outline_points, core_material, mesh_sizes, ops_mat_tags,
    cover_thickness, cover_material, core_holes, voids, bone_geometry,
    additional_patches, rebar_configs, steel_material, sec_tag,
    save_txt_path, save_png_path, save_pkl_path, G, section_name,
    display_results, plot_section):
    """Create dynamic composite section - all parameters required"""
    
    for name, props in materials.items():
        if 'elastic_modulus' not in props:
            raise ValueError(f"Material '{name}': 'elastic_modulus' required")
        if 'poissons_ratio' not in props:
            raise ValueError(f"Material '{name}': 'poissons_ratio' required")
        if 'density' not in props:
            raise ValueError(f"Material '{name}': 'density' required")
    
    mat_objects = {}
    for name, props in materials.items():
        mat_objects[name] = opst.pre.section.create_material(
            name=name,
            elastic_modulus=props['elastic_modulus'],
            poissons_ratio=props['poissons_ratio'],
            density=props['density'],
            yield_strength=props.get('yield_strength', 1.0),
            color=props.get('color', 'gray')
        )
    
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
    
    patch_mat_tags = {k: v for k, v in ops_mat_tags.items() if k in patches}
    SEC.set_ops_mat_tag(patch_mat_tags)
    SEC.mesh()
    
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
    
    if save_txt_path and sec_tag is not None:
        if G is None:
            raise ValueError("G value required")
        GJ = G * SEC.get_j()
        SEC.to_file(save_txt_path, secTag=sec_tag, GJ=GJ, fmt=":.6E")
        
        if save_txt_path.endswith('.py'):
            params_file = save_txt_path.replace('.py', '_params.txt')
        else:
            params_file = save_txt_path + '_params.txt'
            
        with open(params_file, 'w') as f:
            f.write(f"section_tag = {sec_tag}\n")
            f.write(f"GJ = {GJ:.6E}\n")
            f.write(f"section_name = '{section_name}'\n")
    
    if save_png_path:
        fig, ax = plt.subplots(figsize=(8, 8))
        SEC.view(fill=True, show_legend=True, ax=ax)
        ax.set_aspect("equal", "box")
        plt.tight_layout()
        plt.savefig(save_png_path, dpi=300, bbox_inches='tight')
        if not plot_section:
            plt.close(fig)
    
    if save_pkl_path:
        with open(save_pkl_path, 'wb') as f:
            pickle.dump(SEC, f)
    
    if plot_section and not save_png_path:
        SEC.view(fill=True, show_legend=True)
        plt.show()
    
    return SEC, sec_tag, save_txt_path, save_png_path, save_pkl_path, params_file


def create_fiber_section(fiber_configs):
    """
    Create and save fiber section from configuration dictionary.
    
    Parameters
    ----------
    fiber_configs : dict
        Dictionary containing all section parameters. Required keys:
        - materials, outline_points, core_material, mesh_sizes, ops_mat_tags,
          sec_tag, G, save_prefix, section_name
        Optional keys:
        - cover_thickness, cover_material, rebar_configs, steel_material,
          core_holes, voids, bone_geometry, additional_patches,
          display_results, plot_section
    
    Returns
    -------
    tuple
        (sec_id, txt_path, png_path, pkl_path, params_path)
    """
    # Extract save prefix for file paths
    save_prefix = fiber_configs['save_prefix']
    
    # Get mesh sizes - handle both simple and complex formats
    mesh_sizes = fiber_configs['mesh_sizes']
    if isinstance(mesh_sizes, (int, float)):
        # Simple format: single mesh size for cover and core
        mesh_dict = {'cover': mesh_sizes, 'core': mesh_sizes}
    elif isinstance(mesh_sizes, dict):
        # Complex format: dictionary with all patch mesh sizes
        mesh_dict = mesh_sizes
    else:
        raise ValueError("mesh_sizes must be a number or dictionary")
    
    SEC, sec_id, txt_path, png_path, pkl_path, params_path = create_dynamic_composite_section(
        materials=fiber_configs['materials'],
        outline_points=fiber_configs['outline_points'],
        cover_thickness=fiber_configs.get('cover_thickness'),
        cover_material=fiber_configs.get('cover_material', 'concrete_cover'),
        core_material=fiber_configs['core_material'],
        mesh_sizes=mesh_dict,
        ops_mat_tags=fiber_configs['ops_mat_tags'],
        rebar_configs=fiber_configs.get('rebar_configs'),
        steel_material=fiber_configs.get('steel_material', 'steel_rebar'),
        sec_tag=fiber_configs['sec_tag'],
        G=fiber_configs['G'],
        save_txt_path=f'{save_prefix}_commands.py',
        save_png_path=f'{save_prefix}_figure.png',
        save_pkl_path=f'{save_prefix}_object.pkl',
        section_name=fiber_configs['section_name'],
        display_results=fiber_configs.get('display_results', False),
        plot_section=fiber_configs.get('plot_section', False),
        core_holes=fiber_configs.get('core_holes'),
        voids=fiber_configs.get('voids'),
        bone_geometry=fiber_configs.get('bone_geometry'),
        additional_patches=fiber_configs.get('additional_patches')
    )
    return sec_id, txt_path, png_path, pkl_path, params_path

def create_member_element(member_element_config):
    import openseespy.opensees as ops
    
    results = []
    
    # Create all sections
    if 'section' in member_element_config:
        print("# Sections")
        for sec_config in member_element_config['section']:
            sec_type = sec_config['type']
            sec_tag = sec_config['secTag']
            
            if sec_type == 'Elastic':
                E_mod = sec_config['E']
                A = sec_config['A']
                Iz = sec_config['Iz']
                
                # Check if 3D section
                if 'Iy' in sec_config and 'G' in sec_config and 'J' in sec_config:
                    # 3D section
                    Iy = sec_config['Iy']
                    G_mod = sec_config['G']
                    Jxx = sec_config['J']
                    alphaY = sec_config.get('alphaY', None)
                    alphaZ = sec_config.get('alphaZ', None)
                    
                    if alphaY is not None and alphaZ is not None:
                        ops.section('Elastic', sec_tag, E_mod, A, Iz, Iy, G_mod, Jxx, alphaY, alphaZ)
                        results.append(f"ops.section('Elastic', {sec_tag}, {E_mod}, {A}, {Iz}, {Iy}, {G_mod}, {Jxx}, {alphaY}, {alphaZ})")
                    elif alphaY is not None:
                        ops.section('Elastic', sec_tag, E_mod, A, Iz, Iy, G_mod, Jxx, alphaY)
                        results.append(f"ops.section('Elastic', {sec_tag}, {E_mod}, {A}, {Iz}, {Iy}, {G_mod}, {Jxx}, {alphaY})")
                    else:
                        ops.section('Elastic', sec_tag, E_mod, A, Iz, Iy, G_mod, Jxx)
                        results.append(f"ops.section('Elastic', {sec_tag}, {E_mod}, {A}, {Iz}, {Iy}, {G_mod}, {Jxx})")
                else:
                    # 2D section
                    G_mod = sec_config.get('G', None)
                    alphaY = sec_config.get('alphaY', None)
                    
                    if G_mod is not None and alphaY is not None:
                        ops.section('Elastic', sec_tag, E_mod, A, Iz, G_mod, alphaY)
                        results.append(f"ops.section('Elastic', {sec_tag}, {E_mod}, {A}, {Iz}, {G_mod}, {alphaY})")
                    elif G_mod is not None:
                        ops.section('Elastic', sec_tag, E_mod, A, Iz, G_mod)
                        results.append(f"ops.section('Elastic', {sec_tag}, {E_mod}, {A}, {Iz}, {G_mod})")
                    else:
                        ops.section('Elastic', sec_tag, E_mod, A, Iz)
                        results.append(f"ops.section('Elastic', {sec_tag}, {E_mod}, {A}, {Iz})")
                
                print(results[-1])
    
    # Create all geometric transformations
    if 'geomTransf' in member_element_config:
        print("\n# Geometric Transformations")
        for transf_config in member_element_config['geomTransf']:
            transf_type = transf_config['type']
            transf_tag = transf_config['tag']
            
            if transf_type == 'Linear':
                if 'vecxz' in transf_config:
                    ops.geomTransf('Linear', transf_tag, *transf_config['vecxz'])
                    results.append(f"ops.geomTransf('Linear', {transf_tag}, *{transf_config['vecxz']})")
                else:
                    ops.geomTransf('Linear', transf_tag)
                    results.append(f"ops.geomTransf('Linear', {transf_tag})")
            
            elif transf_type == 'PDelta':
                if 'vecxz' in transf_config:
                    ops.geomTransf('PDelta', transf_tag, *transf_config['vecxz'])
                    results.append(f"ops.geomTransf('PDelta', {transf_tag}, *{transf_config['vecxz']})")
                else:
                    ops.geomTransf('PDelta', transf_tag)
                    results.append(f"ops.geomTransf('PDelta', {transf_tag})")
            
            elif transf_type == 'Corotational':
                if 'vecxz' in transf_config:
                    ops.geomTransf('Corotational', transf_tag, *transf_config['vecxz'])
                    results.append(f"ops.geomTransf('Corotational', {transf_tag}, *{transf_config['vecxz']})")
                else:
                    ops.geomTransf('Corotational', transf_tag)
                    results.append(f"ops.geomTransf('Corotational', {transf_tag})")
            
            print(results[-1])
    
    # Create all beam integrations
    if 'beamIntegration' in member_element_config:
        print("\n# Beam Integration")
        for integ_config in member_element_config['beamIntegration']:
            integ_type = integ_config['type']
            integ_tag = integ_config['tag']
            
            if integ_type in ['Lobatto', 'Legendre', 'NewtonCotes', 'Radau', 'Trapezoidal', 'CompositeSimpson']:
                ops.beamIntegration(integ_type, integ_tag, integ_config['secTag'], integ_config['N'])
                results.append(f"ops.beamIntegration('{integ_type}', {integ_tag}, {integ_config['secTag']}, {integ_config['N']})")
            
            elif integ_type == 'UserDefined':
                ops.beamIntegration('UserDefined', integ_tag, integ_config['N'], 
                                  *integ_config['secTags'], *integ_config['locs'], *integ_config['wts'])
                results.append(f"ops.beamIntegration('UserDefined', {integ_tag}, {integ_config['N']}, *{integ_config['secTags']}, *{integ_config['locs']}, *{integ_config['wts']})")
            
            elif integ_type == 'FixedLocation':
                ops.beamIntegration('FixedLocation', integ_tag, integ_config['N'], 
                                  *integ_config['secTags'], *integ_config['locs'])
                results.append(f"ops.beamIntegration('FixedLocation', {integ_tag}, {integ_config['N']}, *{integ_config['secTags']}, *{integ_config['locs']})")
            
            elif integ_type == 'LowOrder':
                ops.beamIntegration('LowOrder', integ_tag, integ_config['N'], *integ_config['secTags'])
                results.append(f"ops.beamIntegration('LowOrder', {integ_tag}, {integ_config['N']}, *{integ_config['secTags']})")
            
            elif integ_type == 'MidDistance':
                ops.beamIntegration('MidDistance', integ_tag, integ_config['N'], 
                                  *integ_config['secTags'], *integ_config['locs'])
                results.append(f"ops.beamIntegration('MidDistance', {integ_tag}, {integ_config['N']}, *{integ_config['secTags']}, *{integ_config['locs']})")
            
            print(results[-1])
    
    # Create all elements
    if 'element' in member_element_config:
        print("\n# Elements")
        for elem_config in member_element_config['element']:
            element_type = elem_config['type']
            ele_tag = elem_config['eleTag']
            ele_nodes = elem_config['eleNodes']
            transf_tag = elem_config['transfTag']
            
            if element_type == 'elasticBeamColumn':
                if 'secTag' in elem_config:
                    ops.element('elasticBeamColumn', ele_tag, *ele_nodes, elem_config['secTag'], transf_tag)
                    results.append(f"ops.element('elasticBeamColumn', {ele_tag}, *{ele_nodes}, {elem_config['secTag']}, {transf_tag})")
                else:
                    if 'G' in elem_config:
                        ops.element('elasticBeamColumn', ele_tag, *ele_nodes,
                                   elem_config['Area'], elem_config['E'], elem_config['G'],
                                   elem_config['J'], elem_config['Iy'], elem_config['Iz'], transf_tag)
                        results.append(f"ops.element('elasticBeamColumn', {ele_tag}, *{ele_nodes}, {elem_config['Area']}, {elem_config['E']}, {elem_config['G']}, {elem_config['J']}, {elem_config['Iy']}, {elem_config['Iz']}, {transf_tag})")
                    else:
                        ops.element('elasticBeamColumn', ele_tag, *ele_nodes,
                                   elem_config['Area'], elem_config['E'], elem_config['Iz'], transf_tag)
                        results.append(f"ops.element('elasticBeamColumn', {ele_tag}, *{ele_nodes}, {elem_config['Area']}, {elem_config['E']}, {elem_config['Iz']}, {transf_tag})")
            
            elif element_type == 'ModElasticBeam2d':
                ops.element('ModElasticBeam2d', ele_tag, *ele_nodes,
                           elem_config['Area'], elem_config['E'], elem_config['Iz'],
                           elem_config['K11'], elem_config['K33'], elem_config['K44'], transf_tag)
                results.append(f"ops.element('ModElasticBeam2d', {ele_tag}, *{ele_nodes}, {elem_config['Area']}, {elem_config['E']}, {elem_config['Iz']}, {elem_config['K11']}, {elem_config['K33']}, {elem_config['K44']}, {transf_tag})")
            
            elif element_type == 'ElasticTimoshenkoBeam':
                if 'Avz' in elem_config:
                    ops.element('ElasticTimoshenkoBeam', ele_tag, *ele_nodes,
                               elem_config['E'], elem_config['G'], elem_config['Area'],
                               elem_config['J'], elem_config['Iy'], elem_config['Iz'],
                               elem_config['Avy'], elem_config['Avz'], transf_tag)
                    results.append(f"ops.element('ElasticTimoshenkoBeam', {ele_tag}, *{ele_nodes}, {elem_config['E']}, {elem_config['G']}, {elem_config['Area']}, {elem_config['J']}, {elem_config['Iy']}, {elem_config['Iz']}, {elem_config['Avy']}, {elem_config['Avz']}, {transf_tag})")
                else:
                    ops.element('ElasticTimoshenkoBeam', ele_tag, *ele_nodes,
                               elem_config['E'], elem_config['G'], elem_config['Area'],
                               elem_config['Iz'], elem_config['Avy'], transf_tag)
                    results.append(f"ops.element('ElasticTimoshenkoBeam', {ele_tag}, *{ele_nodes}, {elem_config['E']}, {elem_config['G']}, {elem_config['Area']}, {elem_config['Iz']}, {elem_config['Avy']}, {transf_tag})")
            
            elif element_type == 'dispBeamColumn':
                ops.element('dispBeamColumn', ele_tag, *ele_nodes, transf_tag, elem_config['integrationTag'])
                results.append(f"ops.element('dispBeamColumn', {ele_tag}, *{ele_nodes}, {transf_tag}, {elem_config['integrationTag']})")
            
            elif element_type == 'forceBeamColumn':
                ops.element('forceBeamColumn', ele_tag, *ele_nodes, transf_tag, elem_config['integrationTag'])
                results.append(f"ops.element('forceBeamColumn', {ele_tag}, *{ele_nodes}, {transf_tag}, {elem_config['integrationTag']})")
            
            elif element_type == 'nonlinearBeamColumn':
                ops.element('nonlinearBeamColumn', ele_tag, *ele_nodes,
                           elem_config['numIntgrPts'], elem_config['secTag'], transf_tag)
                results.append(f"ops.element('nonlinearBeamColumn', {ele_tag}, *{ele_nodes}, {elem_config['numIntgrPts']}, {elem_config['secTag']}, {transf_tag})")
            
            print(results[-1])
    
    return results


def apply_boundary_conditions(boundary_conditions):
    """Apply boundary conditions"""
    for node_id, dofs in boundary_conditions.items():
        ops.fix(node_id, *dofs)


def apply_loads_and_masses(load_configs, mass_configs, shell_meshes, 
                           slab_configs, element_configs, node_coords):
    
    if load_configs is None and mass_configs is None:
        raise ValueError("Both load_configs and mass_configs are None")
    
    if element_configs is None:
        raise ValueError("element_configs required")
    
    if node_coords is None:
        raise ValueError("node_coords required")
    
    import opstool as opst
    from collections import defaultdict  # ✅ ADD THIS IMPORT
    
    results = {
        'nodal_masses': {},
        'load_summary': {},
        'mass_summary': {},
        'load_commands': [],
        'mass_commands': []
    }
    
    if load_configs is not None:
        print("\nApplying loads...")
        
        if 'time_series' in load_configs:
            for ts in load_configs['time_series']:
                tag = ts['tag']
                ts_type = ts['type']
                
                if ts_type == 'Linear':
                    ops.timeSeries('Linear', tag)
                    results['load_commands'].append(f"ops.timeSeries('Linear', {tag})")
                elif ts_type == 'Constant':
                    ops.timeSeries('Constant', tag)
                    results['load_commands'].append(f"ops.timeSeries('Constant', {tag})")
                elif ts_type == 'Trig':
                    ops.timeSeries('Trig', tag, ts['tStart'], ts['tEnd'], ts['period'])
                    results['load_commands'].append(f"ops.timeSeries('Trig', {tag}, {ts['tStart']}, {ts['tEnd']}, {ts['period']})")
            
            results['load_summary']['time_series'] = len(load_configs['time_series'])
        
        if 'patterns' in load_configs:
            for pattern in load_configs['patterns']:
                ops.pattern('Plain', pattern['tag'], pattern['ts_tag'])
                results['load_commands'].append(f"ops.pattern('Plain', {pattern['tag']}, {pattern['ts_tag']})")
            
            results['load_summary']['patterns'] = len(load_configs['patterns'])
        
        if 'nodal_loads' in load_configs:
            # ACCUMULATE loads first, then apply once
            accumulated_loads = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            
            for load_group in load_configs['nodal_loads']:
                for load in load_group['loads']:
                    node_id = load['node']
                    forces = load['forces']
                    for i in range(6):
                        accumulated_loads[node_id][i] += forces[i]
            
            # Now apply accumulated loads
            total_nodal_loads = 0
            for node_id, forces in accumulated_loads.items():
                ops.load(node_id, *forces)
                forces_str = ', '.join(map(str, forces))
                results['load_commands'].append(f"ops.load({node_id}, {forces_str})")
                total_nodal_loads += 1
            
            results['load_summary']['nodal_loads'] = total_nodal_loads
        
        if 'beam_uniform_loads' in load_configs:
            total_beam_uniform = 0
            for load_group in load_configs['beam_uniform_loads']:
                for load in load_group['loads']:
                    opst.pre.transform_beam_uniform_load(load['elements'], 
                                                        wy=load['wy'], 
                                                        wz=load['wz'])
                    results['load_commands'].append(f"opst.pre.transform_beam_uniform_load({load['elements']}, wy={load['wy']}, wz={load['wz']})")
                    total_beam_uniform += len(load['elements'])
            
            results['load_summary']['beam_uniform_loads'] = total_beam_uniform
        
        if 'beam_point_loads' in load_configs:
            total_beam_point = 0
            for load_group in load_configs['beam_point_loads']:
                for load in load_group['loads']:
                    opst.pre.transform_beam_point_load([load['element']], 
                                                       py=load['py'], 
                                                       pz=load['pz'], 
                                                       xl=load['xl'])
                    results['load_commands'].append(f"opst.pre.transform_beam_point_load([{load['element']}], py={load['py']}, pz={load['pz']}, xl={load['xl']})")
                    total_beam_point += 1
            
            results['load_summary']['beam_point_loads'] = total_beam_point
        
        if 'shell_surface_loads' in load_configs:
            if not shell_meshes:
                raise ValueError("shell_meshes required for shell_surface_loads")
            
            total_shell_loads = 0
            for load_group in load_configs['shell_surface_loads']:
                for load in load_group['loads']:
                    mesh_name = load['mesh_name']
                    pressure = load['pressure']
                    specific_elements = load['elements']
                    
                    target_mesh = None
                    for mesh in shell_meshes:
                        if mesh.get('config_name') == mesh_name:
                            target_mesh = mesh
                            break
                    
                    if target_mesh is None:
                        raise ValueError(f"Mesh '{mesh_name}' not found")
                    
                    if specific_elements is None:
                        element_tags = [elem['tag'] for elem in target_mesh['quad4']]
                        element_tags += [elem['tag'] for elem in target_mesh['tri3']]
                    else:
                        element_tags = specific_elements
                    
                    opst.pre.transform_surface_uniform_load(ele_tags=element_tags, p=pressure)
                    results['load_commands'].append(f"opst.pre.transform_surface_uniform_load(ele_tags={element_tags}, p={pressure})")
                    total_shell_loads += len(element_tags)
            
            results['load_summary']['shell_surface_loads'] = total_shell_loads
        
        print("Loads applied")
    
    if mass_configs is not None:
        print("\nApplying masses...")
        
        nodal_masses = {node_id: 0.0 for node_id in node_coords.keys()}
        
        if shell_meshes:
            for shell_mesh in shell_meshes:
                for node_id in shell_mesh['nodes'].keys():
                    if node_id not in nodal_masses:
                        nodal_masses[node_id] = 0.0
        
        if 'beam_column_mass' in mass_configs:
            beam_col_mass_applied = 0
            
            for item in mass_configs['beam_column_mass']:
                tag = item['tag']
                density = item['density']
                area = item['area']
                
                element_found = False
                node_i, node_j = None, None
                
                # Find element nodes from element_configs['element']
                ele_nodes = None
                if 'element' in element_configs:
                    for elem_config in element_configs['element']:
                        if elem_config['eleTag'] == tag:
                            ele_nodes = elem_config['eleNodes']
                            element_found = True
                            break
                
                if ele_nodes is not None:
                    node_i, node_j = ele_nodes[0], ele_nodes[1]
                    
                
                if not element_found:
                    raise ValueError(f"Element {tag} not found")
                
                xi, yi, zi = node_coords[node_i]
                xj, yj, zj = node_coords[node_j]
                length = ((xj-xi)**2 + (yj-yi)**2 + (zj-zi)**2)**0.5
                
                mass = density * area * length
                half_mass = mass / 2.0
                
                if node_i not in nodal_masses:
                    nodal_masses[node_i] = 0.0
                if node_j not in nodal_masses:
                    nodal_masses[node_j] = 0.0
                
                nodal_masses[node_i] += half_mass
                nodal_masses[node_j] += half_mass
                
                beam_col_mass_applied += mass
            
            results['mass_summary']['beam_column_mass'] = beam_col_mass_applied
        
        if 'beam_additional_mass' in mass_configs:
            print("\nApplying additional beam masses...")
            total_beam_additional_mass = 0.0
            
            for item in mass_configs['beam_additional_mass']:
                element_tags = item['element_tags']
                mass_per_length = item['mass_per_length']
                description = item.get('description', 'Additional beam mass')
                
                for etag in element_tags:
                    node_i, node_j = None, None
                    element_found = False
                    
                    # Find element nodes from element_configs['element']
                    ele_nodes = None
                    if 'element' in element_configs:
                        for elem_config in element_configs['element']:
                            if elem_config['eleTag'] == etag:  # ✅ FIXED: 'etag' not 'tag'
                                ele_nodes = elem_config['eleNodes']
                                element_found = True
                                break
                    
                    if ele_nodes is not None:
                        node_i, node_j = ele_nodes[0], ele_nodes[1]
                    
                    if not element_found:
                        raise ValueError(f"Element {etag} not found for beam mass")
                    
                    xi, yi, zi = node_coords[node_i]
                    xj, yj, zj = node_coords[node_j]
                    length = ((xj-xi)**2 + (yj-yi)**2 + (zj-zi)**2)**0.5
                    
                    total_mass = mass_per_length * length
                    half_mass = total_mass / 2.0
                    
                    if node_i not in nodal_masses:
                        nodal_masses[node_i] = 0.0
                    if node_j not in nodal_masses:
                        nodal_masses[node_j] = 0.0
                    
                    nodal_masses[node_i] += half_mass
                    nodal_masses[node_j] += half_mass
                    
                    total_beam_additional_mass += total_mass
            
            results['mass_summary']['beam_additional_mass'] = total_beam_additional_mass
            print(f"Applied {total_beam_additional_mass:.2f} kips additional beam mass")
        
        if 'nodal_mass' in mass_configs:
            node_mass_groups = defaultdict(list)
            for item in mass_configs['nodal_mass']:
                node_mass_groups[item['node']].append(item['mass'])
            
            total_nodal_mass_applied = 0.0
            
            for node_id, mass_list in node_mass_groups.items():
                total_mass = sum(mass_list)
                
                if node_id not in nodal_masses:
                    nodal_masses[node_id] = 0.0
                
                nodal_masses[node_id] += total_mass
                total_nodal_mass_applied += total_mass
            
            results['mass_summary']['nodal_mass_total'] = total_nodal_mass_applied
        
        if 'shell_mass' in mass_configs:
            shell_config = mass_configs['shell_mass']
            
            if shell_config['calculate']:
                if not shell_meshes:
                    raise ValueError("shell_meshes required when calculate=True")
                
                if not slab_configs:
                    raise ValueError("slab_configs required when calculate=True")
                
                exclude_list = shell_config['exclude']
                scale_factor = shell_config['scale']
                
                total_shell_mass_applied = 0.0
                
                for shell_mesh in shell_meshes:
                    config_name = shell_mesh.get('config_name', 'Unknown')
                    
                    if config_name in exclude_list:
                        continue
                    
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
                    
                    shell_ele_tags = [elem['tag'] for elem in shell_mesh['quad4'] + shell_mesh['tri3']]
                    
                    shell_nodal_masses = _calculate_shell_mass_from_areas(
                        ele_tags=shell_ele_tags,
                        density=density,
                        thickness=thickness,
                        opst=opst
                    )
                    
                    mesh_total_mass = 0.0
                    for node_id, shell_mass in shell_nodal_masses.items():
                        if node_id not in nodal_masses:
                            nodal_masses[node_id] = 0.0
                        
                        nodal_masses[node_id] += shell_mass
                        mesh_total_mass += shell_mass
                    
                    total_shell_mass_applied += mesh_total_mass
                
                results['mass_summary']['shell_mass_total'] = total_shell_mass_applied

        if 'shell_additional_mass' in mass_configs:
            print("\nApplying additional shell masses...")
            
            if not shell_meshes:
                raise ValueError("shell_meshes required for shell_additional_mass")
            
            total_shell_additional_mass = 0.0
            
            for item in mass_configs['shell_additional_mass']:
                mesh_name = item['mesh_name']
                mass_per_area = item['mass_per_area']
                specific_elements = item.get('element_tags', None)
                description = item.get('description', 'Additional shell mass')
                
                target_mesh = None
                for mesh in shell_meshes:
                    if mesh.get('config_name') == mesh_name:
                        target_mesh = mesh
                        break
                
                if target_mesh is None:
                    raise ValueError(f"Mesh '{mesh_name}' not found")
                
                if specific_elements is None:
                    shell_ele_tags = [elem['tag'] for elem in target_mesh['quad4']]
                    shell_ele_tags += [elem['tag'] for elem in target_mesh['tri3']]
                else:
                    shell_ele_tags = specific_elements
                
                shell_nodal_masses = _calculate_shell_mass_from_areas(
                    ele_tags=shell_ele_tags,
                    density=mass_per_area,
                    thickness=1.0,
                    opst=opst
                )
                
                mesh_total_mass = 0.0
                for node_id, shell_mass in shell_nodal_masses.items():
                    if node_id not in nodal_masses:
                        nodal_masses[node_id] = 0.0
                    
                    nodal_masses[node_id] += shell_mass
                    mesh_total_mass += shell_mass
                
                total_shell_additional_mass += mesh_total_mass
                print(f"  {mesh_name}: {mesh_total_mass:.2f} kips ({description})")
            
            results['mass_summary']['shell_additional_mass'] = total_shell_additional_mass
            print(f"Applied {total_shell_additional_mass:.2f} kips total additional shell mass")
        
        # ACCUMULATE all mass contributions from ALL sources
        accumulated_masses = defaultdict(float)
        
        # 1. Add masses from nodal_masses dict (from beams, shells, etc)
        for node_id, mass_value in nodal_masses.items():
            accumulated_masses[node_id] += mass_value
        
        # 2. Add masses from shell meshes that were calculated in create_slab
        if shell_meshes:
            for shell_mesh in shell_meshes:
                # Get the mass config from the corresponding slab_config
                mesh_name = shell_mesh.get('config_name', 'Unknown')
                for cfg in slab_configs:
                    if cfg.get('name') == mesh_name:
                        if 'mass_configs' in cfg:
                            # Recalculate shell masses (they weren't applied in create_slab)
                            if 'shell_element_mass' in cfg['mass_configs']:
                                for item in cfg['mass_configs']['shell_element_mass']:
                                    element_tags = item.get('elements')
                                    mass_per_area = item['mass_per_area']
                                    
                                    if element_tags is None:
                                        element_tags = [elem['tag'] for elem in shell_mesh['quad4'] + shell_mesh['tri3']]
                                    
                                    # Get section config to find thickness
                                    sec_config = cfg['shell_section_config']
                                    thickness = sec_config[3]
                                    
                                    shell_nodal_masses = _calculate_shell_mass_from_areas(
                                        ele_tags=element_tags,
                                        density=mass_per_area,
                                        thickness=1.0,
                                        opst=opst
                                    )
                                    
                                    for node_id, shell_mass in shell_nodal_masses.items():
                                        accumulated_masses[node_id] += shell_mass
        
        # NOW assign all masses ONCE
        nodes_with_mass = 0
        total_mass_applied = 0.0
        
        for node_id, total_mass_value in accumulated_masses.items():
            if total_mass_value > 0:
                ops.mass(node_id, total_mass_value, total_mass_value, total_mass_value, 0.0, 0.0, 0.0)
                results['mass_commands'].append(f"ops.mass({node_id}, {total_mass_value}, {total_mass_value}, {total_mass_value}, 0.0, 0.0, 0.0)")
                nodes_with_mass += 1
                total_mass_applied += total_mass_value
        
        results['nodal_masses'] = dict(accumulated_masses)
        
        results['nodal_masses'] = nodal_masses
        results['mass_summary']['nodes_with_mass'] = nodes_with_mass
        results['mass_summary']['total_mass'] = total_mass_applied
        
        print("Masses applied")
    
    return results

def _compute_tri_area_and_normal(vertices):
    """Compute area and normal of triangle"""
    edge_ij = vertices[1] - vertices[0]
    edge_jk = vertices[2] - vertices[1]
    cross_product = np.cross(edge_ij, edge_jk)
    norm = np.linalg.norm(cross_product)
    area = 0.5 * norm
    normal = cross_product / norm
    return area, normal


def _compute_quad_area_and_normal(vertices):
    """Compute area and normal of quadrilateral"""
    triangle1 = vertices[:3]
    triangle2 = np.array([vertices[0], vertices[2], vertices[3]])
    area1, normal1 = _compute_tri_area_and_normal(triangle1)
    area2, normal2 = _compute_tri_area_and_normal(triangle2)
    normal = (normal1 + normal2) / 2.0
    return area1 + area2, normal


def _calculate_shell_mass_from_areas(ele_tags, density, thickness, opst):
    """Calculate shell element mass from areas"""
    
    ele_tags = [int(tag) for tag in ele_tags]
    nodal_masses = defaultdict(float)
    
    for etag in ele_tags:
        node_ids = ops.eleNodes(etag)
        vertices = np.array([ops.nodeCoord(node_id) for node_id in node_ids])
        
        if len(node_ids) == 3:
            area, _ = _compute_tri_area_and_normal(vertices)
        elif len(node_ids) == 4:
            area, _ = _compute_quad_area_and_normal(vertices)
        else:
            raise ValueError(f"Unsupported element with {len(node_ids)} nodes")
        
        element_mass = density * area * thickness
        mass_per_node = element_mass / len(node_ids)
        
        for node_id in node_ids:
            nodal_masses[node_id] += mass_per_node
    
    return dict(nodal_masses)


def build_model(model_params, fiber_configs, material_params,
                node_coords, boundary_conditions, element_configs,
                nodal_spring_configs, diaphragm_list,
                load_configs, mass_configs, visualize, output_dir,
                slab_configs):
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "="*80)
    print("BUILDING MODEL")
    print("="*80)
    
    complete_opensees_commands = []
    
    ops.wipe()
    ops.model("basic", "-ndm", model_params['ndm'], "-ndf", model_params['ndf'])
    complete_opensees_commands.append(f"ops.wipe()")
    complete_opensees_commands.append(f"ops.model('basic', '-ndm', {model_params['ndm']}, '-ndf', {model_params['ndf']})")
    print("Model initialized")
    
    for mat_param in material_params:
        ops.uniaxialMaterial(*mat_param)
        complete_opensees_commands.append(f"ops.uniaxialMaterial{tuple(mat_param)}")
    print("Materials defined")
    
    print("\nCreating nodes...")
    for node_id, coords in node_coords.items():
        ops.node(node_id, *coords)
        complete_opensees_commands.append(f"ops.node({node_id}, {coords[0]}, {coords[1]}, {coords[2]})")
    print(f"Created {len(node_coords)} nodes")
    
    print("\nCreating fiber sections...")
    fiber_section_info = []
    for i, fiber_config in enumerate(fiber_configs):
        
        sec_id, txt_path, png_path, pkl_path, params_path = create_fiber_section(
            fiber_configs=fiber_config
        )
        
        fiber_section_info.append({
            'sec_tag': fiber_config['sec_tag'],
            'txt_path': txt_path,
            'png_path': png_path,
            'pkl_path': pkl_path,
            'params_path': params_path,
            'GJ': fiber_config.get('G', 0.0)
        })
    print(f"Created {len(fiber_section_info)} fiber sections")
    
    print("\nCreating fiber sections in model...")
    for fiber_sec in fiber_section_info:
        commands, figure, loaded_section, loaded_sec_id, loaded_GJ, file_paths = load_saved_section(
            txt_path=fiber_sec['txt_path'],
            png_path=fiber_sec['png_path'],
            pkl_path=fiber_sec['pkl_path'],
            display_commands=False,
            display_image=False,
            return_section_object=True
        )
        
        if loaded_GJ is not None:
            fiber_sec['GJ'] = loaded_GJ
        
        exec(commands)
        
        with open(fiber_sec['txt_path'], 'r') as f:
            fiber_commands = f.read()
        complete_opensees_commands.append(f"\n# Fiber Section {fiber_sec['sec_tag']}")
        complete_opensees_commands.append(fiber_commands)
    print("Fiber sections created")
    
    print("\nCreating member elements...")
    member_results = create_member_element(element_configs)
    complete_opensees_commands.extend(member_results)
    print(f"Created {len(member_results)} member elements")
    
    shell_results = []
    all_slab_ops_commands = []
    slab_springs = []
    slab_file_paths = {}
    
    if slab_configs:
        print("\nCreating slabs...")
        slab_creation_results = create_slab(slab_configs)
        shell_results = slab_creation_results['meshes']
        all_slab_ops_commands = slab_creation_results['ops_commands']
        slab_springs = slab_creation_results['springs']
        slab_file_paths = slab_creation_results['file_paths']
        complete_opensees_commands.extend(all_slab_ops_commands)
        print(f"Created {len(shell_results)} slabs")
        print(f"Captured {len(all_slab_ops_commands)} OpenSees commands")
    
    if diaphragm_list:
        print("\nCreating rigid diaphragms...")
        for perp_dir, ret_node, *constr_nodes in diaphragm_list:
            ops.rigidDiaphragm(perp_dir, ret_node, *constr_nodes)
            complete_opensees_commands.append(f"ops.rigidDiaphragm({perp_dir}, {ret_node}, {', '.join(map(str, constr_nodes))})")
        print(f"Created {len(diaphragm_list)} diaphragms")
    
    print("\nApplying boundary conditions...")
    apply_boundary_conditions(boundary_conditions)
    for node_id, dofs in boundary_conditions.items():
        complete_opensees_commands.append(f"ops.fix({node_id}, {', '.join(map(str, dofs))})")
    print(f"Applied to {len(boundary_conditions)} nodes")
    
    if nodal_spring_configs:
        print("\nCreating support springs...")
        spring_results = create_spring(nodal_spring_configs)
        
        # Record the actual spring creation commands
        for config in nodal_spring_configs:
            node1_tuple = config["node1"]
            spring_id = config["spring_id"]
            direction = config["direction"]
            material_type, mat_tag, K = config["material"]
            boundary_condition = config["boundary_condition"]
            
            node1_tag, x, y, z = node1_tuple
            spring_node = 100000 + spring_id
            
            # Add commands to complete model
            complete_opensees_commands.append(f"ops.node({spring_node}, {x}, {y}, {z})")
            complete_opensees_commands.append(f"ops.fix({spring_node}, {', '.join(map(str, boundary_condition))})")
            complete_opensees_commands.append(f"ops.uniaxialMaterial('{material_type}', {mat_tag}, {K})")
            complete_opensees_commands.append(f"ops.element('zeroLength', {spring_id}, {node1_tag}, {spring_node}, '-mat', {mat_tag}, '-dir', {direction})")
        
        print(f"Created {len(spring_results)} springs")
    
    calculated_nodal_masses = {}
    if load_configs or mass_configs:
        results = apply_loads_and_masses(
            load_configs=load_configs,
            mass_configs=mass_configs,
            shell_meshes=shell_results,
            slab_configs=slab_configs,
            element_configs=element_configs,
            node_coords=node_coords
        )
        calculated_nodal_masses = results.get('nodal_masses', {})
        
        if 'load_commands' in results:
            complete_opensees_commands.extend(results['load_commands'])
        
        if 'mass_commands' in results:
            complete_opensees_commands.extend(results['mass_commands'])
    
    if visualize:
        print("\nCreating visualization...")
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
        print(f"Saved: {output_path}")
    
    all_node_tags = ops.getNodeTags()
    all_ele_tags = ops.getEleTags()
    
    shell_ele_count = 0
    if shell_results:
        for shell_mesh in shell_results:
            shell_ele_count += len(shell_mesh['quad4']) + len(shell_mesh['tri3'])
    
    print("\n" + "="*80)
    print("MODEL BUILD COMPLETE")
    print("="*80)
    print(f"Total Nodes: {len(all_node_tags)}")
    print(f"Total Elements: {len(all_ele_tags)}")
    print(f"  Members: {len(member_results)}")
    print(f"  Shells: {shell_ele_count}")
    print("="*80)
    
    complete_model_path = os.path.join(output_dir, "complete_opensees_model.py")
    with open(complete_model_path, 'w') as f:
        f.write("import openseespy.opensees as ops\n")
        f.write("import opstool as opst\n\n")
        f.write("import numpy as np\n")
        f.write("import matplotlib.pyplot as plt\n")

        for cmd in complete_opensees_commands:
            if cmd.strip():
                f.write(cmd + "\n")
    print(f"\nSaved complete model to: {complete_model_path}")
    
    visualization_path = os.path.join(output_dir, "complete_model.html") if visualize else None
    
    all_file_paths = {
        'fiber_sections': [
            {
                'sec_tag': f['sec_tag'],
                'txt': f['txt_path'],
                'png': f['png_path'],
                'pkl': f['pkl_path'],
                'params': f['params_path']
            } 
            for f in fiber_section_info
        ],
        'slabs': slab_file_paths,
        'complete_model': complete_model_path,
        'visualization': visualization_path
    }
    
    return {
        'fiber_sections': fiber_section_info,
        'shell_meshes': shell_results,
        'total_nodes': len(all_node_tags),
        'total_elements': len(all_ele_tags),
        'slab_ops_commands': all_slab_ops_commands,
        'slab_springs': slab_springs,
        'member_results': member_results,
        'complete_opensees_commands': complete_opensees_commands,
        'all_file_paths': all_file_paths
    }



# """
# Complete Building Model Example - FINAL FIX
# ============================================
# Fixed duplicate time series/pattern tag issue
# """

# import numpy as np
# import openseespy.opensees as ops
# import opstool as opst

# # ============================================================================
# # STEP 1: DEFINE MODEL PARAMETERS
# # ============================================================================

# model_params = {
#     'ndm': 3,
#     'ndf': 6
# }

# output_dir = './outputs100/building_model'  # Line 10 - CHANGE THIS
# import os  # ADD THIS LINE
# os.makedirs(output_dir, exist_ok=True)  # ADD THIS LINE

# # ============================================================================
# # STEP 2: DEFINE NODES
# # ============================================================================

# floor_height = 12.0  # ft
# bay_x = 20.0  # ft
# bay_y = 20.0  # ft

# node_coords = {
#     # Ground floor nodes (z=0)
#     1: (0.0, 0.0, 0.0),
#     2: (20.0, 0.0, 0.0),
#     3: (20.0, 20.0, 0.0),
#     4: (0.0, 20.0, 0.0),
    
#     # First floor nodes (z=12)
#     11: (0.0, 0.0, 12.0),
#     12: (20.0, 0.0, 12.0),
#     13: (20.0, 20.0, 12.0),
#     14: (0.0, 20.0, 12.0)
# }

# # ============================================================================
# # STEP 3: DEFINE UNIAXIAL MATERIALS
# # ============================================================================

# material_params = [
#     ('Concrete01', 1, -4.0, -0.002, -0.5, -0.005),
#     ('Concrete01', 2, -5.0, -0.002, -0.5, -0.005),
#     ('Steel02', 3, 60.0, 29000.0, 0.01, 18.0, 0.925, 0.15),
# ]

# # ============================================================================
# # STEP 4: DEFINE MATERIALS FOR FIBER SECTIONS
# # ============================================================================

# materials_col = {
#     'concrete_core': {
#         'elastic_modulus': 3600.0,
#         'poissons_ratio': 0.2,
#         'density': 0.0868,
#         'color': '#88b378'
#     },
#     'concrete_cover': {
#         'elastic_modulus': 3600.0,
#         'poissons_ratio': 0.2,
#         'density': 0.0868,
#         'color': '#dbb40c'
#     },
#     'steel_rebar': {
#         'elastic_modulus': 29000.0,
#         'poissons_ratio': 0.3,
#         'density': 0.490,
#         'yield_strength': 60.0,
#         'color': 'black'
#     }
# }

# # ============================================================================
# # STEP 5: DEFINE COLUMN FIBER SECTIONS
# # ============================================================================

# width_1 = 18.0 / 12.0
# height_1 = 18.0 / 12.0
# cover_1 = 1.5 / 12.0

# outline_points_1 = [
#     [-width_1/2, -height_1/2],
#     [width_1/2, -height_1/2],
#     [width_1/2, height_1/2],
#     [-width_1/2, height_1/2]
# ]

# rebar_configs_1 = [
#     {
#         'type': 'line',
#         'points': [[-width_1/2 + cover_1, -height_1/2 + cover_1],
#                    [width_1/2 - cover_1, -height_1/2 + cover_1]],
#         'dia': 1.0 / 12.0,
#         'n': 3,
#         'gap': None,
#         'color': 'black'
#     },
#     {
#         'type': 'line',
#         'points': [[-width_1/2 + cover_1, height_1/2 - cover_1],
#                    [width_1/2 - cover_1, height_1/2 - cover_1]],
#         'dia': 1.0 / 12.0,
#         'n': 3,
#         'gap': None,
#         'color': 'black'
#     },
#     {
#         'type': 'line',
#         'points': [[-width_1/2 + cover_1, -height_1/2 + cover_1],
#                    [-width_1/2 + cover_1, height_1/2 - cover_1]],
#         'dia': 1.0 / 12.0,
#         'n': 2,
#         'gap': None,
#         'color': 'black'
#     },
#     {
#         'type': 'line',
#         'points': [[width_1/2 - cover_1, -height_1/2 + cover_1],
#                    [width_1/2 - cover_1, height_1/2 - cover_1]],
#         'dia': 1.0 / 12.0,
#         'n': 2,
#         'gap': None,
#         'color': 'black'
#     }
# ]

# fiber_config_1 = {
#     'materials': materials_col,
#     'outline_points': outline_points_1,
#     'core_material': 'concrete_core',
#     'mesh_sizes': 50,
#     'ops_mat_tags': {
#         'cover': 1,
#         'core': 2,
#         'rebar': 3
#     },
#     'cover_thickness': cover_1,
#     'cover_material': 'concrete_cover',
#     'rebar_configs': rebar_configs_1,
#     'steel_material': 'steel_rebar',
#     'sec_tag': 1,
#     'G': 1500.0,
#     'save_prefix': f'{output_dir}/column_18x18',
#     'section_name': 'Column_18x18',
#     'display_results': False,
#     'plot_section': False
# }

# fiber_configs = [fiber_config_1]

# # ============================================================================
# # STEP 6: DEFINE COLUMNS AND BEAMS
# # ============================================================================

# element_configs = {
#     'section': [
#         {
#             'type': 'Elastic',
#             'secTag': 10,
#             'E': 29000.0,
#             'A': 17.9 / 144.0,
#             'Iz': 800.0 / 1728.0,
#             'Iy': 40.1 / 1728.0,
#             'G': 11200.0,
#             'J': 1.24 / 1728.0
#         }
#     ],
#     'geomTransf': [
#         {'type': 'PDelta', 'tag': 1, 'vecxz': [0, 1, 0]},
#         {'type': 'Linear', 'tag': 2, 'vecxz': [0, 0, 1]}
#     ],
#     'element': [
#         # Force beam columns (fiber sections)
#         {
#             'type': 'forceBeamColumn',
#             'eleTag': 1,
#             'eleNodes': [1, 11],
#             'transfTag': 1,
#             'integrationTag': 1
#         },
#         {
#             'type': 'forceBeamColumn',
#             'eleTag': 2,
#             'eleNodes': [2, 12],
#             'transfTag': 1,
#             'integrationTag': 1
#         },
#         {
#             'type': 'forceBeamColumn',
#             'eleTag': 3,
#             'eleNodes': [3, 13],
#             'transfTag': 1,
#             'integrationTag': 1
#         },
#         {
#             'type': 'forceBeamColumn',
#             'eleTag': 4,
#             'eleNodes': [4, 14],
#             'transfTag': 1,
#             'integrationTag': 1
#         },
#         # Elastic beam columns
#         {
#             'type': 'elasticBeamColumn',
#             'eleTag': 11,
#             'eleNodes': [11, 12],
#             'transfTag': 2,
#             'Area': 17.9 / 144.0,
#             'E': 29000.0,
#             'G': 11200.0,
#             'J': 1.24 / 1728.0,
#             'Iy': 40.1 / 1728.0,
#             'Iz': 800.0 / 1728.0
#         },
#         {
#             'type': 'elasticBeamColumn',
#             'eleTag': 12,
#             'eleNodes': [12, 13],
#             'transfTag': 2,
#             'Area': 17.9 / 144.0,
#             'E': 29000.0,
#             'G': 11200.0,
#             'J': 1.24 / 1728.0,
#             'Iy': 40.1 / 1728.0,
#             'Iz': 800.0 / 1728.0
#         },
#         {
#             'type': 'elasticBeamColumn',
#             'eleTag': 13,
#             'eleNodes': [13, 14],
#             'transfTag': 2,
#             'Area': 17.9 / 144.0,
#             'E': 29000.0,
#             'G': 11200.0,
#             'J': 1.24 / 1728.0,
#             'Iy': 40.1 / 1728.0,
#             'Iz': 800.0 / 1728.0
#         },
#         {
#             'type': 'elasticBeamColumn',
#             'eleTag': 14,
#             'eleNodes': [14, 11],
#             'transfTag': 2,
#             'Area': 17.9 / 144.0,
#             'E': 29000.0,
#             'G': 11200.0,
#             'J': 1.24 / 1728.0,
#             'Iy': 40.1 / 1728.0,
#             'Iz': 800.0 / 1728.0
#         }
#     ],
#     'beamIntegration': [
#         {'type': 'Lobatto', 'tag': 1, 'secTag': 1, 'N': 5}
#     ]
# }


# # ============================================================================
# # STEP 7: DEFINE SLAB
# # ============================================================================

# slab_boundary_nodes = {
#     11: (0.0, 0.0, 12.0),      # NW column node at (0,0,12)
#     12: (20.0, 0.0, 12.0),     # NE column node at (20,0,12)
#     13: (20.0, 20.0, 12.0),    # SE column node at (20,20,12)
#     14: (0.0, 20.0, 12.0)      # SW column node at (0,20,12)
# }

# # IMPORTANT: Use unique time series and pattern tags for slab (tags 1 and 1)
# slab_boundary_nodes = {
#     11: (0.0, 0.0, 12.0),      # NW column node at (0,0,12)
#     12: (20.0, 0.0, 12.0),     # NE column node at (20,0,12)
#     13: (20.0, 20.0, 12.0),    # SE column node at (20,20,12)
#     14: (0.0, 20.0, 12.0)      # SW column node at (0,20,12)
# }

# slab_configs = [
#     {
#         'name': 'Floor_Slab',
#         'boundary_nodes': slab_boundary_nodes,
#         'mesh_size': 10.0,
#         'internal_points': None,
#         'voids': None,
#         'py_file': './outputs/building_model/floor_slab_mesh.py',
#         'png_file': './outputs/building_model/floor_slab_mesh.png',
#         'shell_material_config': ('ElasticIsotropic', 100, 3600.0, 0.2, 0.0868),
#         'shell_section_config': ('PlateFiber', 100, 'ShellMITC4', 0.6666666666666666),
#         'node_font_size': 8,
#         'element_font_size': 6,
#         'ops_ele_type1': 'ShellMITC4',
#         'ops_ele_type2': 'ShellNLDKGT',
#         'shell_boundary_conditions': None,
#         'spring_configs': None,
#         'load_configs': {
#             'time_series': [{'tag': 1, 'type': 'Linear'}],
#             'patterns': [{'tag': 1, 'ts_tag': 1}],
#             'shell_surface_loads': [{
#                 'pattern': 1,
#                 'loads': [{
#                     'pressure': -0.050,
#                     'elements': None
#                 }]
#             }],
#             'nodal_loads': [{
#                 'pattern': 1,
#                 'loads': [
#                     {'node': 11, 'forces': (0, 0, -2.0, 0, 0, 0)},  # NW column
#                     {'node': 13, 'forces': (0, 0, -2.0, 0, 0, 0)}   # SE column
#                 ]
#             }]
#         },
#         'mass_configs': {
#             'shell_element_mass': [{
#                 'mass_per_area': 0.030,
#                 'elements': None,
#                 'description': 'SDL'
#             }],
#             'nodal_mass': [
#                 {'node': 12, 'mass': 0.5},  # NE column
#                 {'node': 14, 'mass': 0.5}   # SW column
#             ]
#         },
#         'start_node_id': 100000,
#         'start_element_id': 100000
#     }
# ]

# # ============================================================================
# # STEP 8: BOUNDARY CONDITIONS
# # ============================================================================

# boundary_conditions = {
#     1: (1, 1, 1, 1, 1, 1),
#     2: (1, 1, 1, 1, 1, 1),
#     3: (1, 1, 1, 1, 1, 1),
#     4: (1, 1, 1, 1, 1, 1)
# }

# # ============================================================================
# # STEP 9: NODAL SPRINGS
# # ============================================================================

# nodal_spring_configs = [
#     {
#         "node1": (1, 0.0, 0.0, 0.0),
#         "spring_id": 5001,
#         "direction": 3,
#         "material": ("Elastic", 6001, 10000.0),
#         "boundary_condition": (1, 1, 1, 1, 1, 1)
#     },
#     {
#         "node1": (2, bay_x, 0.0, 0.0),
#         "spring_id": 5002,
#         "direction": 3,
#         "material": ("Elastic", 6002, 10000.0),
#         "boundary_condition": (1, 1, 1, 1, 1, 1)
#     },
#     {
#         "node1": (3, bay_x, bay_y, 0.0),
#         "spring_id": 5003,
#         "direction": 3,
#         "material": ("Elastic", 6003, 10000.0),
#         "boundary_condition": (1, 1, 1, 1, 1, 1)
#     },
#     {
#         "node1": (4, 0.0, bay_y, 0.0),
#         "spring_id": 5004,
#         "direction": 3,
#         "material": ("Elastic", 6004, 10000.0),
#         "boundary_condition": (1, 1, 1, 1, 1, 1)
#     }
# ]

# # ============================================================================
# # STEP 10: RIGID DIAPHRAGM
# # ============================================================================

# diaphragm_list = [
#     (3, 11, 12, 13, 14)
# ]

# # ============================================================================
# # STEP 11: LOADS AND MASSES FOR BEAMS AND COLUMNS
# # NOTE: Use DIFFERENT tags than slab (slab uses tag 1, beams use tag 2)
# # ============================================================================

# load_configs = {
#     'time_series': [],  # EMPTY - slab already creates timeSeries 1
#     'patterns': [],     # EMPTY - slab already creates pattern 1
    
#     'beam_uniform_loads': [{
#         'pattern': 1,  # Use existing pattern 1 from slab
#         'loads': [
#             {'elements': [11, 12, 13, 14], 'wy': 0.0, 'wz': -0.5}
#         ]
#     }],
    
#     'nodal_loads': [{
#         'pattern': 1,  # Use existing pattern 1 from slab
#         'loads': [
#             {'node': 11, 'forces': (0, 0, -5.0, 0, 0, 0)},
#             {'node': 12, 'forces': (0, 0, -5.0, 0, 0, 0)},
#             {'node': 13, 'forces': (0, 0, -5.0, 0, 0, 0)},
#             {'node': 14, 'forces': (0, 0, -5.0, 0, 0, 0)}
#         ]
#     }]
# }

# mass_configs = {
#     'beam_column_mass': [
#         {'tag': 1, 'density': 0.0868, 'area': 2.25},
#         {'tag': 2, 'density': 0.0868, 'area': 2.25},
#         {'tag': 3, 'density': 0.0868, 'area': 2.25},
#         {'tag': 4, 'density': 0.0868, 'area': 2.25}
#     ],
#     'beam_additional_mass': [{
#         'element_tags': [11, 12, 13, 14],
#         'mass_per_length': 0.050,
#         'description': 'Steel beam self-weight'
#     }],
#     'nodal_mass': [
#         {'node': 11, 'mass': 1.0},
#         {'node': 12, 'mass': 1.0},
#         {'node': 13, 'mass': 1.0},
#         {'node': 14, 'mass': 1.0}
#     ]
# }
# # ============================================================================
# # STEP 12: BUILD MODEL
# # ============================================================================

# if __name__ == "__main__":
    
#     print("="*80)
#     print("BUILDING COMPLETE STRUCTURE MODEL")
#     print("="*80)
#     print("\nModel Configuration:")
#     print(f"  - Nodes: {len(node_coords)}")
#     # Count forceBeamColumn elements
#     column_count = len([e for e in element_configs['element'] if e['type'] == 'forceBeamColumn'])
#     print(f"  - Columns: {column_count}")

#     # Count elasticBeamColumn elements
#     beam_count = len([e for e in element_configs['element'] if e['type'] == 'elasticBeamColumn'])
#     print(f"  - Beams: {beam_count}")
#     print(f"  - Slabs: {len(slab_configs)}")
#     print(f"  - Fiber Sections: {len(fiber_configs)}")
#     print(f"  - Uniaxial Materials: {len(material_params)}")
#     print(f"  - Springs: {len(nodal_spring_configs)}")
#     print(f"  - Diaphragms: {len(diaphragm_list)}")
#     print("\nNOTE: Slab creates TimeSeries 1 and Pattern 1")
#     print("      Beam/column loads reuse Pattern 1")
    
#     # Call build_model
#     results = build_model(
#         model_params=model_params,
#         fiber_configs=fiber_configs,
#         material_params=material_params,
#         node_coords=node_coords,
#         boundary_conditions=boundary_conditions,
#         element_configs=element_configs,
#         nodal_spring_configs=nodal_spring_configs,
#         diaphragm_list=diaphragm_list,
#         load_configs=load_configs,
#         mass_configs=mass_configs,
#         visualize=True,
#         output_dir=output_dir,
#         slab_configs=slab_configs
#     )
    
#     print("\n" + "="*80)
#     print("MODEL BUILD SUMMARY")
#     print("="*80)
#     print(f"Total Nodes: {results['total_nodes']}")
#     print(f"Total Elements: {results['total_elements']}")
    
#     print("\nGenerated Files:")
#     print(f"Complete Model: {results['all_file_paths']['complete_model']}")
#     print(f"Visualization: {results['all_file_paths']['visualization']}")
    
#     print("\n" + "="*80)
#     print("✅ SUCCESS - MODEL BUILD COMPLETE")
#     print("="*80)


