import base64
import requests  
import openai
import re
from pathlib import Path
import fitz  # PyMuPDF
import json
import os
import time
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass
import contextlib
try:
    import prompts
except ImportError:
    from . import prompts

# 导入PDF错误抑制工具
try:
    from pdf_utils import SuppressOutput, safe_pdf_processing
    PDF_UTILS_AVAILABLE = True
except ImportError:
    PDF_UTILS_AVAILABLE = False

# 抑制MuPDF错误输出
import warnings
warnings.filterwarnings("ignore")

# 设置环境变量抑制MuPDF输出
os.environ['MUPDF_QUIET'] = '1'

try:
    import fitz  # PyMuPDF
    # 立即抑制错误输出
    import sys
    if hasattr(os, 'devnull'):
        original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
except ImportError:
    fitz = None

from .prompts import correction_prompt, system_message
from . import prompts

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API配置类"""
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-2.5-flash-lite-preview-06-17"
    max_tokens: int = 4096
    temperature: float = 0.7
    max_retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        """初始化后处理，从环境变量或默认值设置API密钥"""
        # 优先级：环境变量 > 硬编码值
        env_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
        if env_key:
            self.api_key = env_key
        elif not self.api_key:
            # 使用新的OpenRouter API密钥
            self.api_key = "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"
    
    def is_valid(self) -> bool:
        """检查API配置是否有效"""
        return bool(self.api_key and self.api_key.startswith(('sk-', 'or-')))
    
    def get_status(self) -> dict:
        """获取配置状态信息"""
        return {
            "api_key_configured": bool(self.api_key),
            "api_key_source": "environment" if os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY') else "default",
            "base_url": self.base_url,
            "model": self.model,
            "is_valid": self.is_valid()
        }

# 全局配置实例
api_config = APIConfig()

def img_to_base64(image_path, max_size_mb=4):
    """
    将图片文件转换为base64编码，支持自动压缩
    支持本地文件路径、URL和Streamlit上传的文件对象
    现在也支持文本文件的检测和跳过
    """
    import io
    import os
    from pathlib import Path
    from PIL import Image
    
    # 检查文件类型
    if isinstance(image_path, str):
        file_path = Path(image_path)
        if file_path.exists():
            # 检查文件扩展名
            file_ext = file_path.suffix.lower()
            if file_ext in ['.txt', '.md', '.doc', '.docx', '.rtf']:
                # 这是文本文件，不应该作为图像处理
                raise ValueError(f"文件 {image_path} 是文本文件，不能作为图像处理")
    
    # 处理URL
    if isinstance(image_path, str) and image_path.startswith(('http://', 'https://')):
        response = requests.get(image_path)
        response.raise_for_status()  
        image_data = response.content
    # 处理Streamlit上传的文件对象
    elif hasattr(image_path, 'read') and callable(image_path.read):
        try:
            # 保存当前文件位置
            if hasattr(image_path, 'tell') and callable(image_path.tell):
                current_position = image_path.tell()
            else:
                current_position = 0
                
            # 读取文件数据
            image_data = image_path.read()
            
            # 恢复文件位置
            if hasattr(image_path, 'seek') and callable(image_path.seek):
                image_path.seek(current_position)
        except Exception as e:
            raise Exception(f"Failed to read uploaded file: {str(e)}")
    # 处理本地文件路径
    elif isinstance(image_path, str):
        # 检查文件大小，如果太大则压缩
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            # 文件不大，直接读取
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
        else:
            # 文件太大，需要压缩
            logging.info(f"图片文件过大 ({file_size_mb:.2f}MB)，正在压缩...")
            
            # 打开图片进行压缩
            img = Image.open(image_path)
            
            # 转换为RGB模式（如果是RGBA）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 计算压缩参数
            quality = 85
            max_dimension = 1920  # 最大尺寸
            
            # 如果图片尺寸太大，先缩放
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 压缩图片直到满足大小要求
            while quality > 20:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                compressed_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                
                if compressed_size_mb <= max_size_mb:
                    logging.info(f"压缩完成: {file_size_mb:.2f}MB -> {compressed_size_mb:.2f}MB (质量: {quality})")
                    image_data = buffer.getvalue()
                    break
                
                quality -= 10
            else:
                # 如果还是太大，进一步缩小尺寸
                while max_dimension > 800:
                    max_dimension -= 200
                    ratio = max_dimension / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img_resized = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    buffer = io.BytesIO()
                    img_resized.save(buffer, format='JPEG', quality=70, optimize=True)
                    compressed_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                    
                    if compressed_size_mb <= max_size_mb:
                        logging.info(f"缩放压缩完成: {file_size_mb:.2f}MB -> {compressed_size_mb:.2f}MB (尺寸: {new_size})")
                        image_data = buffer.getvalue()
                        break
                else:
                    # 最后的尝试
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=50, optimize=True)
                    final_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                    logging.info(f"最终压缩: {file_size_mb:.2f}MB -> {final_size_mb:.2f}MB")
                    image_data = buffer.getvalue()
    else:
        raise Exception(f"Unsupported image source type: {type(image_path)}")
        
    return base64.b64encode(image_data).decode('utf-8')

def get_file_type(file_path):
    """
    检测文件类型，返回文件类型分类
    
    返回值:
    - 'image': 图片文件
    - 'pdf': PDF文件
    - 'word': Word文档
    - 'text': 纯文本文件
    - 'unknown': 未知类型
    """
    if isinstance(file_path, str):
        file_ext = Path(file_path).suffix.lower()
        
        # 图片文件
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            return 'image'
        
        # PDF文件
        elif file_ext == '.pdf':
            return 'pdf'
        
        # Word文档
        elif file_ext in ['.doc', '.docx']:
            return 'word'
        
        # 文本文件
        elif file_ext in ['.txt', '.md', '.rtf', '.csv']:
            return 'text'
        
        # 其他可能的文本格式
        elif file_ext in ['.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml']:
            return 'text'
    
    return 'unknown'

def read_pdf_file(file_path):
    """
    读取PDF文件内容
    """
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            return text.strip()
    except ImportError:
        try:
            # 如果PyPDF2不可用，尝试使用pdfplumber
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except ImportError:
            return f"[PDF文件: {Path(file_path).name}] - 需要安装PyPDF2或pdfplumber库来读取PDF内容"
    except Exception as e:
        return f"[PDF文件读取失败: {Path(file_path).name}] - 错误: {str(e)}"

def read_word_file(file_path):
    """
    读取Word文档内容
    """
    try:
        import docx
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except ImportError:
        return f"[Word文档: {Path(file_path).name}] - 需要安装python-docx库来读取Word文档"
    except Exception as e:
        return f"[Word文档读取失败: {Path(file_path).name}] - 错误: {str(e)}"

def process_file_content(file_path):
    """
    根据文件类型处理文件内容
    
    返回:
    - (content_type, content): 内容类型和内容
      - content_type: 'text' , 'image', 'pdf'或 'error'
      - content: 文件内容或错误信息
    """
    file_type = get_file_type(file_path)
    file_name = Path(file_path).name
    
    try:
        if file_type == 'image':
            # 图片文件作为base64返回
            return 'image', file_path
        
        elif file_type == 'pdf':
            # PDF文件处理 - 先尝试转换为图像，失败则提取文本
            try:
                # 检查文件大小，如果太大则直接提取文本
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if file_size_mb > 50:  # 大于50MB的PDF直接提取文本
                    logger.info(f"PDF文件过大({file_size_mb:.1f}MB)，直接提取文本: {file_name}")
                    text_content = read_pdf_file(file_path)
                    return 'text', f"[大型PDF文档: {file_name}]\n{text_content}"
                
                # 尝试图像处理
                return 'pdf', file_path
                
            except Exception as e:
                logger.warning(f"PDF处理异常，尝试文本提取: {str(e)}")
                # 如果图像处理失败，尝试提取文本
                try:
                    text_content = read_pdf_file(file_path)
                    if text_content and not text_content.startswith("[PDF文件读取失败"):
                        return 'text', f"[PDF文档(文本模式): {file_name}]\n{text_content}"
                    else:
                        return 'error', f"[PDF处理失败: {file_name}] - 无法读取内容"
                except Exception as text_error:
                    return 'error', f"[PDF处理失败: {file_name}] - {str(text_error)}"
        
        elif file_type == 'word':
            # Word文档提取文本
            content = read_word_file(file_path)
            return 'text', f"[Word文档: {file_name}]\n{content}"
        
        elif file_type == 'text':
            # 纯文本文件
            content = read_text_file(file_path)
            return 'text', f"[文本文件: {file_name}]\n{content}"
        
        else:
            # 未知类型，尝试作为文本读取
            try:
                content = read_text_file(file_path)
                return 'text', f"[文件: {file_name}]\n{content}"
            except:
                return 'error', f"[不支持的文件类型: {file_name}] - 无法处理此文件"
    
    except Exception as e:
        return 'error', f"[文件处理错误: {file_name}] - {str(e)}"

def is_image_file(file_path):
    """检查文件是否为图像文件"""
    return get_file_type(file_path) in ['image', 'pdf']  # PDF也可以作为图像处理

def read_text_file(file_path):
    """读取文本文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

