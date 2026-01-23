"""
Structural Model Builder - Streamlit App with Authentication
Clean, minimal code with organized structure
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
from test3 import build_model
from default_example import get_default_examples

# ========================================================================================
# CHAT SYSTEM
# ========================================================================================

def load_chat_messages():
    """Load chat messages from file"""
    chat_file = 'auth_data/chat_messages.json'
    if os.path.exists(chat_file):
        with open(chat_file, 'r') as f:
            return json.load(f)
    return []

def save_chat_messages(messages):
    """Save chat messages to file"""
    os.makedirs('auth_data', exist_ok=True)
    with open('auth_data/chat_messages.json', 'w') as f:
        json.dump(messages, f, indent=2)

def send_message(username, message):
    """Send a message to admin"""
    messages = load_chat_messages()
    messages.append({
        'id': len(messages) + 1,
        'username': username,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'is_admin_reply': False,
        'reply_to': None
    })
    save_chat_messages(messages)
    return True

def send_admin_reply(message_id, reply_text, admin_username):
    """Send admin reply to a user message"""
    messages = load_chat_messages()
    messages.append({
        'id': len(messages) + 1,
        'username': admin_username,
        'message': reply_text,
        'timestamp': datetime.now().isoformat(),
        'is_admin_reply': True,
        'reply_to': message_id
    })
    save_chat_messages(messages)
    return True

def get_user_conversations(username):
    """Get all messages for a specific user"""
    messages = load_chat_messages()
    user_messages = []
    
    for msg in messages:
        # Get user's own messages
        if msg['username'] == username and not msg['is_admin_reply']:
            user_messages.append(msg)
            # Find admin replies to this message
            for reply in messages:
                if reply.get('reply_to') == msg['id']:
                    user_messages.append(reply)
    
    return sorted(user_messages, key=lambda x: x['timestamp'])

def get_all_conversations():
    """Get all messages grouped by user (for admin view)"""
    messages = load_chat_messages()
    conversations = {}
    
    for msg in messages:
        if not msg['is_admin_reply']:
            user = msg['username']
            if user not in conversations:
                conversations[user] = []
            conversations[user].append(msg)
            
            # Add admin replies
            for reply in messages:
                if reply.get('reply_to') == msg['id']:
                    conversations[user].append(reply)
    
    # Sort each conversation by timestamp
    for user in conversations:
        conversations[user] = sorted(conversations[user], key=lambda x: x['timestamp'])
    
    return conversations

# ========================================================================================
# AUTHENTICATION
# ========================================================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def save_users():
    os.makedirs('auth_data', exist_ok=True)
    with open('auth_data/users.json', 'w') as f:
        json.dump(st.session_state.users, f)

def load_users():
    if os.path.exists('auth_data/users.json'):
        with open('auth_data/users.json', 'r') as f:
            return json.load(f)
    return {}

def sign_up(username, email, password):
    if username in st.session_state.users:
        return False, "Username already exists!"
    
    for user_data in st.session_state.users.values():
        if user_data['email'] == email:
            return False, "Email already registered!"
    
    st.session_state.users[username] = {
        'email': email,
        'password_hash': hash_password(password),
        'models': [],
        'examples': {}
    }
    save_users()
    
    user_dir = f"./user_data/{username}"
    os.makedirs(f"{user_dir}/models", exist_ok=True)
    
    return True, "Registration successful!"

def sign_in(username, password):
    if username not in st.session_state.users:
        return False, "Username not found!"
    
    if st.session_state.users[username]['password_hash'] != hash_password(password):
        return False, "Invalid password!"
    
    st.session_state.authenticated = True
    st.session_state.current_user = username
    return True, "Login successful!"

def sign_out():
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.config_text = ""
    st.session_state.config_added = False
    st.session_state.model_built = False
    st.session_state.selected_example = None
    st.session_state.examples = {}

# ========================================================================================
# USER DATA MANAGEMENT
# ========================================================================================

def get_user_models(username):
    models_dir = f"./user_data/{username}/models"
    if not os.path.exists(models_dir):
        return []
    
    models = []
    for item in os.listdir(models_dir):
        model_path = os.path.join(models_dir, item)
        if os.path.isdir(model_path):
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
                models.append({'name': item, 'created': 'Unknown', 'description': ''})
    
    return sorted(models, key=lambda x: x['created'], reverse=True)

def delete_user_model(username, model_name):
    model_path = f"./user_data/{username}/models/{model_name}"
    if os.path.exists(model_path):
        shutil.rmtree(model_path)
        return True, f"Model '{model_name}' deleted successfully!"
    return False, f"Model '{model_name}' not found!"

def delete_account(username):
    user_dir = f"./user_data/{username}"
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    
    if username in st.session_state.users:
        del st.session_state.users[username]
        save_users()
    
    return True, "Account deleted successfully!"

def save_user_examples(username):
    if username in st.session_state.users:
        st.session_state.users[username]['examples'] = st.session_state.examples
        save_users()

def load_user_examples(username):
    if username in st.session_state.users:
        user_examples = st.session_state.users[username].get('examples', {})
        if not user_examples:
            user_examples = get_default_examples()
            st.session_state.users[username]['examples'] = user_examples
            save_users()
        return user_examples
    return get_default_examples()

# ========================================================================================
# HELPER FUNCTIONS
# ========================================================================================

def create_regular_polygon_nodes(center_x, center_y, radius, n_sides, start_id, z=0.0):
    angles = np.linspace(0, 2*np.pi, n_sides + 1)[:-1]
    nodes = {}
    for i, angle in enumerate(angles):
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        nodes[start_id + i] = (x, y, z)
    return nodes

def patch_gmsh():
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
    try:
        compile(config_text, '<string>', 'exec')
        return True, "Valid"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def create_zip_archive(output_dir):
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_dir)
                z.write(file_path, arcname)
    buf.seek(0)
    return buf.getvalue()

def ensure_output_dir_in_config(config_text, output_dir):
    import re
    modified = re.sub(
        r'output_dir\s*=\s*[\'"][^\'"]*[\'"]',
        f'output_dir = "{output_dir}"',
        config_text
    )
    
    patterns = [
        r'[\'"]\./output[\'"]',
        r'[\'"]\./outputs/[\'"]',
        r'[\'"]\./outputs/building_model[\'"]',
        r'[\'"]outputs/building_model[\'"]'
    ]
    
    for pattern in patterns:
        modified = re.sub(pattern, f'"{output_dir}"', modified)
    
    return modified

# ========================================================================================
# SESSION STATE
# ========================================================================================

def init_session_state():
    defaults = {
        'authenticated': False,
        'current_user': None,
        'users': load_users(),
        'examples': {},
        'config_text': "",
        'config_added': False,
        'model_built': False,
        'output_dir': "output",
        'build_results': None,
        'selected_example': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ========================================================================================
# UI COMPONENTS
# ========================================================================================

def render_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
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

def render_auth_ui():
    st.markdown('<h1 class="main-title">🏗️ Structural Model Builder</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced Finite Element Analysis Platform</p>', unsafe_allow_html=True)
    st.info("Please sign in or sign up to start building structural models")
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    with tab1:
        st.subheader("Sign In")
        with st.form("signin_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.form_submit_button("Sign In", type="primary"):
                if username and password:
                    success, message = sign_in(username, password)
                    if success:
                        st.session_state.examples = get_default_examples()
                        st.session_state.output_dir = f"./user_data/{username}/output"
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all fields")
    
    with tab2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            username = st.text_input("Username", key="reg_user")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_pass")
            
            if st.form_submit_button("Sign Up", type="primary"):
                if username and email and password:
                    if "@" not in email or "." not in email:
                        st.error("Please enter a valid email address")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters")
                    elif " " in username:
                        st.error("Username cannot contain spaces")
                    else:
                        success, message = sign_up(username, email, password)
                        if success:
                            st.success(message)
                            st.info("Now you can sign in with your credentials")
                        else:
                            st.error(message)
                else:
                    st.warning("Please fill all fields")

def render_sidebar():
    with st.sidebar:
        st.success(f"👤 Logged in as: **{st.session_state.current_user}**")
        if st.button("🚪 Sign Out", use_container_width=True):
            sign_out()
            st.rerun()
        
        st.divider()
        
        if not st.session_state.examples:
            st.session_state.examples = get_default_examples()
        
        # User's Models
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
            st.info("No models created yet")
        
        st.divider()
        
        # Example Library
        st.markdown("### 📚 Example Library")
        
        for key, example in st.session_state.examples.items():
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
        
        st.markdown("---")
        
        # Add Example
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
        
        if st.button("👤 Profile", use_container_width=True):
            st.session_state.show_profile = True

def render_profile():
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
        st.write(f"Deleting your account will permanently remove all {len(user_models)} model(s), examples, and account information.")
        
        confirm_delete = st.checkbox("I understand that this action is irreversible", key="confirm_delete_profile")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Delete Account", type="secondary", disabled=not confirm_delete, use_container_width=True):
                if confirm_delete:
                    success, message = delete_account(st.session_state.current_user)
                    if success:
                        st.success(message)
                        sign_out()
                        st.rerun()
        
        with col2:
            if st.button("Close Profile", use_container_width=True):
                st.session_state.show_profile = False
                st.rerun()

def render_editor_tab():
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
                    if st.session_state.selected_example in st.session_state.examples:
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
        
        if st.session_state.config_text:
            st.download_button(
                "💾 Download Configuration",
                st.session_state.config_text.encode('utf-8'),
                f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py",
                "text/x-python",
                use_container_width=True
            )

def render_build_tab():
    if not st.session_state.config_added:
        st.info("⚠️ Please validate your configuration in the Editor tab first!")
        return
    
    st.markdown('<div class="section-header">Build Model</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        model_name = st.text_input(
            "Model Name", 
            value=f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    with col2:
        user_models = get_user_models(st.session_state.current_user)
        existing_names = [m['name'] for m in user_models]
        if model_name in existing_names:
            st.warning("⚠️ Name exists!")
        else:
            st.success("✓ Available")
    
    model_description = st.text_input("Description (optional)", placeholder="Brief description...")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        with st.expander("📋 Configuration Preview"):
            st.code(st.session_state.config_text, language='python', line_numbers=True)
    
    with col2:
        build_disabled = model_name in existing_names
        if st.button("🔨 Build Model", type="primary", use_container_width=True, disabled=build_disabled):
            build_model_process(model_name, model_description)
    
    # Results
    if st.session_state.model_built and os.path.exists(st.session_state.output_dir):
        render_results()

def build_model_process(model_name, model_description):
    original_dir = os.getcwd()  # Save original directory
    
    with st.spinner("Building model..."):
        try:
            # Setup
            user_dir = os.path.abspath(f"./user_data/{st.session_state.current_user}/models/{model_name}")
            os.makedirs(user_dir, exist_ok=True)
            
            # Save metadata
            metadata = {
                'name': model_name,
                'description': model_description,
                'created': datetime.now().isoformat(),
                'username': st.session_state.current_user
            }
            with open(os.path.join(user_dir, "metadata.json"), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save configs
            with open(os.path.join(user_dir, "config_original.py"), 'w') as f:
                f.write(st.session_state.config_text)
            
            # Setup output directory
            output_dir = os.path.join(user_dir, "output")
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            st.session_state.output_dir = output_dir
            
            # Modify config
            modified_config = ensure_output_dir_in_config(st.session_state.config_text, output_dir)
            
            with open(os.path.join(user_dir, "config_modified.py"), 'w') as f:
                f.write(modified_config)
            
            # Execute
            os.chdir(user_dir)
            patch_gmsh()
            
            exec_globals = {
                'build_model': build_model,
                'create_regular_polygon_nodes': create_regular_polygon_nodes,
                'np': __import__('numpy'),
                'opst': __import__('opstool'),
                'os': __import__('os'),
                'output_dir': output_dir,
                '__file__': os.path.join(user_dir, "config.py")
            }
            
            exec(modified_config, exec_globals)
            
            # Handle results
            if 'results' not in exec_globals:
                required_vars = ['model_params', 'fiber_configs', 'node_coords', 'boundary_conditions', 
                               'element_configs', 'nodal_spring_configs', 'diaphragm_list',
                               'load_configs', 'mass_configs', 'slab_configs']
                
                missing_vars = [var for var in required_vars if var not in exec_globals]
                
                if not missing_vars:
                    build_params = {k: exec_globals.get(k) for k in required_vars}
                    build_params.update({
                        'visualize': True,
                        'output_dir': output_dir,
                        'material_params': exec_globals.get('material_params', [])
                    })
                    exec_globals['results'] = build_model(**build_params)
            
            if 'results' in exec_globals:
                st.session_state.build_results = exec_globals['results']
                results_path = os.path.join(user_dir, "results.json")
                with open(results_path, 'w') as f:
                    json.dump(exec_globals['results'], f, indent=2)
            
            st.session_state.model_built = True
            st.success(f"✅ Model '{model_name}' built successfully!")
            
        except Exception as e:
            st.error(f"❌ Build error: {e}")
            import traceback
            st.code(traceback.format_exc(), language='python')
        
        finally:
            # Always restore the original directory
            os.chdir(original_dir)

def render_results():
    st.markdown("---")
    st.markdown('<div class="section-header">Build Results</div>', unsafe_allow_html=True)
    
    files = list(Path(st.session_state.output_dir).rglob("*"))
    imgs = [f for f in files if f.suffix.lower() in ['.png', '.jpg', '.jpeg'] and f.is_file()]
    pys = [f for f in files if f.suffix == '.py' and f.is_file()]
    htmls = [f for f in files if f.suffix == '.html' and f.is_file()]
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = [
        (st.session_state.build_results.get('total_nodes', '✓') if st.session_state.build_results else '✓', "Nodes"),
        (st.session_state.build_results.get('total_elements', '✓') if st.session_state.build_results else '✓', "Elements"),
        (len(imgs), "Images"),
        (len(pys) + len(htmls), "Files")
    ]
    
    for col, (value, label) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
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
    
    # Download options
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

def render_user_guide_tab():
    st.markdown('<div class="section-header">📖 How to Use This Platform</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### Welcome to Structural Model Builder! 🏗️
    
    **Getting Started:**
    
    1. **Select an Example**: Browse the example library in the sidebar and click on any example to load it into the editor.
    
    2. **Edit Configuration**: Modify the Python code in the Editor tab to customize your structural model parameters, materials, nodes, and elements.
    
    3. **Validate & Build**: Click "Validate" to check your configuration for errors, then switch to the "Build & Results" tab and click "Build Model" to generate your structural analysis.
    
    4. **View Results**: Once built, you can view 3D visualizations, download generated images, Python files, and export everything as a ZIP archive.
    
    **Tips:**
    - Save your custom configurations as new examples for future use
    - Give your models descriptive names to easily find them later
    - Use the Profile section to view your statistics and manage your account
    - All your models are saved and can be accessed anytime from the sidebar
    
    **Need Help?** Use the Chat tab to send a message to the administrator!
    """)

