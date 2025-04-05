import streamlit as st
import os
import json
import hashlib
from datetime import datetime
import time
import logging
from functions.pdf_annotator import streamlit_pdf_annotator
from functions.api_correcting.calling_api import correction_with_json_marking_scheme, correction_with_image_marking_scheme, correction_without_marking_scheme, generate_marking_scheme

def setup_logger(log_dir="logs"):
    if not os.path.exists(log_dir): 
        os.makedirs(log_dir) 
    log_file = os.path.join(log_dir,  "app_debug.log") 
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

# Configuration
UPLOAD_DIR = "user_uploads"
DATA_FILE = "user_data.json" 
TEST_ACCOUNTS = {
    "test_user_1": "password1",
    "test_user_2": "password2"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Initialize storage structure
if not os.path.exists(UPLOAD_DIR): 
    os.makedirs(UPLOAD_DIR) 
if not os.path.exists(DATA_FILE): 
    with open(DATA_FILE, "w") as f:
        json.dump({},  f)

def read_user_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f) 

def write_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data,  f, indent=2)

def migrate_old_data(user_data):
    """Migrate old data structure to new format (only if needed)"""
    if user_data.get('migrated'): 
        return user_data

    for user in list(user_data.keys()): 
        if isinstance(user_data[user], list):
            user_data[user] = {
                "password": "",  # Empty, force user to change
                "records": user_data[user],
                "migrated": True
            }
    user_data['migrated'] = True  # Mark the entire data as migrated
    return user_data

def account_management():
    """Sidebar account management"""
    with st.sidebar.expander("🔑  Account Management", expanded=True):
        st.subheader("User  Information")
        st.write(f"Current  User: {st.session_state.current_user}") 

        with st.form("Change  Password"):
            new_password = st.text_input("New  Password", type="password")
            if st.form_submit_button("Update  Password"):
                if len(new_password) < 8:
                    st.error("Password  must be at least 8 characters long.")
                else:
                    user_data = read_user_data()
                    user_data[st.session_state.current_user]['password'] = new_password
                    write_user_data(user_data)
                    st.success("Password  updated successfully.")

def history_panel():
    """Sidebar history query"""
    with st.sidebar.expander("🕒  History", expanded=True):
        user_data = read_user_data()
        user_records = user_data.get(st.session_state.current_user,  {}).get('records', [])

        if user_records:
            st.subheader("Recent  Uploads")
            num_records = st.slider("Number  of records to display", 10, len(user_records), 10)
            for record in user_records[-num_records:]:
                st.caption(f"{record['filename']}") 
                st.markdown(f"🗓️  {record['upload_time']}  📏 {record['file_size']}KB")
                st.progress(float(record.get('progress',  0)))
                if st.button(f"Delete  {record['filename']}", key=f"del_{record['filename']}"):
                    if st.confirm(f"Are  you sure you want to delete {record['filename']}?"):
                        user_dir = os.path.join(UPLOAD_DIR,  st.session_state.current_user) 
                        file_path = os.path.join(user_dir,  record["filename"])
                        if os.path.exists(file_path): 
                            os.remove(file_path) 
                        updated_records = [r for r in user_records if r['filename'] != record['filename']]
                        user_data[st.session_state.current_user]['records'] = updated_records
                        write_user_data(user_data)
                        st.rerun() 
        else:
            st.info("No  history found.")