def force_natural_language(text):
    """强制将可能的JSON格式转换为自然语言"""
    # 如果文本包含大量的JSON特征，进行处理
    if (text.count('{') > 2 and text.count('}') > 2) or ('"' in text and ':' in text and ',' in text):
        # 尝试去除格式符号
        text = re.sub(r'[{}\[\]"]', '', text)
        text = re.sub(r':\s*', ': ', text)
        text = re.sub(r',\s*', '\n', text)
        
        # 添加警告消息
        text = "【注意：以下内容已从结构化格式转换为纯文本】\n\n" + text
    
    return text

def pdf_pages_to_base64_images(pdf_path, zoom=2.0):
    """
    将 PDF 每页转换为 Base64 编码的图像数据列表
    增强版：支持错误抑制和多种备用方案
    
    参数:
        pdf_path (str): PDF 文件路径
        zoom (float): 缩放因子 (提高分辨率)
    
    返回:
        list: 包含每页 Base64 编码图像数据的列表
    """
    if not fitz:
        logger.error("PyMuPDF未安装，无法处理PDF")
        return pdf_fallback_method(pdf_path)
    
    base64_images = []
    
    # 使用自定义的错误抑制器
    suppress_context = SuppressOutput() if PDF_UTILS_AVAILABLE else contextlib.nullcontext()
    
    try:
        with suppress_context:
            # 尝试打开PDF文件
            doc = fitz.open(pdf_path)
            
            # 检查PDF是否损坏或加密
            if doc.is_encrypted:
                logger.warning(f"PDF文件 {pdf_path} 已加密，尝试解密")
                # 尝试用空密码解密
                if not doc.authenticate(""):
                    logger.error(f"PDF文件 {pdf_path} 无法解密")
                    doc.close()
                    return pdf_fallback_method(pdf_path)
            
            if doc.page_count == 0:
                logger.warning(f"PDF文件 {pdf_path} 没有页面")
                doc.close()
                return pdf_fallback_method(pdf_path)
            
            # 限制处理页面数量，避免过大文件
            max_pages = min(doc.page_count, 20)  # 最多处理20页
            
            # 处理每一页
            for page_num in range(max_pages):
                try:
                    with contextlib.redirect_stderr(open(os.devnull, 'w')):
                        page = doc.load_page(page_num)
                        
                        # 使用较小的缩放因子减少内存使用
                        matrix = fitz.Matrix(zoom, zoom)
                        
                        # 获取页面的像素图，抑制错误
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        
                        # 转换为图像数据
                        img_data = pix.tobytes("png")
                        
                        # 检查图像数据大小，如果太大则压缩
                        if len(img_data) > 3 * 1024 * 1024:  # 3MB阈值
                            # 使用PIL压缩图像
                            img = Image.open(io.BytesIO(img_data))
                            
                            # 转换为RGB模式
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')
                            
                            # 计算合适的尺寸
                            max_size = 1600  # 最大尺寸
                            if max(img.size) > max_size:
                                ratio = max_size / max(img.size)
                                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                                img = img.resize(new_size, Image.Resampling.LANCZOS)
                            
                            # 压缩图像
                            buffer = io.BytesIO()
                            img.save(buffer, format='JPEG', quality=80, optimize=True)
                            img_data = buffer.getvalue()
                        
                        # 编码为 Base64
                        base64_str = base64.b64encode(img_data).decode("utf-8")
                        base64_images.append(base64_str)
                        
                        # 清理内存
                        pix = None
                        
                except Exception as e:
                    logger.warning(f"处理PDF第{page_num + 1}页时出错: {str(e)}")
                    # 继续处理下一页，不中断整个过程
                    continue
            
            doc.close()
            
            # 如果没有成功处理任何页面，使用备用方法
            if not base64_images:
                logger.warning(f"PDF文件 {pdf_path} 无法提取任何页面，使用备用方法")
                return pdf_fallback_method(pdf_path)
            
            logger.info(f"成功处理PDF文件 {pdf_path}，共{len(base64_images)}页")
            return base64_images
            
    except Exception as e:
        logger.error(f"PDF处理完全失败 {pdf_path}: {str(e)}")
        # 使用备用方法
        return pdf_fallback_method(pdf_path)

