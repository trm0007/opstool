

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


def apply_surface_load(mesh, load_configs):
    """
    Apply surface load to shell elements using opstool
    
    Parameters
    ----------
    mesh : dict
        Mesh dictionary with 'quad4' and 'tri3' elements
    load_configs : dict
        Load configuration dictionary with keys:
        - 'pressure': float - Pressure load (negative for downward, e.g., -1000 Pa)
        - 'time_series_tag': int - Time series tag
        - 'pattern_tag': int - Pattern tag
        - 'element_tags': list - Specific elements (None = all elements)
    """
    import openseespy.opensees as ops
    try:
        import opstool as opst
    except ImportError:
        raise ImportError("opstool is required for surface loads. Install: pip install opstool")
    
 
    # Extract load parameters - NO DEFAULTS, user must provide all
    load_pressure = load_configs['pressure']
    time_series_tag = load_configs['time_series_tag']
    pattern_tag = load_configs['pattern_tag']
    element_tags = load_configs.get('element_tags')  # Can be None for all elements
    
    if load_pressure is None:
        print("WARNING: No pressure specified in load_configs")
        return
    
    # Create time series and pattern
    ops.timeSeries("Linear", time_series_tag)
    ops.pattern("Plain", pattern_tag, time_series_tag)
    
    # Get all element tags if not specified
    if element_tags is None:
        element_tags = [elem['tag'] for elem in mesh['quad4']]
        element_tags += [elem['tag'] for elem in mesh['tri3']]
    
    # Apply surface load using opstool
    opst.pre.transform_surface_uniform_load(ele_tags=element_tags, p=load_pressure)
    
    print(f"\nSurface load applied:")
    print(f"  Pattern tag: {pattern_tag}")
    print(f"  Time series tag: {time_series_tag}")
    print(f"  Pressure: {load_pressure}")
    print(f"  Elements: {len(element_tags)}")

