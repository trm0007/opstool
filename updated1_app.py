"""
Structural Model Builder - Professional Streamlit App with Authentication
Multi-user support with isolated workspace
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
        'examples': get_default_examples()
    }
    save_users()
    
    # Create user directory
    user_dir = f"./user_data/{username}"
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(f"{user_dir}/models", exist_ok=True)
    os.makedirs(f"{user_dir}/examples", exist_ok=True)
    
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
    
    # Load user's examples
    if 'examples' not in user_data:
        user_data['examples'] = get_default_examples()
        save_users()
    
    return True, "Login successful!"


def sign_out():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.config_text = ""
    st.session_state.config_added = False
    st.session_state.model_built = False
    st.session_state.selected_example = None


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
# EXISTING HELPER FUNCTIONS
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
# PROFESSIONAL STYLES
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
                        # Load user's examples
                        st.session_state.examples = load_user_examples(login_username)
                        st.session_state.output_dir = f"./user_data/{login_username}/output"
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
    
    # Profile Section
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
    
    if st.button("🗑️ Delete Account", type="secondary", disabled=not confirm_delete):
        if confirm_delete:
            username = st.session_state.current_user
            success, message = delete_account(username)
            if success:
                st.success(message)
                sign_out()
                st.rerun()
            else:
                st.error(message)
    
    if st.button("Close Profile"):
        st.session_state.show_profile = False
        st.rerun()


# ========================================================================================
# MAIN APPLICATION (Only shown when authenticated)
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

# TAB 2: BUILD & RESULTS
with tab2:
    if st.session_state.config_added:
        st.markdown('<div class="section-header">Build Model</div>', unsafe_allow_html=True)
        
        # Model name input
        model_name = st.text_input("Model Name", value=f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                                   help="Enter a unique name for this model")
        model_description = st.text_input("Description (optional)", placeholder="Brief description of the model")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            with st.expander("📋 Configuration Preview"):
                st.code(st.session_state.config_text, language='python', line_numbers=True)
        
        with col2:
            if st.button("🔨 Build Model", type="primary", use_container_width=True):
                with st.spinner("Building model..."):
                    try:
                        # Create user-specific output directory
                        user_dir = f"./user_data/{st.session_state.current_user}/models/{model_name}"
                        os.makedirs(user_dir, exist_ok=True)
                        
                        # Save metadata
                        metadata = {
                            'name': model_name,
                            'description': model_description,
                            'created': datetime.now().isoformat(),
                            'username': st.session_state.current_user
                        }
                        with open(f"{user_dir}/metadata.json", 'w') as f:
                            json.dump(metadata, f, indent=2)
                        
                        # Save configuration
                        with open(f"{user_dir}/config.py", 'w') as f:
                            f.write(st.session_state.config_text)
                        
                        od = f"{user_dir}/output"
                        if os.path.exists(od):
                            shutil.rmtree(od)
                        os.makedirs(od, exist_ok=True)
                        
                        st.session_state.output_dir = od
                        
                        patch_gmsh()
                        
                        from test3 import build_model, generate_complete_model_file, create_regular_polygon_nodes
                        
                        eg = {
                            'build_model': build_model,
                            'generate_complete_model_file': generate_complete_model_file,
                            'np': __import__('numpy'),
                            'opst': __import__('opstool'),
                            'create_regular_polygon_nodes': create_regular_polygon_nodes
                        }
                        
                        exec(st.session_state.config_text, eg)
                        
                        if 'results' in eg:
                            st.session_state.build_results = eg['results']
                            # Save results
                            with open(f"{user_dir}/results.json", 'w') as f:
                                json.dump(eg['results'], f, indent=2)
                        
                        st.session_state.model_built = True
                        st.success("✅ Model built successfully!")
                        st.rerun()
                        
                    except Exception as e:
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

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; padding: 2rem 0;'>
    <p style='color: #6b7280; font-size: 0.9rem;'>
        🏗️ <strong>Structural Model Builder</strong> | User: {st.session_state.current_user}
    </p>
</div>
""", unsafe_allow_html=True)
