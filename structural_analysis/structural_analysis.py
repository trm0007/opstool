

import streamlit as st
import os
import json
import zipfile
import sys
import tempfile
import numpy as np
import openseespy.opensees as ops
import opstool as opst
import hashlib
import traceback
import pickle
import matplotlib.pyplot as plt
import opstool.anlys as opst_anlys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(page_title="OpenSees Response Analyzer", layout="wide")

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
        'odbs': []
    }
    save_users()
    
    # Create user directory
    user_dir = f"./.opstool.output/{username}"
    os.makedirs(user_dir, exist_ok=True)
    
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

def get_user_odb_path(username, odb_name):
    """Get the full ODB path for a user"""
    return f"{username}/{odb_name}"

def scan_user_odbs(username):
    """Scan for ODBs belonging to a specific user"""
    odb_dir = "./.opstool.output"
    odbs = []
    
    if os.path.exists(odb_dir):
        # Look for ODB directories that match the pattern: RespStepData-{username}-{odb_name}.odb
        prefix = f"RespStepData-{username}-"
        for item in os.listdir(odb_dir):
            if item.startswith(prefix) and item.endswith('.odb'):
                item_path = os.path.join(odb_dir, item)
                if os.path.isdir(item_path):
                    # Extract ODB name: remove "RespStepData-{username}-" prefix and ".odb" suffix
                    odb_name = item[len(prefix):-4]
                    odbs.append(odb_name)
    
    return sorted(odbs)

def delete_user_odb(username, odb_name):
    """Delete a specific ODB for a user"""
    import shutil
    # ODB is stored as: RespStepData-{username}-{odb_name}.odb
    odb_path = f"./.opstool.output/RespStepData-{username}-{odb_name}.odb"
    
    if os.path.exists(odb_path):
        shutil.rmtree(odb_path)
        return True, f"ODB '{odb_name}' deleted successfully!"
    return False, f"ODB '{odb_name}' not found!"

