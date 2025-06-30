# 修复版本的API调用模块 - 完整版
import base64
import requests  
import openai
import re
from pathlib import Path
import json
import os
import time
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass
import contextlib
import io
from PIL import Image

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 强制使用简化版提示词
USE_SIMPLIFIED_PROMPTS = True
try:
    import prompts_simplified as prompts_module
    logger.info("使用简化版提示词系统")
except ImportError:
    try:
        from . import prompts_simplified as prompts_module
        logger.info("使用简化版提示词系统")
    except ImportError:
        logger.error("简化版提示词模块未找到")
        raise ImportError("无法导入简化版提示词模块")

# 导入PDF错误抑制工具
try:
    from pdf_utils import SuppressOutput, safe_pdf_processing
    PDF_UTILS_AVAILABLE = True
except ImportError:
    PDF_UTILS_AVAILABLE = False

# 抑制MuPDF错误输出
import warnings
warnings.filterwarnings("ignore")
os.environ['MUPDF_QUIET'] = '1'

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

@dataclass
class APIConfig:
    """API配置类"""
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-2.5-flash-lite-preview-06-17"
    max_tokens: int = 50000
    temperature: float = 0.7
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 120
    
    def __post_init__(self):
        """初始化后处理，从环境变量设置API密钥"""
        env_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
        if env_key:
            self.api_key = env_key
            return
        
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
                                return
            except Exception as e:
                logger.warning(f"读取.env文件失败: {e}")
        
        if not self.api_key:
            self.api_key = "请在此处输入您的新API密钥"
    
    def is_valid(self) -> bool:
        """检查API配置是否有效"""
        return bool(self.api_key and self.api_key.startswith(('sk-', 'or-')))
    
    def get_status(self) -> dict:
        """获取配置状态信息"""
        api_key_source = "default"
        if os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY'):
            api_key_source = "environment"
        elif Path('.env').exists():
            try:
                with open('.env', 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key.strip() == 'OPENROUTER_API_KEY' and value.strip() and value.strip() != 'your_api_key_here':
                                api_key_source = ".env file"
                                break
            except:
                pass
        
        return {
            "api_key_configured": bool(self.api_key and self.api_key != "请在此处输入您的新API密钥"),
            "api_key_source": api_key_source,
            "base_url": self.base_url,
            "model": self.model,
            "is_valid": self.is_valid()
        }

# 全局配置实例
api_config = APIConfig()

def img_to_base64(image_path, max_size_mb=4):
    """将图片文件转换为base64编码，支持自动压缩"""
    import io
    import os
    from pathlib import Path
    from PIL import Image
    
    # 检查文件类型
    if isinstance(image_path, str):
        file_path = Path(image_path)
        if file_path.exists():
            file_ext = file_path.suffix.lower()
            if file_ext in ['.txt', '.md', '.doc', '.docx', '.rtf']:
                raise ValueError(f"文件 {image_path} 是文本文件，不能作为图像处理")
    
    # 处理URL
    if isinstance(image_path, str) and image_path.startswith(('http://', 'https://')):
        response = requests.get(image_path)
        response.raise_for_status()  
        image_data = response.content
    # 处理Streamlit上传的文件对象
    elif hasattr(image_path, 'read') and callable(image_path.read):
        try:
            if hasattr(image_path, 'tell') and callable(image_path.tell):
                current_position = image_path.tell()
            else:
                current_position = 0
            image_data = image_path.read()
            if hasattr(image_path, 'seek') and callable(image_path.seek):
                image_path.seek(current_position)
        except Exception as e:
            raise Exception(f"Failed to read uploaded file: {str(e)}")
    # 处理本地文件路径
    elif isinstance(image_path, str):
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
        else:
            logging.info(f"图片文件过大 ({file_size_mb:.2f}MB)，正在压缩...")
            img = Image.open(image_path)
            
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            quality = 85
            max_dimension = 1920
            
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
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
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=50, optimize=True)
                    final_size_mb = len(buffer.getvalue()) / (1024 * 1024)
                    logging.info(f"最终压缩: {file_size_mb:.2f}MB -> {final_size_mb:.2f}MB")
                    image_data = buffer.getvalue()
    else:
        raise Exception(f"Unsupported image source type: {type(image_path)}")
        
    return base64.b64encode(image_data).decode('utf-8')

