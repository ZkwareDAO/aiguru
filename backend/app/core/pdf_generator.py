"""
PDF Generator for AI Grading Results - Migrated from ai_correction
Professional PDF report generation with Chinese font support
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("ReportLab not available. PDF generation will be disabled.")

logger = logging.getLogger(__name__)

class GradingPDFGenerator:
    """Professional PDF generator for AI grading results"""
    
    def __init__(self, font_dir: str = "fonts"):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        self.font_dir = Path(font_dir)
        self.styles = getSampleStyleSheet()
        self._setup_fonts()
        self._setup_styles()
    
    def _setup_fonts(self):
        """Setup Chinese fonts for PDF generation"""
        try:
            # Create fonts directory if it doesn't exist
            if not self.font_dir.exists():
                self.font_dir.mkdir(parents=True, exist_ok=True)
            
            # Common Chinese font files
            font_files = [
                "SimHei.ttf",       # SimHei (Black)
                "simsun.ttc",       # SimSun
                "NotoSansCJK-Regular.ttc",  # Noto Sans CJK
                "msyh.ttc",         # Microsoft YaHei
                "simkai.ttf",       # KaiTi
            ]
            
            # Try to register fonts
            font_registered = False
            for font_file in font_files:
                font_path = self.font_dir / font_file
                if font_path.exists():
                    try:
                        pdfmetrics.registerFont(TTFont('ChineseFont', str(font_path)))
                        font_registered = True
                        logger.info(f"Successfully registered font: {font_file}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to register font {font_file}: {e}")
                        continue
            
            if not font_registered:
                logger.warning("No Chinese fonts found, using default fonts")
                
        except Exception as e:
            logger.error(f"Font setup failed: {e}")
    
    def _setup_styles(self):
        """Setup document styles"""
        # Check if Chinese font is available
        chinese_font = 'ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName=chinese_font if chinese_font == 'ChineseFont' else 'Helvetica-Bold'
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkgreen,
            fontName=chinese_font if chinese_font == 'ChineseFont' else 'Helvetica-Bold'
        )
        
        # Normal text style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName=chinese_font
        )
        
        # Code style
        self.code_style = ParagraphStyle(
            'CustomCode',
            parent=self.styles['Code'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=20,
            backgroundColor=colors.lightgrey,
            fontName='Courier'
        )
        
        # Important information style
        self.important_style = ParagraphStyle(
            'Important',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            textColor=colors.red,
            fontName=chinese_font if chinese_font == 'ChineseFont' else 'Helvetica-Bold'
        )
        
        # Score style
        self.score_style = ParagraphStyle(
            'Score',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.darkblue,
            fontName=chinese_font if chinese_font == 'ChineseFont' else 'Helvetica-Bold'
        )
    
    def _parse_grading_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse grading results into structured format"""
        sections = []
        current_section = {"title": "", "content": [], "type": "general"}
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if it's a question title
            if (re.match(r'^###?\s*题目\s*\d+', line) or 
                re.match(r'^###?\s*Question\s+\d+', line) or
                re.match(r'^第\s*\d+\s*[题组]', line)):
                
                # Save current section
                if current_section["content"]:
                    sections.append(current_section)
                
                # Start new question section
                current_section = {
                    "title": line.replace('#', '').strip(),
                    "content": [],
                    "type": "question"
                }
            
            # Check if it's a summary section
            elif ('总结' in line or 'Summary' in line or '批改总结' in line):
                if current_section["content"]:
                    sections.append(current_section)
                
                current_section = {
                    "title": line.replace('#', '').strip(),
                    "content": [],
                    "type": "summary"
                }
            
            # Check for score information
            elif ('满分' in line or 'Full Marks' in line or '得分' in line or 'Score' in line):
                current_section["content"].append({
                    "type": "score",
                    "content": line
                })
            
            # Check for grading details
            elif ('批改详情' in line or 'Grading Details' in line):
                current_section["content"].append({
                    "type": "details_header",
                    "content": line
                })
            
            # Regular content
            else:
                current_section["content"].append({
                    "type": "text",
                    "content": line
                })
        
        # Add last section
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
    
    def _create_header_footer(self, canvas_obj, doc):
        """Create page header and footer"""
        canvas_obj.saveState()
        
        # Header
        canvas_obj.setFont('Helvetica-Bold', 12)
        canvas_obj.setFillColor(colors.darkblue)
        canvas_obj.drawString(50, A4[1] - 50, "AI智能批改系统 - 批改报告")
        
        # Footer
        canvas_obj.setFont('Helvetica', 10)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawRightString(
            A4[0] - 50, 
            30, 
            f"第 {doc.page} 页 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        canvas_obj.restoreState()
    
    def generate_pdf(self, 
                    content: str, 
                    output_path: str, 
                    title: str = "AI批改结果报告", 
                    student_info: Optional[Dict[str, Any]] = None,
                    statistics: Optional[Dict[str, Any]] = None) -> bool:
        """Generate PDF report from grading results"""
        try:
            # Create output directory
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=100,
                bottomMargin=72
            )
            
            # Document content
            story = []
            
            # Title
            story.append(Paragraph(title, self.title_style))
            story.append(Spacer(1, 20))
            
            # Basic information table
            if student_info or statistics:
                info_data = []
                
                if student_info:
                    info_data.extend([
                        ['学生姓名', student_info.get('name', '未提供')],
                        ['学号', student_info.get('student_id', '未提供')],
                        ['班级', student_info.get('class', '未提供')]
                    ])
                
                if statistics:
                    info_data.extend([
                        ['总分', f"{statistics.get('total_score', 0)}/{statistics.get('total_full_marks', 0)}"],
                        ['得分率', f"{statistics.get('percentage', 0):.1f}%"],
                        ['题目数量', str(statistics.get('questions_graded', 0))]
                    ])
                
                info_data.append(['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                
                info_table = Table(info_data, colWidths=[2*inch, 4*inch])
                info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(info_table)
                story.append(Spacer(1, 20))
            
            # Parse and add grading content
            sections = self._parse_grading_content(content)
            
            for section in sections:
                # Section title
                if section["title"]:
                    if section["type"] == "question":
                        story.append(Paragraph(section["title"], self.subtitle_style))
                    elif section["type"] == "summary":
                        story.append(PageBreak())
                        story.append(Paragraph(section["title"], self.subtitle_style))
                    else:
                        story.append(Paragraph(section["title"], self.subtitle_style))
                
                # Section content
                for content_item in section["content"]:
                    if isinstance(content_item, dict):
                        content_type = content_item.get("type", "text")
                        content_text = content_item.get("content", "")
                        
                        if content_type == "score":
                            story.append(Paragraph(content_text, self.score_style))
                        elif content_type == "details_header":
                            story.append(Paragraph(content_text, self.important_style))
                        else:
                            # Clean text for PDF
                            cleaned_text = self._clean_text_for_pdf(content_text)
                            story.append(Paragraph(cleaned_text, self.normal_style))
                    else:
                        # Handle string content
                        cleaned_text = self._clean_text_for_pdf(str(content_item))
                        story.append(Paragraph(cleaned_text, self.normal_style))
                
                story.append(Spacer(1, 12))
            
            # Build PDF
            doc.build(story, onFirstPage=self._create_header_footer, onLaterPages=self._create_header_footer)
            
            logger.info(f"PDF report generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            return False
    
    def _clean_text_for_pdf(self, text: str) -> str:
        """Clean text for PDF formatting"""
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)      # Italic
        
        # Handle checkmarks and symbols
        text = text.replace('✓', '✓')
        text = text.replace('✗', '✗')
        text = text.replace('→', '→')
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Escape XML entities
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        
        # Restore formatted tags
        text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
        text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
        
        return text
    
    def generate_batch_report(self, 
                            grading_results: List[Dict[str, Any]], 
                            output_dir: str,
                            title_prefix: str = "批改报告") -> List[str]:
        """Generate batch PDF reports"""
        generated_files = []
        
        for i, result in enumerate(grading_results):
            try:
                filename = f"{title_prefix}_{i+1:03d}.pdf"
                output_path = Path(output_dir) / filename
                
                success = self.generate_pdf(
                    content=result.get('content', ''),
                    output_path=str(output_path),
                    title=f"{title_prefix} #{i+1}",
                    student_info=result.get('student_info'),
                    statistics=result.get('statistics')
                )
                
                if success:
                    generated_files.append(str(output_path))
                    
            except Exception as e:
                logger.error(f"Failed to generate report {i+1}: {e}")
        
        logger.info(f"Generated {len(generated_files)} PDF reports")
        return generated_files

# Convenience functions for integration
def create_grading_pdf(content: str, 
                      output_path: str, 
                      title: str = "AI Grading Report",
                      student_info: Optional[Dict[str, Any]] = None,
                      statistics: Optional[Dict[str, Any]] = None) -> bool:
    """Create a PDF report from grading results"""
    try:
        generator = GradingPDFGenerator()
        return generator.generate_pdf(content, output_path, title, student_info, statistics)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return False

def create_batch_pdfs(grading_results: List[Dict[str, Any]], 
                     output_dir: str,
                     title_prefix: str = "Grading Report") -> List[str]:
    """Create batch PDF reports"""
    try:
        generator = GradingPDFGenerator()
        return generator.generate_batch_report(grading_results, output_dir, title_prefix)
    except Exception as e:
        logger.error(f"Batch PDF generation failed: {e}")
        return []

# Font installation helper
def download_fonts():
    """Download required fonts for Chinese text support"""
    import urllib.request
    import zipfile
    
    font_urls = {
        "SimHei.ttf": "https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf",
        "NotoSansCJK-Regular.ttc": "https://github.com/googlefonts/noto-cjk/releases/download/Sans2.004/05_NotoSansCJK-Regular.ttc"
    }
    
    font_dir = Path("fonts")
    font_dir.mkdir(exist_ok=True)
    
    for font_name, url in font_urls.items():
        font_path = font_dir / font_name
        if not font_path.exists():
            try:
                logger.info(f"Downloading font: {font_name}")
                urllib.request.urlretrieve(url, font_path)
                logger.info(f"Successfully downloaded: {font_name}")
            except Exception as e:
                logger.error(f"Failed to download {font_name}: {e}")

if __name__ == "__main__":
    # Test PDF generation
    test_content = """
### 题目1
**满分**: 5分 - 📊 来源: MARKING标准
**得分**: 4分
**批改详情**:
- 建立方程 ✓ [2分]
- 计算过程 ✓ [1分]
- 最终答案有误 ✗ [0分] → 答案应为15

### 题目2
**满分**: 3分 - 📊 来源: MARKING标准
**得分**: 3分
**批改详情**:
- 理解题意 ✓ [1分]
- 推理过程 ✓ [1分]
- 结论正确 ✓ [1分]
"""
    
    test_stats = {
        "total_score": 7,
        "total_full_marks": 8,
        "percentage": 87.5,
        "questions_graded": 2
    }
    
    test_student = {
        "name": "张三",
        "student_id": "2024001",
        "class": "高一(1)班"
    }
    
    success = create_grading_pdf(
        content=test_content,
        output_path="test_report.pdf",
        title="数学作业批改报告",
        student_info=test_student,
        statistics=test_stats
    )
    
    print(f"Test PDF generation: {'Success' if success else 'Failed'}")