def delete_account(username):
    """Delete user account and all associated ODBs"""
    import shutil
    
    # Delete all user's ODBs
    odb_dir = "./.opstool.output"
    prefix = f"RespStepData-{username}-"
    deleted_odbs = 0
    
    if os.path.exists(odb_dir):
        for item in os.listdir(odb_dir):
            if item.startswith(prefix) and item.endswith('.odb'):
                item_path = os.path.join(odb_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    deleted_odbs += 1
    
    # Delete user output results
    user_output_dir = f"output_results/{username}"
    if os.path.exists(user_output_dir):
        shutil.rmtree(user_output_dir)
    
    # Remove user from users dictionary
    if username in st.session_state.users:
        del st.session_state.users[username]
        save_users()
    
    return True, f"Account deleted successfully! Removed {deleted_odbs} ODB(s)."

def clear_output_results(username):
    """Clear all output results for a specific user to free up space"""
    import shutil
    
    user_output_dir = f"output_results/{username}"
    
    if not os.path.exists(user_output_dir):
        return True, "No output results found to clear."
    
    try:
        # Calculate size before deletion
        total_size = 0
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(user_output_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
                file_count += 1
        
        # Convert bytes to human-readable format
        size_mb = total_size / (1024 * 1024)
        
        # Delete the directory
        shutil.rmtree(user_output_dir)
        
        # Recreate empty directory
        os.makedirs(user_output_dir, exist_ok=True)
        
        return True, f"Cleared {file_count} files, freed up {size_mb:.2f} MB of space!"
    
    except Exception as e:
        return False, f"Error clearing output results: {str(e)}"

# ========================================================================================
# INITIALIZE SESSION STATE
# ========================================================================================

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'users' not in st.session_state:
    st.session_state.users = load_users()
if 'available_odbs' not in st.session_state:
    st.session_state.available_odbs = []

# Moment-Curvature session states
if 'mc_code_input' not in st.session_state:
    st.session_state.mc_code_input = """# Model initialization
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Uniaxial materials
ops.uniaxialMaterial('Concrete01', 101, -4.0, -0.002, -0.8, -0.006)
ops.uniaxialMaterial('Concrete01', 102, -5.0, -0.002, -1.0, -0.008)
ops.uniaxialMaterial('Steel01', 103, 60.0, 29000.0, 0.015)

# Fiber section
ops.section('Fiber', 1, '-GJ', 36591031599.06977)
ops.fiber(-5.0, 6.583333, 1.5, 101)
ops.fiber(3.333333, -8.0, 1.5, 101)
ops.fiber(3.333333, 8.0, 1.5, 101)

# Rebar
ops.fiber(-4.5, -7.5, 0.7853982, 103)
ops.fiber(4.5, -7.5, 0.7853982, 103)
ops.fiber(4.5, 7.5, 0.7853982, 103)
ops.fiber(-4.5, 7.5, 0.7853982, 103)

sec_tag = 1
"""

if 'mc_results' not in st.session_state:
    st.session_state.mc_results = None

# Linear Buckling session states
if 'buckling_code_input' not in st.session_state:
    st.session_state.buckling_code_input = """# Model parameters
L = 50.0
h = 8.0
t = 1.0
E = 29000
v = 0.3
mesh_factor = 4

# Create model
ops.wipe()
ops.model("basic", "-ndm", 3, "-ndf", 6)

ops.node(1, 0, -h/2, 0)
ops.node(2, 0, h/2, 0)
ops.node(3, 0, h/2, L)
ops.node(4, 0, -h/2, L)

c = h / mesh_factor
ops.mesh("line", 1, 2, 1, 2, 0, 6, c)
ops.mesh("line", 2, 2, 2, 3, 0, 6, c)
ops.mesh("line", 3, 2, 3, 4, 0, 6, c)
ops.mesh("line", 4, 2, 4, 1, 0, 6, c)

ops.section("ElasticMembranePlateSection", 1, E, v, t)
ops.mesh("quad", 13, 4, 4, 3, 2, 1, 0, 6, c, "ShellNLDKGT", 1)

ops.fixZ(0, 1, 1, 1, 0, 0, 0)
ops.fixZ(L, 1, 1, 0, 0, 0, 0)
ops.fix(1, 0, 0, 0, 1, 0, 0)

mesh_tag = 3
"""

if 'buckling_results' not in st.session_state:
    st.session_state.buckling_results = None

# ========================================================================================
# MODEL BUILDING FUNCTIONS
# ========================================================================================

def build_model(Tn, Sa):
    """Build the structural model"""
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    ops.timeSeries("Path", 1, "-time", *Tn, "-values", *Sa)
    ops.uniaxialMaterial("Elastic", 2, 938000000.0)
    ops.section(
        "Elastic", 1, 30000000000.0, 0.09, 0.0006749999999999999,
        0.0006749999999999999, 12500000000.0, 0.0011407499999999994,
    )
    ops.section("Aggregator", 3, 2, "Vy", 2, "Vz", "-section", 1)
    
    ops.node(1, 0, 0, 0)
    ops.node(2, 0, 0, 3, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(3, 4, 0, 3, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(4, 4, 0, 0)
    ops.node(5, 0, 0, 6, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(6, 4, 0, 6, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(7, 4, 3, 6, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(8, 0, 3, 6, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(9, 0, 3, 3, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(10, 0, 3, 0)
    ops.node(11, 4, 3, 3, "-mass", 200, 200, 200, 0, 0, 0)
    ops.node(12, 4, 3, 0)
    ops.node(13, 2, 1.5, 6)
    ops.node(14, 2, 1.5, 3)
    
    ops.beamIntegration("Lobatto", 1, 3, 5)
    
    beam_data = [
        (1, 1, 2, 1, 1.0, 0.0, -0.0),
        (2, 2, 3, 2, 0.0, 0.0, 1.0),
        (3, 4, 3, 3, 1.0, 0.0, -0.0),
        (4, 2, 5, 4, 1.0, 0.0, -0.0),
        (5, 5, 6, 5, 0.0, 0.0, 1.0),
        (6, 7, 6, 6, 0.0, 0.0, 1.0),
        (7, 8, 7, 7, 0.0, 0.0, 1.0),
        (8, 9, 2, 8, 0.0, 0.0, 1.0),
        (9, 8, 5, 9, 0.0, 0.0, 1.0),
        (10, 10, 9, 10, 1.0, 0.0, -0.0),
        (11, 3, 6, 11, 1.0, 0.0, -0.0),
        (12, 11, 7, 12, 1.0, 0.0, -0.0),
        (13, 11, 3, 13, 0.0, 0.0, 1.0),
        (14, 9, 11, 14, 0.0, 0.0, 1.0),
        (15, 12, 11, 15, 1.0, 0.0, -0.0),
        (16, 9, 8, 16, 1.0, 0.0, -0.0),
    ]
    
    for ele_id, node_i, node_j, transf_id, *vec in beam_data:
        ops.geomTransf("Linear", transf_id, *vec)
        ops.element("forceBeamColumn", ele_id, node_i, node_j, transf_id, 1)
    
    ops.fix(1, 1, 1, 1, 1, 1, 1)
    ops.fix(10, 1, 1, 1, 1, 1, 1)
    ops.fix(4, 1, 1, 1, 1, 1, 1)
    ops.fix(12, 1, 1, 1, 1, 1, 1)
    ops.fix(13, 0, 0, 1, 1, 1, 0)
    ops.fix(14, 0, 0, 1, 1, 1, 0)
    
    ops.rigidDiaphragm(3, 14, 2, 3, 9, 11)
    ops.rigidDiaphragm(3, 13, 5, 6, 7, 8)


def response_spectrum_analysis(username, odb_name, section_response_dof, damping_ratio, scale_factor, Tn, Sa, direction=1, num_modes=7):
    """Perform response spectrum analysis with user-specific ODB"""
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("UmfPack")
    ops.test("NormUnbalance", 0.0001, 10)
    ops.algorithm("Linear")
    ops.integrator("LoadControl", 0.0)
    ops.analysis("Static")
    
    print(f"Performing eigenvalue analysis for {num_modes} modes...")
    eigs = ops.eigen("-genBandArpack", num_modes)
    
    dmp = [damping_ratio] * len(eigs)
    scalf = [scale_factor] * len(eigs)
    
    modal_props = ops.modalProperties("-return", "-unorm")
    
    print(f"Eigenvalues: {eigs}")
    print(f"Periods: {[2*np.pi/np.sqrt(eig) for eig in eigs]}")
    
    # Create user-specific ODB tag using dash instead of slash
    # This will create: RespStepData-{username}-{odb_name}.odb
    full_odb_tag = f"{username}-{odb_name}"
    
    print(f"\nPerforming response spectrum analysis...")
    print(f"ODB will be saved as: RespStepData-{full_odb_tag}.odb")
    
    ODB = opst.post.CreateODB(full_odb_tag, section_response_dof)
    
    for i in range(len(eigs)):
        print(f"  Analyzing mode {i+1}...")
        ops.responseSpectrumAnalysis(direction, "-Tn", *Tn, "-Sa", *Sa, "-mode", i + 1)
        ODB.fetch_response_step()
    
    print("\nCombining modal responses using CQC method...")
    ODB.combine_response_spectrum(method="CQC", lambdas=eigs, damping=dmp, scale=scalf)
    
    ODB.save_response()
    
    print(f"Response spectrum analysis complete!")
    print(f"Results saved with odb_tag: {full_odb_tag}")
    
    return full_odb_tag, num_modes


def post_processing(odb_tag, num_modes, output_dir, visualize_modes, nodal_output_dir, nodal_resp_types, node_ids, selected_dofs, frame_output_dir, frame_resp_types, ele_ids, response_dofs, visualize_resp_types):
    """Post-process and visualize response spectrum analysis results"""
    import opstool.vis.pyvista as pyvista_vis
    
    print("\n" + "="*60)
    print("POST-PROCESSING RESPONSE SPECTRUM RESULTS")
    print("="*60)
    
    nodal_output_dir = os.path.join(output_dir, "nodal_response")
    frame_output_dir = os.path.join(output_dir, "frame_response")
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(nodal_output_dir, exist_ok=True)
    os.makedirs(frame_output_dir, exist_ok=True)
    
    print("\n2. Getting available response types...")
    ele_resp = opst.post.get_element_responses(odb_tag=odb_tag, ele_type="Frame")
    print(f"   ✓ Frame element response types: {list(ele_resp.keys())}")
    
    node_info = opst.post.get_nodal_responses_info()
    print(f"   ✓ Nodal response info retrieved")
    
    print("\n3. Extracting nodal response data...")
    
    for resp_type in nodal_resp_types:
        print(f"   Extracting {resp_type}...")
        
        node_data = opst.post.get_nodal_responses(
            odb_tag=odb_tag, 
            resp_type=resp_type, 
            lazy_load=True
        )
        
        data = {
            "response_type": resp_type,
            "analysis_type": "ResponseSpectrum",
            "note": "time=0 is combined CQC response, time=1,2,3... are modal responses",
            "data": {
                "time": node_data.coords["time"].data.tolist(),
                "node_tags": node_data.coords["nodeTags"].data.tolist(),
                "dofs": node_data.coords["DOFs"].data.tolist() if "DOFs" in node_data.coords else [],
                "node_values": {}
            }
        }
        
        for node_id in node_ids:
            if node_id in node_data.coords["nodeTags"].data:
                if "DOFs" in node_data.coords:
                    available_dofs = [dof for dof in selected_dofs 
                                    if dof in node_data.coords["DOFs"].data]
                    if available_dofs:
                        node_response = node_data.sel(nodeTags=node_id, DOFs=available_dofs)
                        
                        data["data"]["node_values"][f"node_{node_id}"] = {
                            "combined_response": {},
                            "modal_responses": {}
                        }
                        
                        for i, dof in enumerate(available_dofs):
                            combined_val = float(node_response[0, i].values)
                            data["data"]["node_values"][f"node_{node_id}"]["combined_response"][dof] = combined_val
                            
                            modal_vals = [float(v) for v in node_response[1:, i].values]
                            data["data"]["node_values"][f"node_{node_id}"]["modal_responses"][dof] = modal_vals
        
        filename = f"{nodal_output_dir}/{resp_type}_response.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"   ✓ {resp_type} saved to {filename}")
    
    print(f"   ✓ Nodal response results saved to {nodal_output_dir}/")
    
    print("\n4. Extracting frame element response data...")
    
    for resp_type in frame_resp_types:
        print(f"   Extracting {resp_type}...")
        
        resp_array = ele_resp[resp_type]
        
        if resp_type in ["sectionForces", "sectionDeformations"]:
            dof_dim = "secDofs"
            selected_frame_dofs = ["N", "MY", "MZ", "VY", "VZ", "T"]
            has_sections = True
        elif resp_type in ["basicForces", "basicDeformations"]:
            dof_dim = "basicDofs"
            selected_frame_dofs = ["N", "MY1", "MY2", "MZ1", "MZ2", "T"]
            has_sections = False
        else:
            continue
        
        data = {
            "response_type": resp_type,
            "analysis_type": "ResponseSpectrum",
            "note": "time=0 is combined CQC response, time=1,2,3... are modal responses",
            "data": {
                "time": resp_array.coords["time"].data.tolist(),
                "ele_tags": resp_array.coords["eleTags"].data.tolist(),
                "dofs": resp_array.coords[dof_dim].data.tolist(),
                "element_values": {}
            }
        }
        
        if has_sections:
            data["data"]["sec_points"] = resp_array.coords["secPoints"].data.tolist()
        
        available_dofs = resp_array.coords[dof_dim].data.tolist()
        valid_dofs = [dof for dof in selected_frame_dofs if dof in available_dofs]
        
        for ele_id in ele_ids:
            if ele_id in resp_array.coords["eleTags"].data:
                
                if has_sections:
                    ele_response = resp_array.sel(eleTags=ele_id, **{dof_dim: valid_dofs})
                    
                    data["data"]["element_values"][f"ele_{ele_id}"] = {
                        "combined_response": {},
                        "modal_responses": {}
                    }
                    
                    for sec_pt in resp_array.coords["secPoints"].data:
                        sec_data = ele_response.sel(time=0, secPoints=sec_pt).values
                        data["data"]["element_values"][f"ele_{ele_id}"]["combined_response"][f"sec_{sec_pt}"] = {
                            valid_dofs[i]: float(sec_data[i]) for i in range(len(valid_dofs))
                        }
                    
                    for mode_idx in range(1, len(resp_array.coords["time"].data)):
                        mode_data = {}
                        for sec_pt in resp_array.coords["secPoints"].data:
                            sec_data = ele_response.sel(time=mode_idx, secPoints=sec_pt).values
                            mode_data[f"sec_{sec_pt}"] = {
                                valid_dofs[i]: float(sec_data[i]) for i in range(len(valid_dofs))
                            }
                        data["data"]["element_values"][f"ele_{ele_id}"]["modal_responses"][f"mode_{mode_idx}"] = mode_data
                
                else:
                    ele_response = resp_array.sel(eleTags=ele_id, **{dof_dim: valid_dofs})
                    
                    data["data"]["element_values"][f"ele_{ele_id}"] = {
                        "combined_response": {},
                        "modal_responses": {}
                    }
                    
                    combined_data = ele_response.sel(time=0).values
                    data["data"]["element_values"][f"ele_{ele_id}"]["combined_response"] = {
                        valid_dofs[i]: float(combined_data[i]) for i in range(len(valid_dofs))
                    }
                    
                    for mode_idx in range(1, len(resp_array.coords["time"].data)):
                        mode_data = ele_response.sel(time=mode_idx).values
                        data["data"]["element_values"][f"ele_{ele_id}"]["modal_responses"][f"mode_{mode_idx}"] = {
                            valid_dofs[i]: float(mode_data[i]) for i in range(len(valid_dofs))
                        }
        
        filename = f"{frame_output_dir}/frame_{resp_type}_response.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"   ✓ {resp_type} saved to {filename}")
    
    print(f"   ✓ Frame response results saved to {frame_output_dir}/")
    
    print("\n5. Creating visualizations...")
    
    pyvista_vis.set_plot_props(notebook=False)
    
    fig = pyvista_vis.plot_model()
    fig.export_html(os.path.join(output_dir, "model.html"))
    print(f"   ✓ Model saved to {output_dir}/model.html")
    
    fig = pyvista_vis.plot_eigen(mode_tags=list(range(1, min(7, num_modes+1))), subplots=True, scale=2)
    fig.export_html(os.path.join(output_dir, "eigen_modes.html"))
    print(f"   ✓ Eigen modes saved to {output_dir}/eigen_modes.html")
    
    print("\n6. Creating frame response visualizations...")
    
    for vis_resp_type in visualize_resp_types:
        print(f"   Visualizing {vis_resp_type}...")
        
        for resp_dof in response_dofs:
            fig = pyvista_vis.plot_frame_responses(
                odb_tag=odb_tag,
                step=0,
                resp_type=vis_resp_type,
                resp_dof=resp_dof,
                scale=1.5,
            )
            filename = f"frame_{vis_resp_type}_{resp_dof}.html"
            fig.export_html(os.path.join(frame_output_dir, filename))
            print(f"   ✓ {vis_resp_type}-{resp_dof} saved to {frame_output_dir}/{filename}")
    
    print("\n" + "="*60)
    print("POST-PROCESSING COMPLETE!")
    print("="*60)


def create_zip(folder_path, zip_name):
    if not os.path.exists(folder_path):
        return None
    zip_path = os.path.join(tempfile.gettempdir(), f"{zip_name}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    return zip_path


def display_json_files(folder_path):
    if not os.path.exists(folder_path):
        return
    json_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.json')])
    if json_files:
        st.subheader("JSON Response Data")
        for json_file in json_files:
            with st.expander(f"📄 {json_file}"):
                json_path = os.path.join(folder_path, json_file)
                with open(json_path, 'r') as f:
                    data = json.load(f)
                st.json(data)
                with open(json_path, 'rb') as f:
                    st.download_button(
                        label=f"Download {json_file}",
                        data=f,
                        file_name=json_file,
                        mime="application/json",
                        key=f"json_{json_file}"
                    )


def display_html_files(folder_path):
    if not os.path.exists(folder_path):
        return
    html_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.html')])
    if html_files:
        st.subheader("HTML Visualizations")
        for html_file in html_files:
            with st.expander(f"📊 {html_file}"):
                html_path = os.path.join(folder_path, html_file)
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=600, scrolling=True)
                with open(html_path, 'rb') as f:
                    st.download_button(
                        label=f"Download {html_file}",
                        data=f,
                        file_name=html_file,
                        mime="text/html",
                        key=f"html_{html_file}"
                    )


# ========================================================================================
# AUTHENTICATION UI
# ========================================================================================

st.title("🔐 OpenSees Response Analyzer")

if not st.session_state.authenticated:
    st.info("Please sign in or sign up to start creating ODB analyses")
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    # Sign In Tab
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
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all fields")
    
    # Sign Up Tab
    with tab2:
        st.subheader("Sign Up")
        
        with st.form("signup_form"):
            reg_username = st.text_input("Username", key="reg_user", help="Choose a unique username")
            reg_email = st.text_input("Email", key="reg_email", help="Enter your email address")
            reg_password = st.text_input("Password", type="password", key="reg_pass", help="Minimum 6 characters")
            reg_submit = st.form_submit_button("Sign Up", type="primary")
            
            if reg_submit:
                if reg_username and reg_email and reg_password:
                    # Basic validation
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
# AUTHENTICATED USER INTERFACE
# ========================================================================================

# User info and logout in sidebar
with st.sidebar:
    st.success(f"👤 Logged in as: **{st.session_state.current_user}**")
    if st.button("🚪 Sign Out", use_container_width=True):
        sign_out()
        st.rerun()
    
    st.divider()
    
    # Display user's ODBs
    st.subheader("📊 Your ODBs")
    user_odbs = scan_user_odbs(st.session_state.current_user)
    
    if user_odbs:
        for odb in user_odbs:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {odb}")
            with col2:
                if st.button("🗑️", key=f"del_{odb}", help=f"Delete {odb}"):
                    success, message = delete_user_odb(st.session_state.current_user, odb)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("No ODBs created yet")
    
    st.divider()
    
    # Workflow selection
    st.header("Analysis Workflow")
    workflow_step = st.radio(
        "Select Workflow Step",
        ["1. Create & Save ODB", "2. Extract Responses", "3. Moment-Curvature Analysis", "4. Linear Buckling Analysis", "👤 Profile", "📖 User Guide"]
    )

# ========================================================================================
# STEP 1: CREATE & SAVE ODB
# ========================================================================================
if workflow_step == "1. Create & Save ODB":
    st.header("Step 1: Create & Save ODB")
    st.info(f"👤 Creating ODB for user: **{st.session_state.current_user}**")
    
    # ODB Name Input
    st.subheader("ODB Configuration")
    col1, col2 = st.columns([2, 1])
    with col1:
        odb_name = st.text_input(
            "ODB Name",
            value="my_analysis",
            help="Enter a unique name for this ODB (no spaces or special characters)",
            key="odb_name_input"
        )
    with col2:
        # Show if ODB exists
        user_odbs = scan_user_odbs(st.session_state.current_user)
        if odb_name in user_odbs:
            st.warning("⚠️ ODB exists!")
        else:
            st.success("✓ Name available")
    
    analysis_type_step1 = st.selectbox(
        "Select Analysis Type",
        ["Response Spectrum Analysis", "Gravity Analysis"],
        key="analysis_type_step1",
        help="Choose the type of analysis to run"
    )
    
    # RESPONSE SPECTRUM ANALYSIS
    if analysis_type_step1 == "Response Spectrum Analysis":
        st.subheader("Response Spectrum Analysis Configuration")
        
        default_rsa_odb_code = f"""import numpy as np
import openseespy.opensees as ops

# User and ODB info
username = "{st.session_state.current_user}"
odb_name = "{odb_name}"

# Response spectrum data
Tn = [0.0, 0.06, 0.1, 0.12, 0.18, 0.24, 0.3, 0.36, 0.4, 0.42, 0.48, 0.54, 0.6, 0.66, 0.72, 0.78, 0.84, 0.9, 0.96, 1.02,
    1.08, 1.14, 1.2, 1.26, 1.32, 1.38, 1.44, 1.5, 1.56, 1.62, 1.68, 1.74, 1.8, 1.86, 1.92, 1.98, 2.04, 2.1, 2.16, 2.22,
    2.28, 2.34, 2.4, 2.46, 2.52, 2.58, 2.64, 2.7, 2.76, 2.82, 2.88, 2.94, 3.0, 3.06, 3.12, 3.18, 3.24, 3.3, 3.36, 3.42,
    3.48, 3.54, 3.6, 3.66, 3.72, 3.78, 3.84, 3.9, 3.96, 4.02, 4.08, 4.14, 4.2, 4.26, 4.32, 4.38, 4.44, 4.5, 4.56, 4.62,
    4.68, 4.74, 4.8, 4.86, 4.92, 4.98, 5.04, 5.1, 5.16, 5.22, 5.28, 5.34, 5.4, 5.46, 5.52, 5.58, 5.64, 5.7, 5.76, 5.82,
    5.88, 5.94, 6.0]

Sa = [1.9612, 3.72628, 4.903, 4.903, 4.903, 4.903, 4.903, 4.903, 4.903, 4.6696172, 4.0861602, 3.6321424, 3.2683398,
    2.971218, 2.7241068, 2.5142584, 2.3348086, 2.1788932, 2.0425898, 1.9229566, 1.8160712, 1.7199724, 1.6346602,
    1.5562122, 1.485609, 1.4208894, 1.3620534, 1.3071398, 1.2571292, 1.211041, 1.166914, 1.1267094, 1.0894466,
    1.054145, 1.0217852, 0.990406, 0.960988, 0.9335312, 0.9080356, 0.8835206, 0.8599862, 0.838413, 0.8168398,
    0.7972278, 0.7785964, 0.759965, 0.7432948, 0.7266246, 0.710935, 0.6952454, 0.6805364, 0.666808, 0.6540602,
    0.6285646, 0.6040496, 0.5814958, 0.5609032, 0.5403106, 0.5206986, 0.5030478, 0.485397, 0.4697074, 0.4540178,
    0.4393088, 0.4255804, 0.411852, 0.3991042, 0.3863564, 0.3755698, 0.3638026, 0.353016, 0.34321, 0.333404,
    0.3245786, 0.3157532, 0.3069278, 0.2981024, 0.2902576, 0.2833934, 0.2755486, 0.2686844, 0.2618202, 0.254956,
    0.2490724, 0.2431888, 0.2373052, 0.2314216, 0.2265186, 0.220635, 0.215732, 0.210829, 0.205926, 0.2020036,
    0.1971006, 0.1931782, 0.1892558, 0.1853334, 0.181411, 0.1774886, 0.1735662, 0.1706244, 0.166702, 0.1637602]

# Check if ODB name already exists
existing_odbs = scan_user_odbs(username)
if odb_name in existing_odbs:
    print(f"ERROR: ODB '{{odb_name}}' already exists for user '{{username}}'!")
    print("Please choose a different name or delete the existing ODB.")
else:
    # Build model
    print("Building structural model...")
    build_model(Tn, Sa)
    print("✓ Model built successfully")

    # Analysis parameters
    section_response_dof = {{"SectionAggregator": ["P", "MZ", "MY", "T", "VY", "VZ"]}}
    damping_ratio = 0.05
    scale_factor = 1.0

    # Run response spectrum analysis and save ODB
    # ODB will be saved as: RespStepData-{{username}}-{{odb_name}}.odb
    print(f"Running response spectrum analysis for user: {{username}}")
    returned_odb_tag, num_modes = response_spectrum_analysis(
        username=username,
        odb_name=odb_name,
        section_response_dof=section_response_dof,
        damping_ratio=damping_ratio,
        scale_factor=scale_factor,
        Tn=Tn,
        Sa=Sa,
        direction=1,
        num_modes=7
    )

    print(f"✓ Analysis complete! ODB saved as: RespStepData-{{returned_odb_tag}}.odb")
    print(f"✓ Number of modes analyzed: {{num_modes}}")
"""
        
        odb_code = st.text_area(
            "⚙️ Response Spectrum Analysis & ODB Creation Code",
            value=default_rsa_odb_code,
            height=600,
            help="Run response spectrum analysis and save ODB",
            key="rsa_odb_code"
        )
    
    # GRAVITY ANALYSIS
    elif analysis_type_step1 == "Gravity Analysis":
        st.subheader("Gravity Analysis Configuration")
        
        default_gravity_odb_code = f"""import openseespy.opensees as ops
import opstool as opst

# User and ODB info
username = "{st.session_state.current_user}"
odb_name = "{odb_name}"

# Check if ODB name already exists
existing_odbs = scan_user_odbs(username)
if odb_name in existing_odbs:
    print(f"ERROR: ODB '{{odb_name}}' already exists for user '{{username}}'!")
    print("Please choose a different name or delete the existing ODB.")
else:
    # Clear any existing model
    ops.wipe()

    # Load example model - uncomment one of these:
    opst.load_ops_examples("Shell3D")
    # opst.load_ops_examples("ArchBridge")
    # opst.load_ops_examples("suspensionbridge")
    # opst.load_ops_examples("Frame3D2")

    # Apply loads
    print("Applying loads...")
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)

    # Example: gravity load for shell
    _ = opst.pre.gen_grav_load(direction="z", factor=-9810)

    # For frame/bridge models, use instead:
    # ops.load(6, 10, 0.0, 0.0, 0.0, 0.0, 0.0)
    # ops.eleLoad("-ele", 5, "-type", "-beamUniform", 0.0, -10)

    # Set up analysis
    print("Setting up analysis...")
    ops.system("BandGeneral")
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.test("NormDispIncr", 1.0e-12, 10, 3)
    ops.algorithm("Newton")
    ops.integrator("LoadControl", 0.1)
    ops.analysis("Static")

    # Create user-specific ODB tag using dash
    # This will create: RespStepData-{{username}}-{{odb_name}}.odb
    full_odb_tag = f"{{username}}-{{odb_name}}"
    
    print(f"Creating ODB with tag: {{full_odb_tag}}")

    # For shell elements:
    ODB = opst.post.CreateODB(odb_tag=full_odb_tag, project_gauss_to_nodes="copy")

    # For frame elements with fiber sections (IMPORTANT for fiber response extraction):
    # ODB = opst.post.CreateODB(
    #     odb_tag=full_odb_tag, 
    #     elastic_frame_sec_points=9,
    #     save_fiber_sec_resp=True,
    #     fiber_ele_tags=[1, 2]
    # )

    # For standard frame elements:
    # ODB = opst.post.CreateODB(odb_tag=full_odb_tag, elastic_frame_sec_points=9)

    # Run analysis and collect responses
    print("Running analysis...")
    num_steps = 10
    for i in range(num_steps):
        ops.analyze(1)
        ODB.fetch_response_step()
        if (i+1) % 2 == 0:
            print(f"  Completed step {{i+1}}/{{num_steps}}")

    # Save the ODB
    print(f"Saving ODB as 'RespStepData-{{full_odb_tag}}.odb'...")
    ODB.save_response()
    print(f"✓ ODB saved successfully! Tag: {{full_odb_tag}}")
"""
        
        odb_code = st.text_area(
            "⚙️ OpenSees Model & ODB Creation Code",
            value=default_gravity_odb_code,
            height=600,
            help="Write your OpenSees code to create model, run analysis, and save ODB",
            key="gravity_odb_code"
        )
    
    # Run button
    col1, col2 = st.columns([1, 4])
    with col1:
        run_button = st.button("▶️ Run & Save ODB", type="primary")
    with col2:
        if st.button("🔄 Refresh ODB List"):
            st.rerun()
    
    if run_button:
        if not odb_name or odb_name.strip() == "":
            st.error("Please enter a valid ODB name!")
        elif " " in odb_name or not odb_name.replace("_", "").replace("-", "").isalnum():
            st.error("ODB name can only contain letters, numbers, underscores, and hyphens!")
        else:
            user_odbs = scan_user_odbs(st.session_state.current_user)
            if odb_name in user_odbs:
                st.error(f"❌ ODB '{odb_name}' already exists! Please choose a different name or delete the existing one.")
            else:
                with st.spinner("Running analysis and saving ODB..."):
                    try:
                        # Create execution context with all necessary functions and modules
                        exec_context = {
                            'ops': ops,
                            'opst': opst,
                            'np': np,
                            'build_model': build_model,
                            'response_spectrum_analysis': response_spectrum_analysis,
                            'scan_user_odbs': scan_user_odbs,
                            'st': st,
                            'os': os
                        }
                        exec(odb_code, exec_context)
                        st.success(f"✅ ODB '{odb_name}' created and saved successfully!")
                        st.info(f"📊 ODB saved as: {st.session_state.current_user}/{odb_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

# ========================================================================================
# STEP 2: EXTRACT RESPONSES
# ========================================================================================
elif workflow_step == "2. Extract Responses":
    st.header("Step 2: Extract Responses from ODB")
    st.info(f"👤 User: **{st.session_state.current_user}**")
    
    user_odbs = scan_user_odbs(st.session_state.current_user)
    
    if not user_odbs:
        st.warning("⚠️ No ODBs found! Please create and save an ODB first in Step 1.")
        st.stop()
    
    st.subheader("Select ODB")
    selected_odb = st.selectbox(
        "Your ODBs",
        user_odbs,
        help="Select the ODB you want to extract data from"
    )
    
    st.subheader("Select Analysis Type")
    analysis_type = st.selectbox(
        "Analysis Type",
        ["Response Spectrum Analysis", "Gravity Analysis"],
        help="Choose the type of analysis to extract responses from"
    )
    
    # RESPONSE SPECTRUM ANALYSIS
    if analysis_type == "Response Spectrum Analysis":
        st.subheader("Response Spectrum Analysis - Extract Results")
        
        default_rs_extraction_code = f"""import opstool as opst

# User-specific ODB tag
username = "{st.session_state.current_user}"
odb_name = "{selected_odb}"
# ODB is stored as: RespStepData-{{username}}-{{odb_name}}.odb
full_odb_tag = f"{{username}}-{{odb_name}}"

print(f"Loading ODB: RespStepData-{{full_odb_tag}}.odb")
opst.post.loadODB(odb_tag=full_odb_tag)

# Post-processing parameters
output_dir = f"output_results/{{username}}/{{odb_name}}"
num_modes = 7

# Extract and visualize results
post_processing(
    odb_tag=full_odb_tag,
    num_modes=num_modes,
    output_dir=output_dir,
    visualize_modes=6,
    nodal_output_dir="nodal_response",
    nodal_resp_types=["disp", "vel", "accel", "reaction"],
    node_ids=[2, 3, 5, 6, 7, 8, 9, 11],
    selected_dofs=["UX", "UY", "UZ"],
    frame_output_dir="frame_response",
    frame_resp_types=["sectionForces", "sectionDeformations", "basicForces", "basicDeformations"],
    ele_ids=list(range(1, 17)),
    response_dofs=["MY", "MZ", "VY", "VZ"],
    visualize_resp_types=["sectionForces", "sectionDeformations"]
)

print("✓ Post-processing complete!")
"""
        
        rs_extraction_code = st.text_area(
            "⚙️ Post-Processing Configuration",
            value=default_rs_extraction_code,
            height=450,
            key="rs_extraction_code"
        )
        
        if st.button("📊 Extract & Visualize Results", type="primary", key="extract_rs_results"):
            with st.spinner("Extracting and visualizing response spectrum results..."):
                try:
                    # Create execution context with all necessary functions
                    exec_context = {
                        'opst': opst,
                        'ops': ops,
                        'np': np,
                        'post_processing': post_processing,
                        'st': st,
                        'os': os,
                        're': __import__('re')
                    }
                    exec(rs_extraction_code, exec_context)
                    
                    st.success("✅ Post-processing complete!")
                    
                    import re
                    match = re.search(r'output_dir\s*=\s*f?"?([^"\']+)"?', rs_extraction_code)
                    if match:
                        output_dir = match.group(1).replace("{username}", st.session_state.current_user).replace("{odb_name}", selected_odb)
                    else:
                        output_dir = f"output_results/{st.session_state.current_user}/{selected_odb}"
                    
                    if os.path.exists(output_dir):
                        zip_path = create_zip(output_dir, f"{st.session_state.current_user}_{selected_odb}_results")
                        if zip_path and os.path.exists(zip_path):
                            with open(zip_path, 'rb') as f:
                                st.download_button(
                                    "⬇️ Download All Results (ZIP)",
                                    f,
                                    f"{st.session_state.current_user}_{selected_odb}_results.zip",
                                    "application/zip"
                                )
                        
                        nodal_dir = os.path.join(output_dir, "nodal_response")
                        if os.path.exists(nodal_dir):
                            st.subheader("📊 Nodal Responses")
                            display_json_files(nodal_dir)
                        
                        frame_dir = os.path.join(output_dir, "frame_response")
                        if os.path.exists(frame_dir):
                            st.subheader("📊 Frame Responses")
                            display_json_files(frame_dir)
                            display_html_files(frame_dir)
                        
                        st.subheader("📊 Model & Eigen Visualizations")
                        display_html_files(output_dir)
                    
                except Exception as e:
                    st.error(f"Error during extraction: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

    elif analysis_type == "Gravity Analysis":
        st.subheader("Gravity Analysis - Extract Results")
        
        st.subheader("Select Extraction Type")
        extraction_type = st.selectbox(
            "Response Type to Extract",
            ["Nodal Response", "Frame Response", "Shell Response", "Eigen Analysis"],
            help="Choose the type of response data to extract"
        )
        
        if extraction_type == "Nodal Response":
            default_nodal_code = f"""import opstool as opst
import json
import os

# User-specific ODB tag
username = "{st.session_state.current_user}"
odb_name = "{selected_odb}"
# ODB is stored as: RespStepData-{{username}}-{{odb_name}}.odb
full_odb_tag = f"{{username}}-{{odb_name}}"

print(f"Loading ODB: RespStepData-{{full_odb_tag}}.odb")
opst.post.loadODB(odb_tag=full_odb_tag)

# Output directory
output_dir = f"output_results/{{username}}/{{odb_name}}/nodal_response"
os.makedirs(output_dir, exist_ok=True)

# Get nodal responses
print("Extracting nodal responses...")
nodal_resp_types = ["disp", "vel", "accel", "reaction"]
node_ids = [1, 2, 3, 4, 5]  # Modify based on your model
selected_dofs = ["UX", "UY", "UZ", "RX", "RY", "RZ"]

for resp_type in nodal_resp_types:
    print(f"  Extracting {{resp_type}}...")
    try:
        node_data = opst.post.get_nodal_responses(
            odb_tag=full_odb_tag, 
            resp_type=resp_type, 
            lazy_load=True
        )
        
        data = {{
            "response_type": resp_type,
            "analysis_type": "Gravity",
            "data": {{
                "time": node_data.coords["time"].data.tolist(),
                "node_tags": node_data.coords["nodeTags"].data.tolist(),
                "dofs": node_data.coords["DOFs"].data.tolist() if "DOFs" in node_data.coords else [],
                "node_values": {{}}
            }}
        }}
        
        # Extract data for specified nodes
        for node_id in node_ids:
            if node_id in node_data.coords["nodeTags"].data:
                if "DOFs" in node_data.coords:
                    available_dofs = [dof for dof in selected_dofs 
                                    if dof in node_data.coords["DOFs"].data]
                    if available_dofs:
                        node_response = node_data.sel(nodeTags=node_id, DOFs=available_dofs)
                        data["data"]["node_values"][f"node_{{node_id}}"] = {{}}
                        
                        for i, dof in enumerate(available_dofs):
                            values = [float(v) for v in node_response[:, i].values]
                            data["data"]["node_values"][f"node_{{node_id}}"][dof] = values
        
        # Save to JSON
        filename = f"{{output_dir}}/{{resp_type}}_response.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"  ✓ {{resp_type}} saved to {{filename}}")
    except Exception as e:
        print(f"  ✗ Error extracting {{resp_type}}: {{str(e)}}")

print("✓ Nodal response extraction complete!")
"""
            
            extraction_code = st.text_area(
                "⚙️ Nodal Response Extraction Code",
                value=default_nodal_code,
                height=500,
                key="gravity_nodal_extraction"
            )
        
        elif extraction_type == "Frame Response":
            default_frame_code = f"""import opstool as opst
import json
import os

# User-specific ODB tag
username = "{st.session_state.current_user}"
odb_name = "{selected_odb}"
full_odb_tag = f"{{username}}-{{odb_name}}"

print(f"Loading ODB: {{full_odb_tag}}")
opst.post.loadODB(odb_tag=full_odb_tag)

# Output directory
output_dir = f"output_results/{{username}}/{{odb_name}}/frame_response"
os.makedirs(output_dir, exist_ok=True)

# Get frame element responses
print("Extracting frame element responses...")
ele_resp = opst.post.get_element_responses(odb_tag=full_odb_tag, ele_type="Frame")
print(f"Available response types: {{list(ele_resp.keys())}}")

frame_resp_types = ["sectionForces", "sectionDeformations", "basicForces", "basicDeformations"]
ele_ids = [1, 2, 3]  # Modify based on your model

for resp_type in frame_resp_types:
    if resp_type not in ele_resp:
        print(f"  ✗ {{resp_type}} not available")
        continue
        
    print(f"  Extracting {{resp_type}}...")
    
    resp_array = ele_resp[resp_type]
    
    if resp_type in ["sectionForces", "sectionDeformations"]:
        dof_dim = "secDofs"
        selected_frame_dofs = ["N", "MY", "MZ", "VY", "VZ", "T"]
        has_sections = True
    elif resp_type in ["basicForces", "basicDeformations"]:
        dof_dim = "basicDofs"
        selected_frame_dofs = ["N", "MY1", "MY2", "MZ1", "MZ2", "T"]
        has_sections = False
    else:
        continue
    
    data = {{
        "response_type": resp_type,
        "analysis_type": "Gravity",
        "data": {{
            "time": resp_array.coords["time"].data.tolist(),
            "ele_tags": resp_array.coords["eleTags"].data.tolist(),
            "dofs": resp_array.coords[dof_dim].data.tolist(),
            "element_values": {{}}
        }}
    }}
    
    if has_sections:
        data["data"]["sec_points"] = resp_array.coords["secPoints"].data.tolist()
    
    available_dofs = resp_array.coords[dof_dim].data.tolist()
    valid_dofs = [dof for dof in selected_frame_dofs if dof in available_dofs]
    
    for ele_id in ele_ids:
        if ele_id in resp_array.coords["eleTags"].data:
            if has_sections:
                ele_response = resp_array.sel(eleTags=ele_id, **{{dof_dim: valid_dofs}})
                data["data"]["element_values"][f"ele_{{ele_id}}"] = {{}}
                
                for sec_pt in resp_array.coords["secPoints"].data:
                    sec_data = ele_response.sel(secPoints=sec_pt)
                    data["data"]["element_values"][f"ele_{{ele_id}}"][f"sec_{{sec_pt}}"] = {{}}
                    for i, dof in enumerate(valid_dofs):
                        values = [float(v) for v in sec_data[:, i].values]
                        data["data"]["element_values"][f"ele_{{ele_id}}"][f"sec_{{sec_pt}}"][dof] = values
            else:
                ele_response = resp_array.sel(eleTags=ele_id, **{{dof_dim: valid_dofs}})
                data["data"]["element_values"][f"ele_{{ele_id}}"] = {{}}
                for i, dof in enumerate(valid_dofs):
                    values = [float(v) for v in ele_response[:, i].values]
                    data["data"]["element_values"][f"ele_{{ele_id}}"][dof] = values
    
    filename = f"{{output_dir}}/frame_{{resp_type}}_response.json"
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"  ✓ {{resp_type}} saved to {{filename}}")

print("✓ Frame response extraction complete!")
"""
            
            extraction_code = st.text_area(
                "⚙️ Frame Response Extraction Code",
                value=default_frame_code,
                height=500,
                key="gravity_frame_extraction"
            )
        
        elif extraction_type == "Shell Response":
            default_shell_code = f"""import opstool as opst
import json
import os

# User-specific ODB tag
username = "{st.session_state.current_user}"
odb_name = "{selected_odb}"
full_odb_tag = f"{{username}}-{{odb_name}}"

print(f"Loading ODB: {{full_odb_tag}}")
opst.post.loadODB(odb_tag=full_odb_tag)

# Output directory
output_dir = f"output_results/{{username}}/{{odb_name}}/shell_response"
os.makedirs(output_dir, exist_ok=True)

# Get shell element responses
print("Extracting shell element responses...")
ele_resp = opst.post.get_element_responses(odb_tag=full_odb_tag, ele_type="Shell")
print(f"Available response types: {{list(ele_resp.keys())}}")

shell_resp_types = ["stress", "strain", "force"]
ele_ids = [1, 2, 3]  # Modify based on your model

for resp_type in shell_resp_types:
    if resp_type not in ele_resp:
        print(f"  ✗ {{resp_type}} not available")
        continue
        
    print(f"  Extracting {{resp_type}}...")
    
    resp_array = ele_resp[resp_type]
    
    data = {{
        "response_type": resp_type,
        "analysis_type": "Gravity",
        "data": {{
            "time": resp_array.coords["time"].data.tolist(),
            "ele_tags": resp_array.coords["eleTags"].data.tolist(),
            "element_values": {{}}
        }}
    }}
    
    for ele_id in ele_ids:
        if ele_id in resp_array.coords["eleTags"].data:
            ele_response = resp_array.sel(eleTags=ele_id)
            data["data"]["element_values"][f"ele_{{ele_id}}"] = ele_response.values.tolist()
    
    filename = f"{{output_dir}}/shell_{{resp_type}}_response.json"
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"  ✓ {{resp_type}} saved to {{filename}}")

print("✓ Shell response extraction complete!")
"""
            
            extraction_code = st.text_area(
                "⚙️ Shell Response Extraction Code",
                value=default_shell_code,
                height=500,
                key="gravity_shell_extraction"
            )
        
        elif extraction_type == "Eigen Analysis":
            default_eigen_code = f"""import opstool as opst
import os

# User-specific ODB tag
username = "{st.session_state.current_user}"
odb_name = "{selected_odb}"
full_odb_tag = f"{{username}}-{{odb_name}}"

print(f"Loading ODB: {{full_odb_tag}}")
opst.post.loadODB(odb_tag=full_odb_tag)

# Output directory
output_dir = f"output_results/{{username}}/{{odb_name}}/eigen_analysis"
os.makedirs(output_dir, exist_ok=True)

print("Creating eigen mode visualizations...")

# Import pyvista visualization
import opstool.vis.pyvista as pyvista_vis
pyvista_vis.set_plot_props(notebook=False)

# Plot model
fig = pyvista_vis.plot_model()
fig.export_html(os.path.join(output_dir, "model.html"))
print(f"  ✓ Model saved to {{output_dir}}/model.html")

# Plot eigen modes (adjust num_modes as needed)
num_modes = 6
fig = pyvista_vis.plot_eigen(mode_tags=list(range(1, num_modes+1)), subplots=True, scale=2)
fig.export_html(os.path.join(output_dir, "eigen_modes.html"))
print(f"  ✓ Eigen modes saved to {{output_dir}}/eigen_modes.html")

print("✓ Eigen analysis visualization complete!")
"""
            
            extraction_code = st.text_area(
                "⚙️ Eigen Analysis Code",
                value=default_eigen_code,
                height=400,
                key="gravity_eigen_extraction"
            )
        
        # Extract button
        if st.button("📊 Extract Results", type="primary", key="extract_gravity_results"):
            with st.spinner(f"Extracting {extraction_type}..."):
                try:
                    # Create execution context with all necessary functions
                    exec_context = {
                        'opst': opst,
                        'ops': ops,
                        'np': np,
                        'json': json,
                        'os': os,
                        'st': st,
                        're': __import__('re')
                    }
                    exec(extraction_code, exec_context)
                    
                    st.success(f"✅ {extraction_type} extraction complete!")
                    
                    # Determine output directory
                    import re
                    match = re.search(r'output_dir\s*=\s*f?"?([^"\']+)"?', extraction_code)
                    if match:
                        output_dir = match.group(1).replace("{username}", st.session_state.current_user).replace("{odb_name}", selected_odb)
                    else:
                        output_dir = f"output_results/{st.session_state.current_user}/{selected_odb}"
                    
                    if os.path.exists(output_dir):
                        # Create zip
                        zip_path = create_zip(output_dir, f"{st.session_state.current_user}_{selected_odb}_{extraction_type.replace(' ', '_')}")
                        if zip_path and os.path.exists(zip_path):
                            with open(zip_path, 'rb') as f:
                                st.download_button(
                                    "⬇️ Download Results (ZIP)",
                                    f,
                                    f"{st.session_state.current_user}_{selected_odb}_{extraction_type.replace(' ', '_')}.zip",
                                    "application/zip"
                                )
                        
                        # Display results
                        st.subheader(f"📊 {extraction_type} Results")
                        display_json_files(output_dir)
                        display_html_files(output_dir)
                    
                except Exception as e:
                    st.error(f"Error during extraction: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

# ========================================================================================
# MOMENT-CURVATURE ANALYSIS
# ========================================================================================
elif workflow_step == "3. Moment-Curvature Analysis":
    st.header("📐 Moment-Curvature Analysis")
    st.info(f"👤 User: **{st.session_state.current_user}**")
    
    tab1, tab2 = st.tabs(["⚙️ Setup & Run", "📊 Results"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Define Section Code")
            
            code_input = st.text_area(
                "Enter OpenSees commands to define your section",
                value=st.session_state.mc_code_input,
                height=500,
                key="mc_code_area",
                help="Define materials, fibers, and section properties"
            )
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("💾 Save Code", use_container_width=True, key="mc_save"):
                    st.session_state.mc_code_input = code_input
                    st.success("Code saved!")
            
            with col_b:
                if st.button("🔄 Reset to Default", use_container_width=True, key="mc_reset"):
                    st.session_state.mc_code_input = """# Model initialization
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Uniaxial materials
ops.uniaxialMaterial('Concrete01', 101, -4.0, -0.002, -0.8, -0.006)
ops.uniaxialMaterial('Concrete01', 102, -5.0, -0.002, -1.0, -0.008)
ops.uniaxialMaterial('Steel01', 103, 60.0, 29000.0, 0.015)

# Fiber section
ops.section('Fiber', 1, '-GJ', 36591031599.06977)
ops.fiber(-5.0, 6.583333, 1.5, 101)
ops.fiber(3.333333, -8.0, 1.5, 101)
ops.fiber(3.333333, 8.0, 1.5, 101)

# Rebar
ops.fiber(-4.5, -7.5, 0.7853982, 103)
ops.fiber(4.5, -7.5, 0.7853982, 103)
ops.fiber(4.5, 7.5, 0.7853982, 103)
ops.fiber(-4.5, 7.5, 0.7853982, 103)

sec_tag = 1
"""
                    st.rerun()
            
            with col_c:
                if st.button("🗑️ Clear", use_container_width=True, key="mc_clear"):
                    st.session_state.mc_code_input = ""
                    st.rerun()
        
        with col2:
            st.subheader("📤 Upload Section PKL (Optional)")
            
            uploaded_pkl = st.file_uploader(
                "Upload my_section.pkl file",
                type=['pkl'],
                key="mc_pkl",
                help="Upload a pre-saved section pickle file"
            )
            
            if uploaded_pkl:
                try:
                    SEC = pickle.load(uploaded_pkl)
                    st.session_state.sec_object = SEC
                    st.success("✅ Section loaded from PKL!")
                    
                    try:
                        fig, ax = plt.subplots(figsize=(5, 5))
                        SEC.view(fill=False)
                        plt.title("Section Geometry")
                        st.pyplot(fig)
                        plt.close()
                    except:
                        st.warning("Could not visualize section")
                except Exception as e:
                    st.error(f"Error loading PKL: {str(e)}")
            
            st.markdown("---")
            
            st.subheader("⚙️ Analysis Parameters")
            
            analysis_type = st.selectbox(
                "Analysis Type",
                ["Monotonic", "Cyclic"],
                help="Monotonic: push to max curvature. Cyclic: apply cycles."
            )
            
            axial_force = st.number_input(
                "Axial Force",
                value=-20000.0,
                format="%.2f",
                help="Negative for compression"
            )
            
            max_phi = st.number_input(
                "Max Curvature",
                value=0.1,
                format="%.4f",
                help="Maximum curvature to analyze"
            )
            
            axis = st.selectbox(
                "Bending Axis",
                ["y", "z"],
                help="Axis about which bending occurs"
            )
            
            if analysis_type == "Cyclic":
                n_cycles = st.number_input(
                    "Number of Cycles",
                    min_value=1,
                    max_value=20,
                    value=5,
                    help="Number of loading cycles"
                )
            
            st.markdown("---")
            
            pkl_uploaded = 'sec_object' in st.session_state and st.session_state.sec_object is not None
            
            if not pkl_uploaded:
                st.info("💡 You can run analysis with code only, or upload a PKL file for visualization")
            
            if st.button("▶️ RUN ANALYSIS", type="primary", use_container_width=True, key="mc_run"):
                with st.spinner("Running moment-curvature analysis..."):
                    # Create user-specific output directory
                    user_output_dir = f"output_results/{st.session_state.current_user}/moment_curvature"
                    os.makedirs(user_output_dir, exist_ok=True)
                    
                    try:
                        # Execute section code
                        exec(st.session_state.mc_code_input, {"ops": ops})
                        
                        local_vars = {}
                        exec(st.session_state.mc_code_input, {"ops": ops}, local_vars)
                        sec_tag = local_vars.get('sec_tag', 1)
                        
                        st.success("✅ Section created successfully!")
                        
                        # Create moment-curvature analyzer
                        MC = opst_anlys.MomentCurvature(sec_tag=sec_tag, axial_force=axial_force)
                        
                        # Run analysis
                        if analysis_type == "Cyclic":
                            MC.set_cycle_path(max_phi=max_phi, n_cycle=n_cycles, n_hold=2)
                            MC.analyze(axis=axis, cycle_analyze=True, incr_phi=1e-3, 
                                     limit_peak_ratio=0.8, smart_analyze=True)
                        else:
                            MC.analyze(axis=axis, max_phi=max_phi, incr_phi=1e-4, 
                                     limit_peak_ratio=0.8, smart_analyze=True)
                        
                        st.success("✅ Analysis completed successfully!")
                        
                        plots = {}
                        
                        # Plot 1: Moment-Curvature
                        fig1, ax1 = plt.subplots(figsize=(10, 6))
                        phi, M = MC.get_M_phi()
                        ax1.plot(phi, M, 'b-', linewidth=2)
                        ax1.set_xlabel('Curvature', fontsize=12)
                        ax1.set_ylabel('Moment', fontsize=12)
                        ax1.set_title(f'Moment-Curvature Response ({analysis_type})', fontsize=14)
                        ax1.grid(True, alpha=0.3)
                        plt.tight_layout()
                        path = f"{user_output_dir}/moment_curvature.png"
                        plt.savefig(path, dpi=300, bbox_inches='tight')
                        plt.close()
                        plots['mc'] = path
                        
                        # Plot 2: Fiber Responses
                        fig2, ax2 = plt.subplots(figsize=(10, 6))
                        MC.plot_fiber_responses()
                        plt.title('Fiber Stress-Strain Responses', fontsize=14)
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        path = f"{user_output_dir}/fiber_responses.png"
                        plt.savefig(path, dpi=300, bbox_inches='tight')
                        plt.close()
                        plots['fiber'] = path
                        
                        # Get fiber data
                        fiber_data = MC.get_fiber_data()
                        fiber_data_last = fiber_data.isel(Steps=-1)
                        y = fiber_data_last.sel(Properties="yloc")
                        z = fiber_data_last.sel(Properties="zloc")
                        strain = fiber_data_last.sel(Properties="strain")
                        stress = fiber_data_last.sel(Properties="stress")
                        
                        # Plot 3: Strain Distribution
                        fig3, ax3 = plt.subplots(figsize=(8, 6))
                        scatter = ax3.scatter(y, z, c=strain, s=50, cmap="rainbow")
                        plt.colorbar(scatter, ax=ax3, label='Strain')
                        ax3.set_xlabel("Y Coordinate", fontsize=12)
                        ax3.set_ylabel("Z Coordinate", fontsize=12)
                        ax3.set_title("Strain Distribution at Final Step", fontsize=14)
                        ax3.axis('equal')
                        ax3.grid(True, alpha=0.3)
                        plt.tight_layout()
                        path = f"{user_output_dir}/strain_distribution.png"
                        plt.savefig(path, dpi=300, bbox_inches='tight')
                        plt.close()
                        plots['strain'] = path
                        
                        # Plot 4: Stress Distribution
                        fig4, ax4 = plt.subplots(figsize=(8, 6))
                        scatter = ax4.scatter(y, z, c=stress, s=50, cmap="rainbow")
                        plt.colorbar(scatter, ax=ax4, label='Stress')
                        ax4.set_xlabel("Y Coordinate", fontsize=12)
                        ax4.set_ylabel("Z Coordinate", fontsize=12)
                        ax4.set_title("Stress Distribution at Final Step", fontsize=14)
                        ax4.axis('equal')
                        ax4.grid(True, alpha=0.3)
                        plt.tight_layout()
                        path = f"{user_output_dir}/stress_distribution.png"
                        plt.savefig(path, dpi=300, bbox_inches='tight')
                        plt.close()
                        plots['stress'] = path
                        
                        # Save data to JSON
                        data = {
                            'analysis_type': analysis_type,
                            'axial_force': axial_force,
                            'max_curvature': max_phi,
                            'bending_axis': axis,
                            'curvature': phi.tolist(),
                            'moment': M.tolist()
                        }
                        
                        if analysis_type == "Cyclic":
                            data['n_cycles'] = n_cycles
                        
                        json_path = f"{user_output_dir}/mc_data.json"
                        with open(json_path, "w") as f:
                            json.dump(data, f, indent=2)
                        plots['data'] = json_path
                        
                        st.session_state.mc_results = {
                            'plots': plots,
                            'output_dir': user_output_dir,
                            'type': analysis_type,
                            'user': st.session_state.current_user
                        }
                        
                        st.success("✅ Results saved! Go to Results tab.")
                        
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                        st.code(traceback.format_exc())
    
    with tab2:
        if st.session_state.mc_results is None:
            st.info("⚠️ Run analysis first in the Setup & Run tab")
        else:
            results = st.session_state.mc_results
            plots = results['plots']
            
            st.success(f"✅ {results['type']} Analysis Complete")
            
            # Moment-Curvature Plot
            if 'mc' in plots and os.path.exists(plots['mc']):
                st.subheader("Moment-Curvature Response")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.image(plots['mc'], use_container_width=True)
                with col2:
                    with open(plots['mc'], 'rb') as f:
                        st.download_button(
                            "⬇️ Download",
                            f.read(),
                            "moment_curvature.png",
                            "image/png",
                            use_container_width=True
                        )
            
            # Fiber Responses
            if 'fiber' in plots and os.path.exists(plots['fiber']):
                st.subheader("Fiber Stress-Strain Responses")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.image(plots['fiber'], use_container_width=True)
                with col2:
                    with open(plots['fiber'], 'rb') as f:
                        st.download_button(
                            "⬇️ Download",
                            f.read(),
                            "fiber_responses.png",
                            "image/png",
                            use_container_width=True
                        )
            
            # Strain and Stress Distributions
            col1, col2 = st.columns(2)
            
            with col1:
                if 'strain' in plots and os.path.exists(plots['strain']):
                    st.subheader("Strain Distribution")
                    st.image(plots['strain'], use_container_width=True)
                    with open(plots['strain'], 'rb') as f:
                        st.download_button(
                            "⬇️ Download",
                            f.read(),
                            "strain_distribution.png",
                            "image/png",
                            use_container_width=True,
                            key="strain_dl"
                        )
            
            with col2:
                if 'stress' in plots and os.path.exists(plots['stress']):
                    st.subheader("Stress Distribution")
                    st.image(plots['stress'], use_container_width=True)
                    with open(plots['stress'], 'rb') as f:
                        st.download_button(
                            "⬇️ Download",
                            f.read(),
                            "stress_distribution.png",
                            "image/png",
                            use_container_width=True,
                            key="stress_dl"
                        )
            
            # JSON Data Download
            if 'data' in plots and os.path.exists(plots['data']):
                st.subheader("📄 Analysis Data")
                with open(plots['data'], 'r') as f:
                    st.download_button(
                        "⬇️ Download Data (JSON)",
                        f.read(),
                        "moment_curvature_data.json",
                        "application/json",
                        use_container_width=True
                    )
            
            # Create ZIP
            st.subheader("📦 Download All Results")
            if st.button("Create ZIP Archive", use_container_width=True, key="mc_zip"):
                with st.spinner("Creating ZIP archive..."):
                    try:
                        import shutil
                        zip_path = f"{results['output_dir']}/mc_results"
                        shutil.make_archive(zip_path, 'zip', results['output_dir'])
                        with open(f"{zip_path}.zip", 'rb') as f:
                            st.download_button(
                                "⬇️ Download ZIP",
                                f.read(),
                                f"moment_curvature_results_{st.session_state.current_user}.zip",
                                "application/zip",
                                use_container_width=True,
                                key="mc_zip_dl"
                            )
                    except Exception as e:
                        st.error(f"Error creating ZIP: {str(e)}")

# ========================================================================================
# LINEAR BUCKLING ANALYSIS
# ========================================================================================
# elif workflow_step == "4. Linear Buckling Analysis":
#     st.header("🔧 Linear Buckling Analysis")
#     st.info(f"👤 User: **{st.session_state.current_user}**")
    
#     tab1, tab2 = st.tabs(["⚙️ Setup & Run", "📊 Results"])
    
#     with tab1:
#         col1, col2 = st.columns([2, 1])
        
#         with col1:
#             st.subheader("Define Model Code")
        
#         code_input = st.text_area(
#             "Enter OpenSees model commands",
#             value=st.session_state.buckling_code_input,
#             height=500,
#             key="buckling_code_area",
#             help="Define nodes, elements, mesh, and boundary conditions"
#         )
        
#         col_a, col_b, col_c = st.columns(3)
#         with col_a:
#             if st.button("💾 Save Code", use_container_width=True, key="buck_save"):
#                 st.session_state.buckling_code_input = code_input
#                 st.success("Code saved!")
        
#         with col_b:
#             if st.button("🔄 Reset to Default", use_container_width=True, key="buck_reset"):
#                 st.session_state.buckling_code_input = """# Model parameters
# L = 50.0
# h = 8.0
# t = 1.0
# E = 29000
# v = 0.3
# mesh_factor = 4

# # Create model
# ops.wipe()
# ops.model("basic", "-ndm", 3, "-ndf", 6)

# ops.node(1, 0, -h/2, 0)
# ops.node(2, 0, h/2, 0)
# ops.node(3, 0, h/2, L)
# ops.node(4, 0, -h/2, L)

# c = h / mesh_factor
# ops.mesh("line", 1, 2, 1, 2, 0, 6, c)
# ops.mesh("line", 2, 2, 2, 3, 0, 6, c)
# ops.mesh("line", 3, 2, 3, 4, 0, 6, c)
# ops.mesh("line", 4, 2, 4, 1, 0, 6, c)

# ops.section("ElasticMembranePlateSection", 1, E, v, t)
# ops.mesh("quad", 13, 4, 4, 3, 2, 1, 0, 6, c, "ShellNLDKGT", 1)

# ops.fixZ(0, 1, 1, 1, 0, 0, 0)
# ops.fixZ(L, 1, 1, 0, 0, 0, 0)
# ops.fix(1, 0, 0, 0, 1, 0, 0)

# mesh_tag = 3
# """
#                 st.rerun()
        
#         with col_c:
#             if st.button("🗑️ Clear", use_container_width=True, key="buck_clear"):
#                 st.session_state.buckling_code_input = ""
#                 st.rerun()
    
#     with col2:
#         st.subheader("⚙️ Analysis Parameters")
        
#         Pref = st.number_input(
#             "Reference Load",
#             value=1.0,
#             format="%.4f",
#             help="Reference load for buckling analysis"
#         )
        
#         n_modes = st.number_input(
#             "Number of Modes",
#             min_value=1,
#             max_value=20,
#             value=6,
#             help="Number of buckling modes to calculate"
#         )
        
#         st.markdown("**Visualization Settings**")
        
#         mode_start = st.number_input(
#             "Visualize Mode Start",
#             min_value=1,
#             value=1,
#             help="First mode to visualize"
#         )
        
#         mode_end = st.number_input(
#             "Visualize Mode End",
#             min_value=1,
#             value=6,
#             help="Last mode to visualize"
#         )
        
#         cmap = st.selectbox(
#             "Colormap",
#             ["spectral", "viridis", "plasma", "coolwarm", "rainbow"],
#             help="Color scheme for visualization"
#         )
        
#         show_model = st.checkbox("Show Model Plot", value=True)
#         show_bc = st.checkbox("Show Boundary Conditions", value=True)
#         subplots = st.checkbox("Use Subplots", value=True)
        
#         odb_tag = st.text_input(
#             "Output Database Tag",
#             value=f"{st.session_state.current_user}-buckling",
#             help="Unique identifier for this analysis"
#         )
        
#         st.markdown("**Solver Settings**")
        
#         constraint_type = st.selectbox(
#             "Constraint Type",
#             ["Penalty", "Transformation", "Plain"]
#         )
        
#         if constraint_type == "Penalty":
#             alpha_s = st.number_input("Alpha S", value=1e10, format="%.2e")
#             alpha_m = st.number_input("Alpha M", value=1e10, format="%.2e")
#             constraints_args = [constraint_type, alpha_s, alpha_m]
#         else:
#             constraints_args = [constraint_type]
        
#         system_type = st.selectbox(
#             "System Type",
#             ["FullGeneral", "BandGeneral", "SparseSYM"]
#         )
#         system_args = [system_type]
        
#         numberer_type = st.selectbox(
#             "Numberer Type",
#             ["RCM", "Plain", "AMD"]
#         )
#         numberer_args = [numberer_type]
        
#         st.markdown("---")
        
#         if st.button("▶️ RUN ANALYSIS", type="primary", use_container_width=True, key="buck_run"):
#             with st.spinner("Running linear buckling analysis..."):
#                 # Create user-specific output directory
#                 user_output_dir = f"output_results/{st.session_state.current_user}/buckling"
#                 os.makedirs(user_output_dir, exist_ok=True)
                
#                 output_dir = tempfile.mkdtemp()
                
#                 try:
#                     # Execute model code
#                     local_vars = {}
#                     exec(st.session_state.buckling_code_input, {"ops": ops, "opst": opst}, local_vars)
                    
#                     mesh_tag = local_vars.get('mesh_tag', 3)
                    
#                     st.success("✅ Model created successfully!")
                    
#                     # Plot model if requested
#                     model_html_path = None
#                     if show_model:
#                         try:
#                             fig = opst.vis.plotly.plot_model()
#                             model_html_path = os.path.join(user_output_dir, "model.html")
#                             fig.write_html(model_html_path)
#                             st.success("✅ Model visualization created!")
#                         except Exception as e:
#                             st.warning(f"Could not create model plot: {str(e)}")
                    
#                     # Buckling analysis
#                     st.info("Computing stiffness matrices...")
#                     kmat = opst.pre.get_mck(
#                         "k",
#                         constraints_args=constraints_args,
#                         system_args=system_args,
#                         numberer_args=numberer_args
#                     )
                    
#                     # Apply reference load
#                     endNodes = ops.getNodeTags("-mesh", mesh_tag)
#                     dP = Pref / len(endNodes)
                    
#                     ops.timeSeries("Constant", 1)
#                     ops.pattern("Plain", 1, 1)
#                     for nd in endNodes:
#                         ops.load(nd, 0, 0, -dP, 0, 0, 0)
                    
#                     ops.analysis("Static", "-noWarnings")
#                     ops.analyze(1)
                    
#                     st.info("Computing geometric stiffness...")
#                     k = opst.pre.get_mck(
#                         "k",
#                         constraints_args=constraints_args,
#                         system_args=system_args,
#                         numberer_args=numberer_args
#                     )
#                     kgeo = kmat - k
                    
#                     # Save buckling data
#                     st.info("Solving eigenvalue problem...")
#                     opst.post.save_linear_buckling_data(
#                         kmat=kmat,
#                         kgeo=kgeo,
#                         n_modes=n_modes,
#                         odb_tag=odb_tag
#                     )
                    
#                     eigenvalues, eigenvectors = opst.post.get_linear_buckling_data(odb_tag=odb_tag)
                    
#                     st.success("✅ Buckling analysis completed!")
                    
#                     # Save results to user directory
#                     eigenvalues_df = eigenvalues.to_pandas()
#                     modal_data = {
#                         "user": st.session_state.current_user,
#                         "odb_tag": odb_tag,
#                         "total_modes": len(eigenvalues_df),
#                         "reference_load": Pref,
#                         "buckling_factors": {}
#                     }
                    
#                     for mode_idx in eigenvalues_df.index:
#                         buckling_factor = eigenvalues_df.loc[mode_idx]
#                         if hasattr(buckling_factor, 'item'):
#                             buckling_factor = buckling_factor.item()
#                         modal_data["buckling_factors"][f"mode_{mode_idx}"] = {
#                             "mode_number": int(mode_idx),
#                             "buckling_factor": float(buckling_factor),
#                             "critical_load": float(buckling_factor * Pref)
#                         }
                    
#                     json_path = os.path.join(user_output_dir, "buckling_results.json")
#                     with open(json_path, 'w') as f:
#                         json.dump(modal_data, f, indent=4)
                    
#                     # Save eigenvectors to user directory
#                     npz_path = os.path.join(user_output_dir, "eigen_vectors.npz")
#                     np.savez_compressed(
#                         npz_path,
#                         eigen_vectors=eigenvectors.values,
#                         mode_tags=eigenvectors.modeTags.values,
#                         node_tags=eigenvectors.nodeTags.values,
#                         dofs=eigenvectors.DOFs.values
#                     )
                    
#                     # Visualize buckling modes
#                     st.info("Creating visualizations...")
#                     opst.vis.pyvista.set_plot_colors(cmap=cmap)
#                     fig = opst.vis.pyvista.plot_eigen(
#                         mode="buckling",
#                         mode_tags=[mode_start, mode_end],
#                         odb_tag=odb_tag,
#                         subplots=subplots,
#                         show_bc=show_bc
#                     )
                    
#                     html_path = os.path.join(user_output_dir, "buckling_modes.html")
#                     fig.export_html(html_path)
                    
#                     st.success("✅ Visualizations created!")
                    
#                     results = {
#                         'modal_data': modal_data,
#                         'output_dir': user_output_dir,
#                         'json_path': json_path,
#                         'npz_path': npz_path,
#                         'html_path': html_path,
#                         'model_html': model_html_path,
#                         'user': st.session_state.current_user
#                     }
                    
#                     st.session_state.buckling_results = results
#                     st.success("✅ Results saved! Go to Results tab.")
                    
#                 except Exception as e:
#                     st.error(f"Analysis failed: {str(e)}")
#                     st.code(traceback.format_exc())
    
#     with tab2:
#         if st.session_state.buckling_results is None:
#             st.info("⚠️ Run analysis first in the Setup & Run tab")
#         else:
#             results = st.session_state.buckling_results
            
#             st.success("✅ Linear Buckling Analysis Complete")
            
#             # Display buckling factors table
#             st.subheader("Buckling Factors and Critical Loads")
#             modal_data = results['modal_data']
            
#             buckling_table = []
#             for mode_key, mode_info in modal_data['buckling_factors'].items():
#                 buckling_table.append({
#                     'Mode': mode_info['mode_number'],
#                     'Buckling Factor': f"{mode_info['buckling_factor']:.6f}",
#                     'Critical Load': f"{mode_info['critical_load']:.6f}"
#                 })
            
#             st.dataframe(buckling_table, use_container_width=True)
            
#             # Download buttons
#             col1, col2 = st.columns(2)
#             with col1:
#                 if os.path.exists(results['json_path']):
#                     with open(results['json_path'], 'r') as f:
#                         st.download_button(
#                             "⬇️ Download Results (JSON)",
#                             f.read(),
#                             f"buckling_results_{st.session_state.current_user}.json",
#                             "application/json",
#                             use_container_width=True
#                         )
            
#             with col2:
#                 if os.path.exists(results['npz_path']):
#                     with open(results['npz_path'], 'rb') as f:
#                         st.download_button(
#                             "⬇️ Download Eigenvectors (NPZ)",
#                             f.read(),
#                             f"eigen_vectors_{st.session_state.current_user}.npz",
#                             "application/octet-stream",
#                             use_container_width=True
#                         )
            
#             # Model Visualization
#             if results['model_html'] and os.path.exists(results['model_html']):
#                 st.subheader("Model Visualization")
#                 with open(results['model_html'], 'r', encoding='utf-8') as f:
#                     html_content = f.read()
#                 st.components.v1.html(html_content, height=600, scrolling=True)
                
#                 with open(results['model_html'], 'rb') as f:
#                     st.download_button(
#                         "⬇️ Download Model HTML",
#                         f.read(),
#                         "model.html",
#                         "text/html",
#                         use_container_width=True,
#                         key="model_html_dl"
#                     )
            
#             # Buckling Modes Visualization
#             if os.path.exists(results['html_path']):
#                 st.subheader("Buckling Modes Visualization")
#                 with open(results['html_path'], 'r', encoding='utf-8') as f:
#                     html_content = f.read()
#                 st.components.v1.html(html_content, height=600, scrolling=True)
                
#                 with open(results['html_path'], 'rb') as f:
#                     st.download_button(
#                         "⬇️ Download Modes HTML",
#                         f.read(),
#                     "buckling_modes.html",
#                     "text/html",
#                     use_container_width=True,
#                     key="modes_html_dl"
#                 )
            
#             # Create ZIP
#             st.subheader("📦 Download All Results")
#             if st.button("Create ZIP Archive", use_container_width=True, key="buck_zip"):
#                 with st.spinner("Creating ZIP archive..."):
#                     try:
#                         import shutil
#                         zip_path = f"{results['output_dir']}/buckling_results"
#                         shutil.make_archive(zip_path, 'zip', results['output_dir'])
#                         with open(f"{zip_path}.zip", 'rb') as f:
#                             st.download_button(
#                                 "⬇️ Download ZIP",
#                                 f.read(),
#                                 f"buckling_results_{st.session_state.current_user}.zip",
#                                 "application/zip",
#                                     key="buck_zip_dl"
#                             )
#                     except Exception as e:
#                         st.error(f"Error creating ZIP: {str(e)}")

elif workflow_step == "4. Linear Buckling Analysis":
    st.header("🔧 Linear Buckling Analysis")
    st.info(f"👤 User: **{st.session_state.current_user}**")
    
    tab1, tab2 = st.tabs(["⚙️ Setup & Run", "📊 Results"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Define Model Code")
        
            # This text_area should be indented under with col1:
            code_input = st.text_area(
                "Enter OpenSees model commands",
                value=st.session_state.buckling_code_input,
                height=500,
                key="buckling_code_area",
                help="Define nodes, elements, mesh, and boundary conditions"
            )
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("💾 Save Code", use_container_width=True, key="buck_save"):
                    st.session_state.buckling_code_input = code_input
                    st.success("Code saved!")
            
            with col_b:
                if st.button("🔄 Reset to Default", use_container_width=True, key="buck_reset"):
                    st.session_state.buckling_code_input = """# Model parameters
L = 50.0
h = 8.0
t = 1.0
E = 29000
v = 0.3
mesh_factor = 4

# Create model
ops.wipe()
ops.model("basic", "-ndm", 3, "-ndf", 6)

ops.node(1, 0, -h/2, 0)
ops.node(2, 0, h/2, 0)
ops.node(3, 0, h/2, L)
ops.node(4, 0, -h/2, L)

c = h / mesh_factor
ops.mesh("line", 1, 2, 1, 2, 0, 6, c)
ops.mesh("line", 2, 2, 2, 3, 0, 6, c)
ops.mesh("line", 3, 2, 3, 4, 0, 6, c)
ops.mesh("line", 4, 2, 4, 1, 0, 6, c)

ops.section("ElasticMembranePlateSection", 1, E, v, t)
ops.mesh("quad", 13, 4, 4, 3, 2, 1, 0, 6, c, "ShellNLDKGT", 1)

ops.fixZ(0, 1, 1, 1, 0, 0, 0)
ops.fixZ(L, 1, 1, 0, 0, 0, 0)
ops.fix(1, 0, 0, 0, 1, 0, 0)

mesh_tag = 3
"""
                    st.rerun()
            
            with col_c:
                if st.button("🗑️ Clear", use_container_width=True, key="buck_clear"):
                    st.session_state.buckling_code_input = ""
                    st.rerun()
        
        # This should be at same level as "with col1:" - NOT inside it
        with col2:
            st.subheader("⚙️ Analysis Parameters")
            
            Pref = st.number_input(
                "Reference Load",
                value=1.0,
                format="%.4f",
                help="Reference load for buckling analysis"
            )
            
            n_modes = st.number_input(
                "Number of Modes",
                min_value=1,
                max_value=20,
                value=6,
                help="Number of buckling modes to calculate"
            )
            
            st.markdown("**Visualization Settings**")
            
            mode_start = st.number_input(
                "Visualize Mode Start",
                min_value=1,
                value=1,
                help="First mode to visualize"
            )
            
            mode_end = st.number_input(
                "Visualize Mode End",
                min_value=1,
                value=6,
                help="Last mode to visualize"
            )
            
            cmap = st.selectbox(
                "Colormap",
                ["spectral", "viridis", "plasma", "coolwarm", "rainbow"],
                help="Color scheme for visualization"
            )
            
            show_model = st.checkbox("Show Model Plot", value=True)
            show_bc = st.checkbox("Show Boundary Conditions", value=True)
            subplots = st.checkbox("Use Subplots", value=True)
            
            odb_tag = st.text_input(
                "Output Database Tag",
                value=f"{st.session_state.current_user}-buckling",
                help="Unique identifier for this analysis"
            )
            
            st.markdown("**Solver Settings**")
            
            constraint_type = st.selectbox(
                "Constraint Type",
                ["Penalty", "Transformation", "Plain"]
            )
            
            if constraint_type == "Penalty":
                alpha_s = st.number_input("Alpha S", value=1e10, format="%.2e")
                alpha_m = st.number_input("Alpha M", value=1e10, format="%.2e")
                constraints_args = [constraint_type, alpha_s, alpha_m]
            else:
                constraints_args = [constraint_type]
            
            system_type = st.selectbox(
                "System Type",
                ["FullGeneral", "BandGeneral", "SparseSYM"]
            )
            system_args = [system_type]
            
            numberer_type = st.selectbox(
                "Numberer Type",
                ["RCM", "Plain", "AMD"]
            )
            numberer_args = [numberer_type]
            
            st.markdown("---")
            
            if st.button("▶️ RUN ANALYSIS", type="primary", use_container_width=True, key="buck_run"):
                with st.spinner("Running linear buckling analysis..."):
                    # Create user-specific output directory
                    user_output_dir = f"output_results/{st.session_state.current_user}/buckling"
                    os.makedirs(user_output_dir, exist_ok=True)
                    
                    output_dir = tempfile.mkdtemp()
                    
                    try:
                        # Execute model code
                        local_vars = {}
                        exec(st.session_state.buckling_code_input, {"ops": ops, "opst": opst}, local_vars)
                        
                        mesh_tag = local_vars.get('mesh_tag', 3)
                        
                        st.success("✅ Model created successfully!")
                        
                        # Plot model if requested
                        model_html_path = None
                        if show_model:
                            try:
                                fig = opst.vis.plotly.plot_model()
                                model_html_path = os.path.join(user_output_dir, "model.html")
                                fig.write_html(model_html_path)
                                st.success("✅ Model visualization created!")
                            except Exception as e:
                                st.warning(f"Could not create model plot: {str(e)}")
                        
                        # Buckling analysis
                        st.info("Computing stiffness matrices...")
                        kmat = opst.pre.get_mck(
                            "k",
                            constraints_args=constraints_args,
                            system_args=system_args,
                            numberer_args=numberer_args
                        )
                        
                        # Apply reference load
                        endNodes = ops.getNodeTags("-mesh", mesh_tag)
                        dP = Pref / len(endNodes)
                        
                        ops.timeSeries("Constant", 1)
                        ops.pattern("Plain", 1, 1)
                        for nd in endNodes:
                            ops.load(nd, 0, 0, -dP, 0, 0, 0)
                        
                        ops.analysis("Static", "-noWarnings")
                        ops.analyze(1)
                        
                        st.info("Computing geometric stiffness...")
                        k = opst.pre.get_mck(
                            "k",
                            constraints_args=constraints_args,
                            system_args=system_args,
                            numberer_args=numberer_args
                        )
                        kgeo = kmat - k
                        
                        # Save buckling data
                        st.info("Solving eigenvalue problem...")
                        opst.post.save_linear_buckling_data(
                            kmat=kmat,
                            kgeo=kgeo,
                            n_modes=n_modes,
                            odb_tag=odb_tag
                        )
                        
                        eigenvalues, eigenvectors = opst.post.get_linear_buckling_data(odb_tag=odb_tag)
                        
                        st.success("✅ Buckling analysis completed!")
                        
                        # Save results to user directory
                        eigenvalues_df = eigenvalues.to_pandas()
                        modal_data = {
                            "user": st.session_state.current_user,
                            "odb_tag": odb_tag,
                            "total_modes": len(eigenvalues_df),
                            "reference_load": Pref,
                            "buckling_factors": {}
                        }
                        
                        for mode_idx in eigenvalues_df.index:
                            buckling_factor = eigenvalues_df.loc[mode_idx]
                            if hasattr(buckling_factor, 'item'):
                                buckling_factor = buckling_factor.item()
                            modal_data["buckling_factors"][f"mode_{mode_idx}"] = {
                                "mode_number": int(mode_idx),
                                "buckling_factor": float(buckling_factor),
                                "critical_load": float(buckling_factor * Pref)
                            }
                        
                        json_path = os.path.join(user_output_dir, "buckling_results.json")
                        with open(json_path, 'w') as f:
                            json.dump(modal_data, f, indent=4)
                        
                        # Save eigenvectors to user directory
                        npz_path = os.path.join(user_output_dir, "eigen_vectors.npz")
                        np.savez_compressed(
                            npz_path,
                            eigen_vectors=eigenvectors.values,
                            mode_tags=eigenvectors.modeTags.values,
                            node_tags=eigenvectors.nodeTags.values,
                            dofs=eigenvectors.DOFs.values
                        )
                        
                        # Visualize buckling modes
                        st.info("Creating visualizations...")
                        opst.vis.pyvista.set_plot_colors(cmap=cmap)
                        fig = opst.vis.pyvista.plot_eigen(
                            mode="buckling",
                            mode_tags=[mode_start, mode_end],
                            odb_tag=odb_tag,
                            subplots=subplots,
                            show_bc=show_bc
                        )
                        
                        html_path = os.path.join(user_output_dir, "buckling_modes.html")
                        fig.export_html(html_path)
                        
                        st.success("✅ Visualizations created!")
                        
                        results = {
                            'modal_data': modal_data,
                            'output_dir': user_output_dir,
                            'json_path': json_path,
                            'npz_path': npz_path,
                            'html_path': html_path,
                            'model_html': model_html_path,
                            'user': st.session_state.current_user
                        }
                        
                        st.session_state.buckling_results = results
                        st.success("✅ Results saved! Go to Results tab.")
                        
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
                        st.code(traceback.format_exc())
    
    with tab2:
        if st.session_state.buckling_results is None:
            st.info("⚠️ Run analysis first in the Setup & Run tab")
        else:
            results = st.session_state.buckling_results
            
            st.success("✅ Linear Buckling Analysis Complete")
            
            # Display buckling factors table
            st.subheader("Buckling Factors and Critical Loads")
            modal_data = results['modal_data']
            
            buckling_table = []
            for mode_key, mode_info in modal_data['buckling_factors'].items():
                buckling_table.append({
                    'Mode': mode_info['mode_number'],
                    'Buckling Factor': f"{mode_info['buckling_factor']:.6f}",
                    'Critical Load': f"{mode_info['critical_load']:.6f}"
                })
            
            st.dataframe(buckling_table, use_container_width=True)
            
            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                if os.path.exists(results['json_path']):
                    with open(results['json_path'], 'r') as f:
                        st.download_button(
                            "⬇️ Download Results (JSON)",
                            f.read(),
                            f"buckling_results_{st.session_state.current_user}.json",
                            "application/json",
                            use_container_width=True
                        )
            
            with col2:
                if os.path.exists(results['npz_path']):
                    with open(results['npz_path'], 'rb') as f:
                        st.download_button(
                            "⬇️ Download Eigenvectors (NPZ)",
                            f.read(),
                            f"eigen_vectors_{st.session_state.current_user}.npz",
                            "application/octet-stream",
                            use_container_width=True
                        )
            
            # Model Visualization
            if results['model_html'] and os.path.exists(results['model_html']):
                st.subheader("Model Visualization")
                with open(results['model_html'], 'r', encoding='utf-8') as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=600, scrolling=True)
                
                with open(results['model_html'], 'rb') as f:
                    st.download_button(
                        "⬇️ Download Model HTML",
                        f.read(),
                        "model.html",
                        "text/html",
                        use_container_width=True,
                        key="model_html_dl"
                    )
            
            # Buckling Modes Visualization
            if os.path.exists(results['html_path']):
                st.subheader("Buckling Modes Visualization")
                with open(results['html_path'], 'r', encoding='utf-8') as f:
                    html_content = f.read()
                st.components.v1.html(html_content, height=600, scrolling=True)
                
                with open(results['html_path'], 'rb') as f:
                    st.download_button(
                        "⬇️ Download Modes HTML",
                        f.read(),
                    "buckling_modes.html",
                    "text/html",
                    use_container_width=True,
                    key="modes_html_dl"
                )
            
            # Create ZIP
            st.subheader("📦 Download All Results")
            if st.button("Create ZIP Archive", use_container_width=True, key="buck_zip"):
                with st.spinner("Creating ZIP archive..."):
                    try:
                        import shutil
                        zip_path = f"{results['output_dir']}/buckling_results"
                        shutil.make_archive(zip_path, 'zip', results['output_dir'])
                        with open(f"{zip_path}.zip", 'rb') as f:
                            st.download_button(
                                "⬇️ Download ZIP",
                                f.read(),
                                f"buckling_results_{st.session_state.current_user}.zip",
                                "application/zip",
                                    key="buck_zip_dl"
                            )
                    except Exception as e:
                        st.error(f"Error creating ZIP: {str(e)}")

    # The rest of the code for tab2 remains the same...
# ========================================================================================
# PROFILE SECTION
# ========================================================================================
elif workflow_step == "👤 Profile":
    st.header("👤 User Profile")
    
    # Get user data
    user_data = st.session_state.users.get(st.session_state.current_user, {})
    
    # Profile Information Card
    st.subheader("Account Information")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Personal Details")
        st.info(f"""
        **Username:** {st.session_state.current_user}
        
        **Email:** {user_data.get('email', 'N/A')}
        
        **Account Status:** Active ✅
        """)
    
    with col2:
        st.markdown("### Statistics")
        user_odbs = scan_user_odbs(st.session_state.current_user)
        
        # Count output files and calculate storage
        output_dir = f"output_results/{st.session_state.current_user}"
        total_analyses = 0
        total_files = 0
        total_size = 0
        
        if os.path.exists(output_dir):
            total_analyses = len([d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))])
            
            # Calculate total size
            for dirpath, dirnames, filenames in os.walk(output_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                        total_files += 1
                    except:
                        pass
        
        size_mb = total_size / (1024 * 1024)
        
        st.metric("Total ODBs Created", len(user_odbs))
        st.metric("Analyses Completed", total_analyses)
        st.metric("Storage Used", f"{size_mb:.2f} MB")
    
    st.divider()
    
    # Storage Management
    st.subheader("💾 Storage Management")
    
    st.info("""
    **Output Results Directory**  
    Extracted results (JSON files, HTML visualizations) are stored in your output folder.  
    You can safely clear these files to free up space without affecting your ODBs.
    """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write(f"**Current storage:** {size_mb:.2f} MB")
        st.write(f"**Total files:** {total_files}")
        st.write(f"**Path:** `output_results/{st.session_state.current_user}/`")
    
    with col2:
        if st.button("🧹 Clear Output Results", type="secondary", help="Clear all extracted results to free up space"):
            if size_mb > 0:
                success, message = clear_output_results(st.session_state.current_user)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.info("No output results to clear!")
    
    st.caption("⚠️ This will delete all extracted JSON and HTML files, but your ODBs will remain intact.")
    
    st.divider()
    
    # Account Management
    st.subheader("⚙️ Account Management")
    
    st.warning("⚠️ **Danger Zone**")
    st.write("Deleting your account will permanently remove:")
    st.write("- Your account information")
    st.write(f"- All {len(user_odbs)} ODB(s)")
    st.write("- All analysis results and output files")
    st.write("")
    st.write("**This action cannot be undone!**")
    
    # Confirmation checkbox
    confirm_delete = st.checkbox("I understand that this action is irreversible", key="confirm_delete")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🗑️ Delete Account", type="secondary", disabled=not confirm_delete):
            if confirm_delete:
                # Show final confirmation dialog
                st.session_state.show_delete_confirm = True
    
    # Final confirmation
    if st.session_state.get('show_delete_confirm', False):
        st.error("### ⚠️ FINAL CONFIRMATION")
        st.write(f"Are you absolutely sure you want to delete the account **{st.session_state.current_user}**?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete My Account", type="primary", key="final_delete"):
                username = st.session_state.current_user
                success, message = delete_account(username)
                if success:
                    st.success(message)
                    st.info("You will be signed out in 3 seconds...")
                    import time
                    time.sleep(3)
                    sign_out()
                    st.session_state.show_delete_confirm = False
                    st.rerun()
                else:
                    st.error(message)
        
        with col2:
            if st.button("Cancel", key="cancel_delete"):
                st.session_state.show_delete_confirm = False
                st.rerun()

# ========================================================================================
# USER GUIDE SECTION
# ========================================================================================
elif workflow_step == "📖 User Guide":
    st.header("📖 User Guide")
    st.write("Welcome to the OpenSees Response Analyzer! This guide will help you get started.")
    
    # Introduction
    with st.expander("📚 **Introduction**", expanded=True):
        st.markdown("""
        ### What is OpenSees Response Analyzer?
        
        This application provides a user-friendly interface for creating, managing, and analyzing 
        **OpenSees** structural analysis databases (ODBs). Each user has their own isolated workspace 
        where they can:
        
        - ✅ Create and save analysis databases (ODBs)
        - ✅ Run Response Spectrum Analysis (RSA)
        - ✅ Perform Gravity Analysis
        - ✅ Extract and visualize structural responses
        - ✅ Download results in JSON and HTML formats
        
        ---
        
        ### Key Features
        
        🔐 **Secure Authentication**: Each user has a private account with encrypted password  
        📊 **User-Specific ODBs**: Your ODBs are isolated and only visible to you  
        🗑️ **ODB Management**: Create, view, and delete your ODBs easily  
        📈 **Response Extraction**: Extract nodal, frame, shell, and eigen responses  
        💾 **Download Results**: Get your analysis results in JSON and HTML formats  
        """)
    
    # Getting Started
    with st.expander("🚀 **Getting Started**"):
        st.markdown("""
        ### Step 1: Create Your First ODB
        
        1. Navigate to **"1. Create & Save ODB"** from the sidebar
        2. Enter a unique name for your ODB (e.g., `building_analysis`)
        3. Choose an analysis type:
           - **Response Spectrum Analysis**: For seismic analysis
           - **Gravity Analysis**: For static gravity load analysis
        4. Review the pre-filled code template (you can modify it if needed)
        5. Click **"▶️ Run & Save ODB"**
        6. Wait for the analysis to complete
        
        Your ODB will appear in the sidebar under **"📊 Your ODBs"**!
        
        ---
        
        ### Step 2: Extract Responses
        
        1. Navigate to **"2. Extract Responses"** from the sidebar
        2. Select your ODB from the dropdown list
        3. Choose the analysis type (RSA or Gravity)
        4. For **Response Spectrum Analysis**:
           - The extraction code is pre-configured
           - Click **"📊 Extract & Visualize Results"**
           - View and download nodal/frame responses
        
        5. For **Gravity Analysis**, choose extraction type:
           - **Nodal Response**: Displacement, velocity, acceleration, reactions
           - **Frame Response**: Section forces, deformations, basic forces
           - **Shell Response**: Stress, strain, force distributions
           - **Eigen Analysis**: Mode shapes and eigenvalues
        """)
    
    # Analysis Types
    with st.expander("📊 **Analysis Types Explained**"):
        st.markdown("""
        ### Response Spectrum Analysis (RSA)
        
        **What is it?**  
        Response Spectrum Analysis is a seismic analysis method that determines the maximum 
        response of a structure to earthquake ground motion.
        
        **When to use it?**
        - Seismic design and analysis
        - Evaluating building response to earthquakes
        - Code compliance checks (UBC, IBC, Eurocode, etc.)
        
        **What you get:**
        - Modal properties (periods, frequencies)
        - Combined maximum responses using CQC method
        - Nodal displacements, velocities, accelerations
        - Frame element forces and deformations
        
        ---
        
        ### Gravity Analysis
        
        **What is it?**  
        Gravity Analysis applies static loads (like dead loads, live loads) to the structure 
        and calculates the resulting deformations and internal forces.
        
        **When to use it?**
        - Static load analysis
        - Dead load and live load combinations
        - Pre-stress analysis
        - Initial conditions for dynamic analysis
        
        **What you get:**
        - Nodal displacements and reactions
        - Member forces (axial, shear, moment)
        - Element stresses and strains
        - Support reactions
        """)
    
    # ODB Management
    with st.expander("🗂️ **Managing Your ODBs**"):
        st.markdown("""
        ### Viewing Your ODBs
        
        All your ODBs are listed in the sidebar under **"📊 Your ODBs"**.  
        Each ODB shows:
        - The ODB name you specified
        - A delete button (🗑️) for removal
        
        ---
        
        ### Deleting an ODB
        
        1. Find the ODB in the sidebar list
        2. Click the **🗑️** button next to the ODB name
        3. The ODB and all its data will be permanently deleted
        
        ⚠️ **Warning**: This action cannot be undone!
        
        ---
        
        ### ODB Naming Rules
        
        ✅ **Valid names:**
        - `my_analysis`
        - `building-v2`
        - `RSA_Test_01`
        
        ❌ **Invalid names:**
        - `my analysis` (contains spaces)
        - `building/v2` (contains special characters)
        - Empty or duplicate names
        """)
    
    # Tips and Best Practices
    with st.expander("💡 **Tips & Best Practices**"):
        st.markdown("""
        ### Naming Conventions
        
        - Use descriptive names: `office_building_rsa` instead of `test1`
        - Include version numbers: `bridge_analysis_v2`
        - Use underscores or dashes: `frame_3d_analysis`
        
        ---
        
        ### Storage Management
        
        **Keep your workspace clean:**
        
        - **Clear Output Results** regularly to free up space (Profile → Storage Management)
        - Output results include JSON and HTML files from extractions
        - Clearing outputs does **NOT** delete your ODBs
        - You can always re-extract responses from your ODBs
        
        **When to clear:**
        - After downloading important results
        - When storage space is running low
        - After completing a project phase
        
        ---
        
        ### Code Customization
        
        The pre-filled code templates can be modified:
        
        - **Change model parameters**: Update node coordinates, element properties
        - **Modify analysis settings**: Adjust damping, scale factors, number of modes
        - **Select different responses**: Choose which nodes/elements to extract
        - **Add custom loads**: Include your specific load patterns
        
        ---
        
        ### Performance Tips
        
        - Start with small models to verify your setup
        - Use appropriate number of modes (typically 6-12 for RSA)
        - Extract only the responses you need
        - Delete old ODBs you no longer need
        - Clear output results after downloading
        
        ---
        
        ### Troubleshooting
        
        **ODB not appearing?**
        - Click the **🔄 Refresh ODB List** button
        - Check if the analysis completed without errors
        
        **Extraction fails?**
        - Verify the ODB tag matches your saved ODB
        - Check that the nodes/elements you're requesting exist
        - Review the error traceback for specific issues
        
        **Analysis takes too long?**
        - Reduce the number of modes
        - Simplify your model
        - Check for modeling errors
        
        **Running out of space?**
        - Use **Clear Output Results** in Profile section
        - Delete unused ODBs
        - Download and archive old results
        """)
    
    # Data Format Guide
    with st.expander("📄 **Understanding Output Data**"):
        st.markdown("""
        ### JSON Response Files
        
        Response data is saved in JSON format with this structure:
        
        ```json
        {
          "response_type": "disp",
          "analysis_type": "ResponseSpectrum",
          "note": "time=0 is combined CQC response",
          "data": {
            "time": [0, 1, 2, ...],
            "node_tags": [1, 2, 3, ...],
            "dofs": ["UX", "UY", "UZ"],
            "node_values": {
              "node_1": {
                "combined_response": {"UX": 0.05, "UY": 0.02},
                "modal_responses": {"UX": [0.01, 0.02, ...]}
              }
            }
          }
        }
        ```
        
        **Key Fields:**
        - `response_type`: Type of response (disp, vel, accel, reaction, etc.)
        - `time`: Time steps (0 = combined, 1+ = modal responses)
        - `node_values`: Response data organized by node
        - `combined_response`: Maximum response from CQC combination
        - `modal_responses`: Individual mode contributions
        
        ---
        
        ### HTML Visualizations
        
        Interactive 3D visualizations include:
        - **model.html**: 3D model geometry
        - **eigen_modes.html**: Animated mode shapes
        - **frame_responses.html**: Element force/deformation diagrams
        
        You can:
        - Rotate, zoom, and pan the 3D view
        - Toggle element visibility
        - Inspect values by hovering
        - Download images
        """)
    
    # FAQ
    with st.expander("❓ **Frequently Asked Questions**"):
        st.markdown("""
        ### General Questions
        
        **Q: How many ODBs can I create?**  
        A: There's no strict limit, but consider deleting old ODBs you no longer need.
        
        **Q: Can other users see my ODBs?**  
        A: No, each user's ODBs are completely isolated and private.
        
        **Q: What happens if I forget my password?**  
        A: Currently there's no password recovery. Make sure to remember your password!
        
        **Q: Can I download my ODB files?**  
        A: Yes! Use the download buttons to get ZIP files with all results.
        
        **Q: How much storage space do I have?**  
        A: Check your storage usage in the Profile section under Statistics.
        
        ---
        
        ### Storage & File Management
        
        **Q: What's the difference between ODBs and Output Results?**  
        A: ODBs are the analysis databases. Output Results are extracted JSON/HTML files. You can safely delete Output Results and re-extract them from ODBs later.
        
        **Q: Will clearing output results delete my ODBs?**  
        A: No! Clearing output results only removes extracted JSON and HTML files. Your ODBs remain safe and can be used to re-extract data anytime.
        
        **Q: How do I free up storage space?**  
        A: Use the **"🧹 Clear Output Results"** button in Profile → Storage Management. This removes extracted files but keeps your ODBs intact.
        
        **Q: What happens to my files when I clear output results?**  
        A: All JSON files and HTML visualizations in your `output_results/{username}/` folder are deleted. You can re-extract them from your ODBs if needed.
        
        **Q: Should I clear output results regularly?**  
        A: Yes, especially after downloading important results. This keeps your workspace clean and frees up storage for new analyses.
        
        ---
        
        ### Technical Questions
        
        **Q: What version of OpenSees is used?**  
        A: The application uses OpenSeesPy with the latest stable version.
        
        **Q: Can I use my own OpenSees model?**  
        A: Yes! Modify the code template with your model definition.
        
        **Q: What's the difference between section and basic forces?**  
        A: Section forces are at integration points; basic forces are at element ends.
        
        **Q: How is CQC combination performed?**  
        A: Complete Quadratic Combination accounts for modal correlation.
        
        ---
        
        ### Account Questions
        
        **Q: How do I change my email?**  
        A: Email changes aren't currently supported. Create a new account if needed.
        
        **Q: What happens when I delete my account?**  
        A: All your ODBs, results, and account data are permanently deleted.
        
        **Q: Can I recover a deleted ODB?**  
        A: No, deletions are permanent. Download important results before deleting!
        
        **Q: Can I recover cleared output results?**  
        A: No, but you can re-extract them from your ODBs using Step 2: Extract Responses.
        """)
    
    # Contact and Support
    with st.expander("📞 **Contact & Support**"):
        st.markdown("""
        ### Need Help?
        
        If you encounter issues or have questions:
        
        1. **Check this User Guide** - Most common questions are answered here
        2. **Review error messages** - They often explain what went wrong
        3. **Try the example models** - Start with pre-configured examples
        4. **Check your code** - Verify node/element numbering and connectivity
        
        ---
        
        ### Resources
        
        - **OpenSees Documentation**: [opensees.berkeley.edu](https://opensees.berkeley.edu)
        - **OpenSeesPy**: [openseespydoc.readthedocs.io](https://openseespydoc.readthedocs.io)
        - **Opstool Library**: [opstool.readthedocs.io](https://opstool.readthedocs.io)
        
        ---
        
        ### Version Information
        
        **Application Version**: 2.0  
        **Last Updated**: January 2025  
        **Features**: Authentication, Multi-user support, ODB management  
        """)
    
    st.divider()
    
    # Quick Start Card
    st.info("""
    ### 🎯 Quick Start Summary
    
    1️⃣ **Create ODB** → Enter name → Choose analysis → Run  
    2️⃣ **Extract Results** → Select ODB → Choose extraction type → Download  
    3️⃣ **View in Sidebar** → Manage your ODBs → Delete when done  
    
    **Ready to start?** Click **"1. Create & Save ODB"** in the sidebar! 🚀
    """)

st.markdown("---")
st.caption(f"OpenSees Response Analyzer | User: {st.session_state.current_user if st.session_state.authenticated else 'Not logged in'}")


