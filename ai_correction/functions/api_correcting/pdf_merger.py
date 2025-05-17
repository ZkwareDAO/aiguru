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

# Try to import TableStyle from different modules to handle different ReportLab versions
try:
    from reportlab.platypus.tables import TableStyle
    print("Successfully imported TableStyle from reportlab.platypus.tables")
except ImportError:
    try:
        from reportlab.lib.tables import TableStyle
        print("Successfully imported TableStyle from reportlab.lib.tables")
    except ImportError:
        # Fallback implementation if TableStyle import fails
        class TableStyle:
            def __init__(self, commands=None):
                self.commands = commands or []
                print("WARNING: Using fallback TableStyle implementation - PDF generation may fail or look incorrect!")
                
            def setStyle(self, otherStyle):
                print("WARNING: Using fallback TableStyle.setStyle() method - styling will not be applied properly")
                if hasattr(otherStyle, 'commands'):
                    self.commands.extend(otherStyle.commands)
                return self

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from PIL import Image as PILImage
import tempfile
import urllib.request
import shutil
import re

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

        # 优先查找 NotoSansSC-Regular.otf
        noto_font_path = self.font_dir / 'NotoSansSC-Regular.otf'
        if not noto_font_path.exists():
            # 自动下载
            noto_url = 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf'
            print('Downloading NotoSansSC-Regular.otf...')
            download_font(noto_url, noto_font_path)
        if noto_font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont('NotoSansSC', str(noto_font_path)))
                self.chinese_font_name = 'NotoSansSC'
                registerFontFamily('NotoSansSC', normal='NotoSansSC')
                print('Using NotoSansSC for PDF output')
                font_found = True
            except Exception as e:
                print(f'Failed to register NotoSansSC: {e}')

    def merge_pdfs(self, files_to_include, result_text, title, output_path):
        temp_files = []
        try:
            # 记录函数调用信息，便于调试
            print(f"PDF merger called with:\n - files: {files_to_include}\n - output: {output_path}")
            
            # 创建PDF文档，减小页边距减少留空
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=15,    # 进一步减小右边距
                leftMargin=15,     # 进一步减小左边距
                topMargin=15,      # 进一步减小上边距
                bottomMargin=15    # 进一步减小下边距
            )
            
            # 创建样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontName=self.chinese_font_name,  # 使用找到的中文字体
                fontSize=14,        # 减小标题字号
                spaceAfter=3       # 进一步减小标题后的空间
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading1'],
                fontName=self.chinese_font_name,  # 使用找到的中文字体
                fontSize=12,        # 减小子标题字号
                spaceAfter=2       # 进一步减小子标题后的空间
            )
            subheading_style = ParagraphStyle(
                'CustomSubheading',
                parent=styles['Heading2'],
                fontName=self.chinese_font_name,
                fontSize=11,
                spaceAfter=2
            )
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontName=self.chinese_font_name,  # 使用找到的中文字体
                fontSize=10,
                spaceAfter=2,      # 进一步减小段落间距
                leading=12,        # 减小行距
                allowWidows=1,     # 允许段落底部的孤行
                allowOrphans=1     # 允许段落顶部的孤行
            )
            
            # 准备内容
            story = []
            
            # 添加标题
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 3))  # 进一步减小标题后的空间
            
            # 预处理结果文本，分离基本信息和批改内容
            cleaned_text = re.sub(r'\n\s*\n+', '\n', str(result_text))
            
            # 拆分为基本信息和批改内容两部分
            parts = re.split(r'学生答案批改如下:', cleaned_text, 1)
            
            # 先添加基本信息部分
            if len(parts) > 1:
                basic_info = parts[0].strip()
                correction_content = "学生答案批改如下:" + parts[1].strip()
                
                # 提取科目和题目类型
                subject_match = re.search(r'科目：\s*(.*?)(?:\n|$)', basic_info)
                type_match = re.search(r'题目类型：\s*(.*?)(?:\n|$)', basic_info)
                score_match = re.search(r'总分：\s*(\d+)/(\d+)', basic_info)
                
                # 添加基本信息表格
                info_data = []
                if subject_match:
                    info_data.append(["科目", subject_match.group(1)])
                if type_match:
                    info_data.append(["题目类型", type_match.group(1)])
                if score_match:
                    info_data.append(["总分", f"{score_match.group(1)}/{score_match.group(2)}"])
                
                if info_data:
                    # 添加"基本信息"标题
                    story.append(Paragraph("基本信息", heading_style))
                    story.append(Spacer(1, 2))
                    
                    # 创建表格
                    table = Table(info_data, colWidths=[100, 300])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), '#f0f0f0'),
                        ('TEXTCOLOR', (0, 0), (0, -1), '#333333'),
                        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                        ('FONTNAME', (0, 0), (-1, -1), self.chinese_font_name),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 0.5, '#dddddd'),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 5))
            else:
                # 如果没有找到分隔标志，使用整个内容
                basic_info = ""
                correction_content = cleaned_text
            
            # 处理上传的图片文件和对应的批改内容
            if files_to_include:
                # 添加标题：学生答案批改
                story.append(Paragraph("学生答案批改", heading_style))
                story.append(Spacer(1, 3))
                
                # 分析文件关联性并分组
                file_groups = self._group_related_files(files_to_include)
                
                # 解析批改内容，按块提取
                correction_blocks = self._parse_correction_blocks(correction_content)
                
                # 遍历每个相关文件组
                for group_idx, group in enumerate(file_groups):
                    # 组内可能有多种类型的文件
                    group_files = {}
                    group_title = f"批改组 {group_idx + 1}"
                    
                    # 检查组内是否有学生答案标识，作为组标题
                    for file_key in group:
                        if "student_answer" in file_key:
                            # 如果文件名包含数字，提取作为题号
                            number_match = re.search(r'(\d+)', file_key)
                            if number_match:
                                group_title = f"第 {number_match.group(1)} 题"
                            else:
                                group_title = "学生答案"
                            break
                    
                    # 添加组标题
                    story.append(Paragraph(group_title, heading_style))
                    story.append(Spacer(1, 3))
                    
                    # 处理组内的每个文件
                    for file_key in group:
                        file_info = files_to_include[file_key]
                        
                        # 确定文件类型
                        if "question" in file_key:
                            file_type = "question"
                            type_name = "题目"
                        elif "student_answer" in file_key:
                            file_type = "student_answer"
                            type_name = "学生答案"
                        elif "marking_scheme" in file_key:
                            file_type = "marking_scheme"
                            type_name = "评分标准"
                        else:
                            file_type = "unknown"
                            type_name = "未知类型"
                        
                        group_files[file_type] = {
                            'key': file_key,
                            'info': file_info,
                            'type_name': type_name
                        }
                    
                    # 创建多行布局：先全部图片，再AI反馈
                    image_row_data = []
                    image_objects = []
                    
                    # 按顺序处理文件类型
                    ordered_types = ["question", "student_answer", "marking_scheme"]
                    
                    # 首先添加所有图片
                    for file_type in ordered_types:
                        if file_type in group_files:
                            file_data = group_files[file_type]
                            try:
                                # 处理图片并添加到列表
                                img_obj, tmp_file = self._process_image_file(file_data['info'])
                                if img_obj:
                                    temp_files.append(tmp_file)
                                    
                                    # 添加图片标题和图片
                                    image_cell = []
                                    image_cell.append(Paragraph(file_data['type_name'], subheading_style))
                                    image_cell.append(img_obj)
                                    image_row_data.append(image_cell)
                                    image_objects.append(img_obj)
                            except Exception as e:
                                print(f"处理图片 {file_data['key']} 时出错: {str(e)}")
                                continue
                    
                    # 计算每列宽度 - 基于图片数量平均分配
                    num_images = len(image_row_data)
                    if num_images > 0:
                        available_width = A4[0] - 40  # 页面宽度减去边距
                        col_width = available_width / num_images
                        
                        # 创建图片行
                        image_table = Table([image_row_data], colWidths=[col_width] * num_images)
                        image_table.setStyle(TableStyle([
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 5),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                        ]))
                        
                        story.append(image_table)
                        story.append(Spacer(1, 10))
                    
                    # 检查该组是否有对应的批改内容
                    correction_block = None
                    
                    # 如果组内有学生答案文件，查找匹配的批改块
                    if "student_answer" in group_files:
                        student_key = group_files["student_answer"]["key"]
                        number_match = re.search(r'(\d+)', student_key)
                        
                        if number_match:
                            # 查找编号匹配的批改块
                            question_num = number_match.group(1)
                            for block in correction_blocks:
                                if f"第{question_num}题" in block or f"第 {question_num} 题" in block:
                                    correction_block = block
                                    break
                        
                        # 如果没找到特定编号的批改块，但只有一组图片和一个批改块，则使用该块
                        if correction_block is None and len(file_groups) == 1 and len(correction_blocks) == 1:
                            correction_block = correction_blocks[0]
                    
                    # 添加批改内容
                    if correction_block:
                        # 添加批改结果标题
                        story.append(Paragraph("批改结果", subheading_style))
                        story.append(Spacer(1, 3))
                        
                        # 处理批改内容的每一行
                        correction_lines = correction_block.split('\n')
                        for line in correction_lines:
                            if line.strip():
                                # 处理评分行
                                if re.match(r'\d+\.\s*第\d+步', line):
                                    story.append(Paragraph(line, heading_style))
                                # 处理正确点
                                elif "✓ 正确点" in line:
                                    p = Paragraph('<font color="green">'+line+'</font>', body_style)
                                    story.append(p)
                                # 处理错误点
                                elif "✗ 错误点" in line:
                                    p = Paragraph('<font color="red">'+line+'</font>', body_style)
                                    story.append(p)
                                # 处理扣分原因
                                elif "扣分原因" in line:
                                    p = Paragraph('<i>'+line+'</i>', body_style)
                                    story.append(p)
                                # 其他普通行
                                else:
                                    story.append(Paragraph(line, body_style))
                    
                    # 添加分隔线
                    story.append(Spacer(1, 15))
                    story.append(Paragraph("_" * 70, body_style))
                    story.append(Spacer(1, 15))
            
            # 添加总结部分
            story.append(Paragraph("总结", heading_style))
            story.append(Spacer(1, 3))
            
            # 添加总分信息
            score_match = re.search(r'总分：\s*(\d+)/(\d+)', basic_info)
            if score_match:
                score_text = f"最终得分: {score_match.group(1)}/{score_match.group(2)}"
                story.append(Paragraph(score_text, heading_style))
            
            # 生成PDF
            doc.build(story)
            print(f"PDF成功生成到: {output_path}")
            return True, str(output_path)
            
        except Exception as e:
            error_msg = f"PDF生成错误: {str(e)}"
            print(error_msg)  # 添加日志
            import traceback
            traceback.print_exc()  # 打印完整堆栈跟踪
            return False, error_msg
        
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    print(f"清理临时文件失败: {temp_file}, 错误: {str(e)}")
                    pass
                    
    def _process_image_file(self, file_info):
        """处理图片文件并返回图片对象和临时文件路径"""
        img_path = None
        
        # 处理 {'path': '/path/to/file'} 格式
        if isinstance(file_info, dict) and 'path' in file_info:
            img_path = file_info['path']
            print(f"从路径加载图片: {img_path}")
        
        # 处理 UploadedFile 对象格式
        elif hasattr(file_info, 'getvalue'):
            # 使用临时文件保存上传的文件内容
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            tmp_file.write(file_info.getvalue())
            img_path = tmp_file.name
            tmp_file.close()
            print(f"从上传文件创建临时文件: {img_path}")
        
        # 处理直接的文件路径字符串
        elif isinstance(file_info, str) and os.path.exists(file_info):
            img_path = file_info
            print(f"直接使用文件路径: {img_path}")
        
        # 如果找到有效路径，尝试加载图片
        if img_path and os.path.exists(img_path):
            # 使用临时文件处理图片
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            
            # 尝试打开图片文件
            img = PILImage.open(img_path)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 调整图片大小以适应页面宽度，同时保持图片质量
            available_width = A4[0] - 40  # 页面宽度减去边距
            img_width, img_height = img.size
            aspect = img_height / float(img_width)
            
            # 计算最佳大小：保持合理尺寸，不同图片大小应相近
            new_width = available_width * 0.3  # 减小宽度，一行可以放多张图片
            new_height = new_width * aspect
            
            # 确保图片高度不超过页面高度的40%
            max_height = A4[1] * 0.4
            if new_height > max_height:
                new_height = max_height
                new_width = new_height / aspect
            
            img = img.resize((int(new_width), int(new_height)), PILImage.Resampling.LANCZOS)
            img.save(tmp_file.name, 'PNG')
            
            img_obj = Image(tmp_file.name, width=new_width, height=new_height)
            return img_obj, tmp_file.name
        
        return None, None
    
    def _group_related_files(self, files_to_include):
        """
        将相关文件分组
        规则：
        1. 具有相同数字编号的文件分在同一组
        2. 无编号的文件如果是同一题型分在同一组
        3. 如果只有一组答案，默认所有文件为同一组
        """
        if not files_to_include:
            return []
            
        # 如果只有几个文件，通常是同一组
        if len(files_to_include) <= 3:
            return [list(files_to_include.keys())]
            
        # 按编号分组
        numbered_groups = {}
        unnumbered_files = []
        
        for file_key in files_to_include.keys():
            # 查找文件名中的数字
            number_match = re.search(r'(\d+)', file_key)
            
            if number_match:
                question_number = number_match.group(1)
                if question_number not in numbered_groups:
                    numbered_groups[question_number] = []
                numbered_groups[question_number].append(file_key)
            else:
                unnumbered_files.append(file_key)
        
        # 构建最终的文件组
        file_groups = list(numbered_groups.values())
        
        # 处理没有编号的文件
        if unnumbered_files:
            # 如果还没有任何分组，所有无编号文件作为一组
            if not file_groups:
                file_groups.append(unnumbered_files)
            else:
                # 根据文件类型分配到已有的组中，或者创建新组
                for file_key in unnumbered_files:
                    # 检查是否能分配到已有组
                    assigned = False
                    
                    # 尝试根据文件类型匹配
                    file_type = None
                    if "question" in file_key:
                        file_type = "question"
                    elif "student_answer" in file_key:
                        file_type = "student_answer"
                    elif "marking_scheme" in file_key:
                        file_type = "marking_scheme"
                    
                    if file_type:
                        # 查找缺少此类型的组
                        for group in file_groups:
                            has_this_type = False
                            for existing_file in group:
                                if file_type in existing_file:
                                    has_this_type = True
                                    break
                            
                            if not has_this_type:
                                group.append(file_key)
                                assigned = True
                                break
                    
                    # 如果未分配，添加到第一个组
                    if not assigned and file_groups:
                        file_groups[0].append(file_key)
        
        return file_groups
    
    def _parse_correction_blocks(self, correction_content):
        """
        解析批改内容，将其分成不同的批改块
        每个块通常对应一道题的批改
        """
        if not correction_content:
            return []
            
        # 去除"学生答案批改如下:"开头
        content = re.sub(r'^学生答案批改如下:\s*', '', correction_content)
        
        # 查找题目标记，通常是"第X题"或"题目X"格式
        question_markers = re.findall(r'(第\s*\d+\s*题|题目\s*\d+)', content)
        
        # 如果没有找到题目标记，返回整个内容作为一个块
        if not question_markers:
            return [content]
            
        # 用题目标记分割内容
        blocks = []
        for i, marker in enumerate(question_markers):
            # 构建分割的正则表达式
            if i < len(question_markers) - 1:
                next_marker = question_markers[i + 1]
                pattern = f'({re.escape(marker)}.+?)(?={re.escape(next_marker)})'
            else:
                pattern = f'({re.escape(marker)}.+)'
                
            # 查找匹配的块
            match = re.search(pattern, content, re.DOTALL)
            if match:
                blocks.append(match.group(1).strip())
        
        # 如果没有成功分割，返回整个内容
        if not blocks:
            blocks = [content]
            
        return blocks

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