def file_management_page():
    """File upload management page"""
    st.title("📁  File Management Center")
    
    # 添加文件列表按钮
    if st.button("📋 查看文件列表"):
        st.session_state.sub_page = "file_list"
        st.rerun()

    # 使用st.cache_data装饰器缓存文件读取结果
    @st.cache_data(ttl=60)
    def read_cached_user_data():
        return read_user_data()
    
    # 使用st.cache_data装饰器缓存文件处理结果
    # 修改参数名，添加下划线前缀，告诉Streamlit不要哈希这个参数
    @st.cache_data(ttl=300)
    def process_file_with_cache(_file_content, file_type):
        # 模拟文件处理过程
        time.sleep(1)  # 避免过快处理导致的界面卡顿
        return True

    user_dir = os.path.join(UPLOAD_DIR,  st.session_state.current_user) 
    os.makedirs(user_dir,  exist_ok=True)
    
    # 添加题目文件上传功能
    with st.expander("➕  Upload Question File", expanded=True):
        st.info("请上传题目文件，系统将自动识别其中的题目内容")
        uploaded_question_file = st.file_uploader( 
            label="Select a Question file to upload (Max size: 10MB)",
            type=["pdf", "docx", "xlsx", "jpg", "png"],
            key="question_uploader"
        )

        if uploaded_question_file and uploaded_question_file.size <= MAX_FILE_SIZE:
            file_content = uploaded_question_file.getbuffer() 
            file_hash = hashlib.md5(file_content).hexdigest()   # Calculate file hash
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S") 
            filename = f"{timestamp}_{uploaded_question_file.name}" 
            save_path = os.path.join(user_dir,  filename)

            user_data = read_user_data()
            user_entry = user_data.setdefault(st.session_state.current_user,  {
                "password": "",  # Initial password empty
                "records": []
            })

            # Check if the file already exists (based on hash)
            for record in user_entry['records']:
                if record.get("file_hash") == file_hash:
                    st.warning("This file has already been uploaded.")
                    return

            # 使用st.spinner显示文件处理进度
            with st.spinner('正在处理文件...'):
                # 分块写入文件以避免内存占用过大
                chunk_size = 1024 * 1024  # 1MB chunks
                with open(save_path, "wb") as f:
                    for i in range(0, len(file_content), chunk_size):
                        f.write(file_content[i:i + chunk_size])
                        # 更新进度条
                        progress = min(1.0, (i + chunk_size) / len(file_content))
                        st.progress(progress)
                
                # 处理文件
                process_success = process_file_with_cache(file_content, 'question')
                if not process_success:
                    st.error('文件处理失败')
                    return
                
                logging.info("Question File saved and processed")
                st.success('文件处理完成')
            # Add new record
            new_record = {
                "filename": filename,
                "upload_time": timestamp,
                "file_size": uploaded_question_file.size // 1024,
                "file_hash": file_hash,  # Save file hash
                "processing_result": "Completed",
                "progress": 1.0,
                "file_type": "question",
                "file_path": save_path
            }
            user_entry['records'].append(new_record)
            write_user_data(user_data)
            st.success(f"题目文件 {uploaded_question_file.name} 上传成功")

        elif uploaded_question_file:
            st.error("File size exceeds the limit (10MB).")

    with st.expander("➕  Upload New Marking Scheme File", expanded=True):
        st.info("请上传评分标准文件，系统将自动识别其中的评分规则")
        uploaded_marking_scheme_file = st.file_uploader( 
            label="Select a Marking Scheme file to upload (Max size: 10MB)",
            type=["pdf", "docx", "xlsx", "jpg", "png"],
            key="marking_scheme_uploader"
        )

        if uploaded_marking_scheme_file and uploaded_marking_scheme_file.size <= MAX_FILE_SIZE:
            file_content = uploaded_marking_scheme_file.getbuffer() 
            file_hash = hashlib.md5(file_content).hexdigest()   # Calculate file hash
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S") 
            filename = f"{timestamp}_{uploaded_marking_scheme_file.name}" 
            save_path = os.path.join(user_dir,  filename)

            user_data = read_user_data()
            user_entry = user_data.setdefault(st.session_state.current_user,  {
                "password": "",  # Initial password empty
                "records": []
            })

            # Check if the file already exists (based on hash)
            for record in user_entry['records']:
                if record.get("file_hash") == file_hash:
                    st.warning("This file has already been uploaded.")
                    return

            # 使用st.spinner显示文件处理进度
            with st.spinner('正在处理评分标准文件...'):
                # 分块写入文件以避免内存占用过大
                chunk_size = 1024 * 1024  # 1MB chunks
                with open(save_path, "wb") as f:
                    for i in range(0, len(file_content), chunk_size):
                        f.write(file_content[i:i + chunk_size])
                        # 更新进度条
                        progress = min(1.0, (i + chunk_size) / len(file_content))
                        st.progress(progress)
                
                # 处理文件
                process_success = process_file_with_cache(file_content, 'marking_scheme')
                if not process_success:
                    st.error('评分标准文件处理失败')
                    return
                
                logging.info("Marking Scheme File saved and processed")
                st.success('评分标准文件处理完成')

            # Add new record
            new_record = {
                "filename": filename,
                "upload_time": timestamp,
                "file_size": uploaded_marking_scheme_file.size // 1024,
                "file_hash": file_hash,  # Save file hash
                "processing_result": "Completed",
                "progress": 1.0,
                "file_type": "marking_scheme",
                "file_path": save_path
            }
            user_entry['records'].append(new_record)
            write_user_data(user_data)
            st.success(f"评分标准文件 {uploaded_marking_scheme_file.name} 上传成功")

        elif uploaded_marking_scheme_file:
            st.error("File size exceeds the limit (10MB).")

    with st.expander("➕  Upload Student Answer File", expanded=True):
        st.info("请上传学生作答文件，系统将根据评分标准进行自动评分")
        uploaded_answer_file = st.file_uploader( 
            label="Select a Student Answer file to upload (Max size: 10MB)",
            type=["pdf", "docx", "xlsx", "jpg", "png"],
            key="answer_uploader"
        )

        if uploaded_answer_file and uploaded_answer_file.size <= MAX_FILE_SIZE:
            file_content = uploaded_answer_file.getbuffer() 
            file_hash = hashlib.md5(file_content).hexdigest()   # Calculate file hash
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S") 
            filename = f"{timestamp}_{uploaded_answer_file.name}" 
            save_path = os.path.join(user_dir,  filename)

            user_data = read_user_data()
            user_entry = user_data.setdefault(st.session_state.current_user,  {
                "password": "",  # Initial password empty
                "records": []
            })

            # Check if the file already exists (based on hash)
            for record in user_entry['records']:
                if record.get("file_hash") == file_hash:
                    st.warning("This file has already been uploaded.")
                    return

            # 使用st.spinner显示文件处理进度
            with st.spinner('正在处理学生作答文件...'):
                # 分块写入文件以避免内存占用过大
                chunk_size = 1024 * 1024  # 1MB chunks
                with open(save_path, "wb") as f:
                    for i in range(0, len(file_content), chunk_size):
                        f.write(file_content[i:i + chunk_size])
                        # 更新进度条
                        progress = min(1.0, (i + chunk_size) / len(file_content))
                        st.progress(progress)
                
                # 处理文件
                process_success = process_file_with_cache(file_content, 'student_answer')
                if not process_success:
                    st.error('学生作答文件处理失败')
                    return
                
                logging.info("Student Answer File saved and processed")
                st.success('学生作答文件处理完成')

            # Add new record
            new_record = {
                "filename": filename,
                "upload_time": timestamp,
                "file_size": uploaded_answer_file.size // 1024,
                "file_hash": file_hash,  # Save file hash
                "processing_result": "Completed",
                "progress": 1.0,
                "file_type": "student_answer",
                "file_path": save_path
            }
            user_entry['records'].append(new_record)
            write_user_data(user_data)
            st.success(f"学生作答文件 {uploaded_answer_file.name} 上传成功")

        elif uploaded_answer_file:
            st.error("File size exceeds the limit (10MB).")
    
    # PDF标注和评分功能
    with st.expander("📝 PDF标注与评分", expanded=True):
        st.info("请选择需要标注或评分的文件")
        
        user_data = read_user_data()
        user_records = user_data.get(st.session_state.current_user, {}).get('records', [])
        
        # 分类显示文件
        question_files = [r for r in user_records if r.get("file_type") == "question"]
        marking_scheme_files = [r for r in user_records if r.get("file_type") == "marking_scheme"]
        student_answer_files = [r for r in user_records if r.get("file_type") == "student_answer"]
        
        # 选择题目文件
        selected_question = None
        if question_files:
            question_options = ["选择题目文件"] + [r["filename"] for r in question_files]
            selected_question_index = st.selectbox("题目文件", range(len(question_options)), format_func=lambda x: question_options[x])
            if selected_question_index > 0:
                selected_question = question_files[selected_question_index-1]
        else:
            st.warning("请先上传题目文件")
        
        # 选择评分标准文件
        selected_marking_scheme = None
        if marking_scheme_files:
            marking_scheme_options = ["选择评分标准文件"] + [r["filename"] for r in marking_scheme_files]
            selected_marking_scheme_index = st.selectbox("评分标准文件", range(len(marking_scheme_options)), format_func=lambda x: marking_scheme_options[x])
            if selected_marking_scheme_index > 0:
                selected_marking_scheme = marking_scheme_files[selected_marking_scheme_index-1]
        else:
            st.warning("请先上传评分标准文件")
        
        # 选择学生作答文件
        selected_answer = None
        if student_answer_files:
            answer_options = ["选择学生作答文件"] + [r["filename"] for r in student_answer_files]
            selected_answer_index = st.selectbox("学生作答文件", range(len(answer_options)), format_func=lambda x: answer_options[x])
            if selected_answer_index > 0:
                selected_answer = student_answer_files[selected_answer_index-1]
        else:
            st.warning("请先上传学生作答文件")
        
        # 标注功能
        col1, col2 = st.columns(2)
        with col1:
            if st.button("PDF标注") and selected_answer:
                answer_path = os.path.join(user_dir, selected_answer["filename"])
                with open(answer_path, "rb") as f:
                    pdf_file = st.session_state.get("pdf_file", None)
                    if pdf_file is None:
                        st.session_state.pdf_file = f.read()
                    streamlit_pdf_annotator(selected_answer["filename"], user_dir)
        
        # 评分功能
        with col2:
            if st.button("自动评分") and selected_marking_scheme and selected_answer:
                try:
                    marking_scheme_path = os.path.join(user_dir, selected_marking_scheme["filename"])
                    answer_path = os.path.join(user_dir, selected_answer["filename"])
                    
                    # 使用st.spinner显示加载状态
                    with st.spinner('正在进行评分，请稍候...'):
                        with open(marking_scheme_path, "rb") as ms_file, open(answer_path, "rb") as ans_file:
                            # 调用评分API
                            result = correction_with_image_marking_scheme(ms_file, ans_file)
                            
                            # 使用st.empty()创建占位符，动态更新内容
                            result_container = st.empty()
                            result_container.json(result)
                            
                            # 保存评分结果
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            result_filename = f"result_{timestamp}.json"
                            result_path = os.path.join(user_dir, result_filename)
                            with open(result_path, "w") as f:
                                json.dump(result, f, indent=2)
                            
                            st.success(f"评分完成，结果已保存至 {result_filename}")
                            st.download_button(
                                label="下载评分结果",
                                data=json.dumps(result, indent=2),
                                file_name=result_filename,
                                mime="application/json"
                            )
                except Exception as e:
                    st.error(f"评分过程中出错: {str(e)}")
    
    st.write("### 题目文件")
    if question_files:
        for record in question_files:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])
            cols[3].write(record["processing_result"])
    else:
        st.info("暂无题目文件")
    
    st.write("### 评分标准文件")
    if marking_scheme_files:
        for record in marking_scheme_files:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])
            cols[3].write(record["processing_result"])
    else:
        st.info("暂无评分标准文件")
        
    st.write("### 学生作答文件")
    if student_answer_files:
        for record in student_answer_files:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])
            cols[3].write(record["processing_result"])
    else:
        st.info("暂无学生作答文件")

