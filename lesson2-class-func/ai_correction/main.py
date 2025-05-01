import streamlit as st
import os
import json
import hashlib
from datetime import datetime
import time
import logging
from pathlib import Path
# from functions.api_correcting.pdf_merger import ImageToPDFConverter
from functions.api_correcting.calling_api import call_api
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

# 添加一个自然语言转换函数
def ensure_natural_language(text):
    """确保文本是自然语言格式，而不是JSON格式"""
    # 如果文本看起来像JSON（包含多个花括号或引号），进行转换
    if (text.count('{') > 2 and text.count('}') > 2) or ('"' in text and ':' in text):
        try:
            # 尝试解析JSON
            import json
            try:
                parsed = json.loads(text)
                # 如果成功解析为JSON，将其转换为自然语言文本
                converted_text = "# 批改结果\n\n"
                
                # 处理常见的JSON键
                if isinstance(parsed, dict):
                    if "科目类型" in parsed:
                        converted_text += f"## 基本信息\n- 科目类型：{parsed.get('科目类型', '未指定')}\n"
                    if "总分" in parsed:
                        converted_text += f"- 总得分：{parsed.get('总分', '未计算')}\n\n"
                    
                    # 处理分项批改
                    if "分项批改" in parsed and isinstance(parsed["分项批改"], list):
                        converted_text += "## 分步骤批改\n"
                        for i, item in enumerate(parsed["分项批改"], 1):
                            converted_text += f"{i}. "
                            if "步骤序号" in item:
                                converted_text += f"第{item['步骤序号']}部分\n"
                            else:
                                converted_text += f"第{i}部分\n"
                                
                            if "得分" in item:
                                converted_text += f"   - 得分：{item['得分']}\n"
                            
                            if "正确点" in item and isinstance(item["正确点"], list):
                                converted_text += "   - 正确之处：\n"
                                for point in item["正确点"]:
                                    converted_text += f"     * {point}\n"
                            
                            if "错误点" in item and isinstance(item["错误点"], list):
                                converted_text += "   - 需要改进：\n"
                                for point in item["错误点"]:
                                    converted_text += f"     * {point}\n"
                            
                            if "建议" in item:
                                converted_text += f"   - 改进建议：{item['建议']}\n\n"
                    
                    # 总评
                    if "总评" in parsed:
                        converted_text += f"## 总体评价\n{parsed['总评']}\n\n"
                    
                    # 知识点
                    if "知识点" in parsed and isinstance(parsed["知识点"], list):
                        converted_text += "## 知识点掌握情况\n"
                        for point in parsed["知识点"]:
                            converted_text += f"- {point}\n"
                        converted_text += "\n"
                    
                    # 学习建议
                    if "学习建议" in parsed:
                        converted_text += f"## 学习建议\n{parsed['学习建议']}\n"
                
                # 如果无法识别JSON结构，则简单地将键值对转换为文本
                else:
                    converted_text += "无法完全解析批改结果，以下是关键信息：\n\n"
                    converted_text += str(parsed).replace("{", "").replace("}", "").replace(",", "\n").replace("'", "").replace('"', "")
                
                # 添加转换提示
                return "【注意：系统已将结构化数据转换为自然语言格式】\n\n" + converted_text
            
            except json.JSONDecodeError:
                # 如果不是有效的JSON，但看起来像JSON，做简单的文本替换
                text = re.sub(r'[{}\[\]"]', '', text)
                text = re.sub(r':\s*', ': ', text)
                text = re.sub(r',\s*', '\n', text)
                return "【注意：系统已尝试移除JSON格式】\n\n" + text
        except Exception as e:
            # 任何转换错误，添加警告并返回原始文本
            return f"【警告：无法处理可能的JSON格式 ({str(e)})】\n\n" + text
    
    # 如果文本不是JSON格式，直接返回
    return text