def generate_mesh(boundary_nodes, mesh_size, internal_points=None, voids=None,
                  py_file="model.py", png_file="mesh.png",
                  material_E=2e11, material_nu=0.3, material_rho=7850,
                  thickness=0.01, node_font_size=7, element_font_size=6, start_node_id = 20000, start_element_id=20000):
    """
    Generate mesh from boundary nodes with support for voids and create OpenSeesPy file.
    
    Parameters
    ----------
    boundary_nodes : dict
        {node_id: (x, y, z)} - minimum 3 nodes
    mesh_size : float
        Element size
    internal_points : dict, optional
        {point_id: (x, y, z)}
    voids : list of dict, optional
        List of void definitions, each dict: {node_id: (x, y, z)}
        Example: [void1_dict, void2_dict]
    py_file : str
        Output Python file path
    png_file : str
        Output visualization file path
    material_E : float
        Young's modulus (Pa)
    material_nu : float
        Poisson's ratio
    material_rho : float
        Density (kg/m³)
    thickness : float
        Plate thickness (m)
    node_font_size : int
        Font size for node numbers (default: 7)
    element_font_size : int
        Font size for element numbers (default: 6)
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
    
    # Create outer boundary loop
    outer_loop = gmsh.model.geo.addCurveLoop(boundary_lines)
    
    # Process voids
    void_loops = []
    void_point_maps = []
    
    if voids:
        print(f"\nProcessing {len(voids)} voids:")
        for void_idx, void_nodes in enumerate(voids):
            print(f"  Void {void_idx + 1}: {len(void_nodes)} nodes")
            
            # Sort void nodes by angle (around their own center)
            void_coords = np.array([void_nodes[nid] for nid in sorted(void_nodes.keys())])
            void_center = void_coords.mean(axis=0)
            void_angles = np.arctan2(void_coords[:, 1] - void_center[1], 
                                     void_coords[:, 0] - void_center[0])
            void_sorted_indices = np.argsort(void_angles)
            void_sorted_ids = [sorted(void_nodes.keys())[i] for i in void_sorted_indices]
            
            # Create void points and lines
            void_point_map = {}
            for node_id in void_sorted_ids:
                x, y, z = void_nodes[node_id]
                pt = gmsh.model.geo.addPoint(x, y, z, mesh_size)
                void_point_map[node_id] = pt
            
            void_point_maps.append(void_point_map)
            
            # Create void boundary lines
            void_lines = []
            for i in range(len(void_sorted_ids)):
                start = void_sorted_ids[i]
                end = void_sorted_ids[(i + 1) % len(void_sorted_ids)]
                line = gmsh.model.geo.addLine(void_point_map[start], void_point_map[end])
                void_lines.append(line)
            
            # Create void loop
            void_loop = gmsh.model.geo.addCurveLoop(void_lines)
            void_loops.append(void_loop)
    
    # Create surface with voids (outer loop minus void loops)
    all_loops = [outer_loop] + void_loops
    surface = gmsh.model.geo.addPlaneSurface(all_loops)
    
    # Validate geometry before meshing
    if voids and internal_points:
        print("\nValidating geometry...")
        
        def point_in_polygon(point, polygon):
            """Check if point is inside polygon using ray casting algorithm"""
            x, y = point[0], point[1]
            n = len(polygon)
            inside = False
            
            p1x, p1y = polygon[0]
            for i in range(1, n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            
            return inside
        
        def distance_to_polygon(point, polygon):
            """Calculate minimum distance from point to polygon edges"""
            min_dist = float('inf')
            n = len(polygon)
            
            for i in range(n):
                p1 = np.array(polygon[i])
                p2 = np.array(polygon[(i + 1) % n])
                
                # Vector from p1 to p2
                edge = p2 - p1
                edge_len = np.linalg.norm(edge)
                
                if edge_len == 0:
                    dist = np.linalg.norm(point - p1)
                else:
                    # Parameter t for closest point on line segment
                    t = max(0, min(1, np.dot(point - p1, edge) / (edge_len ** 2)))
                    closest = p1 + t * edge
                    dist = np.linalg.norm(point - closest)
                
                min_dist = min(min_dist, dist)
            
            return min_dist
        
        points_to_remove = []
        for int_id, int_coord in internal_points.items():
            int_point = np.array(int_coord[:2])
            should_remove = False
            
            # Check if internal point is inside any void
            for void_idx, void_nodes in enumerate(voids):
                # Get void coordinates in order
                void_coords_list = [void_nodes[n][:2] for n in sorted(void_nodes.keys())]
                void_coords = np.array(void_coords_list)
                
                # Check if point is inside void polygon
                if point_in_polygon(int_point, void_coords):
                    print(f"  ERROR: Internal point {int_id} is INSIDE void {void_idx + 1}")
                    print(f"    Point: ({int_coord[0]:.3f}, {int_coord[1]:.3f})")
                    print(f"    This point MUST be REMOVED to prevent meshing errors")
                    should_remove = True
                    break
                
                # Calculate distance to void boundary
                dist_to_boundary = distance_to_polygon(int_point, void_coords_list)
                
                # Minimum safe distance: 1.5 * mesh_size
                min_safe_distance = mesh_size * 1.5
                
                if dist_to_boundary < min_safe_distance:
                    print(f"  ERROR: Internal point {int_id} is TOO CLOSE to void {void_idx + 1}")
                    print(f"    Distance to void boundary: {dist_to_boundary:.4f}")
                    print(f"    Minimum safe distance: {min_safe_distance:.4f}")
                    print(f"    This point MUST be REMOVED to prevent meshing errors")
                    should_remove = True
                    break
                
                # Warn if within caution zone (1.5x to 2x mesh_size)
                elif dist_to_boundary < mesh_size * 2.0:
                    print(f"  WARNING: Internal point {int_id} is close to void {void_idx + 1}")
                    print(f"    Distance to void boundary: {dist_to_boundary:.4f}")
                    print(f"    Recommended minimum: {mesh_size * 2.0:.4f}")
                    print(f"    Meshing may succeed but quality may be poor")
            
            if should_remove:
                points_to_remove.append(int_id)
        
        # Remove problematic points
        if points_to_remove:
            print(f"\n  >>> Automatically removing {len(points_to_remove)} problematic internal points <<<")
            for pt_id in points_to_remove:
                print(f"      Removed point {pt_id}")
                del internal_points[pt_id]
            
            if len(internal_points) == 0:
                internal_points = None
                print(f"  >>> All internal points removed. Proceeding without internal points <<<")
    
    # Synchronize BEFORE creating internal points
    gmsh.model.geo.synchronize()
    
    # Add internal points to the surface AFTER synchronization
    internal_point_map = {}
    if internal_points:
        print(f"\nEmbedding {len(internal_points)} internal points:")
        for node_id, coord in internal_points.items():
            x, y, z = coord
            # Create point in the geometry
            pt = gmsh.model.geo.addPoint(x, y, z, mesh_size)
            internal_point_map[node_id] = pt
        
        # Synchronize after creating all points
        gmsh.model.geo.synchronize()
        
        # Now embed the points in the surface
        for node_id, pt in internal_point_map.items():
            try:
                gmsh.model.mesh.embed(0, [pt], 2, surface)
                print(f"  Internal point {node_id} embedded successfully")
            except Exception as e:
                print(f"  WARNING: Could not embed internal point {node_id}: {e}")
                print(f"    This point may be inside a void or on a boundary")
    
    # Step 2: Generate mesh with better algorithm settings
    gmsh.option.setNumber("Mesh.Algorithm", 6)  # Frontal-Delaunay for 2D
    gmsh.option.setNumber("Mesh.RecombineAll", 1)
    gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.5)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size * 2)
    
    mesh_success = False
    attempt = 1
    
    # Attempt 1: Frontal-Delaunay with recombination
    try:
        print(f"\nAttempt {attempt}: Meshing with Frontal-Delaunay algorithm...")
        gmsh.model.mesh.generate(2)
        mesh_success = True
        print("  ✓ Meshing successful!")
    except Exception as e:
        print(f"  ✗ Failed: {str(e)[:100]}")
        attempt += 1
        
        # Attempt 2: Delaunay without recombination
        try:
            print(f"\nAttempt {attempt}: Trying Delaunay algorithm without recombination...")
            gmsh.model.mesh.clear()
            gmsh.option.setNumber("Mesh.Algorithm", 5)  # Delaunay
            gmsh.option.setNumber("Mesh.RecombineAll", 0)  # Disable recombination
            gmsh.model.mesh.generate(2)
            mesh_success = True
            print("  ✓ Meshing successful!")
        except Exception as e2:
            print(f"  ✗ Failed: {str(e2)[:100]}")
            attempt += 1
            
            # Attempt 3: MeshAdapt algorithm
            try:
                print(f"\nAttempt {attempt}: Trying MeshAdapt algorithm...")
                gmsh.model.mesh.clear()
                gmsh.option.setNumber("Mesh.Algorithm", 1)  # MeshAdapt
                gmsh.option.setNumber("Mesh.RecombineAll", 0)
                gmsh.model.mesh.generate(2)
                mesh_success = True
                print("  ✓ Meshing successful!")
            except Exception as e3:
                print(f"  ✗ Failed: {str(e3)[:100]}")
                
                # Last resort: If internal points exist, try without them
                if internal_point_map:
                    attempt += 1
                    print(f"\n{'-'*60}")
                    print(f"All meshing attempts failed with internal points.")
                    print(f"Attempting final mesh WITHOUT internal points...")
                    print(f"{'-'*60}")
                    
                    # Rebuild geometry without internal points
                    gmsh.finalize()
                    gmsh.initialize()
                    gmsh.model.add("mesh_retry")
                    
                    # Recreate boundary
                    point_map_retry = {}
                    for node_id in sorted_ids:
                        x, y, z = boundary_nodes[node_id]
                        pt = gmsh.model.geo.addPoint(x, y, z, mesh_size)
                        point_map_retry[node_id] = pt
                    
                    lines_retry = []
                    for i in range(len(sorted_ids)):
                        start = sorted_ids[i]
                        end = sorted_ids[(i + 1) % len(sorted_ids)]
                        line = gmsh.model.geo.addLine(point_map_retry[start], point_map_retry[end])
                        lines_retry.append(line)
                    
                    outer_loop_retry = gmsh.model.geo.addCurveLoop(lines_retry)
                    
                    # Recreate voids
                    void_loops_retry = []
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
                            void_loops_retry.append(void_loop)
                    
                    all_loops_retry = [outer_loop_retry] + void_loops_retry
                    surface_retry = gmsh.model.geo.addPlaneSurface(all_loops_retry)
                    gmsh.model.geo.synchronize()
                    
                    # Try meshing without internal points
                    try:
                        print(f"Attempt {attempt}: Meshing WITHOUT internal points...")
                        gmsh.option.setNumber("Mesh.Algorithm", 5)
                        gmsh.option.setNumber("Mesh.RecombineAll", 0)
                        gmsh.model.mesh.generate(2)
                        mesh_success = True
                        internal_point_map = {}  # Clear internal points
                        print("  ✓ Meshing successful WITHOUT internal points!")
                        print(f"  Note: All internal points were excluded to enable meshing")
                    except Exception as e4:
                        gmsh.finalize()
                        raise Exception(f"Mesh generation failed after all attempts: {e4}")
                else:
                    gmsh.finalize()
                    raise Exception(f"Mesh generation failed: {e3}")
    
    if not mesh_success:
        gmsh.finalize()
        raise Exception("Unexpected meshing failure")
    
    # Step 3: Extract mesh data
    # node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    # temp_nodes = {}
    # for i, tag in enumerate(node_tags):
    #     temp_nodes[int(tag)] = (node_coords[3*i], node_coords[3*i+1], node_coords[3*i+2])

    # Step 3: Extract mesh data (existing code)
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    temp_nodes = {}
    for i, tag in enumerate(node_tags):
        temp_nodes[int(tag)] = (node_coords[3*i], node_coords[3*i+1], node_coords[3*i+2])

    # NEW: Create sequential node ID mapping
    gmsh_node_ids = sorted(temp_nodes.keys())
    gmsh_to_new_id = {old_id: start_node_id + i for i, old_id in enumerate(gmsh_node_ids)}

    # Update temp_nodes with new IDs
    temp_nodes = {gmsh_to_new_id[old_id]: coord for old_id, coord in temp_nodes.items()}
    
    # Get elements
    # quad4_elems = []
    # tri3_elems = []
    
    # for elem_type in gmsh.model.mesh.getElementTypes(dim=2):
    #     elem_tags, elem_nodes = gmsh.model.mesh.getElementsByType(elem_type)
        
    #     if elem_type == 3:  # Quad4
        #     for i, tag in enumerate(elem_tags):
        #         nodes = [int(elem_nodes[i*4 + j]) for j in range(4)]
        #         quad4_elems.append({'tag': int(tag), 'nodes': nodes})
        # elif elem_type == 2:  # Tri3
        #     for i, tag in enumerate(elem_tags):
        #         nodes = [int(elem_nodes[i*3 + j]) for j in range(3)]
        #         tri3_elems.append({'tag': int(tag), 'nodes': nodes})

    # Get elements (existing code location)
    quad4_elems = []
    tri3_elems = []

    element_counter = start_element_id  # ADD THIS

    for elem_type in gmsh.model.mesh.getElementTypes(dim=2):
        elem_tags, elem_nodes = gmsh.model.mesh.getElementsByType(elem_type)
        
        if elem_type == 3:  # Quad4
            for i, tag in enumerate(elem_tags):
                nodes = [gmsh_to_new_id[int(elem_nodes[i*4 + j])] for j in range(4)]  # MODIFIED
                quad4_elems.append({'tag': element_counter, 'nodes': nodes})  # MODIFIED
                element_counter += 1  # ADD THIS
        elif elem_type == 2:  # Tri3
            for i, tag in enumerate(elem_tags):
                nodes = [gmsh_to_new_id[int(elem_nodes[i*3 + j])] for j in range(3)]  # MODIFIED
                tri3_elems.append({'tag': element_counter, 'nodes': nodes})  # MODIFIED
                element_counter += 1  # ADD THIS

    
    
    gmsh.finalize()
    
    # Step 4: Match boundary nodes
    tolerance = mesh_size * 0.01
    node_map = {}
    final_nodes = {}
    used_boundary = set()
    
    for gmsh_id, gmsh_coord in temp_nodes.items():
        matched = False
        
        # Try to match with boundary nodes
        for bnd_id, bnd_coord in boundary_nodes.items():
            if bnd_id in used_boundary:
                continue
            dist = np.linalg.norm(np.array(gmsh_coord) - np.array(bnd_coord))
            if dist < tolerance:
                node_map[gmsh_id] = bnd_id
                final_nodes[bnd_id] = bnd_coord
                used_boundary.add(bnd_id)
                matched = True
                break
        
        # Try to match with void boundary nodes
        if not matched and voids:
            for void_nodes in voids:
                for void_id, void_coord in void_nodes.items():
                    if void_id in used_boundary:
                        continue
                    dist = np.linalg.norm(np.array(gmsh_coord) - np.array(void_coord))
                    if dist < tolerance:
                        node_map[gmsh_id] = void_id
                        final_nodes[void_id] = void_coord
                        used_boundary.add(void_id)
                        matched = True
                        break
                if matched:
                    break
        
        if not matched:
            node_map[gmsh_id] = gmsh_id
            final_nodes[gmsh_id] = gmsh_coord
    
    # Step 5: Match embedded internal points
    if internal_points:
        print(f"\nMatching {len(internal_points)} embedded internal points:")
        
        # Create a reverse mapping of coordinates to GMSH IDs
        coord_to_gmsh = {}
        for gmsh_id, gmsh_coord in temp_nodes.items():
            rounded_coord = tuple(round(c, 12) for c in gmsh_coord)
            coord_to_gmsh[rounded_coord] = gmsh_id
        
        matched_internal = set()
        
        for int_id, int_coord in internal_points.items():
            rounded_int_coord = tuple(round(c, 12) for c in int_coord)
            
            if rounded_int_coord in coord_to_gmsh:
                gmsh_id = coord_to_gmsh[rounded_int_coord]
                
                if gmsh_id in node_map and node_map[gmsh_id] in used_boundary:
                    print(f"  WARNING: Internal point {int_id} coincides with boundary node {node_map[gmsh_id]}")
                    matched_internal.add(int_id)
                    continue
                
                if gmsh_id in node_map and node_map[gmsh_id] != gmsh_id:
                    print(f"  WARNING: Internal point {int_id} location already occupied by node {node_map[gmsh_id]}")
                    max_id = max(list(final_nodes.keys()) + list(internal_points.keys()))
                    new_gmsh_id = max_id + 10000
                    node_map[new_gmsh_id] = int_id
                    final_nodes[int_id] = int_coord
                else:
                    node_map[gmsh_id] = int_id
                    final_nodes[int_id] = int_coord
                
                matched_internal.add(int_id)
                print(f"  Internal point {int_id} → exact match at GMSH node {gmsh_id}")
            else:
                # Tolerance-based matching as fallback
                best_match = None
                best_dist = float('inf')
                
                for gmsh_id, gmsh_coord in temp_nodes.items():
                    if gmsh_id in node_map and node_map[gmsh_id] in used_boundary:
                        continue
                    
                    dist = np.linalg.norm(np.array(gmsh_coord) - np.array(int_coord))
                    if dist < tolerance and dist < best_dist:
                        best_match = gmsh_id
                        best_dist = dist
                
                if best_match is not None:
                    node_map[best_match] = int_id
                    final_nodes[int_id] = int_coord
                    matched_internal.add(int_id)
                    print(f"  Internal point {int_id} → tolerance match (dist={best_dist:.6f})")
                else:
                    print(f"  WARNING: Internal point {int_id} not found in mesh")
    
    # Step 6: Check for duplicate node IDs
    node_id_counts = {}
    for gmsh_id, mapped_id in node_map.items():
        node_id_counts[mapped_id] = node_id_counts.get(mapped_id, 0) + 1
    
    duplicates = {node_id: count for node_id, count in node_id_counts.items() if count > 1}
    if duplicates:
        print(f"\nWARNING: Found {len(duplicates)} duplicate node IDs")
        print("Fixing duplicates...")
        
        fixed_mapping = {}
        id_counter = {}
        
        for gmsh_id, mapped_id in node_map.items():
            if node_id_counts[mapped_id] > 1:
                if mapped_id not in id_counter:
                    fixed_mapping[gmsh_id] = mapped_id
                    id_counter[mapped_id] = 1
                else:
                    new_id = max(list(final_nodes.keys()) + 
                               (list(internal_points.keys()) if internal_points else [])) + id_counter[mapped_id]
                    fixed_mapping[gmsh_id] = new_id
                    final_nodes[new_id] = temp_nodes[gmsh_id]
                    id_counter[mapped_id] += 1
                    print(f"  Fixed: GMSH node {gmsh_id} → new node {new_id}")
            else:
                fixed_mapping[gmsh_id] = mapped_id
        
        node_map = fixed_mapping
        print("Fixed all duplicate node IDs")
    
    # Update element nodes
    for elem in quad4_elems:
        elem['nodes'] = [node_map[n] for n in elem['nodes']]
    for elem in tri3_elems:
        elem['nodes'] = [node_map[n] for n in elem['nodes']]
    
    # Step 7: Create visualization
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    node_coords = np.array([final_nodes[n][:2] for n in final_nodes])
    bnd_coords = np.array([boundary_nodes[n][:2] for n in boundary_nodes])
    
    # Plot mesh elements
    for elem in quad4_elems:
        elem_coords = np.array([final_nodes[n][:2] for n in elem['nodes']])
        ax.fill(elem_coords[:, 0], elem_coords[:, 1], 
                facecolor='cyan', edgecolor='blue', alpha=0.3, linewidth=1)
    for elem in tri3_elems:
        elem_coords = np.array([final_nodes[n][:2] for n in elem['nodes']])
        ax.fill(elem_coords[:, 0], elem_coords[:, 1], 
                facecolor='yellow', edgecolor='orange', alpha=0.3, linewidth=1)
    
    # Plot boundary nodes
    ax.scatter(node_coords[:, 0], node_coords[:, 1], c='black', s=30, zorder=5)
    ax.scatter(bnd_coords[:, 0], bnd_coords[:, 1], c='red', s=100, marker='s', 
               edgecolors='black', linewidth=2, label='Boundary', zorder=6)
    
    # Plot void boundaries
    if voids:
        for void_idx, void_nodes in enumerate(voids):
            void_coords = np.array([void_nodes[n][:2] for n in void_nodes])
            ax.scatter(void_coords[:, 0], void_coords[:, 1], c='purple', s=100, marker='o',
                       edgecolors='black', linewidth=2, 
                       label=f'Void {void_idx + 1}' if void_idx == 0 else '', zorder=6)
            
            # Draw void outline
            void_sorted = sorted(void_nodes.keys())
            void_outline = np.array([void_nodes[n][:2] for n in void_sorted] + 
                                   [void_nodes[void_sorted[0]][:2]])
            ax.plot(void_outline[:, 0], void_outline[:, 1], 'purple', linewidth=2, linestyle='--')
    
    # Plot internal points
    if internal_points:
        int_coords = np.array([internal_points[n][:2] for n in internal_points])
        ax.scatter(int_coords[:, 0], int_coords[:, 1], c='green', s=100, marker='^',
                   edgecolors='black', linewidth=2, label='Internal', zorder=6)
    
    # Add node numbers
    for node_id, coord in final_nodes.items():
        ax.annotate(str(node_id), (coord[0], coord[1]), 
                   fontsize=node_font_size, ha='center', va='bottom', 
                   color='darkblue', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                            edgecolor='none', alpha=0.7))
    
    # Add element numbers
    for elem in quad4_elems:
        elem_coords = np.array([final_nodes[n][:2] for n in elem['nodes']])
        center = elem_coords.mean(axis=0)
        ax.annotate(str(elem['tag']), center, 
                   fontsize=element_font_size, ha='center', va='center',
                   color='darkgreen', style='italic',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='cyan', 
                            edgecolor='none', alpha=0.5))
    
    for elem in tri3_elems:
        elem_coords = np.array([final_nodes[n][:2] for n in elem['nodes']])
        center = elem_coords.mean(axis=0)
        ax.annotate(str(elem['tag']), center, 
                   fontsize=element_font_size, ha='center', va='center',
                   color='darkorange', style='italic',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', 
                            edgecolor='none', alpha=0.5))
    
    title = f'Mesh: {len(final_nodes)} nodes, {len(quad4_elems)} quad4, {len(tri3_elems)} tri3'
    if voids:
        title += f', {len(voids)} voids'
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.legend()
    ax.axis('equal')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(png_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n{'='*60}")
    print(f"Mesh generated successfully!")
    print(f"{'='*60}")
    print(f"Nodes:          {len(final_nodes)}")
    print(f"Quad4 elements: {len(quad4_elems)}")
    print(f"Tri3 elements:  {len(tri3_elems)}")
    if voids:
        print(f"Voids:          {len(voids)}")
    print(f"\nFiles created:")
    print(f"  - {py_file}")
    print(f"  - {png_file}")
    print(f"{'='*60}\n")
    
    return {
        'nodes': final_nodes,
        'quad4': quad4_elems,
        'tri3': tri3_elems,
        'voids': voids if voids else []
    }


def zero_element_boundary_condition(material_props, sections, node_list, boundary_condition, 
                                    element_start_id, spring_node_start_id):
    """
    Create zero-length elements at specified nodes for boundary condition modeling
    """
    import openseespy.opensees as ops
    
    node_mapping = {}
    element_ids = []
    current_elem_id = element_start_id
    current_spring_node_id = spring_node_start_id
    
    ops.uniaxialMaterial(*material_props['config'])
    
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


def create_slab(boundary_nodes, mesh_size, internal_points=None, voids=None,
                py_file="slab_model.py", png_file="slab_mesh.png",
                shell_material_config=("ElasticIsotropic", 1, 2e11, 0.3, 7850),
                shell_section_config=("PlateFiber", 1, 1, 0.01),
                node_font_size=7, element_font_size=6,
                ops_ele_type1="ShellMITC4", ops_ele_type2="ASDShellT3",
                shell_boundary_conditions=[1, 1, 1, 1, 1, 1],
                
                assign_to_ops=True,
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
        
        ops.wipe()
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
        if load_configs is not None and 'pressure' in load_configs:
            apply_surface_load(mesh=mesh, load_configs=load_configs)

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


# Example usage
if __name__ == "__main__":
    
    # Define geometry
    boundary_nodes = {
        1: (0.0, 0.0, 0.0),
        2: (2.0, 0.0, 0.0),
        3: (2.5, 1.5, 0.0),
        4: (2.0, 3.0, 0.0),
        5: (0.0, 3.0, 0.0),
        6: (-0.5, 1.5, 0.0),
    }
    
    internal_points = {
        100: (1.0, 1.5, 0.0),
        101: (0.5, 0.75, 0.0),
    }
    
    # Define voids (holes in the mesh)
    void1 = {
        20000: (0.5, 0.5, 0.0),
        20001: (0.5, 1.0, 0.0),
        20002: (1.0, 1.0, 0.0),
        20003: (1.0, 0.5, 0.0),
    }
    
    void2 = {
        30000: (1.5, 1.5, 0.0),
        30001: (1.5, 2.0, 0.0),
        30002: (2.0, 2.0, 0.0),
        30003: (2.0, 1.5, 0.0),
    }
    
    voids = [void1, void2]  # List of voids
    
    # Define parameters
    mesh_size = 0.5
    load_configs = {
    'pressure': -1000.0,        # -1000 Pa (downward pressure)
    'time_series_tag': 1,       # Time series tag
    'pattern_tag': 1,           # Pattern tag
    'element_tags': None        # None = all elements, or [1,2,3] for specific elements
    }
    # Shell element configs
    shell_material_config = ("ElasticIsotropic", 1, 2e11, 0.3, 7850)
    shell_section_config = ("PlateFiber", 1, 1, 0.005)
    ops_ele_type1 = "ShellMITC4"
    ops_ele_type2 = "ASDShellT3"
    shell_boundary_conditions = [1, 1, 1, 1, 1, 1]
    
    # Zero-length element configs
    zero_length_material_config = ("Elastic", 100, 1e8)
    zero_length_directions = [3]
    zero_length_boundary_conditions = [1, 1, 1, 1, 1, 1]
    
    start_node_id=20000
    start_element_id=20000
    
    # Option 1: Standard boundary with voids
    print("="*60)
    print("CREATING MESH WITH VOIDS - STANDARD BOUNDARY")
    print("="*60)
    slab = create_slab(
        boundary_nodes=boundary_nodes,
        mesh_size=mesh_size,
        internal_points=internal_points,
        voids=voids,
        py_file="slab_with_voids.py",
        png_file="slab_with_voids.png",
        shell_material_config=shell_material_config,
        shell_section_config=shell_section_config,
        ops_ele_type1=ops_ele_type1,
        ops_ele_type2=ops_ele_type2,
        shell_boundary_conditions=shell_boundary_conditions,
        assign_to_ops=True,
        use_zero_length=False,
        load_configs = load_configs,
        start_node_id=start_node_id,  # ADD
        start_element_id=start_element_id  # ADD
    )
    

    # Option 2: Zero-length boundary with voids
    print("\n" + "="*60)
    print("CREATING MESH WITH VOIDS - ZERO-LENGTH BOUNDARY")
    print("="*60)
    slab_zero = create_slab(
        boundary_nodes=boundary_nodes,
        mesh_size=mesh_size,
        internal_points=internal_points,
        voids=voids,
        py_file="slab_with_voids_zero_length1100.py",
        png_file="slab_with_voids_zero_length1100.png",
        shell_material_config=shell_material_config,
        shell_section_config=shell_section_config,
        ops_ele_type1=ops_ele_type1,
        ops_ele_type2=ops_ele_type2,
        shell_boundary_conditions=shell_boundary_conditions,
        assign_to_ops=True,
        use_zero_length=True,
        zero_length_material_config=zero_length_material_config,
        zero_length_directions=zero_length_directions,
        zero_length_boundary_conditions=zero_length_boundary_conditions,
        element_start_id=10000,
        spring_node_start_id=1000000,
        load_configs = load_configs,
        start_node_id=start_node_id,  # ADD
        start_element_id=start_element_id  # ADD
    )
    
    print("\n" + "="*60)
    print("MESH GENERATION COMPLETE")
    print("="*60)





"1st part code end"
"2nd part code"








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

def calculate_and_apply_masses(element_mass_list, element_configs, node_coords):
    """Calculate nodal masses from element masses and apply to OpenSees model"""
    
    element_connectivity = {}
    
    for elem in element_configs.get('force_beam_columns', []):
        element_connectivity[elem['tag']] = {
            'node_i': elem['node_i'],
            'node_j': elem['node_j']
        }
    
    for elem in element_configs.get('elastic_beam_columns', []):
        element_connectivity[elem['tag']] = {
            'node_i': elem['node_i'],
            'node_j': elem['node_j']
        }
    
    nodal_masses = {node_id: 0.0 for node_id in node_coords.keys()}
    
    for elem_data in element_mass_list:
        elem_tag = elem_data['tag']
        elem_mass = elem_data['mass']
        
        if elem_tag not in element_connectivity:
            continue
            
        node_i = element_connectivity[elem_tag]['node_i']
        node_j = element_connectivity[elem_tag]['node_j']
        
        half_mass = elem_mass / 2.0
        
        nodal_masses[node_i] += half_mass
        nodal_masses[node_j] += half_mass
            
    for node_id, total_mass in nodal_masses.items():
        if total_mass > 0:
            ops.mass(node_id, total_mass, total_mass, total_mass, 0.0, 0.0, 0.0)
    
    return nodal_masses

def apply_loads(nodal_loads_list=None, beam_uniform_loads_list=None, 
                beam_point_loads_list=None, pattern_tag=1, ts_tag=1, ts_type="Linear"):
    """Apply all types of loads with time series and pattern"""
    ops.timeSeries(ts_type, ts_tag)
    ops.pattern("Plain", pattern_tag, ts_tag)
    
    if nodal_loads_list is not None:
        for node_id, fx, fy, fz, mx, my, mz in nodal_loads_list:
            ops.load(node_id, fx, fy, fz, mx, my, mz)
    
    if beam_uniform_loads_list is not None:
        for element_id, wy, wz in beam_uniform_loads_list:
            opst.pre.transform_beam_uniform_load([element_id], wy=wy, wz=wz)
    
    if beam_point_loads_list is not None:
        for element_id, py, pz, xl in beam_point_loads_list:
            opst.pre.transform_beam_point_load([element_id], py=py, pz=pz, xl=xl)




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
    visualize=True,
    output_dir="output",
    
    # NEW: Single parameter for all create_slab() configurations
    slab_configs=None  # List of dicts with create_slab() parameters (for slabs, footings, etc.)
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
    
    print("✓ Defined uniaxial materials")
    
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
                assign_to_ops=False,
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
            
            print(f"✓ {config_name}: {len(mesh['nodes'])} nodes, "
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
    
    print(f"✓ Created {len(all_nodes_created)} unique nodes")
    
    # ===================================================================
    # STEP 5: APPLY BOUNDARY CONDITIONS
    # ===================================================================
    
    print("\n" + "="*80)
    print("STEP 5: APPLYING BOUNDARY CONDITIONS")
    print("="*80)
    
    for node_id, dofs in boundary_conditions.items():
        ops.fix(node_id, *dofs)
    
    print(f"✓ Applied boundary conditions to {len(boundary_conditions)} nodes")
    
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
        print(f"✓ Created fiber section with tag {fiber_sec['sec_tag']}")
    
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
    
    print(f"✓ Created zero-length springs")

    # ===================================================================
    # STEP 8: CREATE RIGID DIAPHRAGMS (IF SPECIFIED)
    # ===================================================================
    
    if diaphragm_list:
        print("\n" + "="*80)
        print("STEP 8: CREATING RIGID DIAPHRAGMS")
        print("="*80)
        
        for perp_dir, ret_node, *constr_nodes in diaphragm_list:
            ops.rigidDiaphragm(perp_dir, ret_node, *constr_nodes)
        
        print(f"✓ Created {len(diaphragm_list)} rigid diaphragms")
    
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
    
    print(f"✓ Created {col_count} columns and {beam_count} beams")
    
    # ===================================================================
    # STEP 10: CREATE SHELL ELEMENTS
    # ===================================================================
    
    print("\n" + "="*80)
    # print("STEP 10: CREATING SHELL ELEMENTS")
    # print("="*80)
    
    # shell_ele_count = 0
    # if shell_results:
    #     for shell_mesh in shell_results:
    #         config_name = shell_mesh.get('config_name', 'Unknown')
            
    #         # Get section tag from shell_section_config
    #         sec_tag = shell_mesh['shell_section_config'][1]
            
    #         # Define nDMaterial and section if not already defined
    #         try:
    #             mat_config = shell_mesh['shell_material_config']
    #             ops.nDMaterial(mat_config[0], mat_config[1], mat_config[2], mat_config[3], mat_config[4])
    #         except:
    #             pass  # Material might already exist
            
    #         try:
    #             sec_config = shell_mesh['shell_section_config']
    #             ops.section(sec_config[0], sec_config[1], sec_config[2], sec_config[3])
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
    
    # print(f"✓ Created {shell_ele_count} total shell elements")
    

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
            
            # Get material and section configs from the original slab_configs
            # Find the matching config
            shell_mat_config = None
            shell_sec_config = None
            
            for config in slab_configs:
                if config.get('name') == config_name:
                    shell_mat_config = config['shell_material_config']
                    shell_sec_config = config['shell_section_config']
                    break
            
            if shell_mat_config is None or shell_sec_config is None:
                print(f"  WARNING: Could not find config for {config_name}, skipping...")
                continue
            
            # Get section tag from shell_section_config
            sec_tag = shell_sec_config[1]
            
            # Define nDMaterial and section if not already defined
            try:
                ops.nDMaterial(shell_mat_config[0], shell_mat_config[1], 
                            shell_mat_config[2], shell_mat_config[3], shell_mat_config[4])
            except:
                pass  # Material might already exist
            
            try:
                ops.section(shell_sec_config[0], shell_sec_config[1], 
                        shell_sec_config[2], shell_sec_config[3])
            except:
                pass  # Section might already exist
            
            # Create quad4 elements
            for elem in shell_mesh['quad4']:
                ops.element("ShellMITC4", elem['tag'], *elem['nodes'], sec_tag)
                shell_ele_count += 1
            
            # Create tri3 elements
            for elem in shell_mesh['tri3']:
                ops.element("ASDShellT3", elem['tag'], *elem['nodes'], sec_tag)
                shell_ele_count += 1
            
            print(f"  {config_name}: {len(shell_mesh['quad4']) + len(shell_mesh['tri3'])} elements")

    print(f"✓ Created {shell_ele_count} total shell elements")

    # ===================================================================
    # STEP 11: VISUALIZATION
    # ===================================================================
    
    if visualize:
        print("\n" + "="*80)
        print("STEP 11: CREATING VISUALIZATION")
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
            print(f"✓ Visualization saved to: {output_path}")
            
        except Exception as e:
            print(f"Visualization error: {e}")
    
    # ===================================================================
    # STEP 12: SUMMARY
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
    
    return {
        'fiber_sections': fiber_section_info,
        'shell_meshes': shell_results,
        'total_nodes': len(all_node_tags),
        'total_elements': len(all_ele_tags)
    }





















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

# Single unified configuration list for all shell structures
slab_configs = [
    # ============================================================
    # SLABS
    # ============================================================
    {
        'name': 'Slab_1',
        'type': 'slab',
        'boundary_nodes': {
            1001: (0.0, 0.0, 10.0),
            1002: (20.0, 0.0, 10.0),
            1003: (20.0, 20.0, 10.0),
            1004: (0.0, 20.0, 10.0)
        },
        'mesh_size': 2.0,
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
        # 'node_font_size': 9,      # Larger for footings
        # 'element_font_size': 8,

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
            2001: (20.0, 0.0, 10.0),
            2002: (40.0, 0.0, 10.0),
            2003: (40.0, 20.0, 10.0),
            2004: (20.0, 20.0, 10.0)
        },
        'mesh_size': 2.0,
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
        'start_node_id': 120000,      # Slab 2 mesh nodes start at 120000
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
        'mesh_size': 1.0,
        'internal_points': None,
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
        'start_node_id': 140000,      # Footing 1 mesh nodes start at 140000
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
        'mesh_size': 1.0,
        'internal_points': None,
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
        'start_node_id': 160000,      # Footing 2 mesh nodes start at 160000
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
        'mesh_size': 1.0,
        'internal_points': None,
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
        'start_node_id': 180000,      # Footing 3 mesh nodes start at 180000
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
        'mesh_size': 1.0,
        'internal_points': None,
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
        'start_node_id': 200000,      # Footing 4 mesh nodes start at 200000
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
        'boundary_nodes': create_regular_polygon_nodes(20.0, 20.0, 3.5, 32, 7001, 0.0),
        'mesh_size': 1.0,
        'internal_points': None,
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

        'py_file': 'footing5_circle.py',
        'png_file': 'footing5_circle.png',
        'shell_material_config': ("ElasticIsotropic", 25, 3000.0 * 144.0, 0.2, 0.150 * 1000.0),
        'shell_section_config': ("PlateFiber", 25, 25, 1.0),
        'ops_ele_type1': "ShellMITC4",
        'ops_ele_type2': "ASDShellT3",
        'shell_boundary_conditions': [0, 0, 0, 0, 0, 0],
        'use_zero_length': False,
        'element_start_id': 70000,
        'spring_node_start_id': 1600000,
        'start_node_id': 220000,      # Footing 5 mesh nodes start at 220000
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
        'mesh_size': 1.0,
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
        'start_node_id': 240000,      # Footing 6 mesh nodes start at 240000
        'start_element_id': 250000,   # Footing 6 mesh elements start at 250000
        'load_configs': {
            'pressure': -200.0,
            'time_series_tag': 306,
            'pattern_tag': 406,
            'element_tags': None
        }
    }
]
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
            'mesh_size': 0.5,
            'mat_tags': column_rect_2x2_mat_tags,
            'sec_tag': 1,
            'G': G_concrete,
            'save_prefix': 'column_rect_2x2_4bars',
            'section_name': 'Rect_2x2_4bars'
        },
        {
            'cover': column_rect_2x3_cover,
            'mesh_size': 0.5,
            'mat_tags': column_rect_2x3_mat_tags,
            'sec_tag': 2,
            'G': G_concrete,
            'save_prefix': 'column_rect_2x3_6bars',
            'section_name': 'Rect_2x3_6bars'
        },
        {
            'cover': column_circular_cover,
            'mesh_size': 0.5,
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

    output_dir="output",
    
    # NEW: Single unified parameter for all shell structures (slabs, footings, walls, etc.)
    slab_configs=slab_configs,
    
    visualize=True
)

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
    

