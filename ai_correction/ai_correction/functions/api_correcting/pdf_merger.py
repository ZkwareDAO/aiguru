import os
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
from datetime import datetime
from PIL import Image
import io
import base64

class PDFMerger:
    def __init__(self, upload_dir):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

    def merge_pdfs(self, question_image, student_answer_image, marking_scheme_image, api_result, output_dir):
        """
        合并PDF文件并添加答案和注释
        
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

            # 创建临时PDF文件
            temp_pdf = FPDF()
            
            # 添加题目图片
            temp_pdf.add_page()
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "Question:", ln=True)
            # 将图片转换为base64
            question_img = Image.open(io.BytesIO(question_image.getvalue()))
            question_img_path = output_dir / "temp_question.jpg"
            question_img.save(question_img_path)
            temp_pdf.image(str(question_img_path), x=10, y=30, w=190)
            
            # 添加学生答案图片
            temp_pdf.add_page()
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "Student Answer:", ln=True)
            student_img = Image.open(io.BytesIO(student_answer_image.getvalue()))
            student_img_path = output_dir / "temp_student.jpg"
            student_img.save(student_img_path)
            temp_pdf.image(str(student_img_path), x=10, y=30, w=190)
            
            # 添加评分标准图片
            temp_pdf.add_page()
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "Marking Scheme:", ln=True)
            marking_img = Image.open(io.BytesIO(marking_scheme_image.getvalue()))
            marking_img_path = output_dir / "temp_marking.jpg"
            marking_img.save(marking_img_path)
            temp_pdf.image(str(marking_img_path), x=10, y=30, w=190)
            
            # 添加API批改结果
            temp_pdf.add_page()
            temp_pdf.set_font("Arial", 'B', 14)
            temp_pdf.cell(0, 10, "AI Correction Result:", ln=True)
            temp_pdf.set_font("Arial", '', 12)
            temp_pdf.multi_cell(0, 10, api_result)
            
            # 保存临时PDF
            temp_path = output_dir / "temp_annotations.pdf"
            temp_pdf.output(str(temp_path))
            
            # 清理临时图片文件
            for temp_img in [question_img_path, student_img_path, marking_img_path]:
                if temp_img.exists():
                    temp_img.unlink()
            
            # 生成输出文件名
            output_filename = f"correction_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = output_dir / output_filename
            
            # 重命名临时PDF为最终输出文件
            temp_path.rename(output_path)
            
            return True, str(output_path)

        except Exception as e:
            error_msg = f"Error during PDF merging: {str(e)}"
            # 清理临时文件
            for temp_file in [question_img_path, student_img_path, marking_img_path, temp_path]:
                if 'temp_file' in locals() and temp_file.exists():
                    temp_file.unlink()
            return False, error_msg

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
            question_image,
            student_answer_image,
            marking_scheme_image,
            api_result,
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