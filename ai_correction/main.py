import streamlit as st
import os
import json
import hashlib
from datetime import datetime
import time
import logging
from pathlib import Path
# from functions.api_correcting.pdf_merger import ImageToPDFConverter
from functions.api_correcting.calling_api import call_api, correction_with_image_marking_scheme
import re

# Constants
MAX_FILE_SIZE = 5 * 1024  # 5MB in KB
UPLOAD_DIR = Path("uploads")
DATA_FILE = Path("user_data.json")

# Create necessary directories
UPLOAD_DIR.mkdir(exist_ok=True)

# Test accounts for development
TEST_ACCOUNTS = {
    "test_user_1": {"password": "password1"},
    "test_user_2": {"password": "password2"}
}

try:
    from fpdf import FPDF
except ImportError:
    import subprocess
    import sys
    logging.info("Installing required package: fpdf")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf", "Pillow"])
    from fpdf import FPDF

def setup_logger(log_dir="logs"):
    if not os.path.exists(log_dir): 
        os.makedirs(log_dir) 
    log_file = os.path.join(log_dir, "app_debug.log") 
    logging.basicConfig( 
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s @ %(module)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

# Initialize logger
setup_logger()
logging.info("Starting") 

# Initialize storage structure
if not os.path.exists(DATA_FILE): 
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def read_user_data():
    """从JSON文件读取用户数据，或返回默认数据"""
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            
            # 确保测试账户存在并使用哈希密码
            for test_user, details in TEST_ACCOUNTS.items():
                if test_user not in data:
                    data[test_user] = {
                        "password": details["password"],  # 对于测试账户，保持原始密码
                        "email": f"{test_user}@example.com",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "records": []
                    }
            
            return data
    except FileNotFoundError:
        # 返回带有测试账户的默认数据
        default_data = {}
        for test_user, details in TEST_ACCOUNTS.items():
            default_data[test_user] = {
                "password": details["password"],
                "email": f"{test_user}@example.com",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "records": []
            }
        return default_data

def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Replace the create_download_buttons function with a unified approach
def create_download_options(content, prefix="correction_result"):
    """Create unified download options for content in TXT, PDF and Word formats"""
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create the dropdown menu for download options
    download_option = st.selectbox(
        "Download Format",
        ["Select format...", "Text file (.txt)", "PDF Document (.pdf)", "Word Document (.docx)"],
        key=f"download_format_{prefix}"
    )
    
    # Handle download based on selected option
    if download_option == "Text file (.txt)":
        st.download_button(
            label="Download result",
            data=content.encode('utf-8'),
            file_name=f"{prefix}_{current_time}.txt",
            mime="text/plain",
            key=f"download_txt_{current_time}"
        )
    
    elif download_option == "PDF Document (.pdf)":
        try:
            # Import PDFMerger and create instance
            from functions.api_correcting.pdf_merger import PDFMerger
            pdf_merger = PDFMerger(UPLOAD_DIR)
            
            # Generate PDF and provide download button
            pdf_filename = f"{prefix}_{current_time}.pdf"
            output_path = UPLOAD_DIR / st.session_state.current_user / pdf_filename
            
            # Empty dictionary for files to include (no files by default)
            files_to_include = {}
            success, pdf_path = pdf_merger.merge_pdfs(
                files_to_include,
                content,
                "AI Correction Results",
                output_path
            )
            
            if success and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_bytes = pdf_file.read()
                    st.download_button(
                        label="Download result",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        key=f"download_pdf_{current_time}"
                    )
                # Clean up temporary file
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            else:
                st.error("PDF generation failed. Try downloading as text.")
        except Exception as e:
            st.error(f"PDF generation failed: {str(e)}")
            logging.error(f"PDF generation error: {str(e)}")
    
    elif download_option == "Word Document (.docx)":
        try:
            # Import python-docx for Word document creation
            try:
                import docx
            except ImportError:
                import subprocess
                import sys
                logging.info("Installing required package: python-docx")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
                import docx
            
            # Create a simple Word document with the content
            doc = docx.Document()
            doc.add_heading('AI Correction Results', 0)
            
            # Split the content by lines and add each paragraph
            for paragraph in content.split('\n'):
                if paragraph.strip():  # Skip empty lines
                    doc.add_paragraph(paragraph)
            
            # Save the document to a temporary file
            docx_filename = f"{prefix}_{current_time}.docx"
            temp_path = UPLOAD_DIR / st.session_state.current_user / docx_filename
            doc.save(str(temp_path))
            
            # Provide download button
            with open(temp_path, 'rb') as docx_file:
                docx_bytes = docx_file.read()
                st.download_button(
                    label="Download result",
                    data=docx_bytes,
                    file_name=docx_filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_docx_{current_time}"
                )
            
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            st.error(f"Word document generation failed: {str(e)}")
            logging.error(f"Word document generation error: {str(e)}")

def file_management_page():
    """File management and history page"""
    st.title("📁 File Management Center")
    
    user_data = read_user_data()
    # Filter out records with empty content
    user_records = [
        record for record in user_data.get(st.session_state.current_user, {}).get('records', [])
        if record.get('content') and record['content'].strip()
    ]
    
    if not user_records:
        st.info("No correction records found.")
        return

    st.subheader("📋 Correction History")
    
    for idx, record in enumerate(reversed(user_records)):
        # 获取时间戳，如果不存在则使用默认值
        timestamp = record.get('timestamp', 'No timestamp')
        
        with st.expander(f"Record {len(user_records)-idx}: {timestamp}", expanded=False):
            # 显示上传的图片
            if record.get('files'):
                st.write("📎 Uploaded Files:")
                cols = st.columns(3)
                for i, (file_type, file_info) in enumerate(record['files'].items()):
                    with cols[i]:
                        if file_info and isinstance(file_info, dict) and 'saved_path' in file_info:
                            if os.path.exists(file_info['saved_path']):
                                st.write(f"{file_type.title()}: {file_info.get('filename', 'Unknown file')}")
                                try:
                                    st.image(file_info['saved_path'], caption=file_type.title())
                                except Exception:
                                    st.write("(File preview not available)")

            # 显示结果内容
            st.write("🔍 Correction Result:")
            content = record.get('content', 'No content available')
            st.write(content)

            # Replace download buttons with unified download options
            create_download_options(content, f"record_{len(user_records)-idx}")

    st.info("Please use the AI Correction module to upload files and process them.")

def ai_correction_page():
    """AI correction management page with enhanced UI"""
    # 设置页面标题和说明，增加视觉吸引力
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
        <div style="font-size: 32px; margin-right: 10px;">🤖</div>
        <div>
            <h1 style="margin: 0; padding: 0; font-size: 1.5em;">AI Correction</h1>
            <p style="color: #666; margin-top: 5px; font-size: 0.9em;">Upload files and get instant AI-powered feedback on student answers</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 添加分隔线提高视觉层次感
    st.markdown('<hr style="margin-bottom: 30px;">', unsafe_allow_html=True)
    
    # 确保用户目录存在
    user_dir = UPLOAD_DIR / st.session_state.current_user
    user_dir.mkdir(exist_ok=True)
    
    # 加载用户数据
    user_data = read_user_data()
    if st.session_state.current_user not in user_data:
        user_data[st.session_state.current_user] = {"records": []}
    
    # 显示文件上传进度指示器
    st.markdown("""
    <div style="background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 30px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
            <div style="font-weight: bold; color: #4a4a4a; font-size: 0.9em;">Step 1: Upload Files</div>
            <div style="font-weight: bold; color: #4a4a4a; font-size: 0.9em;">Step 2: Process</div>
            <div style="font-weight: bold; color: #4a4a4a; font-size: 0.9em;">Step 3: Results</div>
        </div>
        <div style="height: 6px; background-color: #e9ecef; border-radius: 3px; position: relative;">
            <div style="height: 100%; width: 33%; background-color: #5cb85c; border-radius: 3px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 上传区域：三列同一排，添加容器样式提高视觉分离度
    st.markdown('<div style="background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 30px;">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div style="padding: 10px; border-radius: 5px; background-color: #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 1em; font-weight: bold; margin-bottom: 10px; color: #333;">Question</div>', unsafe_allow_html=True)
        question = st.file_uploader("Upload question (optional)", type=["pdf", "jpg", "jpeg", "png"], key="question_file")
        if not question:
            st.markdown('<div style="color: #666; font-size: 0.9em; margin-top: 10px;">Helps provide context for the correction</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div style="padding: 10px; border-radius: 5px; background-color: #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 1em; font-weight: bold; margin-bottom: 10px; color: #333;">Student Answer</div>', unsafe_allow_html=True)
        student_answer = st.file_uploader("Upload student answer", type=["pdf", "jpg", "jpeg", "png"], key="student_answer_file")
        if not student_answer:
            st.markdown('<div style="color: #ff4b4b; font-size: 0.9em; margin-top: 10px; font-weight: bold;">Required file for correction</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div style="padding: 10px; border-radius: 5px; background-color: #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 1em; font-weight: bold; margin-bottom: 10px; color: #333;">Marking Scheme</div>', unsafe_allow_html=True)
        marking_scheme = st.file_uploader("Upload marking scheme (optional)", type=["pdf", "jpg", "jpeg", "png", "json"], key="marking_scheme_file")
        if not marking_scheme:
            st.markdown('<div style="color: #666; font-size: 0.9em; margin-top: 10px;">Improves accuracy of grading</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 添加批改严格程度选择
    st.markdown('<div style="padding: 10px; border-radius: 5px; background-color: #ffffff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 1em; font-weight: bold; margin-bottom: 10px; color: #333;">Correction Settings</div>', unsafe_allow_html=True)
    
    # 添加文件格式提示
    st.markdown("""
    <div style="background-color: #f8f9fb; padding: 10px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #4b8bf4;">
        <h4 style="margin-top: 0;">File Requirements:</h4>
        <ul style="margin-bottom: 0;">
            <li>Supported formats: JPEG, PNG, PDF</li>
            <li>Maximum file size: 5MB per file</li>
            <li>Images should be clear and readable</li>
            <li>Student answer file is required</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 严格程度选择器
    strictness_options = {
        "宽松": "Lenient - Focus on major concepts, be forgiving of minor errors",
        "中等": "Moderate - Balance between strictness and leniency (Default)",
        "严格": "Strict - Rigorous grading with detailed error analysis"
    }
    strictness_level = st.select_slider(
        "Grading Strictness",
        options=list(strictness_options.keys()),
        value="中等",
        format_func=lambda x: strictness_options[x]
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 提交按钮区域，增加醒目程度
    st.markdown('<div style="display: flex; justify-content: center; margin: 20px 0 30px 0;">', unsafe_allow_html=True)
    process_button = st.button("📝 Process Correction", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 检查是否有文件提交且点击了提交按钮
    if process_button:
        if not student_answer:
            st.error("⚠️ Student answer file is required for correction.")
            return
        else:
            # 更新处理指示器
            st.markdown("""
            <div style="background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 30px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                    <div style="font-weight: bold; color: #4a4a4a; font-size: 0.9em;">Step 1: Upload Files ✓</div>
                    <div style="font-weight: bold; color: #5cb85c; font-size: 0.9em;">Step 2: Processing...</div>
                    <div style="font-weight: bold; color: #4a4a4a; font-size: 0.9em;">Step 3: Results</div>
                </div>
                <div style="height: 6px; background-color: #e9ecef; border-radius: 3px; position: relative;">
                    <div style="height: 100%; width: 66%; background-color: #5cb85c; border-radius: 3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 显示处理中的消息和动画
            with st.spinner("AI analyzing student answer. This may take a moment..."):
                # 保存上传的文件（如果存在）
                user_files = {}
                if question:
                    question_path = save_uploaded_file(user_dir, question, "question", user_data)
                    user_files["question"] = {"filename": question.name, "saved_path": str(question_path)}
                
                if student_answer:
                    student_answer_path = save_uploaded_file(user_dir, student_answer, "student_answer", user_data)
                    user_files["student_answer"] = {"filename": student_answer.name, "saved_path": str(student_answer_path)}
                
                if marking_scheme:
                    marking_scheme_path = save_uploaded_file(user_dir, marking_scheme, "marking_scheme", user_data)
                    user_files["marking_scheme"] = {"filename": marking_scheme.name, "saved_path": str(marking_scheme_path)}
                
                try:
                    # 确保至少有学生答案文件
                    if not student_answer:
                        st.error("⚠️ Student answer file is required for correction.")
                        return
                    
                    # 验证文件是否成功读取
                    try:
                        # 尝试读取文件内容验证文件完整性
                        student_answer_contents = student_answer.read()
                        student_answer.seek(0)  # 重置文件指针以便后续使用
                        
                        if not student_answer_contents:
                            st.error("⚠️ Student answer file appears to be empty. Please check that the file contains actual content and try again.")
                            logging.error(f"Empty file uploaded: {student_answer.name}")
                            return
                            
                        logging.info(f"Successfully validated student answer file: {student_answer.name}, size: {len(student_answer_contents)} bytes")
                    except Exception as file_error:
                        st.error(f"⚠️ Error reading student answer file: {str(file_error)}")
                        logging.error(f"File validation error: {str(file_error)}")
                        return
                        
                    # 创建图像文件列表，过滤掉None值
                    image_files = []
                    if question:
                        image_files.append(question)
                        logging.info(f"Added question file: {question.name}")
                    if student_answer:
                        image_files.append(student_answer)
                        logging.info(f"Added student answer file: {student_answer.name}")
                    if marking_scheme:
                        image_files.append(marking_scheme)
                        logging.info(f"Added marking scheme file: {marking_scheme.name}")
                    
                    logging.info(f"Preparing to call API with {len(image_files)} files and strictness level: {strictness_level}")
                        
                    # 使用展开运算符传递文件列表作为位置参数
                    api_result = correction_with_image_marking_scheme(
                        *image_files, 
                        strictness_level=strictness_level
                    )
                    
                    if api_result and isinstance(api_result, str):
                        # 保存结果到会话状态
                        st.session_state.correction_success = True
                        st.session_state.correction_result = api_result
                        
                        # 保存结果到用户记录
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        correction_record = {
                            "timestamp": timestamp,
                            "content": api_result,
                            "files": user_files
                        }
                        
                        user_data[st.session_state.current_user]["records"].append(correction_record)
                        save_user_data(user_data)
                        
                        # 更新进度指示器到第3步
                        st.markdown("""
                        <div style="background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 30px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                                <div style="font-weight: bold; color: #4a4a4a; font-size: 0.9em;">Step 1: Upload Files ✓</div>
                                <div style="font-weight: bold; color: #4a4a4a; font-size: 0.9em;">Step 2: Process ✓</div>
                                <div style="font-weight: bold; color: #5cb85c; font-size: 0.9em;">Step 3: Results Ready</div>
                            </div>
                            <div style="height: 6px; background-color: #e9ecef; border-radius: 3px; position: relative;">
                                <div style="height: 100%; width: 100%; background-color: #5cb85c; border-radius: 3px;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 显示成功消息
                        st.success("✅ Correction processed successfully!")
                    else:
                        st.error("❌ Failed to process correction. API returned an invalid result.")
                        st.session_state.correction_success = False
                except Exception as e:
                    error_message = str(e)
                    st.error(f"❌ Error processing correction: {error_message}")
                    
                    # 针对常见错误提供更具体的帮助信息
                    if "No module named" in error_message:
                        st.info("Missing required module. Attempting to install...")
                        try:
                            import subprocess
                            import sys
                            if "PyPDF2" in error_message:
                                subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
                                st.success("Required module installed. Please try uploading files again.")
                            elif "Pillow" in error_message:
                                subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
                                st.success("Required module installed. Please try uploading files again.")
                        except Exception as install_error:
                            st.error(f"Failed to install module: {str(install_error)}")
                    elif "timeout" in error_message.lower() or "connection" in error_message.lower():
                        st.info("Failed to connect to API server. Please check your network connection and try again later.")
                    elif "api key" in error_message.lower():
                        st.info("API key issue. Please contact administrator to check API settings.")
                    elif "'NoneType' object has no attribute" in error_message:
                        st.info("There was an issue processing one of the uploaded files. Please ensure your files are valid images or PDFs and try again.")
                        logging.error(f"File processing error: Likely caused by an invalid file upload or format issue.")
                    elif "Failed to read uploaded file" in error_message:
                        st.info("Unable to read one of the uploaded files. Please ensure your files are not corrupted and try uploading again.")
                        logging.error(f"File reading error: {error_message}")
                    elif "Unsupported image source type" in error_message:
                        st.info("One of your files has an unsupported format. Please use JPG, PNG, or PDF files only.")
                        logging.error(f"Unsupported file type error: {error_message}")
                    elif "批改失败" in error_message:
                        # 这是API内部错误，提供更友好的错误消息
                        st.info("The AI correction service encountered an error. This might be due to temporarily high load or issues with the file format.")
                        logging.error(f"API correction error: {error_message}")
                        
                    logging.error(f"Correction processing error: {error_message}")
                    st.session_state.correction_success = False
    
    # 显示结果区域
    if hasattr(st.session_state, 'correction_success') and st.session_state.correction_success:
        st.markdown('<div style="background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 30px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 1.1em; font-weight: bold; color: #333; margin-bottom: 15px;">Correction Results</div>', unsafe_allow_html=True)
        
        # 增强结果显示区域
        st.markdown('<div style="background-color: white; border-radius: 5px; padding: 20px; border-left: 5px solid #5cb85c; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
        
        # 优化结果的显示方式，替换纯文本为格式化内容
        result_text = st.session_state.correction_result
        
        # 首先处理主要的标题格式
        result_text = re.sub(r'# (.*?)(\n|$)', r'<div style="font-weight: bold; font-size: 1.1em; color: #333; margin: 10px 0 5px 0; border-bottom: 1px solid #eee; padding-bottom: 5px;">\1</div>', result_text)
        result_text = re.sub(r'## (.*?)(\n|$)', r'<div style="font-weight: bold; font-size: 1em; color: #444; margin: 8px 0 4px 0;">\1</div>', result_text)
        result_text = re.sub(r'### (.*?)(\n|$)', r'<div style="font-weight: bold; font-size: 0.95em; color: #555; margin: 6px 0 3px 0;">\1</div>', result_text)
        
        # 处理其他特定标题格式
        result_text = re.sub(r'学生答案批改如下:', r'<div style="font-weight: bold; font-size: 1em; color: #333;">学生答案批改如下:</div>', result_text)
        
        # 处理分数显示
        result_text = re.sub(r'总分：(\d+)/(\d+)', r'<div style="font-size: 0.95em; margin: 5px 0;">总分：<span style="font-weight: bold; color: #5cb85c;">\1</span>/\2</div>', result_text)
        result_text = re.sub(r'(\d+)\s*\([Ii]\)', r'<div style="font-size: 1em; font-weight: bold; color: #5cb85c; margin: 8px 0;">\1 分</div>', result_text)
        
        # 处理步骤评分
        result_text = re.sub(r'(\d+)\. 第\d+步：(.*?) - (\d+)/(\d+)', r'<div style="font-size: 0.95em; margin: 10px 0 5px 0;"><span style="font-weight: bold;">\1. 第\1步：\2</span> - <span style="color: #5cb85c; font-weight: bold;">\3</span>/\4</div>', result_text)
        
        # 处理正确和错误点
        result_text = re.sub(r'- ✓ 正确点：(.*?)(\n|$)', r'<div style="color: #5cb85c; margin-left: 20px; font-size: 0.9em;">✓ 正确点：\1</div>', result_text)
        result_text = re.sub(r'- ✗ 错误点：(.*?)(\n|$)', r'<div style="color: #d9534f; margin-left: 20px; font-size: 0.9em;">✗ 错误点：\1</div>', result_text)
        result_text = re.sub(r'- 扣分原因：(.*?)(\n|$)', r'<div style="color: #777; margin-left: 20px; font-size: 0.9em;">🔍 扣分原因：\1</div>', result_text)
        
        # 科目和题型信息
        result_text = re.sub(r'- 科目：(.*?)(\n|$)', r'<div style="font-size: 0.9em; margin: 3px 0;">📚 科目：<span style="color: #333;">\1</span></div>', result_text)
        result_text = re.sub(r'- 题目类型：(.*?)(\n|$)', r'<div style="font-size: 0.9em; margin: 3px 0;">📝 题目类型：<span style="color: #333;">\1</span></div>', result_text)
        
        # 处理一般列表项
        lines = result_text.split('\n')
        formatted_lines = []
        for line in lines:
            # 跳过已经处理过的行
            if '<div' in line:
                formatted_lines.append(line)
                continue
                
            # 处理列表项
            if line.strip().startswith('-') or line.strip().startswith('•'):
                line = f'<div style="margin-left: 15px; font-size: 0.9em;">{line}</div>'
            # 处理缩进的数学公式
            elif line.strip().startswith('∴') or line.strip().startswith('∵'):
                line = f'<div style="margin-left: 15px; font-family: monospace; font-size: 0.9em;">{line}</div>'
            # 处理普通文本
            elif line.strip():
                line = f'<div style="font-size: 0.9em; line-height: 1.4; margin: 3px 0;">{line}</div>'
            else:
                line = '<div style="height: 8px;"></div>'  # 空行
            formatted_lines.append(line)
        
        result_text = ''.join(formatted_lines)
        
        # 应用一致的基础字体大小和行高
        result_text = f'<div style="font-size: 14px; line-height: 1.4;">{result_text}</div>'
        
        st.markdown(result_text, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 提供下载选项
        st.markdown('<div style="font-size: 1em; font-weight: bold; color: #333; margin: 20px 0 15px 0;">Download Options</div>', unsafe_allow_html=True)
        
        # 使用统一的下载选项函数
        create_download_options(st.session_state.correction_result)
        
        # 添加清除结果的按钮，更直观友好
        st.markdown('<div style="display: flex; justify-content: center; margin-top: 20px;">', unsafe_allow_html=True)
        if st.session_state.correction_success:
            if st.button("🔄 Start New Correction", use_container_width=True):
                st.session_state.correction_success = False
                st.session_state.correction_result = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # 关闭结果区域容器

    # 添加页脚
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; color: #666; font-size: 0.8em;">
        AI Guru Correction System • Powered by advanced AI • © 2025
    </div>
    """, unsafe_allow_html=True)

# 新增辅助函数用于保存上传的文件
def save_uploaded_file(user_dir, uploaded_file, file_type, user_data):
    """
    保存上传的文件并更新用户记录
    
    参数:
    user_dir: Path对象，用户目录路径
    uploaded_file: UploadedFile对象，上传的文件
    file_type: str，文件类型
    user_data: dict，用户数据字典
    
    返回:
    Path对象，保存的文件路径
    """
    file_path = user_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 更新用户记录
    file_size = uploaded_file.size / 1024
    record = {
        "filename": uploaded_file.name,
        "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_size": round(file_size, 2),
        "file_type": file_type,
        "processing_result": "Uploaded"
    }
    
    if st.session_state.current_user in user_data:
        user_data[st.session_state.current_user]["records"].append(record)
        save_user_data(user_data)
    
    return file_path

# 添加密码哈希函数
def hash_password(password):
    """对密码进行安全哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()

# 修改主函数添加注册功能
def main():
    # 初始化会话状态
    if 'logged_in' not in st.session_state:
        st.session_state.update({
            'logged_in': False,
            'current_user': None,
            'page': 'main_menu',
            'show_register': False  # 添加新状态变量控制注册表单显示
        })

    # 侧边栏导航（只在登录后显示）
    if st.session_state.logged_in:
        with st.sidebar:
            st.title("🎓 AI Guru")
            st.write(f"Welcome, {st.session_state.current_user}!")
            
            # 导航菜单
            st.subheader("📍 Navigation")
            menu_options = {
                "main_menu": "🏠 Main Menu",
                "file_management": "📁 File Management",
                "ai_correction": "🤖 AI Correction",
            }
            
            selected_page = st.radio("Go to:", list(menu_options.values()))
            st.session_state.page = list(menu_options.keys())[list(menu_options.values()).index(selected_page)]
            
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.current_user = None
                st.session_state.page = "main_menu"
                st.rerun()

    # 登录和注册页面
    if not st.session_state.logged_in:
        st.title("🔐 User Authentication")
        
        # 切换登录/注册按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login", use_container_width=True, 
                         type="primary" if not st.session_state.show_register else "secondary"):
                st.session_state.show_register = False
        with col2:
            if st.button("Register", use_container_width=True,
                         type="primary" if st.session_state.show_register else "secondary"):
                st.session_state.show_register = True
        
        # 根据状态显示登录或注册表单
        if st.session_state.show_register:
            # 注册表单
            with st.form("register_form"):
                st.subheader("📝 Create New Account")
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                email = st.text_input("Email (optional)")
                
                register_submitted = st.form_submit_button("Register")
                
                if register_submitted:
                    # 进行表单验证
                    if not new_username or not new_password:
                        st.error("Username and password are required.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        # 检查用户名是否已存在
                        user_data = read_user_data()
                        if new_username in user_data:
                            st.error("Username already exists. Please choose another one.")
                        else:
                            # 创建新用户
                            user_data[new_username] = {
                                "password": hash_password(new_password),
                                "email": email,
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "records": []
                            }
                            save_user_data(user_data)
                            
                            # 提示成功并自动设置为登录状态
                            st.success("Registration successful! You can now log in.")
                            st.session_state.show_register = False
                            st.rerun()
        else:
            # 登录表单
            with st.form("login_form"):
                st.subheader("👤 Login to Your Account")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Login")
                
                if login_submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        # 检查测试账户
                        if username in TEST_ACCOUNTS and TEST_ACCOUNTS[username]['password'] == password:
                            st.session_state.logged_in = True
                            st.session_state.current_user = username
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            # 检查注册用户
                            user_data = read_user_data()
                            if username in user_data and user_data[username].get('password') == hash_password(password):
                                st.session_state.logged_in = True
                                st.session_state.current_user = username
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error("Invalid username or password.")
        
        # 添加一个忘记密码的链接（可以在将来实现）
        st.markdown("---")
        st.markdown("<div style='text-align: center'>Forgot your password? Contact administrator.</div>", unsafe_allow_html=True)
        return

    # 页面路由
    if st.session_state.page == "file_management":
        file_management_page()
    elif st.session_state.page == "ai_correction":
        ai_correction_page()
    else:  # main menu
        st.title("🏠 Main Menu")
        st.write("Welcome to AI Guru! Select an option from the sidebar to get started.")
        
        # 显示使用统计
        user_data = read_user_data()
        user_records = user_data.get(st.session_state.current_user, {}).get('records', [])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Files", len(user_records))
        correction_results = [r for r in user_records if r.get("file_type") == "correction_result"]
        col2.metric("Completed Corrections", len(correction_results))
        pdf_files = [r for r in user_records if r.get("file_type") in ["pdf", "annotated_pdf"]]
        col3.metric("PDF Files", len(pdf_files))

if __name__ == "__main__":
    main()