def download_page():
    st.title("📥  File List")
    user_data = read_user_data()
    user_records = user_data.get(st.session_state.current_user, {}).get('records', [])
    user_dir = os.path.join(UPLOAD_DIR, st.session_state.current_user)
    
    # 返回按钮
    if st.button("⬅️ 返回上一页"):
        st.session_state.sub_page = None
        st.rerun()
    
    # 按文件类型分类显示
    st.write("### 题目文件")
    question_files = [r for r in user_records if r.get("file_type") == "question"]
    if question_files:
        for record in question_files:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])
            if cols[3].button("删除", key=f"del_q_{record['filename']}"):
                file_path = os.path.join(user_dir, record["filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)
                updated_records = [r for r in user_records if r['filename'] != record['filename']]
                user_data[st.session_state.current_user]['records'] = updated_records
                write_user_data(user_data)
                st.rerun()
    else:
        st.info("暂无题目文件")
    
    st.write("### 评分标准文件")
    marking_scheme_files = [r for r in user_records if r.get("file_type") == "marking_scheme"]
    if marking_scheme_files:
        for record in marking_scheme_files:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])
            if cols[3].button("删除", key=f"del_m_{record['filename']}"):
                file_path = os.path.join(user_dir, record["filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)
                updated_records = [r for r in user_records if r['filename'] != record['filename']]
                user_data[st.session_state.current_user]['records'] = updated_records
                write_user_data(user_data)
                st.rerun()
    else:
        st.info("暂无评分标准文件")
        
    st.write("### 学生作答文件")
    student_answer_files = [r for r in user_records if r.get("file_type") == "student_answer"]
    if student_answer_files:
        for record in student_answer_files:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])
            if cols[3].button("删除", key=f"del_s_{record['filename']}"):
                file_path = os.path.join(user_dir, record["filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)
                updated_records = [r for r in user_records if r['filename'] != record['filename']]
                user_data[st.session_state.current_user]['records'] = updated_records
                write_user_data(user_data)
                st.rerun()
    else:
        st.info("暂无学生作答文件")

    # 查找所有已完成的文件
    completed_records = [record for record in user_records if record["processing_result"] == "Completed"]

    if completed_records:
        st.subheader("标注文件")
        for record in completed_records:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])

            # 提供下载按钮
            file_path = os.path.join(user_dir, record["filename"])
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    cols[3].download_button(
                        label="下载文件",
                        data=f.read(),
                        file_name=record["filename"],
                        mime="application/octet-stream"
                    )
        
        # 查找标注后的PDF文件
        annotated_files = [f for f in os.listdir(user_dir) if f.startswith("annotated_")]
        if annotated_files:
            st.subheader("标注后的文件")