def get_file_type(file_path):
    """检测文件类型，返回文件类型分类"""
    if isinstance(file_path, str):
        file_ext = Path(file_path).suffix.lower()
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            return 'image'
        elif file_ext == '.pdf':
            return 'pdf'
        elif file_ext in ['.doc', '.docx']:
            return 'word'
        elif file_ext in ['.txt', '.md', '.rtf', '.csv']:
            return 'text'
        elif file_ext in ['.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml']:
            return 'text'
    return 'unknown'

def read_pdf_file(file_path):
    """读取PDF文件内容"""
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
    """读取Word文档内容"""
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

def process_file_content(file_path):
    """根据文件类型处理文件内容"""
    file_type = get_file_type(file_path)
    file_name = Path(file_path).name
    
    try:
        if file_type == 'image':
            return 'image', file_path
        elif file_type == 'pdf':
            try:
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if file_size_mb > 50:
                    logger.info(f"PDF文件过大({file_size_mb:.1f}MB)，直接提取文本: {file_name}")
                    text_content = read_pdf_file(file_path)
                    return 'text', f"[大型PDF文档: {file_name}]\n{text_content}"
                return 'pdf', file_path
            except Exception as e:
                logger.warning(f"PDF处理异常，尝试文本提取: {str(e)}")
                try:
                    text_content = read_pdf_file(file_path)
                    if text_content and not text_content.startswith("[PDF文件读取失败"):
                        return 'text', f"[PDF文档(文本模式): {file_name}]\n{text_content}"
                    else:
                        return 'error', f"[PDF处理失败: {file_name}] - 无法读取内容"
                except Exception as text_error:
                    return 'error', f"[PDF处理失败: {file_name}] - {str(text_error)}"
        elif file_type == 'word':
            content = read_word_file(file_path)
            return 'text', f"[Word文档: {file_name}]\n{content}"
        elif file_type == 'text':
            content = read_text_file(file_path)
            return 'text', f"[文本文件: {file_name}]\n{content}"
        else:
            try:
                content = read_text_file(file_path)
                return 'text', f"[文件: {file_name}]\n{content}"
            except:
                return 'error', f"[不支持的文件类型: {file_name}] - 无法处理此文件"
    except Exception as e:
        return 'error', f"[文件处理错误: {file_name}] - {str(e)}"

def pdf_pages_to_base64_images(pdf_path, zoom=2.0):
    """将 PDF 每页转换为 Base64 编码的图像数据列表"""
    if not fitz:
        logger.error("PyMuPDF未安装，无法处理PDF")
        return []
    
    base64_images = []
    suppress_context = SuppressOutput() if PDF_UTILS_AVAILABLE else contextlib.nullcontext()
    
    try:
        with suppress_context:
            doc = fitz.open(pdf_path)
            
            if doc.is_encrypted:
                logger.warning(f"PDF文件 {pdf_path} 已加密，尝试解密")
                if not doc.authenticate(""):
                    logger.error(f"PDF文件 {pdf_path} 无法解密")
                    doc.close()
                    return []
            
            if doc.page_count == 0:
                logger.warning(f"PDF文件 {pdf_path} 没有页面")
                doc.close()
                return []
            
            max_pages = min(doc.page_count, 20)
            
            for page_num in range(max_pages):
                try:
                    with contextlib.redirect_stderr(open(os.devnull, 'w')):
                        page = doc.load_page(page_num)
                        matrix = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        img_data = pix.tobytes("png")
                        
                        if len(img_data) > 3 * 1024 * 1024:
                            img = Image.open(io.BytesIO(img_data))
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')
                            
                            max_size = 1600
                            if max(img.size) > max_size:
                                ratio = max_size / max(img.size)
                                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                                img = img.resize(new_size, Image.Resampling.LANCZOS)
                            
                            buffer = io.BytesIO()
                            img.save(buffer, format='JPEG', quality=80, optimize=True)
                            img_data = buffer.getvalue()
                        
                        base64_str = base64.b64encode(img_data).decode("utf-8")
                        base64_images.append(base64_str)
                        pix = None
                        
                except Exception as e:
                    logger.warning(f"处理PDF第{page_num + 1}页时出错: {str(e)}")
                    continue
            
            doc.close()
            
            if not base64_images:
                logger.warning(f"PDF文件 {pdf_path} 无法提取任何页面")
                return []
            
            logger.info(f"成功处理PDF文件 {pdf_path}，共{len(base64_images)}页")
            return base64_images
            
    except Exception as e:
        logger.error(f"PDF处理完全失败 {pdf_path}: {str(e)}")
        return []

