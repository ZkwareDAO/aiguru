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
    """替换数学符号为普通字符"""
    # 完全删除此函数或保留为空函数
    return text

class PDFMerger:
    def __init__(self, upload_dir):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # 注册中文字体
        self.setup_chinese_font()

    def setup_chinese_font(self):
        """设置中文字体"""
        # 定义可能的字体路径
        font_paths = [
            # Linux 中文字体路径
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # 文泉驿微米黑
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Noto Sans CJK
            
            # macOS 中文字体路径
            '/Library/Fonts/Arial Unicode.ttf',
            '/System/Library/Fonts/PingFang.ttc',
            
            # Windows 中文字体路径
            'C:/Windows/Fonts/simsun.ttc',  # 宋体
            'C:/Windows/Fonts/simhei.ttf',  # 黑体
            'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
            
            # 退路 - 使用 ReportLab 内置字体
            None
        ]
        
        # 尝试注册第一个可用的字体
        self.chinese_font_name = 'Helvetica'  # 默认退路字体
        
        for font_path in font_paths:
            if font_path and os.path.exists(font_path):
                try:
                    font_name = os.path.basename(font_path).split('.')[0]
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    self.chinese_font_name = font_name
                    print(f"Using Chinese font: {font_name}")
                    break
                except Exception as e:
                    print(f"Failed to register font {font_path}: {str(e)}")
            elif font_path is None:
                # 没有找到合适的中文字体，使用内置字体
                print("No Chinese font found, using Helvetica (Chinese characters may show as blocks)")

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
                leading=16         # 减小行距
            )
            
            # 准备内容
            story = []
            
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
                            story.append(img_obj)
                            story.append(Spacer(1, 10))  # 减小图片后的空间
                            
                        except Exception as e:
                            story.append(Paragraph(f"Unable to load image {file_type}: {str(e)}", body_style))
            
            # 添加一个小的分隔
            story.append(Spacer(1, 10))
            
            # 添加AI响应内容
            story.append(Paragraph("AI Response:", heading_style))
            story.append(Spacer(1, 8))
            
            # 处理原始文本，按段落分割 - 不再对数学符号进行替换
            paragraphs = str(result_text).split('\n')
            for para in paragraphs:
                if para.strip():
                    # 处理特殊HTML字符
                    para = para.replace('&', '&amp;')
                    para = para.replace('<', '&lt;')
                    para = para.replace('>', '&gt;')
                    # 保持原始格式，不进行数学符号替换
                    story.append(Paragraph(para, body_style))
            
            # 生成PDF
            doc.build(story)
            return True, str(output_path)
            
        except Exception as e:
            error_msg = f"Error during PDF generation: {str(e)}"
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