def pdf_fallback_method(pdf_path):
    """PDF处理的备用方法 - 尝试多种方案"""
    logger.info(f"尝试PDF备用处理方案: {pdf_path}")
    
    # 方案1: 尝试提取文本内容
    try:
        text_content = read_pdf_file(pdf_path)
        if text_content and not text_content.startswith("[PDF文件读取失败"):
            logger.info("备用方案1成功: 提取PDF文本内容")
            # 返回空列表，让调用方处理文本内容
            return []
    except Exception as e:
        logger.warning(f"备用方案1失败: {str(e)}")
    
    # 方案2: 尝试使用更简单的PyMuPDF设置
    try:
        import warnings
        import contextlib
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with contextlib.redirect_stderr(open(os.devnull, 'w')):
                doc = fitz.open(pdf_path)
                
                # 只处理第一页，使用最小设置
                if doc.page_count > 0:
                    page = doc.load_page(0)
                    # 使用最小缩放
                    matrix = fitz.Matrix(1.0, 1.0)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    img_data = pix.tobytes("jpeg")
                    base64_str = base64.b64encode(img_data).decode("utf-8")
                    doc.close()
                    logger.info("备用方案2成功: 简化PDF处理")
                    return [base64_str]
                
                doc.close()
    except Exception as e:
        logger.warning(f"备用方案2失败: {str(e)}")
    
    # 方案3: 创建错误提示图像
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建一个简单的错误提示图像
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # 添加文字
        text_lines = [
            "PDF文件处理失败",
            f"文件: {os.path.basename(pdf_path)}",
            "可能的原因:",
            "- PDF文件损坏或格式不支持",
            "- 文件过大或页面过多",
            "- 系统资源不足",
            "",
            "建议:",
            "- 尝试重新保存PDF文件",
            "- 减少文件大小",
            "- 转换为图片格式"
        ]
        
        y_offset = 50
        for line in text_lines:
            draw.text((50, y_offset), line, fill='black')
            y_offset += 40
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        logger.info("备用方案3成功: 创建错误提示图像")
        return [base64_str]
        
    except Exception as e:
        logger.error(f"备用方案3失败: {str(e)}")
    
    # 最终方案: 返回空列表
    logger.error(f"所有PDF处理方案都失败: {pdf_path}")
    return []

