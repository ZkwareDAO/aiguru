import os
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
from datetime import datetime

class PDFMerger:
    def __init__(self, upload_dir):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

    def merge_pdfs(self, original_pdf_path, answer_text, annotation_text, output_dir):
        """
        合并PDF文件并添加答案和注释
        
        参数:
        original_pdf_path: str, 原始PDF文件路径
        answer_text: str, 答案文本
        annotation_text: str, 注释文本
        output_dir: Path, 输出目录
        
        返回:
        tuple: (成功标志, 输出文件路径或错误信息)
        """
        try:
            # 创建临时PDF文件
            temp_pdf = FPDF()
            temp_pdf.add_page()
            
            # 添加答案部分
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "Answers:", ln=True)
            temp_pdf.set_font("Arial", '', 12)
            temp_pdf.multi_cell(0, 10, answer_text)
            
            # 添加注释部分
            temp_pdf.add_page()
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "Annotations:", ln=True)
            temp_pdf.set_font("Arial", '', 12)
            temp_pdf.multi_cell(0, 10, annotation_text)
            
            # 保存临时PDF
            temp_path = output_dir / "temp_annotations.pdf"
            temp_pdf.output(str(temp_path))

            # 合并PDF
            merger = PdfWriter()
            
            # 添加原始PDF
            original_pdf = PdfReader(original_pdf_path)
            for page in original_pdf.pages:
                merger.add_page(page)
            
            # 添加注释PDF
            annotations_pdf = PdfReader(str(temp_path))
            for page in annotations_pdf.pages:
                merger.add_page(page)

            # 生成输出文件名
            output_filename = f"merged_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = output_dir / output_filename
            
            # 保存合并后的PDF
            merger.write(str(output_path))
            merger.close()
            
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            
            return True, str(output_path)

        except Exception as e:
            error_msg = f"Error during PDF merging: {str(e)}"
            # 清理临时文件
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            return False, error_msg

def process_pdf_merge(original_pdf, answer_file, annotation_file, output_dir):
    """
    处理PDF合并请求
    
    参数:
    original_pdf: UploadedFile, 原始PDF文件
    answer_file: UploadedFile, 答案文件
    annotation_file: UploadedFile, 注释文件
    output_dir: Path, 输出目录
    
    返回:
    tuple: (成功标志, 输出文件路径或错误信息)
    """
    try:
        # 保存原始PDF
        original_pdf_path = output_dir / original_pdf.name
        with open(original_pdf_path, "wb") as f:
            f.write(original_pdf.getbuffer())
        
        # 读取答案和注释文件
        answer_text = answer_file.getvalue().decode("utf-8")
        annotation_text = annotation_file.getvalue().decode("utf-8")
        
        # 创建PDF合并器
        merger = PDFMerger(str(output_dir))
        
        # 合并PDF
        success, result = merger.merge_pdfs(
            str(original_pdf_path),
            answer_text,
            annotation_text,
            output_dir
        )
        
        # 清理原始PDF文件
        if original_pdf_path.exists():
            original_pdf_path.unlink()
        
        return success, result
        
    except Exception as e:
        return False, f"Error processing files: {str(e)}"