def render_chat_tab():
    st.markdown('<div class="section-header">💬 Chat with Administrator</div>', unsafe_allow_html=True)
    
    # Check if current user is admin (you can set this username as admin)
    is_admin = st.session_state.current_user == "admin"
    
    if is_admin:
        # Admin view - see all conversations
        st.info("👨‍💼 Admin Mode: View and reply to user messages")
        
        conversations = get_all_conversations()
        
        if not conversations:
            st.info("No messages yet!")
        else:
            # Select user to view conversation
            users = list(conversations.keys())
            selected_user = st.selectbox("Select User", users)
            
            if selected_user:
                st.markdown(f"### Conversation with: {selected_user}")
                
                # Display messages
                for msg in conversations[selected_user]:
                    if msg['is_admin_reply']:
                        st.markdown(f"""
                        <div style='background: #e3f2fd; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;'>
                            <strong>🛡️ Admin:</strong> {msg['message']}<br>
                            <small style='color: #666;'>{datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M')}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style='background: #f5f5f5; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;'>
                            <strong>👤 {msg['username']}:</strong> {msg['message']}<br>
                            <small style='color: #666;'>{datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M')}</small>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Reply form
                st.markdown("---")
                with st.form(f"admin_reply_{selected_user}"):
                    reply_text = st.text_area("Your Reply", placeholder="Type your reply here...")
                    
                    if st.form_submit_button("Send Reply", type="primary", use_container_width=True):
                        if reply_text:
                            # Get the last user message ID
                            user_msgs = [m for m in conversations[selected_user] if not m['is_admin_reply']]
                            if user_msgs:
                                last_msg_id = user_msgs[-1]['id']
                                send_admin_reply(last_msg_id, reply_text, st.session_state.current_user)
                                st.success("✅ Reply sent!")
                                st.rerun()
                        else:
                            st.warning("Please enter a reply")
    
    else:
        # Regular user view
        st.info("💬 Send a message to the administrator. They will reply here!")
        
        # Display user's conversation
        user_messages = get_user_conversations(st.session_state.current_user)
        
        if user_messages:
            st.markdown("### Your Messages")
            for msg in user_messages:
                if msg['is_admin_reply']:
                    st.markdown(f"""
                    <div style='background: #e3f2fd; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;'>
                        <strong>🛡️ Admin Reply:</strong> {msg['message']}<br>
                        <small style='color: #666;'>{datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='background: #f5f5f5; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;'>
                        <strong>You:</strong> {msg['message']}<br>
                        <small style='color: #666;'>{datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M')}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Message form
        st.markdown("### Send New Message")
        with st.form("user_message_form"):
            message = st.text_area(
                "Your Message", 
                placeholder="Ask a question, report an issue, or request help...",
                height=150
            )
            
            if st.form_submit_button("📤 Send Message", type="primary", use_container_width=True):
                if message:
                    send_message(st.session_state.current_user, message)
                    st.success("✅ Message sent! The admin will reply soon.")
                    st.rerun()
                else:
                    st.warning("Please enter a message")

# ========================================================================================
# MAIN APP
# ========================================================================================

def main():
    st.set_page_config(
        page_title="Structural Model Builder",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_session_state()
    render_styles()
    
    if not st.session_state.authenticated:
        render_auth_ui()
        st.stop()
    
    render_sidebar()
    render_profile()
    
    st.markdown('<h1 class="main-title">🏗️ Structural Model Builder</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced Finite Element Analysis Platform</p>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Editor", "🚀 Build & Results", "📖 User Guide", "💬 Chat"])
    
    with tab1:
        render_editor_tab()
    
    with tab2:
        render_build_tab()
    
    with tab3:
        render_user_guide_tab()
    
    with tab4:
        render_chat_tab()
    
    # Footer
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

if __name__ == "__main__":
    main()