def file_management_page():
    """File management and history page"""
    st.title("📁 File Management Center")
    
    user_data = read_user_data()
    user_records = user_data.get(st.session_state.current_user, {}).get('records', [])
    
    # 过滤只包含有批改结果的记录
    correction_records = [record for record in user_records if 'content' in record and record['content']]
    
    if not correction_records:
        st.info("No correction records found.")
        return

    st.subheader("📋 Correction History")
    
    for idx, record in enumerate(reversed(correction_records)):
        # 获取时间戳，如果不存在则使用默认值
        timestamp = record.get('timestamp', 'No timestamp')
        
        with st.expander(f"Record {len(correction_records)-idx}: {timestamp}", expanded=False):
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

            # 显示结果内容 - 添加自然语言转换
            st.write("🔍 Correction Result:")
            content = record.get('content', 'No content available')
            # 添加: 确保显示的内容是自然语言格式
            content = ensure_natural_language(content)
            st.write(content)

            # 添加下载按钮 - 也需要确保下载的内容是自然语言
            col1, col2 = st.columns(2)
            with col1:
                # TXT下载
                current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                st.download_button(
                    label="Download as TXT",
                    data=content.encode('utf-8'),  # 使用转换后的内容
                    file_name=f"correction_result_{current_time}.txt",
                    mime="text/plain",
                    key=f"txt_{idx}"
                )

            with col2:
                # PDF下载
                try:
                    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                    pdf_filename = f"correction_result_{current_time}.pdf"
                    
                    # 导入 PDFMerger 类
                    from functions.api_correcting.pdf_merger import PDFMerger
                    
                    # 创建 PDFMerger 实例
                    pdf_merger = PDFMerger(UPLOAD_DIR)
                    
                    # 创建临时文件对象来模拟UploadedFile对象
                    class MockFileObject:
                        def __init__(self, path):
                            self.path = path
                            self.type = self._determine_type(path)
                            
                        def _determine_type(self, path):
                            suffix = Path(path).suffix.lower()
                            if suffix in ['.jpg', '.jpeg']:
                                return 'image/jpeg'
                            elif suffix == '.png':
                                return 'image/png'
                            elif suffix == '.pdf':
                                return 'application/pdf'
                            else:
                                return 'application/octet-stream'
                                
                        def getvalue(self):
                            with open(self.path, 'rb') as f:
                                return f.read()
                    
                    # 准备上传文件信息
                    files_to_include = {}
                    for file_type, file_info in record.get('files', {}).items():
                        if isinstance(file_info, dict) and 'saved_path' in file_info:
                            saved_path = file_info['saved_path']
                            if os.path.exists(saved_path):
                                # 创建模拟文件对象
                                files_to_include[file_type] = MockFileObject(saved_path)
                    
                    output_path = UPLOAD_DIR / st.session_state.current_user / pdf_filename
                    
                    # 调用 merge_pdfs 方法生成 PDF
                    success, pdf_path = pdf_merger.merge_pdfs(
                        files_to_include,
                        content,  # 使用转换后的内容
                        "AI Correction Results",
                        output_path
                    )
                    
                    if success:
                        with open(pdf_path, 'rb') as pdf_file:
                            pdf_bytes = pdf_file.read()
                            st.download_button(
                                label="Download as PDF",
                                data=pdf_bytes,
                                file_name=pdf_filename,
                                mime="application/pdf",
                                key=f"pdf_{idx}"
                            )
                        
                        # 删除临时生成的PDF
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
                    else:
                        st.error(f"Failed to generate PDF: {pdf_path}")
                        
                except Exception as e:
                    st.error(f"Failed to generate PDF: {str(e)}")
                    logging.error(f"Error during PDF generation: {str(e)}")

    st.info("Please use the AI Correction module to upload files and process them.")