def extract_json_from_str(input_str):
    """从字符串中提取JSON对象"""
    try:
        # 尝试直接解析整个字符串
        return json.loads(input_str)
    except json.JSONDecodeError:
        # 如果失败，尝试找到JSON块
        import re
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, input_str, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        # 如果仍然失败，返回原始字符串
        return input_str

def call_tongyiqianwen_api(input_text: str, *input_contents, system_message: str = "") -> str:
    """
    调用API进行多类型文件处理，支持批改严格程度和语言设置
    增强版：支持图像、PDF、Word文档、文本文件等多种类型，带重试机制和错误处理
    
    参数:
    input_text: 字符串，提示文本
    input_contents: 一系列文件路径（支持图像、PDF、Word、文本等多种格式）/str/(type,base64 image)
    system_message: 系统消息
    
    返回:
    字符串，API响应内容
    """
    from openai import OpenAI
    
    # 检查API配置
    if not api_config.is_valid():
        error_msg = """
🚫 API配置错误

可能的解决方案：
1. 设置环境变量：
   - OPENROUTER_API_KEY=your_api_key
   - 或 OPENAI_API_KEY=your_api_key

2. 检查API密钥格式：
   - OpenRouter密钥应以 'sk-or-' 开头
   - OpenAI密钥应以 'sk-' 开头

3. 确认密钥有效性：
   - 登录 https://openrouter.ai 检查密钥状态
   - 确认账户有足够的余额

当前配置状态：
""" + json.dumps(api_config.get_status(), ensure_ascii=False, indent=2)
        logger.error("API配置无效")
        return error_msg
    
    try:
        client = OpenAI(
            api_key=api_config.api_key,
            base_url=api_config.base_url
        )
    except Exception as e:
        error_msg = f"❌ OpenAI客户端初始化失败: {str(e)}"
        logger.error(error_msg)
        return error_msg
    
    content = [{"type": "text", "text": input_text}]
    
    # 处理文件
    try:
        for single_content in input_contents:
            if (
                isinstance(single_content, tuple) and 
                len(single_content) == 2 and 
                all(isinstance(item, str) for item in single_content)
            ):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{single_content[0]};base64,{single_content[1]}"
                    }
                })   
            
            elif os.path.isfile(single_content):
                content_type, processed_content = process_file_content(single_content)            
                if content_type == 'text':
                    content.append({
                        "type": "text",
                        "text": processed_content
                    })
                elif content_type == 'image':
                    # 普通图像文件
                    base_64_image = img_to_base64(single_content)
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base_64_image}"
                        }
                    })    
                # 检查是否是PDF文件
                elif content_type == 'pdf':
                    # PDF文件作为图像处理
                    base_64_images = pdf_pages_to_base64_images(single_content)
                    for base_64_image in base_64_images:
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base_64_image}"
                            }
                        })
                else:
                    raise ValueError(f"The file {single_content} could not be processed.")
            else:
                content.append({
                    "type": "text",
                    "text": single_content
                })
    except Exception as e:
        error_msg = f"❌ 文件处理失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

    # 调用API，带重试机制
    for attempt in range(api_config.max_retries):
        try:
            final_message = []
            if system_message:
                final_message.append({"role": "system", "content": system_message})
            final_message.append({"role": "user", "content": content})
            
            logger.info(f"API调用尝试 {attempt + 1}/{api_config.max_retries}")
            
            response = client.chat.completions.create(
                model=api_config.model,
                messages=final_message,
                max_tokens=api_config.max_tokens,
                temperature=api_config.temperature
            )

            # 获取结果并处理
            result = response.choices[0].message.content
        
            # 验证结果不为空
            if not result or not result.strip():
                logger.warning("API返回空结果")
                if attempt < api_config.max_retries - 1:
                    time.sleep(api_config.retry_delay)
                    continue
                else:
                    fallback_msg = "❌ API返回了空结果。可能的原因：文件内容无法识别或API服务暂时不可用。"
                    logger.error("所有重试都失败，返回fallback消息")
                    return fallback_msg
            
            logger.info("API调用成功")
            return result
        
        except Exception as e:
            error_str = str(e)
            logger.error(f"API调用失败 (尝试 {attempt + 1}): {error_str}")
            
            # 特殊错误处理
            if "401" in error_str or "Unauthorized" in error_str:
                auth_error_msg = f"""
❌ 认证失败 (401 Unauthorized)

问题分析：
- API密钥无效或已过期
- 密钥格式错误
- 账户余额不足

解决方案：
1. 检查API密钥：
   - 当前使用的密钥来源：{api_config.get_status()['api_key_source']}
   - 密钥前缀：{api_config.api_key[:10]}...

2. 更新API密钥：
   - 访问 https://openrouter.ai/keys
   - 生成新的API密钥
   - 设置环境变量：OPENROUTER_API_KEY=your_new_key

3. 检查账户状态：
   - 登录 https://openrouter.ai
   - 查看账户余额和使用情况

原始错误：{error_str}
"""
                logger.error("认证失败")
                return auth_error_msg
            
            elif "429" in error_str or "rate_limit" in error_str.lower():
                rate_limit_msg = f"❌ API调用频率限制，请稍后重试。错误：{error_str}"
                if attempt < api_config.max_retries - 1:
                    wait_time = api_config.retry_delay * (2 ** attempt)  # 指数退避
                    logger.info(f"遇到频率限制，等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                    continue
                else:
                    return rate_limit_msg
            
            elif "500" in error_str or "502" in error_str or "503" in error_str:
                server_error_msg = f"❌ 服务器错误，请稍后重试。错误：{error_str}"
                if attempt < api_config.max_retries - 1:
                    time.sleep(api_config.retry_delay * (attempt + 1))
                    continue
                else:
                    return server_error_msg
            
            # 其他错误
            if attempt < api_config.max_retries - 1:
                time.sleep(api_config.retry_delay * (attempt + 1))  # 指数退避
                continue
            else:
                error_msg = f"""
❌ API调用失败 (所有重试已耗尽)

错误详情：{error_str}

可能的解决方案：
1. 检查网络连接
2. 验证API密钥有效性
3. 确认账户余额充足
4. 稍后重试

配置信息：
{json.dumps(api_config.get_status(), ensure_ascii=False, indent=2)}
"""
                logger.error(error_msg)
                return error_msg

# 标准API调用函数
default_api = call_tongyiqianwen_api

class GradingResult:
    """批改结果标准化类"""
    
    def __init__(self, success: bool = True, data: Any = None, error_message: str = "", processing_time: float = 0.0):
        self.success = success
        self.data = data
        self.error_message = error_message
        self.processing_time = processing_time
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，适合网站API返回"""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

def safe_api_call(func):
    """装饰器：为API调用添加统一的错误处理和结果包装"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            logger.info(f"开始执行 {func.__name__}")
            result = func(*args, **kwargs)
            processing_time = time.time() - start_time
            logger.info(f"{func.__name__} 执行成功，耗时: {processing_time:.2f}秒")
            return GradingResult(success=True, data=result, processing_time=processing_time)
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"{func.__name__} 执行失败: {str(e)}"
            logger.error(error_msg)
            return GradingResult(success=False, error_message=error_msg, processing_time=processing_time)
    return wrapper

def generate_json_marking_scheme(*image_file, api=default_api):
    """生成评分方案，返回JSON形式"""
    try:
        prompt = prompts.marking_scheme_prompt
        result = api(prompt, *image_file, system_message=prompts.system_message)
        return extract_json_from_str(result)
    except Exception as e:
        error_msg = "生成评分方案失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_marking_scheme_json(marking_schemes: tuple[str], student_answers: tuple[str], strictness_level="中等", api=default_api):
    """使用图像中的评分方案进行批改，返json形式
    marking_schemes,student_answers:tuple(path)
    """
    try:
        # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = prompts.correction_prompt + "\n\n"
        prompt += prompts.strictness_descriptions[strictness_level] + '\n\n'
        prompt += prompts.get_marking_scheme_notice()
        student_answer_notice = prompts.get_student_answer_notice()
        result = api(prompt, *marking_schemes, student_answer_notice, *student_answers, system_message=prompts.system_message)
        return extract_json_from_str(result)
    except Exception as e:
        error_msg = "批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_without_marking_scheme_json(student_answer: tuple[str], strictness_level="中等", api=default_api):
    """自动生成评分方案并批改，返回纯json形式"""
    try:
        # 先生成评分方案
        marking_scheme = generate_json_marking_scheme(*student_answer, api=api)
        
        # 使用生成的评分方案进行批改
        prompt = prompts.correction_prompt + "\n\n"
        prompt += prompts.strictness_descriptions[strictness_level] + '\n\n'
        prompt += prompts.get_auto_scheme_notice()
        prompt += json.dumps(marking_scheme, ensure_ascii=False) + "\n\n"
        student_answer_notice = prompts.get_student_answer_notice()
        result = api(prompt, student_answer_notice, *student_answer, system_message=prompts.system_message)
        return extract_json_from_str(result)
    except Exception as e:
        error_msg = "批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_single_group(*image_files, strictness_level="中等", api=default_api, group_index=1):
    """
    对单个文件组（通常对应一道题）进行批改，返回JSON格式
    
    参数:
    image_files: 图像文件列表，通常包含题目、学生答案、评分标准
    strictness_level: 批改严格程度
    api: API调用函数
    group_index: 组索引，用于标识是第几道题
    """
    try:
        # 使用统一的批改提示词
        prompt = prompts.correction_prompt + "\n\n" + prompts.strictness_descriptions[strictness_level]
        return force_natural_language(api(prompt, *image_files, system_message=prompts.system_message))
    except Exception as e:
        error_msg = f"第{group_index}题批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def generate_comprehensive_summary(all_results, total_groups=1, api=default_api):
    """
    基于所有批改结果生成综合总结
    
    参数:
    all_results: 所有批改结果的列表
    total_groups: 总题目数量
    """
    try:
        # 使用统一的综合总结提示词
        prompt = prompts.comprehensive_summary_prompt(total_groups).replace("{{all_results}}", str(all_results))
        # 系统消息
        system_message = prompts.summary_system_message if hasattr(prompts, 'summary_system_message') else ""
        result = api(prompt, system_message=system_message)
        return result
        
    except Exception as e:
        error_msg = "生成综合总结失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_of_multiple_answers(marking_schemes: tuple[str], student_answers: str, strictness_level="中等", api=default_api):
    """使用图像中的评分方案进行批改，返json形式
    marking_schemes:paths
    student_answers:path of pdf
    """
    try:
        final_result = {"individual_grading": [],
       "overall_comment": ""}
        base64_student_answers = pdf_pages_to_base64_images(student_answers)

         # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = prompts.correction_prompt + "\n\n"
        prompt += prompts.strictness_descriptions[strictness_level] + '\n\n'
        prompt += prompts.get_marking_scheme_notice()
        student_answer_notice = prompts.get_student_answer_notice()
        #批改每一页
        for i in base64_student_answers:
            result = api(prompt, *marking_schemes, student_answer_notice, ("png", i), system_message=prompts.system_message)
            individual_result = extract_json_from_str(result)
            final_result["individual_grading"].append(individual_result)
        comment = generate_comprehensive_summary(str(final_result["individual_grading"]), total_groups=len(base64_student_answers), api=api)
        final_result["overall_comment"] = comment
        return final_result
    except Exception as e:
        error_msg = "批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

# ==================== 向后兼容接口 ====================

def efficient_correction_single(*image_files, strictness_level="中等", api=default_api):
    """
    🎯 专为老师批量批改设计的高效简洁批改函数
    输出简洁格式，便于老师快速处理大量作业
    
    参数:
    image_files: 图像文件列表
    strictness_level: 批改严格程度
    api: API调用函数
    
    返回:
    简洁的批改结果字符串
    """
    try:
        # 使用已有的批改功能
        detailed_result = correction_single_group(*image_files, strictness_level=strictness_level, api=api)
        
        # 如果结果太长，进行简化处理
        if len(detailed_result) > 500:
            # 使用prompts.py中的简洁提示词
            prompt = prompts.efficient_simplification_prompt() + detailed_result
            # 调用API进行简化
            simplified = api(prompt, system_message=prompts.system_message)
            return simplified
        return detailed_result
        
    except Exception as e:
        error_msg = "高效批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def batch_efficient_correction(*image_files, strictness_level="中等", api=default_api):
    """
    🚀 批量高效批改函数，专为老师处理多份作业设计
    
    参数:
    image_files: 图像文件列表
    strictness_level: 批改严格程度
    api: API调用函数
    
    返回:
    批量批改结果字符串
    """
    try:
        from datetime import datetime
        
        results = []
        total_files = len(image_files)
        
        for i, file in enumerate(image_files, 1):
            try:
                # 为每个文件调用高效批改
                result = efficient_correction_single(file, 
                                                   strictness_level=strictness_level, 
                                                   api=api)
                
                # 添加序号标识
                file_name = getattr(file, 'name', f'文件{i}')
                header = f"## 📄 {file_name} ({i}/{total_files})\n\n"
                results.append(header + result)
                
            except Exception as e:
                error_msg = f"文件 {i} 批改失败: {str(e)}"
                results.append(f"## ❌ 文件 {i}\n{error_msg}")
        
        # 组合所有结果
        final_result = "\n\n---\n\n".join(results)
        
        # 添加批量批改总结
        summary_header = f"\n\n# 📊 批改总览\n**共批改 {total_files} 份作业**\n✅ 批改完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return final_result + summary_header
        
    except Exception as e:
        error_msg = "批量批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def generate_marking_scheme(*image_file, api=default_api):
    """生成评分方案，返回纯文本形式（向后兼容）"""
    try:
        # 使用新的JSON生成函数并转换为文本
        json_result = generate_json_marking_scheme(*image_file, api=api)
        
        # 使用prompts.py中的格式化函数
        return prompts.marking_scheme_text_format(json_result)
            
    except Exception as e:
        error_msg = "生成评分方案失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_marking_scheme_legacy(marking_schemes: tuple[str], student_answers: tuple[str], strictness_level="中等", api=default_api):
    """使用图像中的评分方案进行批改，返回文本形式（向后兼容）"""
    try:
         # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = prompts.correction_prompt + "\n\n"
        prompt += prompts.strictness_descriptions[strictness_level] + '\n\n'
        prompt += prompts.get_marking_scheme_notice()
        student_answer_notice = prompts.get_student_answer_notice()
        result = api(prompt, *marking_schemes, student_answer_notice, *student_answers, system_message=prompts.system_message)
        
        # 将结果转换为自然语言格式
        return force_natural_language(result)
            
    except Exception as e:
        error_msg = "批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_without_marking_scheme_legacy(student_answer: tuple[str], strictness_level="中等", api=default_api):
    """自动生成评分方案并批改，返回文本形式（向后兼容）"""
    try:
        # 先生成评分方案
        marking_scheme = generate_json_marking_scheme(*student_answer, api=api)
        
        # 使用生成的评分方案进行批改
        prompt = prompts.correction_prompt + "\n\n"
        prompt += prompts.strictness_descriptions[strictness_level] + '\n\n'
        prompt += prompts.get_auto_scheme_notice()
        prompt += json.dumps(marking_scheme, ensure_ascii=False) + "\n\n"
        student_answer_notice = prompts.get_student_answer_notice()
        result = api(prompt, student_answer_notice, *student_answer, system_message=prompts.system_message)
        
        # 将结果转换为自然语言格式
        return force_natural_language(result)
            
    except Exception as e:
        error_msg = "批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

# 创建兼容的函数别名，保持原有函数名
correction_with_marking_scheme = correction_with_marking_scheme_legacy
correction_without_marking_scheme = correction_without_marking_scheme_legacy

# ==================== 网站版本兼容接口 ====================

@safe_api_call
def web_generate_marking_scheme(image_files: List[str]) -> Dict[str, Any]:
    """
    网站版本：生成评分方案
    
    参数:
    image_files: 图像文件路径列表
    
    返回:
    标准化的批改结果
    """
    result = generate_json_marking_scheme(*image_files, api=default_api)
    return {
        "marking_scheme": result,
        "files_processed": len(image_files)
    }

@safe_api_call
def web_correction_with_scheme(marking_scheme_files: List[str], student_answer_files: List[str], 
                              strictness_level: str = "中等") -> Dict[str, Any]:
    """
    网站版本：使用评分方案进行批改
    
    参数:
    marking_scheme_files: 评分方案文件路径列表
    student_answer_files: 学生答案文件路径列表
    strictness_level: 批改严格程度
    
    返回:
    标准化的批改结果
    """
    result = correction_with_marking_scheme_json(
        tuple(marking_scheme_files), 
        tuple(student_answer_files), 
        strictness_level=strictness_level, 
        api=default_api
    )
    return {
        "grading_result": result,
        "strictness_level": strictness_level,
        "scheme_files": len(marking_scheme_files),
        "answer_files": len(student_answer_files)
    }

@safe_api_call
def web_correction_without_scheme(student_answer_files: List[str], 
                                 strictness_level: str = "中等") -> Dict[str, Any]:
    """
    网站版本：不使用评分方案进行批改
    
    参数:
    student_answer_files: 学生答案文件路径列表
    strictness_level: 批改严格程度
    
    返回:
    标准化的批改结果
    """
    result = correction_without_marking_scheme_json(
        tuple(student_answer_files), 
        strictness_level=strictness_level, 
        api=default_api
    )
    return {
        "grading_result": result,
        "strictness_level": strictness_level,
        "answer_files": len(student_answer_files)
    }

@safe_api_call
def web_correction_multiple_answers(marking_scheme_files: List[str], student_pdf_path: str, 
                                   strictness_level: str = "中等") -> Dict[str, Any]:
    """
    网站版本：批改多页PDF答案
    
    参数:
    marking_scheme_files: 评分方案文件路径列表
    student_pdf_path: 学生PDF答案文件路径
    strictness_level: 批改严格程度
    
    返回:
    标准化的批改结果
    """
    result = correction_of_multiple_answers(
        tuple(marking_scheme_files), 
        student_pdf_path, 
        strictness_level=strictness_level, 
        api=default_api
    )
    return {
        "grading_result": result,
        "strictness_level": strictness_level,
        "scheme_files": len(marking_scheme_files),
        "pdf_path": student_pdf_path
    }

def get_api_status() -> Dict[str, Any]:
    """
    获取API状态信息
    
    返回:
    API状态信息
    """
    return {
        "api_config": api_config.get_status(),
        "status": "ready",
        "timestamp": time.time()
    }

def update_api_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新API配置
    
    参数:
    new_config: 新的配置字典
    
    返回:
    更新结果
    """
    try:
        if "api_key" in new_config:
            api_config.api_key = new_config["api_key"]
        if "base_url" in new_config:
            api_config.base_url = new_config["base_url"]
        if "model" in new_config:
            api_config.model = new_config["model"]
        if "max_tokens" in new_config:
            api_config.max_tokens = new_config["max_tokens"]
        if "temperature" in new_config:
            api_config.temperature = new_config["temperature"]
        if "max_retries" in new_config:
            api_config.max_retries = new_config["max_retries"]
        if "retry_delay" in new_config:
            api_config.retry_delay = new_config["retry_delay"]
        
        logger.info("API配置更新成功")
        return {"success": True, "message": "配置更新成功", "updated_config": new_config}
    except Exception as e:
        error_msg = f"配置更新失败: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

# ==================== 批处理接口 ====================

@safe_api_call
def web_batch_correction(batch_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    网站版本：批量批改处理
    
    参数:
    batch_requests: 批量请求列表，每个请求包含必要的参数
    
    返回:
    批量处理结果
    """
    results = []
    total_requests = len(batch_requests)
    
    for i, request in enumerate(batch_requests):
        logger.info(f"处理批量请求 {i + 1}/{total_requests}")
        
        try:
            if request.get("type") == "with_scheme":
                result = web_correction_with_scheme(
                    request["marking_scheme_files"],
                    request["student_answer_files"],
                    request.get("strictness_level", "中等")
                )
            elif request.get("type") == "without_scheme":
                result = web_correction_without_scheme(
                    request["student_answer_files"],
                    request.get("strictness_level", "中等")
                )
            elif request.get("type") == "multiple_answers":
                result = web_correction_multiple_answers(
                    request["marking_scheme_files"],
                    request["student_pdf_path"],
                    request.get("strictness_level", "中等")
                )
            else:
                result = GradingResult(success=False, error_message=f"未知的请求类型: {request.get('type')}")
            
            results.append({
                "request_index": i,
                "request_id": request.get("id", f"batch_{i}"),
                "result": result.to_dict()
            })
            
        except Exception as e:
            logger.error(f"批量请求 {i + 1} 处理失败: {str(e)}")
            results.append({
                "request_index": i,
                "request_id": request.get("id", f"batch_{i}"),
                "result": GradingResult(success=False, error_message=str(e)).to_dict()
            })
    
    success_count = sum(1 for r in results if r["result"]["success"])
    
    return {
        "total_requests": total_requests,
        "success_count": success_count,
        "failure_count": total_requests - success_count,
        "results": results
    }

# 添加缺失的 intelligent_correction_with_files 函数
def intelligent_correction_with_files(question_files=None, answer_files=None, marking_scheme_files=None, 
                                    strictness_level="中等", mode="efficient"):
    """
    智能文件批改函数 - 向后兼容性支持
    严格区分文件类型，确保不会混淆
    
    参数:
    - question_files: 题目文件列表（用于生成评分标准）
    - answer_files: 学生答案文件列表（必需，用于批改）
    - marking_scheme_files: 评分标准文件列表（可选，用于参考批改标准）
    - strictness_level: 严格程度

    - mode: 批改模式
    
    返回:
    - 批改结果字符串
    """
    if not answer_files:
        error_msg = "必须提供学生答案文件"
        return error_msg
    
    try:
        # 严格区分文件类型，转换为元组格式
        answer_tuple = tuple(answer_files) if answer_files else ()
        marking_tuple = tuple(marking_scheme_files) if marking_scheme_files else ()
        question_tuple = tuple(question_files) if question_files else ()
        
        logger.info(f"文件类型分析 - 题目文件: {len(question_tuple)}, 答案文件: {len(answer_tuple)}, 评分标准: {len(marking_tuple)}")
        
        # 根据不同模式选择不同的处理方式
        if mode == "efficient":
            # 高效模式 - 优先使用评分标准
            if marking_scheme_files:
                logger.info("高效模式：使用评分标准批改")
                return correction_with_marking_scheme(marking_tuple, answer_tuple, 
                                                    strictness_level=strictness_level)
            else:
                logger.info("高效模式：无评分标准，直接高效批改")
                return efficient_correction_single(*answer_tuple, 
                                                 strictness_level=strictness_level)
        
        elif mode == "detailed":
            # 详细模式 - 如果有评分标准使用标准批改，否则自动生成标准并批改
            if marking_scheme_files:
                logger.info("详细模式：使用评分标准进行详细批改")
                return correction_with_marking_scheme(marking_tuple, answer_tuple, 
                                                    strictness_level=strictness_level)
            else:
                logger.info("详细模式：自动生成评分标准并批改")
                return correction_without_marking_scheme(answer_tuple, 
                                                       strictness_level=strictness_level)
        
        elif mode == "batch":
            # 批量模式 - 批量处理多个答案文件
            logger.info("批量模式：批量处理学生答案")
            return batch_efficient_correction(*answer_tuple, 
                                            strictness_level=strictness_level)
        
        elif mode == "generate_scheme":
            # 生成标准模式 - 优先使用题目文件，其次使用答案文件
            if question_files:
                logger.info("生成评分标准：基于题目文件")
                return generate_marking_scheme(*question_tuple)
            elif answer_files:
                logger.info("生成评分标准：基于答案文件（没有题目文件）")
                return generate_marking_scheme(*answer_tuple)
            else:
                error_msg = "生成评分标准需要题目文件或答案文件"
                return error_msg
        
        elif mode == "auto":
            # 自动模式 - 智能选择最佳批改方式
            if marking_scheme_files:
                logger.info("自动模式：检测到评分标准，使用标准批改")
                return correction_with_marking_scheme(marking_tuple, answer_tuple, 
                                                    strictness_level=strictness_level)
            elif question_files:
                logger.info("自动模式：检测到题目文件，基于题目生成评分标准并批改")
                # 先基于题目生成评分标准，再进行批改
                scheme_result = generate_marking_scheme(*question_tuple)
                # 然后使用生成的标准进行批改
                return correction_without_marking_scheme(answer_tuple, 
                                                       strictness_level=strictness_level)
            else:
                logger.info("自动模式：只有答案文件，自动生成评分标准并批改")
                return correction_without_marking_scheme(answer_tuple, 
                                                       strictness_level=strictness_level)
        
        else:
            # 默认使用高效模式
            logger.info(f"未知模式 '{mode}'，使用默认高效模式")
            if marking_scheme_files:
                return correction_with_marking_scheme(marking_tuple, answer_tuple, 
                                                    strictness_level=strictness_level)
            else:
                return efficient_correction_single(*answer_tuple, 
                                                 strictness_level=strictness_level)
    
    except Exception as e:
        error_msg = f"智能批改失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    # 测试网站版本接口
    print("API配置状态:")
    print(json.dumps(get_api_status(), ensure_ascii=False, indent=2))
    
    # 示例调用
    # r = correction_of_multiple_answers(("d:/Robin/Project/paper/q16ms.png",), "d:/Robin/Project/paper/q16.pdf")
    # print(json.dumps(r, ensure_ascii=0, indent=2))