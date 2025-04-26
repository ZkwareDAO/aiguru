import streamlit as st
import os
import json
import hashlib
from datetime import datetime
import time
import logging
from pathlib import Path
from functions.pdf_merger_leo import ImageToPDFConverter
from functions.api_correcting.calling_api import call_api

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
    """Read user data from JSON file or return default data"""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default data with test accounts
        return {
            "test_user_1": {
                "password": "password1",
                "records": []
            },
            "test_user_2": {
                "password": "password2",
                "records": []
            }
        }

def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def file_management_page():
    """File management and history page"""
    st.title("📁 File Management Center")
    
    # Add history panel at the top of the file management page
    st.header("🕒 Recent History")
    user_data = read_user_data()
    user_records = user_data.get(st.session_state.current_user, {}).get('records', [])
    
    if user_records:
        for record in user_records[-3:]:  # Show last 3 records
            with st.container():
                st.caption(f"📄 {record['filename']}")
                st.markdown(f"🗓️ {record['upload_time']}  📏 {record['file_size']}KB")
                st.progress(float(record.get('progress', 0)))
                st.divider()
    else:
        st.info("No upload history available")
    
    st.info("Please use the AI Correction module to upload files and process them.")

def ai_correction_page():
    """AI correction management page with integrated file list"""
    st.title("🤖 AI Correction")
    
    # 创建页面选项卡
    tab1, tab2, tab3 = st.tabs(["AI Correction", "File List", "Image to PDF"])
    
    # 确保用户目录存在
    user_dir = UPLOAD_DIR / st.session_state.current_user
    user_dir.mkdir(exist_ok=True)
    
    # 加载用户数据
    user_data = read_user_data()
    if st.session_state.current_user not in user_data:
        user_data[st.session_state.current_user] = {"records": []}
    
    # Tab 1: AI Correction
    with tab1:
        # 上传区域：三列同一排
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Question")
            question = st.file_uploader("Upload question (optional)", type=["pdf", "jpg", "jpeg", "png"], key="question_file")
        with col2:
            st.subheader("Student Answer")
            student_answer = st.file_uploader("Upload student answer", type=["pdf", "jpg", "jpeg", "png"], key="student_answer_file")
        with col3:
            st.subheader("Marking Scheme")
            marking_scheme = st.file_uploader("Upload marking scheme (optional)", type=["pdf", "jpg", "jpeg", "png", "json"], key="marking_scheme_file")

        # 添加分隔线
        st.markdown("---")

        # session state用于保存结果
        if 'correction_result' not in st.session_state:
            st.session_state.correction_result = None
        if 'correction_success' not in st.session_state:
            st.session_state.correction_success = False
        if 'correction_history' not in st.session_state:
            st.session_state.correction_history = []

        # AI批改处理逻辑
        if student_answer is not None:
            # 保存上传的文件
            file_size = student_answer.size / 1024  # Convert to KB
            
            if file_size > MAX_FILE_SIZE:
                st.error(f"File size exceeds maximum limit of {MAX_FILE_SIZE}KB")
            else:
                # 保存学生答案文件
                student_file = save_uploaded_file(user_dir, student_answer, "student_answer", user_data)
                
                # 保存题目文件（如果有）
                question_file = None
                if question is not None:
                    question_file = save_uploaded_file(user_dir, question, "question", user_data)
                
                # 保存评分标准文件（如果有）
                marking_file = None
                if marking_scheme is not None:
                    marking_file = save_uploaded_file(user_dir, marking_scheme, "marking_scheme", user_data)
                
                # 处理文件开始按钮
                if st.button("Start AI Correction"):
                    st.info("Processing files with AI correction...")
                    
                    progress_bar = st.progress(0)
                    for i in range(10):
                        # 模拟处理过程
                        time.sleep(0.1)
                        progress_bar.progress((i+1)/10)
                    
                    try:
                        # 准备API调用的文本内容
                        prompt_text = "请批改以下学生答案"
                        
                        # 准备文件内容
                        api_inputs = [prompt_text]  # 第一个参数始终是文本提示
                        
                        # 添加题目文件内容（如果有）
                        if question_file:
                            api_inputs.append(str(question_file))
                        
                        # 添加学生答案文件内容（必需）
                        api_inputs.append(str(student_file))
                        
                        # 添加评分标准文件内容（如果有）
                        if marking_file:
                            api_inputs.append(str(marking_file))
                        
                        # 调用API处理函数
                        result = call_api(*api_inputs)
                        
                        if result:
                            st.session_state.correction_success = True
                            st.session_state.correction_result = result
                            
                            # 生成唯一的结果文件名
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            raw_filename = f"correction_result_{timestamp}.txt"
                            raw_file = user_dir / raw_filename
                            
                            # 保存结果文件
                            with open(raw_file, "w", encoding="utf-8") as f:
                                f.write(str(result))
                            
                            # 创建结果记录
                            result_record = {
                                "filename": raw_filename,
                                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "file_size": round(os.path.getsize(raw_file) / 1024, 2),
                                "file_type": "correction_result",
                                "processing_result": "Completed",
                                "content": str(result)  # 保存结果内容
                            }
                            
                            # 更新session state中的历史记录
                            st.session_state.correction_history.append(result_record)
                            
                            # 更新用户数据
                            if st.session_state.current_user in user_data:
                                user_data[st.session_state.current_user]["records"].append(result_record)
                                save_user_data(user_data)
                            
                    except Exception as e:
                        st.error(f"Error during correction: {str(e)}")
                        st.text("Full error details:")
                        st.exception(e)
                        logging.error(f"AI correction error: {str(e)}")

        # 只在批改结果出来后显示预览
        if st.session_state.correction_success and st.session_state.correction_result:
            st.success("AI Correction completed!")

            # 预览区
            st.markdown("### Uploaded Files Preview")
            preview_cols = st.columns(3)
            # 题目预览
            if question:
                with preview_cols[0]:
                    st.image(question, caption="Question Preview", use_column_width=True)
            # 学生答案预览
            if student_answer:
                with preview_cols[1]:
                    st.image(student_answer, caption="Student Answer Preview", use_column_width=True)
            # 评分标准预览
            if marking_scheme and marking_scheme.type != "application/json":
                with preview_cols[2]:
                    st.image(marking_scheme, caption="Marking Scheme Preview", use_column_width=True)
            elif marking_scheme:
                with preview_cols[2]:
                    st.info("JSON Marking Scheme loaded")
                    try:
                        marking_content = marking_scheme.read().decode('utf-8')
                        with st.expander("View Marking Scheme Content"):
                            st.json(json.loads(marking_content))
                    except Exception as e:
                        st.warning(f"Unable to preview JSON content: {str(e)}")

            # 显示批改结果
            st.markdown("### AI Response")
            st.markdown(str(st.session_state.correction_result))
            
            # 提供下载按钮
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="Download Result",
                data=str(st.session_state.correction_result),
                file_name=f"correction_result_{timestamp}.txt",
                mime="text/plain",
                key=f"download_result_{timestamp}"
            )
            
            # 显示历史结果
            if st.session_state.correction_history:
                with st.expander("View Correction History"):
                    for idx, record in enumerate(reversed(st.session_state.correction_history)):
                        st.markdown(f"### Result {idx + 1}")
                        st.markdown(f"Time: {record['upload_time']}")
                        st.markdown(record['content'])
                        st.download_button(
                            label=f"Download Result {idx + 1}",
                            data=record['content'],
                            file_name=record['filename'],
                            mime="text/plain",
                            key=f"download_history_{idx}"
                        )
                        st.markdown("---")

        # 添加清除结果的按钮
        if st.session_state.correction_success:
            if st.button("Clear Results"):
                st.session_state.correction_success = False
                st.session_state.correction_result = None
                st.rerun()
    
    # Tab 2: File List
    with tab2:
        user_records = user_data.get(st.session_state.current_user, {}).get('records', [])
        
        # 分类显示文件
        file_categories = {
            "题目文件": "question",
            "评分标准文件": "marking_scheme",
            "学生作答文件": "student_answer",
            "批改结果": "correction_result",
            "批注文件": "annotated_pdf"
        }
        
        for title, file_type in file_categories.items():
            st.write(f"### {title}")
            filtered_files = [r for r in user_records if r.get("file_type") == file_type]
            
            if filtered_files:
                for record in filtered_files:
                    cols = st.columns([5, 2, 2, 2])
                    cols[0].write(record["filename"])
                    cols[1].metric("Size", f"{record['file_size']}KB")
                    cols[2].write(record["upload_time"])
                    
                    # 处理文件操作
                    file_path = user_dir / record["filename"]
                    if os.path.exists(file_path):
                        # 提供文件删除功能
                        if cols[3].button("删除", key=f"del_{file_type}_{record['filename']}_{id(record)}"):
                            try:
                                os.remove(file_path)
                                # 更新记录
                                updated_records = [r for r in user_records if r['filename'] != record['filename']]
                                user_data[st.session_state.current_user]['records'] = updated_records
                                save_user_data(user_data)
                                st.success(f"文件 {record['filename']} 已删除")
                                st.rerun()
                            except Exception as e:
                                st.error(f"删除文件时出错: {str(e)}")
                        
                        # 为可下载文件提供下载按钮
                        if file_type in ["correction_result", "annotated_pdf"]:
                            file_ext = record["filename"].split(".")[-1].lower()
                            mime_type = {
                                "json": "application/json",
                                "pdf": "application/pdf",
                                "txt": "text/plain"
                            }.get(file_ext, "application/octet-stream")
                            
                            # Modified file reading code with proper encoding handling
                            if file_ext in ["json", "txt"]:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    download_data = f.read()
                            else:
                                with open(file_path, "rb") as f:
                                    download_data = f.read()
                            
                            # 为下载按钮创建一个新的列
                            st.download_button(
                                label="下载",
                                data=download_data,
                                file_name=record["filename"],
                                mime=mime_type,
                                key=f"dl_{file_type}_{record['filename']}_{id(record)}"
                            )
                    else:
                        cols[3].warning("文件不存在")
            else:
                st.info(f"暂无{title}")
    
    # Tab 3: Image to PDF (简化版)
    with tab3:
        st.header("Image to PDF Converter")
        
        # 实例化转换器
        converter = ImageToPDFConverter(UPLOAD_DIR)
        
        # 图片上传区域
        uploaded_images = st.file_uploader(
            "Upload images to convert to PDF", 
            type=["jpg", "jpeg", "png"], 
            accept_multiple_files=True,
            key="upload_images_convert"
        )
        
        if uploaded_images:
            # 保存上传的图片
            image_paths = []
            image_records = []
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for img in uploaded_images:
                img_path = user_dir / img.name
                with open(img_path, "wb") as f:
                    f.write(img.getbuffer())
                image_paths.append(str(img_path))
                
                # 添加图片记录
                file_size = img.size / 1024
                image_records.append({
                    "filename": img.name,
                    "upload_time": current_time,
                    "file_size": round(file_size, 2),
                    "file_type": "image",
                    "processing_result": "Uploaded"
                })
            
            # 更新用户记录
            user_data[st.session_state.current_user]["records"].extend(image_records)
            save_user_data(user_data)
            
            # 显示图片预览
            st.subheader(f"Preview ({len(uploaded_images)} images)")
            cols = st.columns(min(3, len(uploaded_images)))
            for i, img in enumerate(uploaded_images[:3]):
                cols[i % 3].image(img, caption=img.name, use_column_width=True)
            
            # 转换选项
            output_filename = st.text_input(
                "PDF Filename (optional)", 
                value=f"converted_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if not output_filename.endswith('.pdf'):
                output_filename += '.pdf'
            
            # 转换按钮
            if st.button("Convert to PDF"):
                with st.spinner("Converting images to PDF..."):
                    try:
                        # 处理输出路径
                        output_path = str(user_dir / output_filename)
                        
                        # 检查文件是否已存在
                        if os.path.exists(output_path):
                            output_filename = f"{os.path.splitext(output_filename)[0]}_{int(time.time())}.pdf"
                            output_path = str(user_dir / output_filename)
                        
                        # 执行转换
                        output_path = converter.convert_multiple_images_to_pdf(image_paths, output_path)
                        
                        # 记录PDF文件
                        pdf_size = os.path.getsize(output_path) / 1024
                        pdf_record = {
                            "filename": os.path.basename(output_path),
                            "upload_time": current_time,
                            "file_size": round(pdf_size, 2),
                            "file_type": "pdf",
                            "processing_result": "Completed"
                        }
                        
                        user_data[st.session_state.current_user]["records"].append(pdf_record)
                        save_user_data(user_data)
                        
                        # 显示成功信息和下载按钮
                        st.success(f"Successfully converted {len(image_paths)} images to PDF!")
                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="Download PDF",
                                data=f.read(),
                                file_name=os.path.basename(output_path),
                                mime="application/pdf"
                            )
                    
                    except Exception as e:
                        st.error(f"Error during conversion: {str(e)}")
                        logging.error(f"Image conversion error: {str(e)}")

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

