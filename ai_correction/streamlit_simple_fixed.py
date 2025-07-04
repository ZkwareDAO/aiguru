#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI? - ?
?calling_api.py?main.py??
"""

import streamlit as st
import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
import time
import re
import base64
import html
from functions.api_correcting import (
    intelligent_correction_with_files, 
    img_to_base64,
    api_config,  # ?API?
    call_tongyiqianwen_api,  # ?API?
    batch_correction_with_standard,  # ?
    batch_correction_without_standard,  # ?
    simplified_batch_correction  # ??
)
# ? functions.api_correcting ?
FIXED_API_AVAILABLE = True
print("???API?")
import logging
import io
from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Streamlit?
def st_rerun():
    """?Streamlit?"""
    try:
        # ?rerun
        st.rerun()
    except AttributeError:
        # ?rerun?experimental_rerun
        try:
            st.experimental_rerun()
        except AttributeError:
            # ?
            try:
                st.legacy_caching.clear_cache()
            except:
                pass
            st.stop()

# ?
st.set_page_config(
    page_title="AI?",
    page_icon="?",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ?API?
try:
    from functions.api_correcting import (
        correction_single_group,
        efficient_correction_single,
        batch_efficient_correction,
        generate_marking_scheme,
        correction_with_marking_scheme,
        correction_without_marking_scheme
    )
    
    # ?API??
    api_status = api_config.get_status()
    if api_config.is_valid():
        API_AVAILABLE = True
        st.success(f"??AI??({api_status['api_key_source']})")
    else:
        API_AVAILABLE = False
        st.error("??API?")
        
        # ?
        with st.expander("? API?", expanded=True):
            st.markdown("""
            ### ?OpenRouter API?
            
            **?1??(?)**
            ```bash
            # Windows PowerShell
            $env:OPENROUTER_API_KEY="your_api_key_here"
            
            # Windows CMD
            set OPENROUTER_API_KEY=your_api_key_here
            
            # Linux/Mac
            export OPENROUTER_API_KEY=your_api_key_here
            ```
            
            **?2??env?**
            1. ? `config_template.env` ??`.env`
            2. ? `.env` ?API?
            3. ?
            
            **?API??*
            1. ? [OpenRouter](https://openrouter.ai)
            2. ??
            3. ? [API Keys](https://openrouter.ai/keys)
            4. ?API?
            5. ?
            """)
            
            st.info(f"**?** {json.dumps(api_status, ensure_ascii=False, indent=2)}")
            
except ImportError as e:
    API_AVAILABLE = False
    st.warning(f"? AI?{str(e)}")
    
    # ?
    def correction_single_group(*files, **kwargs):
        return """# ? ? (?)

## ?
- ??
- ??/10 ??
- ?B+

## ?
### ???
- ?
- ?
- ?

### ???
- ????
- ??

### ? ?
1. ??
2. ??
3. ??

**?API??*"""
    
    def efficient_correction_single(*files, **kwargs):
        return """? **?** (?)

**??/10** | **?B+**

? **?**
????
????

??**?**
???
???

? **?**
????
???

*?API*"""
    
    def batch_efficient_correction(*files, **kwargs):
        return f"""? **?** (?)

?{len(files)}??
??.5/10
?{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## ?
- ?1??/10 (B+)
- ?2??/10 (B)
- ?3??/10 (B+)

## ?
??

*?API?*"""
    
    def generate_marking_scheme(*files, **kwargs):
        return """? **?** (?)

## ?
- ??
- ?
- ??
- ??0??

## ?
1. **?** (2??
   - ????
   - ????
   - ?0??

2. **?** (3??
   - ????
   - ????
   - ?1??
   - ????

3. **?** (3??
   - ????
   - ?2??
   - ?1??
   - ????

4. **?** (2??
   - ????
   - ????
   - ?0??

*?API*"""
    
    def correction_with_marking_scheme(scheme, *files, **kwargs):
        return correction_single_group(*files, **kwargs)
    
    def correction_without_marking_scheme(*files, **kwargs):
        return correction_single_group(*files, **kwargs)

# ?LaTeX?Unicode?
def convert_latex_to_unicode(text):
    """?LaTeX?Unicode?"""
    if not isinstance(text, str):
        return text
    
    # ?LaTeX?
    replacements = {
        '\\times': '?',
        '\\div': '?',
        '\\pm': '?',
        '\\sqrt': '?',
        '\\pi': '?',
        '\\leq': '?',
        '\\geq': '?',
        '\\neq': '?',
        '\\approx': '?',
        '\\cdot': '?',
        '\\angle': '?',
        '\\triangle': '?',
        '\\circ': '?',
        '\\alpha': '?',
        '\\beta': '?',
        '\\gamma': '?',
        '\\delta': '?',
        '\\theta': '?',
        '\\infty': '?'
    }
    
    result = text
    for latex, unicode_char in replacements.items():
        result = result.replace(latex, unicode_char)
    
    return result

# ??
try:
    from PIL import Image
    import base64
    from io import BytesIO
    PREVIEW_AVAILABLE = True
except ImportError:
    PREVIEW_AVAILABLE = False

# ?
DATA_FILE = Path("user_data.json")
UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = ['txt', 'md', 'pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']

# ?
UPLOAD_DIR.mkdir(exist_ok=True)

# ?CSS? - ?
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #475569 100%);
        color: #ffffff;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    #MainMenu, .stDeployButton, footer, header {visibility: hidden;}
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
    }
    
    .result-container {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid rgba(96, 165, 250, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        backdrop-filter: blur(15px);
    }
    
    /* ? - ??*/
    .split-container {
        display: flex;
        gap: 1.5rem;
        height: 80vh;
        margin-top: 1rem;
        padding: 0;
    }
    
    .left-panel, .right-panel {
        background: rgba(30, 41, 59, 0.95);
        border: 2px solid rgba(96, 165, 250, 0.4);
        border-radius: 20px;
        padding: 0;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        flex: 1;
        position: relative;
        overflow: hidden;
    }
    
    .panel-header {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
        border-bottom: 1px solid rgba(96, 165, 250, 0.3);
        padding: 1rem 1.5rem;
        font-weight: 600;
        font-size: 1.1rem;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-radius: 18px 18px 0 0;
    }
    
    .panel-content {
        height: calc(100% - 4rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding: 1.5rem;
        position: relative;
    }
    
    /* ? */
    .panel-content::-webkit-scrollbar {
        width: 8px;
    }
    
    .panel-content::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 4px;
    }
    
    .panel-content::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        border-radius: 4px;
        transition: all 0.3s ease;
    }
    
    .panel-content::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #2563eb, #7c3aed);
    }
    
    /* ? */
    .file-preview-inner {
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(96, 165, 250, 0.2);
        border-radius: 12px;
        padding: 1rem;
        min-height: 200px;
    }
    
    /* ? */
    .correction-result-inner {
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        min-height: 200px;
        font-family: 'Consolas', 'Monaco', monospace;
        line-height: 1.6;
        color: #e2e8f0;
    }
    
    /* ??*/
    .file-selector-container {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(96, 165, 250, 0.2);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* ? */
    .left-panel:hover, .right-panel:hover {
        border-color: rgba(96, 165, 250, 0.6);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    
    /* ? */
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
        color: #ffffff !important;
    }
    
    /* ? */
    .panel-content {
        scroll-behavior: smooth;
    }
    
    /* ? */
    .panel-content:focus-within {
        outline: 2px solid rgba(96, 165, 250, 0.5);
        outline-offset: -2px;
    }
    
    /* ? */
    .file-preview-inner img {
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        border: 1px solid rgba(96, 165, 250, 0.2);
        transition: transform 0.3s ease;
    }
    
    .file-preview-inner img:hover {
        transform: scale(1.02);
    }
    
    /* ? */
    .correction-result-inner pre {
        font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
        font-size: 0.9rem;
        line-height: 1.6;
        color: #e2e8f0;
        background: transparent;
        border: none;
        padding: 0;
        margin: 0;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    /* ??*/
    @media (max-width: 768px) {
        .split-container {
            flex-direction: column;
            height: auto;
        }
        
        .left-panel, .right-panel {
            min-height: 400px;
        }
        
        .panel-content {
            height: 400px;
        }
    }
    
    .file-switcher {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }
    
    .file-switcher button {
        background: rgba(59, 130, 246, 0.2) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
    }
    
    .file-switcher button:hover,
    .file-switcher button.active {
        background: rgba(59, 130, 246, 0.4) !important;
        color: #ffffff !important;
        border-color: rgba(59, 130, 246, 0.6) !important;
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        color: white !important;
    }
    
    .css-1d391kg {
        background: rgba(15, 23, 42, 0.95) !important;
        backdrop-filter: blur(10px);
    }
</style>
""", unsafe_allow_html=True)

# ?
def get_file_type(file_name):
    """?"""
    ext = Path(file_name).suffix.lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        return 'image'
    elif ext == '.pdf':
        return 'pdf'
    elif ext in ['.txt', '.md']:
        return 'text'
    elif ext in ['.doc', '.docx']:
        return 'document'
    else:
        return 'unknown'

def safe_download_data(data):
    """
    ?Streamlit?
    
    Args:
        data: ??
        
    Returns:
        str: ?
    """
    if isinstance(data, dict):
        # ?
        if data.get('has_separate_scheme', False):
            marking_scheme = data.get('marking_scheme', '')
            correction_content = data.get('correction_result', '')
            return f"=== ? ===\n\n{marking_scheme}\n\n=== ? ===\n\n{correction_content}"
        else:
            return str(data.get('correction_result', data))
    elif data is None:
        return ""
    else:
        return str(data)

def get_image_base64(image_path, max_size_mb=4):
    """?base64?"""
    try:
        import base64
        import os
        from PIL import Image
        import io
        
        # ??
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            # ??
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        else:
            # ??
            print(f"? ({file_size_mb:.2f}MB)??..")
            
            # ?
            img = Image.open(image_path)
            
            # ?RGB?RGBA??
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # ?
            quality = 85
            max_dimension = 1920  # ??
            
            # ?
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # ?
            while quality > 20:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                compressed_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                
                if compressed_size_mb <= max_size_mb:
                    print(f"?: {file_size_mb:.2f}MB -> {compressed_size_mb:.2f}MB (?: {quality})")
                    return base64.b64encode(buffer.getvalue()).decode()
                
                quality -= 10
            
            # ??
            while max_dimension > 800:
                max_dimension -= 200
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                img_resized.save(buffer, format='JPEG', quality=70, optimize=True)
                compressed_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                
                if compressed_size_mb <= max_size_mb:
                    print(f"?: {file_size_mb:.2f}MB -> {compressed_size_mb:.2f}MB (?: {new_size})")
                    return base64.b64encode(buffer.getvalue()).decode()
            
            # ?
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=50, optimize=True)
            final_size_mb = len(buffer.getvalue()) / (1024 * 1024)
            print(f"?? {file_size_mb:.2f}MB -> {final_size_mb:.2f}MB")
            return base64.b64encode(buffer.getvalue()).decode()
            
    except Exception as e:
        print(f"?: {e}")
        return None

def preview_file(file_path, file_name):
    """?"""
    try:
        file_type = get_file_type(file_name)
        
        if file_type == 'image' and PREVIEW_AVAILABLE:
            try:
                image = Image.open(file_path)
                st.image(image, caption=file_name, use_column_width=True)
            except Exception as e:
                st.error(f"?: {e}")
                
        elif file_type == 'text':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if len(content) > 5000:
                    content = content[:5000] + "\n...(?)"
                st.text_area("?", content, height=400, disabled=True)
            except Exception as e:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    if len(content) > 5000:
                        content = content[:5000] + "\n...(?)"
                    st.text_area("?", content, height=400, disabled=True)
                except Exception as e2:
                    st.error(f"?: {e2}")
                    
        elif file_type == 'pdf':
            st.info(f"? PDF?: {file_name}")
            st.write("PDF?")
            
        elif file_type == 'document':
            st.info(f"? Word?: {file_name}")
            st.write("Word?")
            
        else:
            st.info(f"? ?: {file_name}")
            st.write("?")
            
    except Exception as e:
        st.error(f"?: {e}")

# ?session state
def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'page' not in st.session_state:
        st.session_state.page = "home"
    if 'correction_result' not in st.session_state:
        st.session_state.correction_result = None
    if 'uploaded_files_data' not in st.session_state:
        st.session_state.uploaded_files_data = {}
    if 'current_file_index' not in st.session_state:
        st.session_state.current_file_index = 0
    if 'correction_settings' not in st.session_state:
        st.session_state.correction_settings = {}

# ?
def read_users():
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        
        # ?demo?
        if "demo" not in data:
            data["demo"] = {
                "password": hashlib.sha256("demo".encode()).hexdigest(),
                "email": "demo@example.com",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "records": []
            }
            save_users(data)
        
        return data
    except:
        return {}

def save_users(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"?: {e}")

def save_files(files, username, file_category=None):
    """
    ?
    
    Args:
        files: ??
        username: ??
        file_category: ? ('question', 'answer', 'marking')
    """
    user_dir = UPLOAD_DIR / username
    user_dir.mkdir(exist_ok=True)
    
    # ?
    category_prefixes = {
        'question': 'QUESTION_',
        'answer': 'ANSWER_', 
        'marking': 'MARKING_'
    }
    
    saved_files = []
    for file in files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.name).suffix
        safe_name = re.sub(r'[^\w\-_.]', '_', Path(file.name).stem)
        
        # ?
        if file_category and file_category in category_prefixes:
            prefix = category_prefixes[file_category]
            filename = f"{prefix}{timestamp}_{safe_name}{file_ext}"
        else:
            filename = f"{timestamp}_{safe_name}{file_ext}"
        
        file_path = user_dir / filename
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        
        # ?
        saved_files.append({
            "path": str(file_path),
            "name": filename,
            "original_name": file.name,
            "category": file_category or "unknown"
        })
    
    return saved_files

# ??
def show_home():
    st.markdown('<h1 class="main-title">? AI?</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 1.1rem;">AI?</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("? ?", use_container_width=True, type="primary"):
            if st.session_state.logged_in:
                st.session_state.page = "grading"
                st_rerun()
            else:
                st.session_state.page = "login"
                st_rerun()
    
    with col2:
        if st.button("? ?", use_container_width=True):
            if st.session_state.logged_in:
                st.session_state.page = "history"
                st_rerun()
            else:
                st.session_state.page = "login"
                st_rerun()
    
    with col3:
        if st.button("? ?", use_container_width=True):
            st.session_state.page = "login"
            st_rerun()
    
    # ?
    st.markdown("---")
    st.markdown("### ? ?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**? ?**")
        st.write("? ?")
        st.write("? ?")
        st.write("? ?")
    
    with col2:
        st.markdown("**? ?**")
        st.write("? ?")
        st.write("? ?")
        st.write("? ?")
    
    with col3:
        st.markdown("**? ?**")
        st.write("? ?")
        st.write("? ?")
        st.write("? ?")

# ?
def show_login():
    st.markdown('<h2 class="main-title">? ?</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["?", "?"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("?", placeholder="?")
            password = st.text_input("?", type="password", placeholder="?")
            
            col1, col2 = st.columns(2)
            with col1:
                login_btn = st.form_submit_button("?", use_container_width=True)
            with col2:
                demo_btn = st.form_submit_button("?", use_container_width=True)
            
            if login_btn or demo_btn:
                if demo_btn:
                    username, password = "demo", "demo"
                
                if username and password:
                    users = read_users()
                    stored_pwd = users.get(username, {}).get('password')
                    input_pwd = hashlib.sha256(password.encode()).hexdigest()
                    
                    if stored_pwd == input_pwd:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.page = "grading"
                        st.success(f"?{username}?")
                        st_rerun()
                    else:
                        st.error("?")
                else:
                    st.error("?")
        
        st.info("? ?demo/demo")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("?")
            new_email = st.text_input("?")
            new_password = st.text_input("?", type="password")
            confirm_password = st.text_input("?", type="password")
            
            register_btn = st.form_submit_button("?", use_container_width=True)
            
            if register_btn:
                if all([new_username, new_password, confirm_password]):
                    if new_password == confirm_password:
                        users = read_users()
                        if new_username not in users:
                            users[new_username] = {
                                "password": hashlib.sha256(new_password.encode()).hexdigest(),
                                "email": new_email or f"{new_username}@example.com",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "records": []
                            }
                            save_users(users)
                            st.success("?")
                        else:
                            st.error("?")
                    else:
                        st.error("?")
                else:
                    st.error("?")

# ?
def show_grading():
    """?"""
    st.header("? AI?")
    
    # ?
    batch_settings = st.session_state.get('batch_settings', {
        'enable_batch': True,
        'batch_size': 10,
        'skip_missing': True,
        'separate_summary': True,
        'generate_summary': True,
        'max_steps': 3
    })
    
    # ??
    with st.expander("? ?", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"? ?: {'?' if batch_settings['enable_batch'] else '?'}")
            st.write(f"? ?: {batch_settings['batch_size']}??)
            st.write(f"? ?: {'?? if batch_settings['skip_missing'] else '??}")
        with col2:
            st.write(f"? ?: {'?? if batch_settings['separate_summary'] else '??}")
            st.write(f"? ?: {'?? if batch_settings['generate_summary'] else '??}")
            st.write(f"? ?? {batch_settings['max_steps']}??)
    
    # ?
    st.markdown("### ? ?")
    
    # ?
    with st.expander("? ?", expanded=False):
        st.markdown("""
        ### ? ?
        
        ?AI??
        
        - **? ?** ??`QUESTION_?`?AI?
        - **? ?** ??`ANSWER_?`?AI?  
        - **? ?** ??`MARKING_?`?AI?
        
        **?**??
        - ? **?**??00%??
        - ??**??*?
        - ??**?**??
        - ? **?**?AI?
        
        ?
        """)
    
    # ?
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**? ?**")
        st.caption("? ??QUESTION_?")
        question_files = st.file_uploader(
            "?",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="?- ?QUESTION_?",
            key="question_upload"
        )
        if question_files:
            st.success(f"??{len(question_files)} ??)
            with st.expander("? ?"):
                for f in question_files:
                    st.text(f"?: {f.name}")
                    st.text(f"?? QUESTION_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    with col2:
        st.markdown("**? ?**")
        st.caption("? ??ANSWER_?")
        answer_files = st.file_uploader(
            "?",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="?- ?ANSWER_?",
            key="answer_upload"
        )
        if answer_files:
            st.success(f"??{len(answer_files)} ??)
            with st.expander("? ?"):
                for f in answer_files:
                    st.text(f"?: {f.name}")
                    st.text(f"?? ANSWER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    with col3:
        st.markdown("**? ?**")
        st.caption("? ??MARKING_?")
        marking_files = st.file_uploader(
            "?",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            help="?- ?MARKING_?",
            key="marking_upload"
        )
        if marking_files:
            st.success(f"??{len(marking_files)} ??)
            with st.expander("? ?"):
                for f in marking_files:
                    st.text(f"?: {f.name}")
                    st.text(f"?? MARKING_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                    st.divider()
    
    # ??
    all_uploaded_files = []
    if question_files:
        all_uploaded_files.extend(question_files)
    if answer_files:
        all_uploaded_files.extend(answer_files)
    if marking_files:
        all_uploaded_files.extend(marking_files)
    
    # ?
    if st.button("? ?AI?", type="primary", use_container_width=True):
        if not all_uploaded_files:
            st.error("? ?")
            return
            
        if not API_AVAILABLE:
            st.error("??AI?API?")
            return
        
        # ?
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # ??
            status_text.text("? ??..")
            progress_bar.progress(10)
            
            # ?
            saved_files = []
            
            # ?
            if question_files:
                saved_question_files = save_files(question_files, st.session_state.username, 'question')
                saved_files.extend(saved_question_files)
            
            # ?
            if answer_files:
                saved_answer_files = save_files(answer_files, st.session_state.username, 'answer')
                saved_files.extend(saved_answer_files)
            
            # ?
            if marking_files:
                saved_marking_files = save_files(marking_files, st.session_state.username, 'marking')
                saved_files.extend(saved_marking_files)
            
            file_paths = [f["path"] for f in saved_files]
            
            progress_bar.progress(30)
            status_text.text("? ?AI?...")
            
            # ?
            if batch_settings['enable_batch']:
                # ??
                if any('MARKING' in f.name.upper() for f in all_uploaded_files):
                    # ??
                    from functions.api_correcting.calling_api import enhanced_batch_correction_with_standard
                    
                    # ?
                    marking_files = [f["path"] for f in saved_files if 'MARKING' in f["name"].upper()]
                    answer_files = [f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()]
                    
                    result = enhanced_batch_correction_with_standard(
                        answer_files,
                        file_info_list=saved_files,
                        batch_size=batch_settings['batch_size'],
                        generate_summary=batch_settings['generate_summary']
                    )
                else:
                    # ??
                    from functions.api_correcting.calling_api import enhanced_batch_correction_without_standard
                    
                    answer_files = [f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()]
                    
                    result = enhanced_batch_correction_without_standard(
                        answer_files,
                        file_info_list=saved_files,
                        batch_size=batch_settings['batch_size'],
                        generate_summary=batch_settings['generate_summary']
                    )
            else:
                # ?
                result = intelligent_correction_with_files(
                    answer_files=[f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()],
                    marking_scheme_files=[f["path"] for f in saved_files if 'MARKING' in f["name"].upper()],
                    strictness_level="?"
                )
            
            progress_bar.progress(90)
            status_text.text("????..")
            
            if result:
                # ?
                grading_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # ?
                result_data = {
                    "result": result,
                    "time": grading_time,
                    "files": [f["name"] for f in saved_files],
                    "settings": batch_settings,
                    "type": "enhanced_batch" if batch_settings['enable_batch'] else "traditional"
                }
                
                # ?session
                if "grading_results" not in st.session_state:
                    st.session_state.grading_results = []
                st.session_state.grading_results.append(result_data)
                
                # ?session state?
                st.session_state.correction_result = result
                st.session_state.uploaded_files_data = saved_files
                st.session_state.current_file_index = 0  # ??
                
                # ?
                st.session_state.correction_task = {
                    'status': 'completed',
                    'all_file_info': saved_files,
                    'question_files': [f["path"] for f in saved_files if 'QUESTION' in f["name"].upper()],
                    'answer_files': [f["path"] for f in saved_files if 'ANSWER' in f["name"].upper()],
                    'marking_files': [f["path"] for f in saved_files if 'MARKING' in f["name"].upper()]
                }
                
                # ?
                st.session_state.correction_settings = {
                    'has_marking_scheme': bool(marking_files),
                    'strictness': '?',
                    'use_batch_processing': batch_settings['enable_batch'],
                    'batch_size': batch_settings['batch_size']
                }
                
                progress_bar.progress(100)
                status_text.text("? ??)
                
                st.success("???...")
                st.balloons()
                
                # ?
                time.sleep(1)
                st.session_state.page = "result"
                st_rerun()
                
            else:
                st.error("???")
                
        except Exception as e:
            import traceback
            st.error(f"???{str(e)}")
            # ?
            with st.expander("? ?", expanded=True):
                st.code(traceback.format_exc())
            
        finally:
            progress_bar.empty()
            status_text.empty()

# ??
def show_result():
    """?iframe?"""
    
    if not st.session_state.logged_in:
        st.warning("?")
        st.session_state.page = "login"
        st_rerun()
        return
    
    # ?
    if 'correction_task' in st.session_state and st.session_state.correction_task.get('status') == 'pending':
        # ?
        st.markdown('<h2 class="main-title">? AI??..</h2>', unsafe_allow_html=True)
        
        # ??
        progress_container = st.container()
        with progress_container:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center; padding: 50px;">
                    <div class="spinner"></div>
                    <h3 style="color: #3b82f6; margin-top: 30px;">? AI?...</h3>
                    <p style="color: #94a3b8; margin-top: 10px;">??/p>
                    <p style="color: #64748b; font-size: 0.9em; margin-top: 15px;">????| ? ? | ? ?</p>
                </div>
                <style>
                .spinner {
                    margin: 0 auto;
                    width: 60px;
                    height: 60px;
                    border: 5px solid rgba(59, 130, 246, 0.1);
                    border-radius: 50%;
                    border-top-color: #3b82f6;
                    animation: spin 1s ease-in-out infinite;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                </style>
                """, unsafe_allow_html=True)
        
        # ?
        with st.spinner(""):
            try:
                task = st.session_state.correction_task
                settings = st.session_state.correction_settings
                
                # ?AI? - ?API
                from functions.api_correcting.calling_api import enhanced_batch_correction_with_standard, enhanced_batch_correction_without_standard
                
                if settings.get('has_marking_scheme') and task['marking_files']:
                    # ??- ??
                    result = enhanced_batch_correction_with_standard(
                        content_list=task['answer_files'],
                        file_info_list=task['all_file_info'],
                        batch_size=settings.get('batch_size', 10),
                        generate_summary=True
                    )
                else:
                    # ??- ??
                    result = enhanced_batch_correction_without_standard(
                        content_list=task['answer_files'],
                        file_info_list=task['all_file_info'],
                        batch_size=settings.get('batch_size', 10),
                        generate_summary=True
                    )
                
                # ?
                users = read_users()
                if st.session_state.username in users:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'files': [f['display_name'] for f in task['all_file_info']],
                        'file_data': task['all_file_info'],
                        'settings': settings,
                        'result': result,
                        'files_count': len(task['all_file_info'])
                    }
                    users[st.session_state.username]['records'].append(record)
                    save_users(users)
                
                # ??
                st.session_state.correction_result = result
                st.session_state.correction_task['status'] = 'completed'
                
                # ?
                st_rerun()
                
            except Exception as e:
                st.error(f"?{str(e)}")
                st.session_state.correction_task['status'] = 'failed'
                if st.button("?"):
                    st.session_state.page = "grading"
                    st_rerun()
                return
    
    st.markdown('<h2 class="main-title">? ?</h2>', unsafe_allow_html=True)
    
    # ?
    if not st.session_state.get('correction_result') or not st.session_state.get('uploaded_files_data'):
        st.warning("??)
        if st.button("?", use_container_width=True):
            st.session_state.page = "grading"
            st_rerun()
        return
    
    # ??
    files_data = st.session_state.get('uploaded_files_data', [])
    current_index = st.session_state.get('current_file_index', 0)
    correction_result = st.session_state.get('correction_result')
    
    # ?
    if current_index >= len(files_data):
        st.session_state.current_file_index = 0
        current_index = 0
    
    # ?
    has_separate_scheme = False
    marking_scheme = None
    correction_content = correction_result
    html_content = None
    
    if isinstance(correction_result, dict):
        # ?HTML??
        if correction_result.get('format') == 'enhanced':
            correction_content = correction_result.get('text', '')
            html_content = correction_result.get('html', '')
        else:
            has_separate_scheme = correction_result.get('has_separate_scheme', False)
            if has_separate_scheme:
                marking_scheme = correction_result.get('marking_scheme', '')
                correction_content = correction_result.get('correction_result', '')
            else:
                correction_content = correction_result.get('correction_result', str(correction_result))
    elif isinstance(correction_result, str):
        correction_content = correction_result
    else:
        correction_content = str(correction_result)
    
    # ?
    col_left, col_right = st.columns(2)
    
    # ??
    with col_left:
        st.markdown("### ? ?")
        
        # ?HTML??
        if files_data and current_index < len(files_data):
            current_file = files_data[current_index]
            
            # ?
            preview_html = generate_file_preview_html(current_file)
            
            # ?components.html?
            st.components.v1.html(preview_html, height=520, scrolling=True)
            
            # ?
            if len(files_data) > 1:
                st.markdown("---")
                new_index = st.selectbox(
                    "?",
                    range(len(files_data)),
                    format_func=lambda i: f"{i+1}. {files_data[i]['name']}",
                    index=current_index,
                    key="file_selector_result"
                )
                if new_index != current_index:
                    st.session_state.current_file_index = new_index
                    st_rerun()
    
    # ??
    with col_right:
        # ?
        if has_separate_scheme and marking_scheme:
            st.markdown("### ? ?")
            
            # ??
            if 'result_display_mode' not in st.session_state:
                st.session_state.result_display_mode = 'correction'
            
            # ?
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("? ?", use_container_width=True, 
                           type="primary" if st.session_state.result_display_mode == 'correction' else "secondary"):
                    st.session_state.result_display_mode = 'correction'
                    st_rerun()
            
            with col_r2:
                if st.button("? ?", use_container_width=True,
                           type="primary" if st.session_state.result_display_mode == 'scheme' else "secondary"):
                    st.session_state.result_display_mode = 'scheme'
                    st_rerun()
            
            # ?
            display_content = marking_scheme if st.session_state.result_display_mode == 'scheme' else correction_content
            content_title = "?" if st.session_state.result_display_mode == 'scheme' else "?"
            
            # ?LaTeX?Unicode?
            display_content = convert_latex_to_unicode(display_content)
        
        else:
            st.markdown("### ? ?")
            display_content = correction_content
            content_title = "?"
            
            # ?LaTeX?Unicode?
            display_content = convert_latex_to_unicode(display_content)
        
        # ?HTML
        if html_content and st.session_state.get('result_display_mode', 'correction') == 'correction':
            # ?HTML?
            result_html = html_content
        else:
            # ?
            result_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        margin: 0;
                        padding: 20px;
                        background: #ffffff;
                        color: #333333;
                        font-family: 'SF Mono', Monaco, monospace;
                        min-height: 100vh;
                        box-sizing: border-box;
                    }}
                    pre {{
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        margin: 0;
                        line-height: 1.6;
                        font-size: 14px;
                    }}
                    ::-webkit-scrollbar {{
                        width: 12px;
                    }}
                    ::-webkit-scrollbar-track {{
                        background: rgba(0, 0, 0, 0.3);
                        border-radius: 6px;
                    }}
                    ::-webkit-scrollbar-thumb {{
                        background: #4a5568;
                        border-radius: 6px;
                    }}
                    ::-webkit-scrollbar-thumb:hover {{
                        background: #60a5fa;
                    }}
                </style>
            </head>
            <body>
                <pre>{html.escape(str(display_content))}</pre>
            </body>
            </html>
            """
        
        # ?components.html?
        st.components.v1.html(result_html, height=480, scrolling=True)
    
    # ?
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # ?
        download_content = correction_content
        if has_separate_scheme and marking_scheme:
            download_content = f"=== ? ===\n\n{marking_scheme}\n\n=== ? ===\n\n{correction_content}"
        
        st.download_button(
            "? ?",
            str(download_content),
            file_name="correction_result.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        # ??
        if has_separate_scheme and marking_scheme:
            st.download_button(
                "? ?",
                str(marking_scheme),
                file_name="marking_scheme.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.write("")  # ?
    
    with col3:
        if st.button("? ?", use_container_width=True):
            st.session_state.page = "grading"
            st_rerun()
    
    with col4:
        if st.button("? ?", use_container_width=True):
            st.session_state.page = "history"
            st_rerun()

def generate_file_preview_html(file_data):
    """?HTML"""
    
    # ?HTML?
    base_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 20px;
                background: #ffffff;
                color: #333333;
                font-family: Arial, sans-serif;
                box-sizing: border-box;
            }}
            .error {{
                text-align: center;
                padding: 50px;
            }}
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 0 auto;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }}
            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                line-height: 1.6;
                font-family: monospace;
                background: rgba(0,0,0,0.2);
                padding: 15px;
                border-radius: 8px;
                overflow-x: auto;
            }}
            h3 {{
                text-align: center;
                color: #60a5fa;
                margin-bottom: 20px;
            }}
            ::-webkit-scrollbar {{
                width: 12px;
            }}
            ::-webkit-scrollbar-track {{
                background: rgba(0, 0, 0, 0.3);
                border-radius: 6px;
            }}
            ::-webkit-scrollbar-thumb {{
                background: #4a5568;
                border-radius: 6px;
            }}
            ::-webkit-scrollbar-thumb:hover {{
                background: #60a5fa;
            }}
        </style>
    </head>
    <body>
        {content}
    </body>
    </html>
    """
    
    # ??
    if not file_data.get('path') or not Path(file_data['path']).exists():
        content = '<div class="error"><h3>? ??/h3><p>??/p></div>'
        return base_template.format(content=content)
    
    file_type = get_file_type(file_data['name'])
    
    if file_type == 'image':
        # ?
        try:
            image_base64 = get_image_base64(file_data['path'])
            if image_base64:
                content = f'<h3>??{html.escape(file_data["name"])}</h3><img src="data:image/png;base64,{image_base64}" alt="Preview" />'
            else:
                content = '<div class="error"><p>?</p></div>'
        except Exception as e:
            content = f'<div class="error"><p>?: {html.escape(str(e))}</p></div>'
    
    elif file_type == 'text':
        # ?
        try:
            with open(file_data['path'], 'r', encoding='utf-8') as f:
                text_content = f.read()
            content = f'<h3>? {html.escape(file_data["name"])}</h3><pre>{html.escape(text_content)}</pre>'
        except Exception as e:
            content = f'<div class="error"><p>?: {html.escape(str(e))}</p></div>'
    
    elif file_type == 'pdf':
        # PDF?
        try:
            from functions.api_correcting.calling_api import pdf_pages_to_base64_images
            pdf_images = pdf_pages_to_base64_images(file_data['path'], zoom=1.5)
            
            if pdf_images:
                # ?PDF?HTML
                pdf_pages_html = ""
                total_pages = len(pdf_images)
                
                for i, img_base64 in enumerate(pdf_images):
                    # ??
                    page_indicator = f'<div style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -20px 20px -20px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">? ??{i+1} ??/ ??{total_pages} ??/div>'
                    
                    # PDF?
                    page_content = f'<div style="margin-bottom: 40px; width: 100%; text-align: center;"><img src="data:image/png;base64,{img_base64}" style="width: 100%; height: auto; max-width: 100%; border: 3px solid #4a5568; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); background-color: white; object-fit: contain; display: block; margin: 0 auto; transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform=\'scale(1.02)\'; this.style.boxShadow=\'0 12px 24px rgba(0,0,0,0.4)\'" onmouseout="this.style.transform=\'scale(1)\'; this.style.boxShadow=\'0 8px 16px rgba(0,0,0,0.3)\'" alt="PDF ?{i+1}?? /></div>'
                    
                    pdf_pages_html += page_indicator + page_content
                
                # ?
                navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">? ?PDF?</span></div>'
                
                content = f'<h3>? {html.escape(file_data["name"])}</h3>{pdf_pages_html}{navigation_hint}'
            else:
                content = f'<div class="error"><h3>? PDF?</h3><p>{html.escape(file_data["name"])}</p><p>PDF??/p></div>'
        except Exception as e:
            content = f'<div class="error"><h3>? PDF?</h3><p>{html.escape(file_data["name"])}</p><p>PDF?: {html.escape(str(e))}</p><p>?PyMuPDF?</p></div>'
    
    else:
        # ?
        content = f'<div class="error"><h3>? {html.escape(file_data["name"])}</h3><p>?: {file_type}</p><p>??/p></div>'
    
    return base_template.format(content=content)

# ? - ??
def show_result_original():
    if not st.session_state.logged_in:
        st.warning("?")
        st.session_state.page = "login"
        st_rerun()
        return
    
    # ?
    if 'correction_task' in st.session_state and st.session_state.correction_task.get('status') == 'pending':
        # ?
        st.markdown('<h2 class="main-title">? AI??..</h2>', unsafe_allow_html=True)
        
        # ?
        progress_container = st.container()
        with progress_container:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center; padding: 50px;">
                    <div class="spinner"></div>
                    <h3 style="color: #3b82f6; margin-top: 30px;">? AI?...</h3>
                    <p style="color: #94a3b8; margin-top: 10px;">?</p>
                </div>
                <style>
                .spinner {
                    margin: 0 auto;
                    width: 60px;
                    height: 60px;
                    border: 5px solid rgba(59, 130, 246, 0.1);
                    border-radius: 50%;
                    border-top-color: #3b82f6;
                    animation: spin 1s ease-in-out infinite;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                </style>
                """, unsafe_allow_html=True)
        
        # ?
        with st.spinner(""):
            try:
                task = st.session_state.correction_task
                settings = st.session_state.correction_settings
                
                # ?AI? - ?API
                if settings.get('has_marking_scheme') and task['marking_files']:
                    # ??
                    result = batch_correction_with_standard(
                    marking_scheme_files=task['marking_files'],
                        student_answer_files=task['answer_files'],
                        strictness_level=settings['strictness']
                    )
                else:
                    # ??
                    result = batch_correction_without_standard(
                        question_files=task['question_files'],
                        student_answer_files=task['answer_files'],
                        strictness_level=settings['strictness']
                )
                
                # ?
                users = read_users()
                if st.session_state.username in users:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'files': [f['display_name'] for f in task['all_file_info']],
                        'file_data': task['all_file_info'],
                        'settings': settings,
                        'result': result,
                        'files_count': len(task['all_file_info'])
                    }
                    users[st.session_state.username]['records'].append(record)
                    save_users(users)
                
                # ??
                st.session_state.correction_result = result
                st.session_state.correction_task['status'] = 'completed'
                
                # ?
                st_rerun()
                
            except Exception as e:
                st.error(f"?{str(e)}")
                st.session_state.correction_task['status'] = 'failed'
                if st.button("?"):
                    st.session_state.page = "grading"
                    st_rerun()
                return
    
    # ?
    if not st.session_state.correction_result or not st.session_state.uploaded_files_data:
        st.warning("?")
        st.session_state.page = "grading"
        st_rerun()
        return
    
    st.markdown('<h2 class="main-title">? ?</h2>', unsafe_allow_html=True)
    
    # ??
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        settings = st.session_state.correction_settings
        mode_text = "?? if settings.get('has_marking_scheme') else "?"
        st.markdown(f"**??* {mode_text} | {settings.get('strictness', 'N/A')}")
    
    with col2:
        if st.button("? ?"):
            st.session_state.page = "grading"
            st_rerun()
    
    with col3:
        filename = f"correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        # ??
        result_data = st.session_state.correction_result
        if isinstance(result_data, dict):
            if result_data.get('has_separate_scheme', False):
                marking_scheme = result_data.get('marking_scheme', '')
                correction_content = result_data.get('correction_result', '')
                download_content = f"=== ? ===\n\n{marking_scheme}\n\n=== ? ===\n\n{correction_content}"
            else:
                download_content = str(result_data.get('correction_result', result_data))
        else:
            download_content = str(result_data)
        
        st.download_button("? ?", 
                         data=download_content, 
                         file_name=filename, 
                         mime="text/plain")
    
    with col4:
        if st.button("? ?"):
            st.session_state.page = "home"
            st_rerun()
    
    st.markdown("---")
    
    # ?CSS?
    st.markdown("""
    <style>
    .stColumn > div {
        height: auto;
    }
    .stTextArea > div > div > textarea {
        font-family: 'Courier New', monospace;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ??
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("### ? ?")
        
        # ?
        preview_container = st.container()
        
        with preview_container:
            if st.session_state.uploaded_files_data:
                # ?
                if st.session_state.current_file_index >= len(st.session_state.uploaded_files_data):
                    st.session_state.current_file_index = 0
                
                current_file = st.session_state.uploaded_files_data[st.session_state.current_file_index]
                
                # ??- ??
                st.markdown("""
                <style>
                .file-preview-frame {
                    height: 520px !important;
                    max-height: 520px !important;
                    overflow: hidden !important;
                    border: 3px solid #4a5568;
                    border-radius: 12px;
                    padding: 0 !important;
                    margin: 0 !important;
                    background-color: #1a202c;
                    margin-bottom: 20px;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    position: relative;
                    box-sizing: border-box !important;
                    cursor: default !important;
                }
                .preview-content-wrapper {
                    height: 100% !important;
                    max-height: 520px !important;
                    width: 100% !important;
                    overflow-y: auto !important;
                    overflow-x: hidden !important;
                    padding: 15px;
                    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
                    box-sizing: border-box !important;
                    display: block !important;
                }
                .preview-image-container {
                    width: 100% !important;
                    height: auto !important;
                    max-width: 100% !important;
                    text-align: center;
                    padding: 10px;
                    box-sizing: border-box !important;
                }
                .preview-image {
                    max-width: calc(100% - 20px) !important;
                    max-height: 450px !important;
                    height: auto !important;
                    width: auto !important;
                    border: 2px solid #4a5568;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    background-color: white;
                    object-fit: contain !important;
                    display: block !important;
                    margin: 0 auto !important;
                }
                .pdf-page-container {
                    margin-bottom: 25px;
                    text-align: center;
                    width: 100% !important;
                    max-width: 100% !important;
                    box-sizing: border-box !important;
                    padding: 0 10px;
                }
                .pdf-page-container img {
                    max-width: calc(100% - 20px) !important;
                    max-height: 400px !important;
                    height: auto !important;
                    width: auto !important;
                    border: 2px solid #4a5568;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    background-color: white;
                    object-fit: contain !important;
                    display: block !important;
                    margin: 0 auto !important;
                }
                .page-number-badge {
                    color: #e2e8f0;
                    font-size: 0.9rem;
                    margin-bottom: 10px;
                    font-weight: 600;
                    background-color: #4a5568;
                    padding: 6px 16px;
                    border-radius: 20px;
                    display: inline-block;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                .preview-text-content {
                    width: calc(100% - 20px) !important;
                    height: calc(100% - 40px) !important;
                    max-height: 450px !important;
                    background-color: #2d3748;
                    border: 2px solid #4a5568;
                    border-radius: 8px;
                    padding: 20px;
                    color: #e2e8f0;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9rem;
                    line-height: 1.6;
                    overflow-y: auto !important;
                    overflow-x: hidden !important;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
                    box-sizing: border-box !important;
                    margin: 10px auto;
                }
                .preview-placeholder {
                    display: flex !important;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: calc(100% - 30px) !important;
                    max-height: 490px !important;
                    text-align: center;
                    color: #a0aec0;
                    padding: 15px;
                    box-sizing: border-box !important;
                }
                .preview-placeholder h3 {
                    color: #f6ad55;
                    margin-bottom: 20px;
                    font-size: 1.5rem;
                }
                .preview-placeholder p {
                    font-size: 1.1rem;
                    margin-bottom: 10px;
                }
                /* ?Streamlit? */
                .file-preview-frame * {
                    max-width: 100% !important;
                    box-sizing: border-box !important;
                }
                .file-preview-frame img {
                    max-width: calc(100% - 40px) !important;
                    max-height: 450px !important;
                    object-fit: contain !important;
                }
                /* ?Streamlit??*/
                .file-preview-frame .stImage {
                    max-width: 100% !important;
                    overflow: hidden !important;
                }
                .file-preview-frame .stImage > div {
                    max-width: 100% !important;
                    overflow: hidden !important;
                }
                /* ? - ??*/
                .file-preview-frame,
                .file-preview-frame *,
                .file-preview-frame img,
                .file-preview-frame .preview-image,
                .file-preview-frame .preview-image-container,
                .file-preview-frame .preview-content-wrapper {
                    max-width: 100% !important;
                    max-height: 520px !important;
                    overflow: hidden !important;
                    box-sizing: border-box !important;
                }
                .file-preview-frame img {
                    width: auto !important;
                    height: auto !important;
                    max-width: calc(100% - 60px) !important;
                    max-height: 400px !important;
                    object-fit: contain !important;
                    object-position: center !important;
                }
                /* ? */
                .file-preview-frame > * {
                    contain: layout size !important;
                }
                
                /* ? - ??*/
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar {
                    width: 14px;
                    height: 14px;
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-track {
                    background: rgba(0, 0, 0, 0.4);
                    border-radius: 8px;
                    border: 1px solid rgba(74, 85, 104, 0.3);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-thumb {
                    background: linear-gradient(135deg, #4a5568, #2d3748);
                    border-radius: 8px;
                    border: 2px solid rgba(0, 0, 0, 0.2);
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-thumb:hover {
                    background: linear-gradient(135deg, #60a5fa, #3b82f6);
                    transform: scale(1.05);
                    box-shadow: 0 4px 8px rgba(96, 165, 250, 0.3);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-thumb:active {
                    background: linear-gradient(135deg, #2563eb, #1d4ed8);
                }
                .file-preview-frame .preview-content-wrapper::-webkit-scrollbar-corner {
                    background: rgba(0, 0, 0, 0.4);
                    border-radius: 8px;
                }
                
                /* ??*/
                .file-preview-frame {
                    position: relative;
                    z-index: 1;
                    user-select: none;
                    -webkit-user-select: none;
                    -moz-user-select: none;
                    -ms-user-select: none;
                }
                .file-preview-frame .preview-content-wrapper {
                    position: relative;
                    z-index: 2;
                    cursor: default;
                    scroll-behavior: smooth;
                    overflow-scrolling: touch; /* iOS? */
                }
                
                /* ??*/
                .file-preview-frame .preview-content-wrapper {
                    overscroll-behavior: contain;
                    scroll-snap-type: none;
                }
                
                /* ? */
                .file-preview-frame:hover {
                    border-color: #60a5fa;
                    box-shadow: 0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3);
                    transition: all 0.3s ease;
                }
                
                /* ??*/
                .file-preview-frame::before {
                    content: "????;
                    position: absolute;
                    top: 8px;
                    right: 12px;
                    background: rgba(96, 165, 250, 0.8);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    z-index: 10;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                    pointer-events: none;
                }
                .file-preview-frame:hover::before {
                    opacity: 1;
                }
                
                /* ? */
                .file-preview-frame {
                    outline: none;
                }
                .file-preview-frame:focus {
                    border-color: #60a5fa;
                    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2);
                }
                </style>
                
                <script>
                // ? - ?
                (function() {
                    // ?DOMContentLoaded
                    function setupPreviewScrolling() {
                        console.log('Setting up preview scrolling...');
                        
                        // ?
                        const previewFrames = document.querySelectorAll('.file-preview-frame');
                        const resultFrames = document.querySelectorAll('.correction-result-frame');
                        
                        console.log('Found preview frames:', previewFrames.length);
                        console.log('Found result frames:', resultFrames.length);
                        
                        // ??
                        previewFrames.forEach((previewFrame, index) => {
                            const contentWrapper = previewFrame.querySelector('.preview-content-wrapper');
                            
                            if (contentWrapper) {
                                console.log('Setting up preview frame', index);
                                
                                // ??
                                const newFrame = previewFrame.cloneNode(true);
                                previewFrame.parentNode.replaceChild(newFrame, previewFrame);
                                
                                const newContentWrapper = newFrame.querySelector('.preview-content-wrapper');
                                
                                // ??- ?
                                newFrame.addEventListener('wheel', function(e) {
                                    // ?
                                    e.preventDefault();
                                    e.stopPropagation();
                                    e.stopImmediatePropagation();
                                    
                                    // ??
                                    const canScrollDown = newContentWrapper.scrollTop < (newContentWrapper.scrollHeight - newContentWrapper.clientHeight - 1);
                                    const canScrollUp = newContentWrapper.scrollTop > 0;
                                    
                                    // ??
                                    if ((e.deltaY > 0 && canScrollDown) || (e.deltaY < 0 && canScrollUp)) {
                                        // ??
                                        const scrollAmount = e.deltaY;
                                        newContentWrapper.scrollTop += scrollAmount;
                                    }
                                    
                                    return false;
                                }, { passive: false, capture: true });
                                
                                // ??
                                newFrame.addEventListener('mouseenter', function(e) {
                                    // ?
                                    newFrame.style.borderColor = '#60a5fa';
                                    newFrame.style.boxShadow = '0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3)';
                                    
                                    // ??
                                    newFrame.setAttribute('tabindex', '0');
                                    newFrame.focus();
                                });
                                
                                // ??
                                newFrame.addEventListener('mouseleave', function(e) {
                                    // ?
                                    newFrame.style.borderColor = '#4a5568';
                                    newFrame.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
                                });
                                
                                // ?
                                newFrame.addEventListener('keydown', function(e) {
                                    switch(e.key) {
                                        case 'ArrowUp':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: -50, behavior: 'smooth' });
                                            break;
                                        case 'ArrowDown':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: 50, behavior: 'smooth' });
                                            break;
                                        case 'PageUp':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: -300, behavior: 'smooth' });
                                            break;
                                        case 'PageDown':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollBy({ top: 300, behavior: 'smooth' });
                                            break;
                                        case 'Home':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollTo({ top: 0, behavior: 'smooth' });
                                            break;
                                        case 'End':
                                            e.preventDefault();
                                            e.stopPropagation();
                                            newContentWrapper.scrollTo({ top: newContentWrapper.scrollHeight, behavior: 'smooth' });
                                            break;
                                    }
                                });
                            }
                        });
                         
                         // ??
                         resultFrames.forEach((resultFrame, index) => {
                             const contentWrapper = resultFrame.querySelector('.result-content-wrapper');
                             
                             if (contentWrapper) {
                                 console.log('Setting up result frame', index);
                                 
                                 // ??
                                 const newFrame = resultFrame.cloneNode(true);
                                 resultFrame.parentNode.replaceChild(newFrame, resultFrame);
                                 
                                 const newContentWrapper = newFrame.querySelector('.result-content-wrapper');
                                 
                                 // ??- ?
                                 newFrame.addEventListener('wheel', function(e) {
                                     // ?
                                     e.preventDefault();
                                     e.stopPropagation();
                                     e.stopImmediatePropagation();
                                     
                                     // ??
                                     const canScrollDown = newContentWrapper.scrollTop < (newContentWrapper.scrollHeight - newContentWrapper.clientHeight - 1);
                                     const canScrollUp = newContentWrapper.scrollTop > 0;
                                     
                                     // ??
                                     if ((e.deltaY > 0 && canScrollDown) || (e.deltaY < 0 && canScrollUp)) {
                                         // ??
                                         const scrollAmount = e.deltaY;
                                         newContentWrapper.scrollTop += scrollAmount;
                                     }
                                     
                                     return false;
                                 }, { passive: false, capture: true });
                                 
                                 // ??
                                 newFrame.addEventListener('mouseenter', function(e) {
                                     // ?
                                     newFrame.style.borderColor = '#60a5fa';
                                     newFrame.style.boxShadow = '0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3)';
                                     
                                     // ??
                                     newFrame.setAttribute('tabindex', '0');
                                     newFrame.focus();
                                 });
                                 
                                 // ??
                                 newFrame.addEventListener('mouseleave', function(e) {
                                     // ?
                                     newFrame.style.borderColor = '#4a5568';
                                     newFrame.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
                                 });
                                 
                                 // ?
                                 newFrame.addEventListener('keydown', function(e) {
                                     switch(e.key) {
                                         case 'ArrowUp':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: -50, behavior: 'smooth' });
                                             break;
                                         case 'ArrowDown':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: 50, behavior: 'smooth' });
                                             break;
                                         case 'PageUp':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: -300, behavior: 'smooth' });
                                             break;
                                         case 'PageDown':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollBy({ top: 300, behavior: 'smooth' });
                                             break;
                                         case 'Home':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollTo({ top: 0, behavior: 'smooth' });
                                             break;
                                         case 'End':
                                             e.preventDefault();
                                             e.stopPropagation();
                                             newContentWrapper.scrollTo({ top: newContentWrapper.scrollHeight, behavior: 'smooth' });
                                             break;
                                     }
                                 });
                             }
                         });
                     }
                     
                     // ?DOM?
                     setTimeout(setupPreviewScrolling, 100);
                     setTimeout(setupPreviewScrolling, 500);
                     setTimeout(setupPreviewScrolling, 1000);
                    
                    // ?DOM?
                    const observer = new MutationObserver(function(mutations) {
                        mutations.forEach(function(mutation) {
                            if (mutation.type === 'childList') {
                                const addedNodes = Array.from(mutation.addedNodes);
                                if (addedNodes.some(node => node.nodeType === 1 && (
                                    node.classList && (node.classList.contains('file-preview-frame') || node.classList.contains('correction-result-frame')) ||
                                    (node.querySelector && (node.querySelector('.file-preview-frame') || node.querySelector('.correction-result-frame')))
                                ))) {
                                    setTimeout(setupPreviewScrolling, 100);
                                }
                            }
                        });
                    });
                    
                    // ?DOM?
                    if (document.body) {
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true
                        });
                    }
                    
                    // ?DOM?
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', setupPreviewScrolling);
                    } else {
                        setupPreviewScrolling();
                    }
                })();
                </script>
                
                /* ? */
                .file-preview-frame img:hover {
                    transform: scale(1.02);
                    transition: transform 0.3s ease;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                }
                </style>
                """, unsafe_allow_html=True)
                
                # ? - ?HTML?
                preview_html = ""
                
                if current_file['path'] and Path(current_file['path']).exists():
                    file_type = get_file_type(current_file['name'])
                    
                    if file_type == 'image':
                        try:
                            # ?base64?
                            image_base64 = get_image_base64(current_file['path'])
                            if not image_base64:
                                # ?base64
                                import base64
                                with open(current_file['path'], "rb") as img_file:
                                    image_base64 = base64.b64encode(img_file.read()).decode()
                            
                            if image_base64:
                                file_ext = current_file['path'].split('.')[-1].lower()
                                mime_type = f"image/{file_ext}" if file_ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'] else "image/jpeg"
                                
                                # ?HTML - ??
                                image_info = f'<div class="image-info-bar" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -10px 20px -10px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">???: {current_file["name"]}</div>'
                                
                                image_content = f'<div class="image-container" style="text-align: center; width: 100%; position: relative; margin-bottom: 20px;"><img src="data:{mime_type};base64,{image_base64}" style="max-width: 100%; height: auto; max-height: 600px; border: 3px solid #4a5568; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); background-color: white; object-fit: contain; display: block; margin: 0 auto; transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: zoom-in;" onmouseover="this.style.transform=\'scale(1.05)\'; this.style.boxShadow=\'0 12px 24px rgba(0,0,0,0.4)\'" onmouseout="this.style.transform=\'scale(1)\'; this.style.boxShadow=\'0 8px 16px rgba(0,0,0,0.3)\'" alt="{current_file["name"]}" /></div>'
                                
                                navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">? ??/span></div>'
                                
                                preview_html = f'<div class="file-preview-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector(\'.preview-content-wrapper\'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; overflow-y: auto; overflow-x: hidden; padding: 10px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; overscroll-behavior: contain; -webkit-overflow-scrolling: touch;">{image_info}{image_content}{navigation_hint}</div></div>'
                            else:
                                raise Exception("?base64?")
                        except Exception as e:
                            preview_html = f'<div class="file-preview-frame" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); overscroll-behavior: contain;"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">? ?</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">?: {str(e)}</p></div></div>'
                    
                    elif file_type == 'pdf':
                        try:
                            # PDF??
                            from functions.api_correcting.calling_api import pdf_pages_to_base64_images
                            pdf_images = pdf_pages_to_base64_images(current_file['path'], zoom=1.5)
                            
                            if pdf_images:
                                # ?PDF?HTML - ?
                                pdf_pages_html = ""
                                total_pages = len(pdf_images)
                                
                                for i, img_base64 in enumerate(pdf_images):
                                    # ?
                                    page_indicator = f'<div class="pdf-page-indicator" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -10px 20px -10px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">? ??{i+1} ??/ ??{total_pages} ??/div>'
                                    
                                    # PDF?
                                    page_content = f'<div class="pdf-page-container" style="margin-bottom: 40px; width: 100%; position: relative;"><img src="data:image/png;base64,{img_base64}" style="width: 100%; height: auto; max-width: 100%; border: 3px solid #4a5568; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); background-color: white; object-fit: contain; display: block; transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform=\'scale(1.02)\'; this.style.boxShadow=\'0 12px 24px rgba(0,0,0,0.4)\'" onmouseout="this.style.transform=\'scale(1)\'; this.style.boxShadow=\'0 8px 16px rgba(0,0,0,0.3)\'" alt="PDF ?{i+1}?? /></div>'
                                    
                                    pdf_pages_html += page_indicator + page_content
                                
                                # ?
                                navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">? ?</span></div>'
                                
                                preview_html = f'<div class="file-preview-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector(\'.preview-content-wrapper\'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; overflow-y: auto; overflow-x: hidden; padding: 10px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; overscroll-behavior: contain; -webkit-overflow-scrolling: touch;">{pdf_pages_html}{navigation_hint}</div></div>'
                            else:
                                raise Exception("PDF??)
                        except Exception as e:
                            preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">? PDF ?</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">?: {str(e)}</p><p style="font-size: 0.9rem;">?PyMuPDF?</p></div></div>'
                    
                    elif file_type == 'text':
                        try:
                            with open(current_file['path'], 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            if len(content) > 5000:
                                content = content[:5000] + "\n\n...(??"
                            
                            # HTML?
                            import html
                            content_escaped = html.escape(content)
                            
                            # ?HTML - ??
                            file_info = f'<div class="text-info-bar" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -10px 20px -10px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">? ?: {current_file["name"]} ({len(content)} ?)</div>'
                            
                            text_content = f'<div class="text-content-area" style="width: 100%; min-height: 400px; background-color: #2d3748; border: 3px solid #4a5568; border-radius: 12px; padding: 25px; color: #e2e8f0; font-family: \'SF Mono\', \'Monaco\', \'Inconsolata\', \'Roboto Mono\', \'Source Code Pro\', monospace; font-size: 0.95rem; line-height: 1.7; white-space: pre-wrap; word-wrap: break-word; box-shadow: 0 8px 16px rgba(0,0,0,0.3), inset 0 2px 4px rgba(0,0,0,0.1); box-sizing: border-box; transition: all 0.3s ease; position: relative;">{content_escaped}</div>'
                            
                            navigation_hint = '<div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">? ??/span></div>'
                            
                            preview_html = f'<div class="file-preview-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector(\'.preview-content-wrapper\'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="overscroll-behavior: contain;"><div class="preview-content-wrapper" style="height: 520px; overflow-y: auto; overflow-x: hidden; padding: 10px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; overscroll-behavior: contain; -webkit-overflow-scrolling: touch;">{file_info}{text_content}{navigation_hint}</div></div>'
                            
                        except Exception as e:
                            preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">? ?</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">?: {str(e)}</p></div></div>'
                    
                    else:
                        preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">? {file_type.upper()} ?</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">??/p></div></div>'
                else:
                    # ?
                    warning_msg = "? ?? if not current_file['path'] else "? ??
                    preview_html = f'<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">? ??/h3><p style="font-size: 1.1rem; margin-bottom: 10px;">{warning_msg}</p></div></div>'
                
                # ?HTML
                st.markdown(preview_html, unsafe_allow_html=True)
                
                # ??
                st.markdown("---")
                
                # ?
                category = current_file.get('category', 'other')
                category_icons = {
                    'question': '?',
                    'answer': '?', 
                    'marking': '?',
                    'other': '?'
                }
                category_names = {
                    'question': '?',
                    'answer': '?',
                    'marking': '?',
                    'other': '?'
                }
                
                icon = category_icons.get(category, '?')
                name = category_names.get(category, '?')
                file_type_display = current_file.get('type', get_file_type(current_file['name']))
                
                st.info(f"{icon} **{name}**: {current_file['name']} ({file_type_display})")
                
            else:
                # ?
                preview_html = '<div class="file-preview-frame"><div class="preview-content-wrapper" style="height: 520px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #a0aec0; padding: 15px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);"><h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">? ?</h3><p style="font-size: 1.1rem; margin-bottom: 10px;">?</p></div></div>'
                st.markdown(preview_html, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### ? ?")
                
        # ? - ??
        if st.session_state.correction_result:
            # ?class?
            import html
            result_html = f'''
            <div class="correction-result-frame" onwheel="event.preventDefault(); event.stopPropagation(); var wrapper = this.querySelector('.result-content-wrapper'); if(wrapper) {{ var canScrollDown = wrapper.scrollTop < (wrapper.scrollHeight - wrapper.clientHeight - 1); var canScrollUp = wrapper.scrollTop > 0; if ((event.deltaY > 0 && canScrollDown) || (event.deltaY < 0 && canScrollUp)) {{ wrapper.scrollTop += event.deltaY; }} }} return false;" style="height: 520px; border: 3px solid #4a5568; border-radius: 12px; background-color: #1a202c; box-shadow: 0 8px 16px rgba(0,0,0,0.3); overflow: hidden; position: relative; z-index: 1; user-select: none; -webkit-user-select: none; -moz-user-select: none; -ms-user-select: none; overscroll-behavior: contain;">
                <div class="result-content-wrapper" style="height: 100%; overflow-y: auto; overflow-x: hidden; padding: 20px; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); scroll-behavior: smooth; position: relative; z-index: 2; cursor: default; overflow-scrolling: touch; overscroll-behavior: contain; scroll-snap-type: none; -webkit-overflow-scrolling: touch;">
                    <div class="result-info-bar" style="position: sticky; top: 0; z-index: 5; background: rgba(74, 85, 104, 0.95); backdrop-filter: blur(8px); color: #e2e8f0; font-size: 0.85rem; margin: 0 -20px 20px -20px; padding: 12px 20px; font-weight: 600; text-align: center; border-bottom: 2px solid rgba(96, 165, 250, 0.3); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">? ? ({len(st.session_state.correction_result)} ?)</div>
                    <pre style="margin: 0; padding: 0; color: #e2e8f0; font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Source Code Pro', monospace; font-size: 0.95rem; line-height: 1.7; white-space: pre-wrap; word-wrap: break-word; background: rgba(45, 55, 72, 0.3); padding: 20px; border-radius: 8px; border: 1px solid rgba(74, 85, 104, 0.3);">{html.escape(st.session_state.correction_result)}</pre>
                    <div style="text-align: center; padding: 20px; color: #94a3b8; font-size: 0.9rem; border-top: 1px solid rgba(74, 85, 104, 0.3); margin-top: 20px; background: rgba(45, 55, 72, 0.5); border-radius: 8px;"><span style="background: rgba(96, 165, 250, 0.1); padding: 6px 12px; border-radius: 20px; border: 1px solid rgba(96, 165, 250, 0.3);">? ??/span></div>
                </div>
            </div>
            <style>
            /* ??- ??*/
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar {{
                width: 14px;
                height: 14px;
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-track {{
                background: rgba(0, 0, 0, 0.4);
                border-radius: 8px;
                border: 1px solid rgba(74, 85, 104, 0.3);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-thumb {{
                background: linear-gradient(135deg, #4a5568, #2d3748);
                border-radius: 8px;
                border: 2px solid rgba(0, 0, 0, 0.2);
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-thumb:hover {{
                background: linear-gradient(135deg, #60a5fa, #3b82f6);
                transform: scale(1.05);
                box-shadow: 0 4px 8px rgba(96, 165, 250, 0.3);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-thumb:active {{
                background: linear-gradient(135deg, #2563eb, #1d4ed8);
            }}
            .correction-result-frame .result-content-wrapper::-webkit-scrollbar-corner {{
                background: rgba(0, 0, 0, 0.4);
                border-radius: 8px;
            }}
            
            /* ??*/
            .correction-result-frame:hover {{
                border-color: #60a5fa;
                box-shadow: 0 12px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(96, 165, 250, 0.3);
                transition: all 0.3s ease;
            }}
            
            /* ??*/
            .correction-result-frame:focus {{
                border-color: #60a5fa;
                box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2);
                outline: none;
            }}
            
            /* ??*/
            .correction-result-frame::before {{
                content: "????;
                position: absolute;
                top: 8px;
                right: 12px;
                background: rgba(96, 165, 250, 0.8);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.7rem;
                font-weight: 600;
                z-index: 10;
                opacity: 0;
                transition: opacity 0.3s ease;
                pointer-events: none;
            }}
            .correction-result-frame:hover::before {{
                opacity: 1;
            }}
            </style>
            '''
            st.markdown(result_html, unsafe_allow_html=True)
        else:
            # ??
            empty_html = '''
            <div class="correction-result-frame" style="height: 520px; border: 3px solid #4a5568; border-radius: 12px; background-color: #1a202c; box-shadow: 0 8px 16px rgba(0,0,0,0.3); display: flex; justify-content: center; align-items: center;">
                <div style="text-align: center; color: #a0aec0;">
                    <h3 style="color: #f6ad55; margin-bottom: 20px; font-size: 1.5rem;">? ?</h3>
                    <p style="font-size: 1.1rem;">??/p>
                </div>
            </div>
            '''
            st.markdown(empty_html, unsafe_allow_html=True)
    
    # ? (??
    if len(st.session_state.uploaded_files_data) > 1:
            file_options = []
            for i, file_data in enumerate(st.session_state.uploaded_files_data):
                file_name = file_data['name']
            category = file_data.get('category', 'other')
            
            # ?category?
            if category == 'question':
                label = f"? ?: {file_name}"
            elif category == 'answer':
                label = f"? ?: {file_name}"
            elif category == 'marking':
                label = f"? ?: {file_name}"
            else:
                # ??
                if 'question' in file_name.lower() or '?' in file_name:
                    label = f"? ?: {file_name}"
                elif 'answer' in file_name.lower() or '?' in file_name or '?' in file_name:
                    label = f"? ?: {file_name}"
                elif 'scheme' in file_name.lower() or 'marking' in file_name.lower() or '?' in file_name:
                    label = f"? ?: {file_name}"
                else:
                    label = f"? ?{i+1}: {file_name}"
                file_options.append(label)
            
            new_selection = st.selectbox(
            "? ?:",
                options=range(len(file_options)),
                format_func=lambda x: file_options[x],
                index=st.session_state.current_file_index,
                key="file_switcher"
            )
            
            if new_selection != st.session_state.current_file_index:
                st.session_state.current_file_index = new_selection
                st_rerun()

# ?
def show_history():
    if not st.session_state.logged_in:
        st.warning("?")
        st.session_state.page = "login"
        st_rerun()
        return
    
    st.markdown('<h2 class="main-title">? ?</h2>', unsafe_allow_html=True)
    
    users = read_users()
    records = users.get(st.session_state.username, {}).get('records', [])
    
    if not records:
        st.info("?")
        if st.button("? ??, use_container_width=True):
            st.session_state.page = "grading"
            st_rerun()
        return
    
    # ?
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("??, len(records))
    with col2:
        total_files = sum(r.get('files_count', 0) for r in records)
        st.metric("??, total_files)
    with col3:
        if st.button("???"):
            if 'confirm_delete' not in st.session_state:
                st.session_state.confirm_delete = True
            else:
                users[st.session_state.username]['records'] = []
                save_users(users)
                del st.session_state.confirm_delete
                st.success('??)
                st_rerun()

    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        st.warning("??)
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("???", use_container_width=True):
                users[st.session_state.username]['records'] = []
                save_users(users)
                del st.session_state.confirm_delete
                st.success("??)
                st_rerun()
        with col_cancel:
            if st.button("???", use_container_width=True):
                del st.session_state.confirm_delete
                st_rerun()
    
    st.markdown("---")
    
    # ?
    for i, record in enumerate(reversed(records), 1):
        with st.expander(f"? ? {i} - {record['timestamp']}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**??* {', '.join(record.get('files', ['??]))}")
                settings = record.get('settings', {})
                mode_text = "?? if settings.get('has_marking_scheme') else "?"
                st.write(f"**??* {mode_text} | {settings.get('strictness', 'N/A')}")
            
            with col2:
                if st.button("???", key=f"view_{i}", use_container_width=True):
                    # ?session state
                    st.session_state.correction_result = record.get('result', '')
                    
                    # ?
                    file_data = record.get('file_data', [])
                    if file_data:
                        # ??
                        st.session_state.uploaded_files_data = [
                            {
                                'name': f['name'],
                                'path': f.get('path'),
                                'type': f.get('type', get_file_type(f['name']))
                            }
                            for f in file_data
                        ]
                    else:
                        # ?file_data??
                        file_names = record.get('files', [])
                        st.session_state.uploaded_files_data = [
                            {'name': name, 'path': None, 'type': get_file_type(name)} 
                            for name in file_names
                        ]
                    
                    st.session_state.correction_settings = record.get('settings', {})
                    # ??
                    st.session_state.current_file_index = 0
                    st.session_state.page = "result"
                    st_rerun()
                    st_rerun()
                
                if record.get('result'):
                    # ??
                    result_data = record.get('result', '')
                    if isinstance(result_data, dict):
                        # ?
                        if result_data.get('has_separate_scheme', False):
                            marking_scheme = result_data.get('marking_scheme', '')
                            correction_content = result_data.get('correction_result', '')
                            download_content = f"=== ? ===\n\n{marking_scheme}\n\n=== ? ===\n\n{correction_content}"
                        else:
                            download_content = str(result_data.get('correction_result', result_data))
                    else:
                        download_content = str(result_data)
                    
                    st.download_button(
                        "? ?",
                        data=download_content,
                        file_name=f"record_{record['timestamp'].replace(':', '-').replace(' ', '_')}.txt",
                        mime="text/plain",
                        key=f"download_{i}",
                        use_container_width=True
                    )

# ??
def show_sidebar():
    """??""
    with st.sidebar:
        st.markdown('<h3 style="color: #3b82f6;">? AI?</h3>', unsafe_allow_html=True)
        
        if st.session_state.logged_in:
            st.markdown(f"? **{st.session_state.username}**")
            st.markdown("---")
            
            # ?
            if st.button("? ?", use_container_width=True):
                st.session_state.page = "home"
                st_rerun()
            
            if st.button("? ?", use_container_width=True):
                st.session_state.page = "grading"
                st_rerun()
            
            if st.button("? ?", use_container_width=True):
                st.session_state.page = "history"
                st_rerun()
            
            # ? (?)
            if st.session_state.correction_result:
                if st.button("? ?", use_container_width=True):
                    st.session_state.page = "result"
                    st_rerun()
            
            st.markdown("---")
            
            # ?
            st.header("???")
            
            # ?
            enable_batch = st.checkbox("?", value=True, help="??)
            
            if enable_batch:
                batch_size = st.slider("?", min_value=5, max_value=15, value=10, 
                                     help="?")
            else:
                batch_size = None
                
            # ?
            st.subheader("? ?")
            
            skip_missing = st.checkbox("??, value=True, 
                                     help="?")
            
            separate_summary = st.checkbox("?", value=True,
                                         help="??)
            
            generate_summary = st.checkbox("?", value=True,
                                         help="?")
            
            # ?
            st.subheader("? ?")
            max_steps = st.selectbox("?", [3, 5, 7], index=0,
                                   help="??)
            
            # ?session_state??
            st.session_state.batch_settings = {
                'enable_batch': enable_batch,
                'batch_size': batch_size if enable_batch else 10,
                'skip_missing': skip_missing,
                'separate_summary': separate_summary,
                'generate_summary': generate_summary,
                'max_steps': max_steps
            }
            
            st.markdown("---")
            
            # ?
            users = read_users()
            count = len(users.get(st.session_state.username, {}).get('records', []))
            st.metric("?", count)
            
            st.markdown("---")
            
            # ??
            if API_AVAILABLE:
                st.success("??AI?")
            else:
                st.warning("? ?")
            
            st.markdown("---")
            
            # ??
            if st.button("? ??, use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.correction_result = None
                st.session_state.page = "home"
                st_rerun()
        else:
            # ??
            if st.button("? ?", use_container_width=True):
                st.session_state.page = "login"
                st_rerun()
            
            st.markdown("---")
            st.markdown("### ? ?")
            st.markdown("""
            - ? ?
            - ? ?/?
            - ? ?
            - ? ?
            """)
            
            st.markdown("---")
            
            # ??
            if API_AVAILABLE:
                st.success("???")
            else:
                st.warning("? ?")
        
        # ??
        st.markdown("---")
        st.header("? ?")
        
        # API??
        st.subheader("? AI?")
        st.info(f"**?**: {api_config.model}")
        st.info(f"**??*: OpenRouter (Google)")
        
        if API_AVAILABLE:
            st.success("??AI??)
        else:
            st.warning("? ??)
        
        st.markdown("---")
        
        # ?
        st.subheader("? ?")
        st.markdown("""
        1. **?**?PDF?Word?
        2. **?**??
        3. **??*?
        4. **??*???AI?"?
        5. **?**?
        """)
        
        # ??
        st.markdown("---")
        st.subheader("? ??)
        st.markdown(f"""
        - **AI?**: Google Gemini 2.5 Flash Lite Preview
        - **API??*: OpenRouter
        - **?**: ?PDF?Word??
        - **??*: 4MB (?)
        """)

# ??
def main():
    init_session()
    show_sidebar()
    
    # ?
    if st.session_state.page == "home":
        show_home()
    elif st.session_state.page == "login":
        show_login()
    elif st.session_state.page == "grading":
        show_grading()
    elif st.session_state.page == "history":
        show_history()
    elif st.session_state.page == "result":
        show_result()
    else:
        show_home()

if __name__ == "__main__":
    main() 

