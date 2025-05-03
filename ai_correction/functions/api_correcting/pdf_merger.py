import os
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
from datetime import datetime
from PIL import Image
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from PIL import Image as PILImage
import tempfile
import urllib.request
import shutil

# 添加下载字体功能
def download_font(font_url, save_path):
    """下载字体文件到指定路径"""
    try:
        with urllib.request.urlopen(font_url) as response, open(save_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        return True
    except Exception as e:
        print(f"Error downloading font: {str(e)}")
        return False

class PDFWithChinese(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        # 使用内置的 Arial Unicode MS 字体，支持中文
        self.add_font('Arial', '', fname=None, uni=True)

    def write_chinese(self, text, font_size=12):
        """写入中文内容"""
        self.set_font('Arial', '', font_size)
        # 将文本按行分割并写入
        lines = str(text).split('\n')
        for line in lines:
            encoded_text = line.encode('latin-1', errors='ignore').decode('latin-1')
            self.multi_cell(0, 10, encoded_text)

def replace_math_symbols(text):
    """保留数学符号的原始形式，不进行替换"""
    return text

class PDFMerger:
    def __init__(self, upload_dir):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # 确保字体目录存在
        self.font_dir = Path(__file__).parent / 'fonts'
        self.font_dir.mkdir(exist_ok=True)
        
        # 注册中文字体
        self.setup_chinese_font()

    def setup_chinese_font(self):
        """设置中文字体，适应不同操作系统环境"""
        # 获取当前操作系统
        import platform
        system_name = platform.system().lower()
        
        # 定义不同系统的字体路径
        font_paths = []
        
        # Windows字体路径
        if 'win' in system_name:
            font_paths.extend([
                'C:/Windows/Fonts/simsun.ttc',    # 宋体
                'C:/Windows/Fonts/simhei.ttf',    # 黑体
                'C:/Windows/Fonts/msyh.ttc',      # 微软雅黑
                'C:/Windows/Fonts/simkai.ttf',    # 楷体
                'C:/Windows/Fonts/simfang.ttf',   # 仿宋
            ])
        
        # Linux字体路径
        elif 'linux' in system_name:
            font_paths.extend([
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',   # 文泉驿微米黑
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/truetype/arphic/uming.ttc',        # AR PL UMing
                '/usr/share/fonts/truetype/arphic/ukai.ttc',         # AR PL UKai
                '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc', # 备用路径
                
                # Debian/Ubuntu特定路径
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                
                # CentOS/RHEL特定路径
                '/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc',
            ])
        
        # macOS字体路径
        elif 'darwin' in system_name:
            font_paths.extend([
                '/Library/Fonts/Arial Unicode.ttf',
                '/System/Library/Fonts/PingFang.ttc',
                '/Library/Fonts/STHeiti Light.ttc',
                '/Library/Fonts/STHeiti Medium.ttc',
                '/Library/Fonts/Hiragino Sans GB.ttc',
            ])
        
        # 检查是否有内嵌字体可用
        embedded_fonts = []
        
        # 自动扫描字体目录中的所有字体文件
        for ext in ['.ttc', '.ttf', '.otf']:
            for font_file in self.font_dir.glob(f'*{ext}'):
                embedded_fonts.append(str(font_file))
                
        # 添加常用内嵌字体名称（如果存在的话）        
        specific_embedded_fonts = [
            str(self.font_dir / 'NotoSansSC-Regular.otf'),  # 思源黑体简体中文
            str(self.font_dir / 'fzht.ttf'),               # 方正黑体
            str(self.font_dir / 'simsun.ttc'),              # 宋体
            str(self.font_dir / 'simhei.ttf'),              # 黑体
            str(self.font_dir / 'msyh.ttc'),                # 微软雅黑
            str(self.font_dir / 'wqy-microhei.ttc')         # 文泉驿微米黑
        ]
        
        # 将找到的嵌入字体添加到列表中（确保没有重复）
        for font in specific_embedded_fonts:
            if font not in embedded_fonts and os.path.exists(font):
                embedded_fonts.append(font)
                
        print(f"Found {len(embedded_fonts)} embedded fonts")
        
        # 添加内嵌字体到搜索路径
        font_paths.extend(embedded_fonts)
        
        # 尝试注册第一个可用的字体
        self.chinese_font_name = 'Helvetica'  # 默认退路字体
        
        font_found = False
        
        # 特殊处理：如果发现思源黑体或方正黑体，优先使用它们
        priority_fonts = []
        for font_path in font_paths:
            if not font_path or not os.path.exists(font_path):
                continue
                
            basename = os.path.basename(font_path).lower()
            if 'noto' in basename or 'source' in basename or 'fzht' in basename:
                priority_fonts.append(font_path)
                
        # 将优先字体移到列表最前面
        for pf in reversed(priority_fonts):
            if pf in font_paths:
                font_paths.remove(pf)
                font_paths.insert(0, pf)
        
        for font_path in font_paths:
            if font_path and os.path.exists(font_path):
                try:
                    basename = os.path.basename(font_path).lower()
                    font_name = os.path.splitext(basename)[0]
                    
                    # 特别处理思源黑体
                    if 'noto' in font_name and ('sc' in font_name or 'cjk' in font_name):
                        pdfmetrics.registerFont(TTFont('NotoSansSC', font_path))
                        self.chinese_font_name = 'NotoSansSC'
                        registerFontFamily('NotoSansSC', normal='NotoSansSC')
                        print(f"Using Chinese font: NotoSansSC")
                        font_found = True
                    
                    # 特别处理方正黑体
                    elif 'fzht' in font_name:
                        pdfmetrics.registerFont(TTFont('FZHei', font_path))
                        self.chinese_font_name = 'FZHei'
                        registerFontFamily('FZHei', normal='FZHei')
                        print(f"Using Chinese font: FZHei (FangZheng HeiTi)")
                        font_found = True
                    
                    # 特别处理微软雅黑
                    elif 'msyh' in font_name:
                        pdfmetrics.registerFont(TTFont('Microsoft YaHei', font_path))
                        self.chinese_font_name = 'Microsoft YaHei'
                        
                        # 尝试注册加粗版本（如果存在）
                        bold_path = 'C:/Windows/Fonts/msyhbd.ttc'
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('Microsoft YaHei Bold', bold_path))
                            
                        # 注册字体家族
                        registerFontFamily('Microsoft YaHei', normal='Microsoft YaHei',
                                         bold='Microsoft YaHei Bold' if os.path.exists(bold_path) else 'Microsoft YaHei')
                        
                        print(f"Using Chinese font: Microsoft YaHei with family support")
                        font_found = True
                        
                    # 特别处理宋体
                    elif 'simsun' in font_name:
                        pdfmetrics.registerFont(TTFont('SimSun', font_path))
                        self.chinese_font_name = 'SimSun'
                        
                        # 尝试注册加粗版本（如果存在）
                        bold_path = 'C:/Windows/Fonts/simhei.ttf'  # 通常使用黑体作为宋体的粗体
                        if 'win' in system_name and os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont('SimSun Bold', bold_path))
                            registerFontFamily('SimSun', normal='SimSun', bold='SimSun Bold')
                        else:
                            registerFontFamily('SimSun', normal='SimSun', bold='SimSun')
                        
                        print(f"Using Chinese font: SimSun with family support")
                        font_found = True
                    
                    # 处理文泉驿字体
                    elif 'wqy' in font_name:
                        pdfmetrics.registerFont(TTFont('WenQuanYi', font_path))
                        self.chinese_font_name = 'WenQuanYi'
                        registerFontFamily('WenQuanYi', normal='WenQuanYi')
                        print(f"Using Chinese font: WenQuanYi")
                        font_found = True
                    
                    # 其他通用字体处理
                    else:
                        # 为字体名生成一个有效的标识符
                        safe_name = ''.join(c for c in font_name if c.isalnum())
                        if not safe_name:
                            safe_name = f"Font{hash(font_path) % 10000}"
                            
                        pdfmetrics.registerFont(TTFont(safe_name, font_path))
                        self.chinese_font_name = safe_name
                        registerFontFamily(safe_name, normal=safe_name)
                        print(f"Using Chinese font: {safe_name} from {basename}")
                        font_found = True
                        
                    if font_found:
                        break
                        
                except Exception as e:
                    print(f"Failed to register font {font_path}: {str(e)}")
        
        # 使用备用方案 - 尝试下载并注册一个开源中文字体
        if not font_found:
            try:
                # 如果download_fonts模块存在，尝试使用它下载字体
                import importlib.util
                download_module_path = Path(__file__).parent / 'download_fonts.py'
                
                if download_module_path.exists():
                    print("Attempting to download fonts using download_fonts.py...")
                    spec = importlib.util.spec_from_file_location("download_fonts", download_module_path)
                    download_fonts = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(download_fonts)
                    
                    # 执行下载
                    download_fonts.main()
                    
                    # 重新检查是否有可用字体
                    for ext in ['.ttf', '.otf', '.ttc']:
                        for font_file in self.font_dir.glob(f'*{ext}'):
                            try:
                                font_name = font_file.stem
                                safe_name = ''.join(c for c in font_name if c.isalnum())
                                if not safe_name:
                                    safe_name = f"Font{hash(str(font_file)) % 10000}"
                                
                                pdfmetrics.registerFont(TTFont(safe_name, str(font_file)))
                                self.chinese_font_name = safe_name
                                registerFontFamily(safe_name, normal=safe_name)
                                print(f"Using downloaded font: {safe_name}")
                                font_found = True
                                break
                            except Exception as e:
                                print(f"Failed to register downloaded font {font_file}: {str(e)}")
                                
                    if not font_found:
                        print("No usable fonts found after download attempt.")
                else:
                    print("download_fonts.py not found, cannot download fonts automatically")
                    
                if not font_found:
                    print("WARNING: No Chinese font found. PDF output may not display Chinese characters correctly.")
                    print("Consider installing appropriate Chinese fonts on your system.")
            except Exception as e:
                print(f"Failed in font download process: {str(e)}")
                
        # 最后的退路方案 - 使用基本ASCII字体
        if not font_found:
            print("CRITICAL: Using Helvetica as fallback. Chinese characters will not display correctly.")

    def merge_pdfs(self, files_to_include, result_text, title, output_path):
        temp_files = []
        try:
            # 创建PDF文档，减小页边距
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=36,    # 减小右边距
                leftMargin=36,     # 减小左边距
                topMargin=36,      # 减小上边距
                bottomMargin=36    # 减小下边距
            )
            
            # 创建样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontName=self.chinese_font_name,  # 使用找到的中文字体
                fontSize=16,        # 减小标题字号
                spaceAfter=10      # 减小标题后的空间
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading1'],
                fontName=self.chinese_font_name,  # 使用找到的中文字体
                fontSize=14,        # 减小子标题字号
                spaceAfter=8       # 减小子标题后的空间
            )
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontName=self.chinese_font_name,  # 使用找到的中文字体
                fontSize=12,
                spaceAfter=6,      # 减小段落间距
                leading=16,        # 减小行距
                allowWidows=1,     # 允许段落底部的孤行
                allowOrphans=1     # 允许段落顶部的孤行
            )
            
            # 替换特殊数学符号
            def process_math_text(text):
                # 保持原始数学符号
                return text
            
            # 准备内容
            story = []
            
            # 添加标题
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 10))
            
            # 处理上传的图片文件
            if files_to_include:
                for file_type, uploaded_file in files_to_include.items():
                    if uploaded_file and uploaded_file.type.startswith('image/'):
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                                img_data = uploaded_file.getvalue()
                                img = PILImage.open(io.BytesIO(img_data))
                                
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                
                                # 调整图片大小以适应页面宽度
                                available_width = A4[0] - 72  # 页面宽度减去边距
                                img_width, img_height = img.size
                                aspect = img_height / float(img_width)
                                
                                new_width = min(available_width, img_width)
                                new_height = new_width * aspect
                                
                                img = img.resize((int(new_width), int(new_height)), PILImage.Resampling.LANCZOS)
                                img.save(tmp_file.name, 'PNG')
                                temp_files.append(tmp_file.name)
                            
                            img_obj = Image(tmp_file.name, width=new_width, height=new_height)
                            
                            # 添加标识说明图片类型
                            if file_type == 'question':
                                story.append(Paragraph("题目:", heading_style))
                            elif file_type == 'answer':
                                story.append(Paragraph("学生答案:", heading_style))
                            elif file_type == 'marking':
                                story.append(Paragraph("评分标准:", heading_style))
                            
                            story.append(Spacer(1, 5))
                            story.append(img_obj)
                            story.append(Spacer(1, 10))  # 减小图片后的空间
                            
                        except Exception as e:
                            story.append(Paragraph(f"无法加载图片 {file_type}: {str(e)}", body_style))
            
            # 添加一个小的分隔
            story.append(Spacer(1, 10))
            
            # 添加AI响应内容
            story.append(Paragraph("AI批改结果:", heading_style))
            story.append(Spacer(1, 8))
            
            # 处理原始文本，按段落分割
            paragraphs = str(result_text).split('\n')
            for para in paragraphs:
                if para.strip():
                    # 处理特殊HTML字符
                    para = para.replace('&', '&amp;')
                    para = para.replace('<', '&lt;')
                    para = para.replace('>', '&gt;')
                    # 特殊处理数学符号，保持原样
                    try:
                        story.append(Paragraph(process_math_text(para), body_style))
                    except Exception as e:
                        # 如果段落渲染失败，尝试分割长句子
                        print(f"Error rendering paragraph: {str(e)}")
                        sentences = para.split('. ')
                        for sentence in sentences:
                            if sentence:
                                try:
                                    story.append(Paragraph(process_math_text(sentence + '.'), body_style))
                                except:
                                    # 如果单个句子也失败，则简单显示
                                    print(f"Error rendering sentence, displaying as plain text")
                                    story.append(Spacer(1, 5))
                                    story.append(Paragraph("无法正确渲染部分内容", body_style))
            
            # 生成PDF
            doc.build(story)
            return True, str(output_path)
            
        except Exception as e:
            error_msg = f"PDF生成错误: {str(e)}"
            print(error_msg)  # 添加日志
            return False, error_msg
        
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception:
                    pass