def call_tongyiqianwen_api(input_text: str, *input_contents, system_message: str = "") -> str:
    """调用API进行多类型文件处理"""
    from openai import OpenAI
    
    if not api_config.is_valid():
        error_msg = f"""
🚫 API配置错误

可能的解决方案：
1. 设置环境变量：OPENROUTER_API_KEY=your_api_key
2. 检查API密钥格式
3. 确认密钥有效性

当前配置状态：
{json.dumps(api_config.get_status(), ensure_ascii=False, indent=2)}"""
        logger.error("API配置无效")
        return error_msg
    
    try:
        client = OpenAI(
            api_key=api_config.api_key,
            base_url=api_config.base_url,
            timeout=api_config.timeout
        )
    except Exception as e:
        error_msg = f"❌ OpenAI客户端初始化失败: {str(e)}"
        logger.error(error_msg)
        return error_msg
    
    content = [{"type": "text", "text": input_text}]
    
    try:
        for single_content in input_contents:
            if (isinstance(single_content, tuple) and 
                len(single_content) == 2 and 
                all(isinstance(item, str) for item in single_content)):
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
                    base_64_image = img_to_base64(single_content)
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base_64_image}"
                        }
                    })    
                elif content_type == 'pdf':
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

            result = response.choices[0].message.content
        
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
            
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                timeout_error_msg = f"""❌ 请求超时错误
问题分析：网络连接超时、API服务器响应缓慢、处理的文件过大或过多
解决方案：检查网络连接、减少单次处理的文件数量、稍后重试
错误详情：{error_str}"""
                if attempt < api_config.max_retries - 1:
                    wait_time = api_config.retry_delay * (2 ** attempt)
                    logger.info(f"遇到超时错误，等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                    continue
                else:
                    return timeout_error_msg
            
            if "401" in error_str or "Unauthorized" in error_str:
                auth_error_msg = f"""❌ 认证失败 (401 Unauthorized)
问题分析：API密钥无效或已过期、密钥格式错误、账户余额不足
解决方案：检查API密钥、更新API密钥、检查账户状态
当前使用的密钥来源：{api_config.get_status()['api_key_source']}
原始错误：{error_str}"""
                logger.error("认证失败")
                return auth_error_msg
            
            elif "429" in error_str or "rate_limit" in error_str.lower():
                rate_limit_msg = f"❌ API调用频率限制，请稍后重试。错误：{error_str}"
                if attempt < api_config.max_retries - 1:
                    wait_time = api_config.retry_delay * (2 ** attempt)
                    logger.info(f"遇到频率限制，等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                    continue
                else:
                    return rate_limit_msg
            
            elif "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
                if "504" in error_str:
                    server_error_msg = f"""❌ 网关超时错误 (504 Gateway Timeout)
问题分析：API服务器响应超时、网络连接不稳定、服务器负载过高
解决方案：检查网络连接稳定性、稍后重试、考虑减少单次处理的文件数量
错误详情：{error_str}"""
                else:
                    server_error_msg = f"❌ 服务器错误，请稍后重试。错误：{error_str}"
                
                if attempt < api_config.max_retries - 1:
                    wait_time = api_config.retry_delay * (2 ** attempt)
                    logger.info(f"遇到服务器错误，等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                    continue
                else:
                    return server_error_msg
            
            if attempt < api_config.max_retries - 1:
                time.sleep(api_config.retry_delay * (attempt + 1))
                continue
            else:
                error_msg = f"""❌ API调用失败 (所有重试已耗尽)
错误详情：{error_str}
可能的解决方案：检查网络连接、验证API密钥有效性、确认账户余额充足、稍后重试
配置信息：{json.dumps(api_config.get_status(), ensure_ascii=False, indent=2)}"""
                logger.error(error_msg)
                return error_msg

# 标准API调用函数
default_api = call_tongyiqianwen_api

# ===================== 结果类和装饰器 =====================
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

# ===================== 核心批改函数 =====================
def batch_correction_with_standard(marking_scheme_files: List[str], student_answer_files: List[str], 
                                  strictness_level: str = "中等", api=default_api) -> dict:
    """批量批改 - 有批改标准模式"""
    try:
        marking_contents = []
        marking_file_info = []
        for i, file in enumerate(marking_scheme_files):
            content_type, content = process_file_content(file)
            if content_type == 'error':
                raise ValueError(f"处理批改标准文件失败: {content}")
            elif content_type == 'image' or content_type == 'pdf':
                marking_contents.append(file)
                marking_file_info.append(f"【批改方案文件 {i+1}】: {os.path.basename(file)}")
            else:
                marking_contents.append(content)
                marking_file_info.append(f"【批改方案文件 {i+1}】: {os.path.basename(file)}")
        
        student_contents = []
        student_file_info = []
        for i, file in enumerate(student_answer_files):
            content_type, content = process_file_content(file)
            if content_type == 'error':
                raise ValueError(f"处理学生答案文件失败: {content}")
            elif content_type == 'image' or content_type == 'pdf':
                student_contents.append(file)
                student_file_info.append(f"【学生作答文件 {i+1}】: {os.path.basename(file)}")
            else:
                student_contents.append(content)
                student_file_info.append(f"【学生作答文件 {i+1}】: {os.path.basename(file)}")
        
        prompt = prompts_module.get_complete_grading_prompt(file_info_list=[])
        
        api_args = []
        if marking_contents:
            api_args.append("=" * 50)
            api_args.append("批改方案文件（包含正确答案和评分标准）：")
            api_args.append("=" * 50)
            for i, (info, content) in enumerate(zip(marking_file_info, marking_contents)):
                api_args.append(f"\n{info}")
                api_args.append(content)
            api_args.append("\n" + "=" * 50)
        
        if student_contents:
            api_args.append("\n" + "=" * 50)
            api_args.append("学生作答文件（需要批改的答案）：")
            api_args.append("=" * 50)
            for i, (info, content) in enumerate(zip(student_file_info, student_contents)):
                api_args.append(f"\n{info}")
                api_args.append(content)
            api_args.append("\n" + "=" * 50)
        
        api_args.append("\n【批改指令】：")
        api_args.append(prompt)
        
        result = api(*api_args, system_message=prompts_module.system_message_simplified)
        
        return {
            "correction_result": result,
            "has_separate_scheme": False
        }
        
    except Exception as e:
        error_msg = f"批改失败: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

def batch_correction_without_standard(question_files: List[str], student_answer_files: List[str], 
                                     strictness_level: str = "中等", api=default_api) -> dict:
    """批量批改 - 无批改标准模式（自动生成批改标准）"""
    try:
        logger.info("正在根据题目生成批改标准...")
        
        # 对于简化版，我们直接使用学生答案文件进行批改
        # 因为简化版假设MARKING_文件包含完整信息
        if not student_answer_files:
            raise ValueError("缺少学生答案文件")
        
        # 使用简化版批改逻辑
        file_info_list = []
        for file_path in student_answer_files:
            filename = os.path.basename(file_path)
            file_info = {
                'name': filename,
                'path': file_path,
                'type': get_file_type(file_path),
                'expected_category': 'answer'
            }
            file_info_list.append(file_info)
        
        prompt = prompts_module.get_complete_grading_prompt(file_info_list=file_info_list)
        
        api_args = []
        api_args.append("=" * 50)
        api_args.append("学生作答文件（需要批改的答案）：")
        api_args.append("=" * 50)
        
        for file_path in student_answer_files:
            api_args.append(f"\n文件：{os.path.basename(file_path)}")
            content_type, content = process_file_content(file_path)
            if content_type == 'error':
                raise ValueError(f"处理学生答案文件失败: {content}")
            elif content_type in ['image', 'pdf']:
                api_args.append(file_path)
            else:
                api_args.append(content)
        
        api_args.append("\n" + "=" * 50)
        api_args.append("\n【批改指令】：")
        api_args.append(prompt)
        
        result = api(*api_args, system_message=prompts_module.system_message_simplified)
        
        return {
            "correction_result": result,
            "has_separate_scheme": False
        }
        
    except Exception as e:
        error_msg = f"批改失败: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

def intelligent_correction_with_files(question_files=None, answer_files=None, marking_scheme_files=None, 
                                    strictness_level="中等", mode="efficient"):
    """智能文件批改函数 - 简化版本"""
    if not answer_files:
        error_msg = "必须提供学生答案文件"
        logger.error(error_msg)
        return error_msg
    
    try:
        if marking_scheme_files:
            logger.info(f"使用批改标准模式 - 标准文件: {len(marking_scheme_files)}, 答案文件: {len(answer_files)}")
            result = batch_correction_with_standard(
                marking_scheme_files,
                answer_files,
                strictness_level=strictness_level,
                api=default_api
            )
        else:
            logger.info(f"使用自动生成批改标准模式 - 答案文件: {len(answer_files)}")
            files_for_scheme = question_files if question_files else answer_files
            result = batch_correction_without_standard(
                files_for_scheme,
                answer_files,
                strictness_level=strictness_level,
                api=default_api
            )
        
        return result
        
    except Exception as e:
        error_msg = f"智能批改失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def simplified_batch_correction(files_dict: dict, strictness_level: str = "严格", api=None) -> dict:
    """使用简化提示词的批量批改函数 - 修复版本"""
    if api is None:
        api = default_api
    
    try:
        answer_files = files_dict.get('answer_files', [])
        marking_files = files_dict.get('marking_files', [])
        question_files = files_dict.get('question_files', [])
        
        if not answer_files:
            return {
                "success": False,
                "error": "缺少学生答案文件",
                "message": "必须提供学生答案文件"
            }
        
        # 构建文件信息列表
        file_info_list = []
        all_files = [
            (answer_files, 'answer'),
            (marking_files, 'marking'),
            (question_files, 'question')
        ]
        
        for file_list, expected_category in all_files:
            for file_path in file_list:
                filename = os.path.basename(file_path)
                file_info = {
                    'name': filename,
                    'path': file_path,
                    'type': get_file_type(file_path),
                    'expected_category': expected_category
                }
                file_info_list.append(file_info)
        
        prompt = prompts_module.get_complete_grading_prompt(file_info_list=file_info_list)
        system_msg = prompts_module.system_message_simplified
        
        api_args = []
        
        # 检查文件完整性
        if not answer_files:
            return {
                "success": False,
                "error": "缺少学生答案文件",
                "message": "缺少学生答案文件"
            }
        
        # 处理文件
        if question_files:
            api_args.append("=" * 50)
            api_args.append("📋 题目文件（来自题目上传区域）：")
            api_args.append("=" * 50)
            for file_path in question_files:
                api_args.append(f"\n文件：{os.path.basename(file_path)}")
                content_type, content = process_file_content(file_path)
                if content_type == 'error':
                    raise ValueError(f"处理题目文件失败: {content}")
                elif content_type in ['image', 'pdf']:
                    api_args.append(file_path)
                else:
                    api_args.append(content)
        
        if answer_files:
            api_args.append("\n" + "=" * 50)
            api_args.append("✏️ 学生答案（来自学生答案上传区域）：")
            api_args.append("=" * 50)
            for file_path in answer_files:
                api_args.append(f"\n文件：{os.path.basename(file_path)}")
                content_type, content = process_file_content(file_path)
                if content_type == 'error':
                    raise ValueError(f"处理学生答案文件失败: {content}")
                elif content_type in ['image', 'pdf']:
                    api_args.append(file_path)
                else:
                    api_args.append(content)
        
        if marking_files:
            api_args.append("\n" + "=" * 50)
            api_args.append("📊 批改方案（来自批改方案上传区域）：")
            api_args.append("=" * 50)
            for file_path in marking_files:
                api_args.append(f"\n文件：{os.path.basename(file_path)}")
                content_type, content = process_file_content(file_path)
                if content_type == 'error':
                    raise ValueError(f"处理批改方案文件失败: {content}")
                elif content_type in ['image', 'pdf']:
                    api_args.append(file_path)
                else:
                    api_args.append(content)
        
        api_args.append("\n" + "=" * 50)
        api_args.append("\n【批改指令】：")
        api_args.append(prompt)
        
        result = api(*api_args, system_message=system_msg)
        
        return {
            "success": True,
            "result": result,
            "mode": "simplified_fixed",
            "strictness": strictness_level,
            "file_classification": "automatic_by_filename"
        }
        
    except Exception as e:
        logger.error(f"简化批改失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "批改过程中发生错误"
        }

# ===================== 向后兼容函数 =====================
def correction_single_group(*image_files, strictness_level="中等", api=default_api, group_index=1):
    """对单个文件组进行批改"""
    try:
        prompt = prompts_module.get_complete_grading_prompt(file_info_list=[])
        return api(prompt, *image_files, system_message=prompts_module.system_message_simplified)
    except Exception as e:
        error_msg = f"第{group_index}题批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def efficient_correction_single(*image_files, strictness_level="中等", api=default_api):
    """高效简洁批改函数"""
    try:
        detailed_result = correction_single_group(*image_files, strictness_level=strictness_level, api=api)
        if len(detailed_result) > 500:
            prompt = f"""请将以下详细批改结果简化为高效简洁的格式，保留关键信息：
{detailed_result}
要求：
1. 保留题目编号和得分
2. 简要说明主要错误
3. 给出改进建议"""
            simplified = api(prompt, system_message=prompts_module.system_message_simplified)
            return simplified
        return detailed_result
    except Exception as e:
        error_msg = "高效批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def batch_efficient_correction(*image_files, strictness_level="中等", api=default_api):
    """批量高效批改函数"""
    try:
        from datetime import datetime
        
        results = []
        total_files = len(image_files)
        
        for i, file in enumerate(image_files, 1):
            try:
                result = efficient_correction_single(file, 
                                                   strictness_level=strictness_level, 
                                                   api=api)
                
                file_name = getattr(file, 'name', f'文件{i}')
                header = f"## 📄 {file_name} ({i}/{total_files})\n\n"
                results.append(header + result)
                
            except Exception as e:
                error_msg = f"文件 {i} 批改失败: {str(e)}"
                results.append(f"## ❌ 文件 {i}\n{error_msg}")
        
        final_result = "\n\n---\n\n".join(results)
        summary_header = f"\n\n# 📊 批改总览\n**共批改 {total_files} 份作业**\n✅ 批改完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return final_result + summary_header
        
    except Exception as e:
        error_msg = "批量批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def generate_marking_scheme(*image_file, api=default_api):
    """生成评分方案"""
    try:
        prompt = "请根据题目生成详细的评分标准，包括每个步骤的分值分配。"
        result = api(prompt, *image_file, system_message=prompts_module.system_message_simplified)
        return result
    except Exception as e:
        error_msg = "生成评分方案失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_marking_scheme(marking_schemes, student_answers, strictness_level="中等", api=default_api):
    """使用评分方案进行批改（向后兼容）"""
    try:
        if isinstance(marking_schemes, (tuple, list)):
            marking_schemes = list(marking_schemes)
        else:
            marking_schemes = [marking_schemes]
        
        if isinstance(student_answers, (tuple, list)):
            student_answers = list(student_answers)
        else:
            student_answers = [student_answers]
        
        result = batch_correction_with_standard(
            marking_schemes,
            student_answers,
            strictness_level=strictness_level,
            api=api
        )
        return result.get('correction_result', result)
    except Exception as e:
        error_msg = "批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_without_marking_scheme(student_answer, strictness_level="中等", api=default_api):
    """不使用评分方案进行批改（向后兼容）"""
    try:
        if isinstance(student_answer, (tuple, list)):
            student_answer = list(student_answer)
        else:
            student_answer = [student_answer]
        
        result = batch_correction_without_standard(
            student_answer,
            student_answer,
            strictness_level=strictness_level,
            api=api
        )
        return result.get('correction_result', result)
    except Exception as e:
        error_msg = "批改失败"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

# ===================== Web接口函数 =====================
@safe_api_call
def web_correction_with_scheme(marking_scheme_files: List[str], student_answer_files: List[str], 
                              strictness_level: str = "中等") -> Dict[str, Any]:
    """网站版本：使用评分方案进行批改"""
    result = batch_correction_with_standard(
        marking_scheme_files, 
        student_answer_files, 
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
    """网站版本：不使用评分方案进行批改"""
    result = batch_correction_without_standard(
        student_answer_files,
        student_answer_files,
        strictness_level=strictness_level, 
        api=default_api
    )
    return {
        "grading_result": result,
        "strictness_level": strictness_level,
        "answer_files": len(student_answer_files)
    }

@safe_api_call
def web_batch_correction(batch_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    """网站版本：批量批改处理"""
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

# ===================== API配置函数 =====================
def get_api_status() -> Dict[str, Any]:
    """获取API状态信息"""
    return {
        "api_config": api_config.get_status(),
        "status": "ready",
        "timestamp": time.time()
    }

def update_api_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """更新API配置"""
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