def main():
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.update({
            'logged_in': False,
            'current_user': None,
            'page': 'main_menu',
            'sub_page': None
        })

    # Sidebar for navigation (only show when logged in)
    if st.session_state.logged_in:
        with st.sidebar:
            st.title("🎓 AI Guru")
            st.write(f"Welcome, {st.session_state.current_user}!")
            
            # Navigation menu (简化菜单选项)
            st.subheader("📍 Navigation")
            menu_options = {
                "main_menu": "🏠 Main Menu",
                "file_management": "📁 File Management",
                "ai_correction": "🤖 AI Correction"
            }
            
            selected_page = st.radio("Go to:", list(menu_options.values()))
            st.session_state.page = list(menu_options.keys())[list(menu_options.values()).index(selected_page)]
            
            # Logout button
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.current_user = None
                st.session_state.page = "main_menu"
                st.rerun()

    # Login page
    if not st.session_state.logged_in:
        st.title("🔐 User Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                # Check test accounts
                if username in TEST_ACCOUNTS:
                    stored_password = TEST_ACCOUNTS[username]['password']
                    if stored_password == password:
                        st.session_state.logged_in = True
                        st.session_state.current_user = username
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid password!")
                else:
                    st.error("User not found!")
        return

    # Protected pages - only accessible when logged in
    if st.session_state.logged_in:
        # 默认进入主页
        if "page" not in st.session_state:
            st.session_state.page = "main_menu"
            
        # 页面导航处理
        if st.session_state.page == "file_management":
            file_management_page()
        elif st.session_state.page == "ai_correction":
            ai_correction_page()
        else:  # 主页显示基本信息
            st.title("🏠 Main Menu")
            st.write("Welcome to AI Guru! Select an option from the sidebar to get started.")
            
            # 显示简单的使用统计
            user_data = read_user_data()
            user_records = user_data.get(st.session_state.current_user, {}).get('records', [])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Files", len(user_records))
            
            correction_results = [r for r in user_records if r.get("file_type") == "correction_result"]
            col2.metric("Completed Corrections", len(correction_results))
            
            pdf_files = [r for r in user_records if r.get("file_type") in ["pdf", "annotated_pdf"]]
            col3.metric("PDF Files", len(pdf_files))
    else:
        st.warning("Please log in to access this page.")
        st.session_state.page = "main_menu"

if __name__ == "__main__":
    main()