def process_correction_pdf(question_image, student_answer_image, marking_scheme_image, api_result, output_dir):
    """
    处理批改PDF生成请求
    
    参数:
    question_image: UploadedFile, 题目图片
    student_answer_image: UploadedFile, 学生答案图片
    marking_scheme_image: UploadedFile, 评分标准图片
    api_result: str, API返回的批改结果
    output_dir: Path, 输出目录
    
    返回:
    tuple: (成功标志, 输出文件路径或错误信息)
    """
    try:
        # 检查文件是否已选择
        if not all([question_image, student_answer_image, marking_scheme_image]):
            return False, "Please select all required files (Question, Student Answer, and Marking Scheme)"

        # 创建PDF合并器
        merger = PDFMerger(str(output_dir))
        
        # 合并PDF
        success, result = merger.merge_pdfs(
            {'question': question_image, 'answer': student_answer_image, 'marking': marking_scheme_image},
            api_result,
            "AI Correction Results",
            output_dir
        )
        
        return success, result
        
    except Exception as e:
        return False, f"Error processing files: {str(e)}"

class ImageToPDFConverter:
    def __init__(self, upload_dir):
        self.upload_dir = Path(upload_dir)

    def convert_multiple_images_to_pdf(self, image_paths, output_path):
        """
        Convert multiple images to a single PDF file
        
        Args:
            image_paths (list): List of paths to image files
            output_path (str): Path where the PDF should be saved
        
        Returns:
            str: Path to the created PDF file
        """
        try:
            # 检查是否有图片文件
            if not image_paths:
                raise Exception("No image files provided")

            # 打开第一张图片
            first_image = Image.open(image_paths[0])
            first_image = first_image.convert('RGB')
            
            # 转换其他图片
            other_images = []
            for img_path in image_paths[1:]:
                img = Image.open(img_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                other_images.append(img)
            
            # 保存为PDF
            first_image.save(output_path, save_all=True, append_images=other_images)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Error converting images to PDF: {str(e)}")