def ai_correction_page():
    """AI correction management page with integrated file list"""
    st.title("🤖 AI Correction")
    
    # 创建页面选项卡
    tab1, tab2 = st.tabs(["AI Correction", "File List"])
    
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
                        prompt_text = """请批改以下学生答案。在输出时，请严格遵循以下规则：

1. 数学符号使用规范（最重要！必须严格执行）：
   - 必须使用标准数学符号，而不是LaTeX代码
   - 正确示例：
     √(a² + 16) + √(b² + 16)    ✓
     x² + y² = r²                ✓
     ∫f(x)dx                     ✓
   - 错误示例：
     \sqrt{a^2 + 16}            ✗
     x^2 + y^2 = r^2            ✗
     \int f(x)dx                ✗
   
   常用符号参考：
   - 根号：√ 而不是 \sqrt
   - 平方：² 而不是 ^2
   - 立方：³ 而不是 ^3
   - 积分：∫ 而不是 \int
   - 求和：∑ 而不是 \sum
   - 无穷：∞ 而不是 \infty
   - 小于等于：≤ 而不是 \leq
   - 大于等于：≥ 而不是 \geq
   - 不等于：≠ 而不是 \neq
   - 属于：∈ 而不是 \in
   - 角：∠ 而不是 \angle
   - 垂直：⊥ 而不是 \perp
   - 平行：∥ 而不是 \parallel
   - 因为：∵ 而不是 \because
   - 所以：∴ 而不是 \therefore

2. 评价和反馈使用自然语言：
   - 错误分析用完整的句子描述
   - 改进建议用清晰的语言表达
   - 解题思路用通俗易懂的语言说明
   - 得分点说明用具体的文字描述

3. 输出格式：
   第一部分：基本信息
   - 题目类型
   - 总分值
   - 实际得分

   第二部分：详细批改
   - 按步骤列出评分点
   - 每个步骤的得分情况
   - 正确之处的具体说明
   - 错误之处的具体分析
   - 针对性的改进建议

   第三部分：总体评价
   - 整体表现分析
   - 知识点掌握情况
   - 具体的改进建议

请特别注意：所有数学公式必须使用标准数学符号，严禁使用LaTeX代码。这是最重要的规则，必须严格执行。"""
                        
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
                        
                        # 添加: 确保结果是自然语言格式
                        result = ensure_natural_language(result)
                        
                        if result:
                            st.session_state.correction_success = True
                            st.session_state.correction_result = result
                            
                            # 保存结果到用户记录
                            user_data = read_user_data()
                            if st.session_state.current_user not in user_data:
                                user_data[st.session_state.current_user] = {'records': []}

                            # 在处理结果时保存更详细的文件信息
                            uploaded_files = {}
                            for file_type, file_obj in [
                                ('question', question_file),
                                ('answer', student_file),
                                ('marking', marking_file)
                            ]:
                                if file_obj:
                                    # 检查是否是 UploadedFile 对象
                                    if hasattr(file_obj, 'name') and hasattr(file_obj, 'getvalue'):
                                        # 处理新上传的文件
                                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                        file_ext = os.path.splitext(file_obj.name)[1]
                                        saved_filename = f"{file_type}_{timestamp}{file_ext}"
                                        save_path = UPLOAD_DIR / st.session_state.current_user / saved_filename
                                        
                                        save_path.parent.mkdir(parents=True, exist_ok=True)
                                        with open(save_path, 'wb') as f:
                                            f.write(file_obj.getvalue())
                                        
                                        uploaded_files[file_type] = {
                                            'filename': file_obj.name,
                                            'saved_path': str(save_path),
                                            'timestamp': timestamp
                                        }
                                    elif isinstance(file_obj, (str, Path)):
                                        # 处理已经保存的文件路径
                                        file_path = Path(file_obj)
                                        if file_path.exists():
                                            uploaded_files[file_type] = {
                                                'filename': file_path.name,
                                                'saved_path': str(file_path),
                                                'timestamp': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y%m%d_%H%M%S')
                                            }

                            record = {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'content': result,
                                'files': uploaded_files
                            }

                            user_data[st.session_state.current_user]['records'].append(record)
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
            
            # 修改下载部分
            st.markdown("### Download Options")
            download_col1, download_col2 = st.columns([2, 1])
            
            with download_col1:
                file_type = st.selectbox(
                    "Select file type",
                    ["Text (.txt)", "PDF (.pdf)"],
                    key="download_type"
                )
            
            if file_type == "PDF (.pdf)":
                # PDF选项
                st.markdown("#### PDF Options")
                include_images = st.checkbox("Include uploaded images", value=True)
                include_question = st.checkbox("Include question", value=True)
                include_answer = st.checkbox("Include student answer", value=True)
                include_marking = st.checkbox("Include marking scheme", value=True)
                
                if st.button("Generate and Download PDF"):
                    try:
                        from functions.api_correcting.pdf_merger import PDFMerger
                        
                        # 创建PDF合并器
                        merger = PDFMerger(UPLOAD_DIR)
                        
                        # 准备要包含的文件，直接使用文件对象而不是保存后的路径
                        files_to_include = {}
                        
                        if include_question and question:
                            files_to_include['question'] = question
                        if include_answer and student_answer:
                            files_to_include['answer'] = student_answer
                        if include_marking and marking_scheme:
                            files_to_include['marking'] = marking_scheme
                        
                        # 生成PDF
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_filename = f"correction_result_{timestamp}.pdf"
                        output_path = user_dir / output_filename
                        
                        # 确保传递完整的AI响应内容
                        full_result = str(st.session_state.correction_result)
                        
                        success, result_path = merger.merge_pdfs(
                            files_to_include,
                            full_result,  # 传递完整的响应内容
                            "AI Correction Results",
                            output_path
                        )
                        
                        if success:
                            with open(result_path, "rb") as pdf_file:
                                pdf_data = pdf_file.read()
                                st.download_button(
                                    label="Download PDF",
                                    data=pdf_data,
                                    file_name=output_filename,
                                    mime="application/pdf",
                                    key=f"download_pdf_{timestamp}"
                                )
                        else:
                            st.error(f"Failed to generate PDF: {result_path}")
                            
                    except Exception as e:
                        st.error(f"Error generating PDF: {str(e)}")
                        logging.error(f"PDF generation error: {str(e)}")
            
            else:  # Text file
                # 原有的文本文件下载逻辑
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="Download Text",
                    data=str(st.session_state.correction_result),
                    file_name=f"correction_result_{timestamp}.txt",
                    mime="text/plain",
                    key=f"download_result_{timestamp}"
                )

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