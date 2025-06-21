from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os
from pathlib import Path
import re
import logging

class CorrectionPDFGenerator:
    """专门用于生成批改结果PDF的类"""
    
    def __init__(self, font_dir="functions/api_correcting/fonts"):
        self.font_dir = Path(font_dir)
        self.styles = getSampleStyleSheet()
        self._setup_fonts()
        self._setup_styles()
    
    def _setup_fonts(self):
        """设置中文字体"""
        try:
            # 检查字体目录是否存在
            if not self.font_dir.exists():
                self.font_dir.mkdir(parents=True, exist_ok=True)
            
            # 常用字体文件名
            font_files = [
                "SimHei.ttf",  # 黑体
                "simsun.ttc",  # 宋体
                "NotoSansCJK-Regular.ttc",  # Noto Sans CJK
                "msyh.ttc",   # 微软雅黑
                "simkai.ttf", # 楷体
            ]
            
            # 尝试注册字体
            font_registered = False
            for font_file in font_files:
                font_path = self.font_dir / font_file
                if font_path.exists():
                    try:
                        pdfmetrics.registerFont(TTFont('ChineseFont', str(font_path)))
                        font_registered = True
                        logging.info(f"成功注册字体: {font_file}")
                        break
                    except Exception as e:
                        logging.warning(f"注册字体 {font_file} 失败: {e}")
                        continue
            
            if not font_registered:
                logging.warning("未找到可用的中文字体，将使用默认字体")
                
        except Exception as e:
            logging.error(f"字体设置失败: {e}")
    
    def _setup_styles(self):
        """设置文档样式"""
        # 标题样式
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
        )
        
        # 副标题样式
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkgreen,
            fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
        )
        
        # 正文样式
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        )
        
        # 代码样式
        self.code_style = ParagraphStyle(
            'CustomCode',
            parent=self.styles['Code'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=20,
            backgroundColor=colors.lightgrey,
            fontName='Courier'
        )
        
        # 重要信息样式
        self.important_style = ParagraphStyle(
            'Important',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            textColor=colors.red,
            fontName='ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
        )
    
    def _parse_content(self, content):
        """解析批改结果内容"""
        sections = []
        current_section = {"title": "", "content": []}
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是标题行
            if (line.startswith('#') or 
                line.startswith('=') or 
                re.match(r'^第\s*\d+\s*[题组]', line) or
                re.match(r'^Problem\s+\d+', line) or
                '批改结果' in line or
                'Grading Result' in line):
                
                # 保存当前节
                if current_section["content"]:
                    sections.append(current_section)
                
                # 开始新节
                current_section = {
                    "title": line.replace('#', '').replace('=', '').strip(),
                    "content": []
                }
            else:
                current_section["content"].append(line)
        
        # 添加最后一节
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
    
    def _create_header_footer(self, canvas, doc):
        """创建页眉页脚"""
        canvas.saveState()
        
        # 页眉
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(colors.darkblue)
        canvas.drawString(50, A4[1] - 50, "AI智能批改系统 - 批改报告")
        
        # 页脚
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(
            A4[0] - 50, 
            30, 
            f"第 {doc.page} 页 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        canvas.restoreState()
    
    def generate_pdf(self, content, output_path, title="AI批改结果报告", files_info=None, settings=None):
        """生成PDF文件"""
        try:
            # 创建输出目录
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建PDF文档
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=100,
                bottomMargin=72
            )
            
            # 文档内容
            story = []
            
            # 标题
            story.append(Paragraph(title, self.title_style))
            story.append(Spacer(1, 20))
            
            # 基本信息表格
            if settings:
                info_data = [
                    ['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    ['批改严格程度', settings.get('strictness_level', '中等')],
                    ['输出语言', '中文' if settings.get('language', 'zh') == 'zh' else '英文'],
                    ['处理组数', str(settings.get('groups_processed', 1))],
                ]
                
                info_table = Table(info_data, colWidths=[2*inch, 4*inch])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(Paragraph("批改信息", self.subtitle_style))
                story.append(info_table)
                story.append(Spacer(1, 20))
            
            # 解析并添加内容
            sections = self._parse_content(content)
            
            for i, section in enumerate(sections):
                if section["title"]:
                    story.append(Paragraph(section["title"], self.subtitle_style))
                
                for line in section["content"]:
                    if line.strip():
                        # 检查是否是特殊格式的行
                        if line.startswith('✓') or line.startswith('- ✓'):
                            # 正确标记
                            styled_line = f'<font color="green">{line}</font>'
                            story.append(Paragraph(styled_line, self.normal_style))
                        elif line.startswith('✗') or line.startswith('- ✗'):
                            # 错误标记
                            styled_line = f'<font color="red">{line}</font>'
                            story.append(Paragraph(styled_line, self.normal_style))
                        elif line.startswith('△') or line.startswith('- △'):
                            # 部分正确标记
                            styled_line = f'<font color="orange">{line}</font>'
                            story.append(Paragraph(styled_line, self.normal_style))
                        elif '总分：' in line or 'Total score:' in line or '得分：' in line:
                            # 分数行
                            styled_line = f'<b><font color="blue">{line}</font></b>'
                            story.append(Paragraph(styled_line, self.important_style))
                        elif re.match(r'.*\d+/\d+.*分', line):
                            # 包含分数的行
                            styled_line = f'<b>{line}</b>'
                            story.append(Paragraph(styled_line, self.normal_style))
                        else:
                            story.append(Paragraph(line, self.normal_style))
                
                # 添加节之间的间距
                if i < len(sections) - 1:
                    story.append(Spacer(1, 15))
            
            # 构建PDF
            doc.build(story, onFirstPage=self._create_header_footer, onLaterPages=self._create_header_footer)
            
            logging.info(f"PDF生成成功: {output_path}")
            return True, str(output_path)
            
        except Exception as e:
            logging.error(f"PDF生成失败: {e}")
            return False, str(e)
    
    def generate_simple_pdf(self, content, output_path, title="批改结果"):
        """生成简单的纯文本PDF（备用方案）"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            
            c = canvas.Canvas(str(output_path), pagesize=A4)
            width, height = A4
            
            # 设置字体
            try:
                c.setFont("ChineseFont", 12)
            except:
                c.setFont("Helvetica", 12)
            
            # 标题
            c.drawCentredText(width/2, height - 50, title)
            
            # 内容
            lines = content.split('\n')
            y = height - 100
            
            for line in lines:
                if y < 50:  # 换页
                    c.showPage()
                    try:
                        c.setFont("ChineseFont", 12)
                    except:
                        c.setFont("Helvetica", 12)
                    y = height - 50
                
                c.drawString(50, y, line[:100])  # 限制行长度
                y -= 15
            
            c.save()
            return True, str(output_path)
            
        except Exception as e:
            logging.error(f"简单PDF生成失败: {e}")
            return False, str(e)

# 测试函数
if __name__ == "__main__":
    generator = CorrectionPDFGenerator()
    test_content = """
# 第1题批改结果

## 学生答题过程
步骤1：解方程 2x + 3 = 7
步骤2：移项得 2x = 7 - 3 = 4
步骤3：两边除以2得 x = 2

## 步骤分析
✓ 步骤1：正确识别方程类型
✗ 步骤2：计算错误，应该是 2x = 4
✓ 步骤3：除法运算正确

## 得分详情
总分：8/10 分

## 改进建议
注意计算的准确性，加强基础运算练习。
"""
    
    success, path = generator.generate_pdf(
        test_content, 
        "test_output.pdf", 
        "测试批改报告"
    )
    print(f"生成结果: {success}, 路径: {path}") 