def main():
    """Main function for Streamlit interaction"""
    if 'logged_in' not in st.session_state: 
        st.session_state.update({ 
            'logged_in': False,
            'current_user': None,
            'page': 'main_menu',
            'sub_page': None
        })

    if not st.session_state.logged_in: 
        st.title("🔐  User Login")
        with st.form("login_form"): 
            username = st.text_input("Username") 
            password = st.text_input("Password",  type="password")
            if st.form_submit_button("Login"): 
                user_data = read_user_data()
                user_data = migrate_old_data(user_data)

                if username in TEST_ACCOUNTS:
                    if username not in user_data:
                        user_data[username] = {
                            "password": TEST_ACCOUNTS[username],
                            "records": []
                        }
                        write_user_data(user_data)

                    stored_password = user_data[username]['password']
                    if stored_password == password:
                        st.session_state.logged_in  = True
                        st.session_state.current_user  = username
                        st.rerun() 
                        return
                    else:
                        st.error("Incorrect  password.")
                else:
                    st.error("Only  test accounts are allowed to log in.")
        return  # If not logged in, return

    st.title(f"Welcome  back, {st.session_state.current_user}!") 

    with st.sidebar: 
        account_management()
        history_panel()

        st.divider() 
        page_options = {
            "🏠 主菜单": "main_menu",
            "📝 AI批改": "ai_correction",
            "📥 文件管理": "file_management"
        }
        selected = st.radio("Navigation  Menu", page_options.keys()) 
        st.session_state.page  = page_options[selected]

        st.divider() 
        if st.button("Logout"): 
            st.session_state.logged_in  = False
            st.session_state.current_user  = None
            st.rerun() 
            return

    if st.session_state.page == "main_menu":
        from pages.main_menu import main_menu_page
        main_menu_page()
    elif st.session_state.page == "ai_correction":
        if st.session_state.sub_page == "file_list":
            download_page()
        else:
            file_management_page()  # AI批改功能
    elif st.session_state.page == "file_management":
        download_page()  # 文件管理功能

if __name__ == "__main__":
    main()