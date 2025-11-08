"""
Core AI Grading Engine - Migrated from ai_correction system
Consolidated functionality for AI-powered grading with multi-model support
"""

import base64
import os
import re
import json
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass
import contextlib
import io
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """Enhanced API configuration for multi-model support"""
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    
    # Multi-model support with priority ordering
    available_models: list = None
    current_model_index: int = 0
    
    max_tokens: int = 50000
    temperature: float = 0.7
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 120
    
    def __post_init__(self):
        """Initialize available models and load API key from environment"""
        if self.available_models is None:
            self.available_models = [
                "google/gemini-2.5-flash-lite-preview-06-17",  # Primary model
                "google/gemini-2.5-flash",                    # Backup 1
                "google/gemini-2.5-pro",                      # Backup 2
                "anthropic/claude-3-haiku",                   # Backup 3
                "meta-llama/llama-3-8b-instruct:free",       # Free model 1
                "microsoft/wizardlm-2-8x22b:free",           # Free model 2
                "gryphe/mythomist-7b:free"                    # Free model 3
            ]
        
        # Load API key from environment
        env_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
        if env_key:
            self.api_key = env_key
        else:
            # Try loading from .env file
            env_file_path = Path('.env')
            if env_file_path.exists():
                try:
                    with open(env_file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                if key.strip() == 'OPENROUTER_API_KEY' and value.strip():
                                    self.api_key = value.strip()
                                    break
                except Exception as e:
                    logger.warning(f"Failed to read .env file: {e}")
        
        if not self.api_key:
            self.api_key = "Please set your API key in environment variables"
    
    @property
    def model(self) -> str:
        """Get current model"""
        if self.current_model_index < len(self.available_models):
            return self.available_models[self.current_model_index]
        return self.available_models[0]
    
    def switch_to_next_model(self) -> bool:
        """Switch to next available model"""
        if self.current_model_index < len(self.available_models) - 1:
            self.current_model_index += 1
            logger.info(f"Switched to backup model: {self.model}")
            return True
        return False
    
    def reset_model(self):
        """Reset to primary model"""
        self.current_model_index = 0
        logger.info(f"Reset to primary model: {self.model}")
    
    def is_valid(self) -> bool:
        """Check if API configuration is valid"""
        return bool(self.api_key and self.api_key.startswith(('sk-', 'or-')))

# Global configuration instance
api_config = APIConfig()

def img_to_base64(image_path, max_size_mb=4):
    """Convert image file to base64 encoding with auto compression"""
    if not PIL_AVAILABLE:
        raise ImportError("PIL is required for image processing")
    
    # Handle different input types
    if isinstance(image_path, str) and image_path.startswith(('http://', 'https://')):
        # Handle URL
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests is required for URL image processing")
        response = requests.get(image_path)
        response.raise_for_status()
        image_data = response.content
    elif hasattr(image_path, 'read') and callable(image_path.read):
        # Handle file-like object (e.g., Streamlit uploaded file)
        try:
            current_position = image_path.tell() if hasattr(image_path, 'tell') else 0
            image_data = image_path.read()
            if hasattr(image_path, 'seek'):
                image_path.seek(current_position)
        except Exception as e:
            logger.error(f"Error reading file object: {e}")
            raise
    else:
        # Handle file path
        file_path = Path(image_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Check if it's actually an image file
        file_ext = file_path.suffix.lower()
        if file_ext in ['.txt', '.md', '.doc', '.docx', '.rtf']:
            raise ValueError(f"File {image_path} is a text file, not an image")
        
        with open(file_path, 'rb') as f:
            image_data = f.read()
    
    # Check file size and compress if needed
    file_size_mb = len(image_data) / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        # Compress image
        image = Image.open(io.BytesIO(image_data))
        
        # Calculate compression ratio
        target_size = max_size_mb * 0.8  # Target 80% of max size for safety
        compression_ratio = target_size / file_size_mb
        
        # Reduce dimensions
        width, height = image.size
        new_width = int(width * (compression_ratio ** 0.5))
        new_height = int(height * (compression_ratio ** 0.5))
        
        # Resize image
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        format_name = 'JPEG' if image.mode == 'RGB' else 'PNG'
        quality = max(30, int(85 * compression_ratio))  # Minimum quality 30
        
        if format_name == 'JPEG':
            image.save(output, format=format_name, quality=quality, optimize=True)
        else:
            image.save(output, format=format_name, optimize=True)
        
        image_data = output.getvalue()
        logger.info(f"Compressed image from {file_size_mb:.2f}MB to {len(image_data)/(1024*1024):.2f}MB")
    
    # Convert to base64
    base64_str = base64.b64encode(image_data).decode('utf-8')
    
    # Determine MIME type
    image = Image.open(io.BytesIO(image_data))
    format_name = image.format.lower() if image.format else 'jpeg'
    mime_type = f"image/{format_name}"
    
    return f"data:{mime_type};base64,{base64_str}"

def pdf_pages_to_base64_images(pdf_path, dpi=150, max_size_mb=4):
    """Convert PDF pages to base64 images"""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF is required for PDF processing")
    
    images = []
    
    try:
        # Suppress PyMuPDF warnings
        with contextlib.redirect_stderr(io.StringIO()):
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert to image
                mat = fitz.Matrix(dpi/72, dpi/72)  # Scaling factor
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Compress if needed
                output = io.BytesIO()
                image.save(output, format='PNG', optimize=True)
                img_data = output.getvalue()
                
                # Check size and compress more if needed
                if len(img_data) / (1024 * 1024) > max_size_mb:
                    # Further compression
                    width, height = image.size
                    compression_ratio = max_size_mb / (len(img_data) / (1024 * 1024))
                    new_width = int(width * (compression_ratio ** 0.5))
                    new_height = int(height * (compression_ratio ** 0.5))
                    
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    image.save(output, format='PNG', optimize=True)
                    img_data = output.getvalue()
                
                # Convert to base64
                base64_str = base64.b64encode(img_data).decode('utf-8')
                images.append(f"data:image/png;base64,{base64_str}")
            
            doc.close()
    
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {e}")
        raise
    
    return images

async def call_ai_api_async(prompt, system_message="", images=None, files=None):
    """Async AI API call with multi-model fallback"""
    return call_ai_api(prompt, system_message, images, files)

def call_ai_api(prompt, system_message="", images=None, files=None):
    """Core AI API calling function with multi-model support and retry logic"""
    
    if not api_config.is_valid():
        raise ValueError("API key not properly configured")
    
    # Prepare messages
    messages = []
    
    if system_message:
        messages.append({"role": "system", "content": system_message})
    
    # Process files if provided
    processed_images = []
    if files:
        for file_path in files:
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                if file_path.suffix.lower() == '.pdf':
                    # Convert PDF to images
                    pdf_images = pdf_pages_to_base64_images(file_path)
                    processed_images.extend(pdf_images)
                elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    # Convert image to base64
                    img_base64 = img_to_base64(file_path)
                    processed_images.append(img_base64)
                else:
                    # Handle text files
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            prompt += f"\n\n=== {file_path.name} ===\n{content}"
                    except Exception as e:
                        logger.warning(f"Could not read file {file_path}: {e}")
    
    if images:
        processed_images.extend(images if isinstance(images, list) else [images])
    
    # Build user message
    user_content = [{"type": "text", "text": prompt}]
    
    for img in processed_images:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": img}
        })
    
    messages.append({"role": "user", "content": user_content})
    
    # Try each model with retry logic
    last_exception = None
    
    for model_attempt in range(len(api_config.available_models)):
        current_model = api_config.model
        
        for retry_attempt in range(api_config.max_retries):
            try:
                headers = {
                    "Authorization": f"Bearer {api_config.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": current_model,
                    "messages": messages,
                    "max_tokens": api_config.max_tokens,
                    "temperature": api_config.temperature
                }
                
                if not REQUESTS_AVAILABLE:
                    raise ImportError("requests library is required")
                
                response = requests.post(
                    f"{api_config.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=api_config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"Successful API call with model: {current_model}")
                    return content
                else:
                    error_msg = f"API error {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    last_exception = Exception(error_msg)
                    
                    # If rate limited or server error, try next model
                    if response.status_code in [429, 500, 502, 503, 504]:
                        break
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {retry_attempt + 1} failed for model {current_model}: {str(e)}")
                
                if retry_attempt < api_config.max_retries - 1:
                    wait_time = api_config.retry_delay * (2 ** retry_attempt)
                    time.sleep(wait_time)
        
        # Try next model
        if not api_config.switch_to_next_model():
            break
    
    # Reset to primary model for next call
    api_config.reset_model()
    
    # If all models failed, raise the last exception
    if last_exception:
        raise last_exception
    else:
        raise Exception("All AI models failed to respond")

def process_file_content(file_path):
    """Process file content based on file type"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_ext = file_path.suffix.lower()
    
    if file_ext == '.pdf':
        # For PDF files, we'll use image processing
        return f"[PDF FILE: {file_path.name} - Will be processed as images]"
    elif file_ext in ['.txt', '.md']:
        # Text files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
    elif file_ext in ['.png', '.jpg', '.jpeg']:
        # Image files
        return f"[IMAGE FILE: {file_path.name} - Will be processed as base64 image]"
    else:
        # Unknown file type
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return f"[BINARY FILE: {file_path.name} - Cannot process as text]"

def convert_latex_to_unicode(text):
    """Convert LaTeX symbols to Unicode equivalents"""
    latex_mappings = {
        r'\times': '×',
        r'\div': '÷',
        r'\pm': '±',
        r'\mp': '∓',
        r'\le': '≤',
        r'\ge': '≥',
        r'\ne': '≠',
        r'\approx': '≈',
        r'\equiv': '≡',
        r'\angle': '∠',
        r'\pi': 'π',
        r'\alpha': 'α',
        r'\beta': 'β',
        r'\gamma': 'γ',
        r'\delta': 'δ',
        r'\theta': 'θ',
        r'\lambda': 'λ',
        r'\mu': 'μ',
        r'\sigma': 'σ',
        r'\omega': 'ω',
        r'\infty': '∞',
        r'\sum': '∑',
        r'\prod': '∏',
        r'\int': '∫',
        r'\sqrt': '√',
        r'\partial': '∂',
        r'\nabla': '∇',
        r'\Delta': 'Δ',
        r'\Omega': 'Ω',
        r'\Phi': 'Φ',
        r'\Psi': 'Ψ',
        r'\in': '∈',
        r'\notin': '∉',
        r'\subset': '⊂',
        r'\supset': '⊃',
        r'\cap': '∩',
        r'\cup': '∪',
        r'\wedge': '∧',
        r'\vee': '∨',
        r'\neg': '¬',
        r'\forall': '∀',
        r'\exists': '∃',
        r'\emptyset': '∅',
        r'\rightarrow': '→',
        r'\leftarrow': '←',
        r'\leftrightarrow': '↔',
        r'\Rightarrow': '⇒',
        r'\Leftarrow': '⇐',
        r'\Leftrightarrow': '⇔',
    }
    
    result = text
    for latex, unicode_char in latex_mappings.items():
        result = result.replace(latex, unicode_char)
    
    # Handle superscripts and subscripts
    superscript_map = str.maketrans('0123456789+-=()abcdefghijklmnopqrstuvwxyz', 
                                   '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖᑫʳˢᵗᵘᵛʷˣʸᶻ')
    subscript_map = str.maketrans('0123456789+-=()abcdefghijklmnopqrstuvwxyz',
                                 '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐᵦ𝒸𝒹ₑ𝒻𝒸ₕᵢⱼₖₗₘₙₒₚᑫᵣₛₜᵤᵥwₓᵧ𝒵')
    
    # Simple superscript/subscript handling
    result = re.sub(r'\^(\w)', lambda m: m.group(1).translate(superscript_map), result)
    result = re.sub(r'_(\w)', lambda m: m.group(1).translate(subscript_map), result)
    
    return result

def detect_loop_and_cleanup(text, max_repetitions=3):
    """Detect and clean up repetitive content"""
    lines = text.split('\n')
    cleaned_lines = []
    line_counts = {}
    
    for line in lines:
        stripped_line = line.strip()
        if stripped_line:
            line_counts[stripped_line] = line_counts.get(stripped_line, 0) + 1
            if line_counts[stripped_line] <= max_repetitions:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def enforce_strict_format(text):
    """Enforce strict formatting rules for grading output"""
    # Remove LaTeX symbols
    text = convert_latex_to_unicode(text)
    
    # Fix common formatting issues
    text = re.sub(r'\$+', '', text)  # Remove $ symbols
    text = re.sub(r'\^([^$\s]+)', r'^\1', text)  # Fix superscripts
    text = re.sub(r'_{([^}]+)}', r'_\1', text)  # Fix subscripts
    
    # Ensure proper line breaks for sections
    text = re.sub(r'(### 题目\d+)', r'\n\1', text)
    text = re.sub(r'(\*\*满分\*\*)', r'\n\1', text)
    text = re.sub(r'(\*\*得分\*\*)', r'\n\1', text)
    text = re.sub(r'(\*\*批改详情\*\*)', r'\n\1', text)
    
    return text.strip()

def clean_grading_output(text):
    """Clean and standardize grading output"""
    # Apply all cleaning functions
    text = convert_latex_to_unicode(text)
    text = detect_loop_and_cleanup(text)
    text = enforce_strict_format(text)
    
    return text

def convert_to_html_markdown(text):
    """Convert grading output to HTML-friendly markdown"""
    # Convert bold markers
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Convert checkmarks and crosses
    text = text.replace('✓', '✅')
    text = text.replace('✗', '❌')
    
    # Convert line breaks
    text = text.replace('\n', '<br>\n')
    
    return text

# Compatibility functions for the old API
def call_tongyiqianwen_api(*args, **kwargs):
    """Compatibility wrapper for the old API function name"""
    if len(args) == 1:
        return call_ai_api(args[0], **kwargs)
    elif len(args) == 2:
        return call_ai_api(args[0], args[1], **kwargs)
    elif len(args) > 2:
        # Handle file arguments
        prompt = args[0]
        system_message = kwargs.get('system_message', '')
        files = list(args[1:])
        return call_ai_api(prompt, system_message, files=files)
    else:
        raise ValueError("Invalid arguments for API call")

# Configuration management
def update_api_config(**kwargs):
    """Update API configuration"""
    global api_config
    for key, value in kwargs.items():
        if hasattr(api_config, key):
            setattr(api_config, key, value)

def get_api_status():
    """Get current API configuration status"""
    return {
        "api_key_configured": api_config.is_valid(),
        "current_model": api_config.model,
        "available_models": api_config.available_models,
        "model_index": api_config.current_model_index,
        "base_url": api_config.base_url
    }

# Initialize logging
def setup_logging():
    """Setup logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'ai_grading.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

# Initialize on import
setup_logging()