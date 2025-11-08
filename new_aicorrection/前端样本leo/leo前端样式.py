import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
import numpy as np

# 设置页面配置
st.set_page_config(
    page_title="作业批改系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_type = None  # 'student' 或 'teacher'
    st.session_state.username = None
    st.session_state.current_view = "main"  # "main" 或 "assignment_detail"
    st.session_state.selected_assignment = None

# 简约的自定义CSS样式
st.markdown("""
<style>
/* 全局样式 */
* {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

body {
    background-color: #f0f2f5;
    color: #333;
}

/* 主容器 */
.main {
    background-color: #ffffff;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    padding: 30px;
    margin-top: 20px;
}

/* 标题样式 */
.title {
    color: #2c3e50;
    text-align: center;
    font-weight: 600;
    font-size: 2.2rem;
    margin-bottom: 10px;
}

.subtitle {
    color: #7f8c8d;
    text-align: center;
    font-weight: 400;
    font-size: 1.1rem;
    margin-bottom: 30px;
}

/* 卡片样式 */
.card {
    background: #ffffff;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border: 1px solid #eaeaea;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.card-title {
    font-weight: 600;
    font-size: 1.3rem;
    margin-bottom: 15px;
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 8px;
}

/* 按钮样式 */
.stButton>button {
    background: #3498db;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 100%;
}

.stButton>button:hover {
    background: #2980b9;
    transform: translateY(-2px);
}

/* 输入框样式 */
.stTextInput>div>div>input {
    border-radius: 6px;
    border: 1px solid #ddd;
    padding: 12px;
    font-size: 1rem;
}

.stTextInput>div>div>input:focus {
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

/* 选择框样式 */
.stSelectbox>div>div>select {
    border-radius: 6px;
    border: 1px solid #ddd;
    padding: 12px;
    font-size: 1rem;
}

/* 表格样式 */
table {
    width: 100%;
    border-collapse: collapse;
}

table th, table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

table th {
    background-color: #f8f9fa;
    font-weight: 600;
}

/* 链接样式 */
.file-link {
    color: #3498db;
    text-decoration: none;
    cursor: pointer;
}

.file-link:hover {
    text-decoration: underline;
}

/* 侧边栏样式 */
.css-1d391kg {
    background-color: #2c3e50;
}

.css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3 {
    color: white !important;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .main {
        padding: 15px;
    }
    
    .title {
        font-size: 1.8rem;
    }
}
</style>
""", unsafe_allow_html=True)

# 模拟数据
def get_mock_assignments():
    return pd.DataFrame({
        '作业名称': ['数学作业1', '英语作文', '物理实验报告'],
        '科目': ['数学', '英语', '物理'],
        '截止时间': ['2023-10-20 18:00', '2023-10-21 20:00', '2023-10-22 17:00'],
        '状态': ['未提交', '已提交', '已批改']
    })

def get_mock_history():
    return pd.DataFrame({
        '作业名称': ['数学作业1', '英语作文', '物理实验报告', '化学练习', '语文阅读'],
        '提交时间': ['2023-10-15 08:30', '2023-10-16 14:20', '2023-10-17 10:15', '2023-10-18 16:45', '2023-10-19 09:00'],
        '状态': ['已批改', '已批改', '待批改', '已批改', '待批改'],
        '得分': ['85/100', '92/100', '-', '78/100', '-']
    })

def get_mock_teacher_history():
    return pd.DataFrame({
        '作业名称': ['数学作业1', '英语作文', '物理实验报告', '化学练习', '语文阅读'],
        '布置时间': ['2023-10-10', '2023-10-12', '2023-10-14', '2023-10-16', '2023-10-18'],
        '提交人数': ['25/30', '28/30', '22/30', '27/30', '26/30'],
        '待批改': [2, 1, 5, 0, 3]
    })

# 模拟统计数据
def get_assignment_stats(assignment_name):
    # 模拟统计数据
    if assignment_name == "数学作业1":
        return {
            "总平均分": 85.2,
            "总中位数": 87.0,
            "总最高分": 98,
            "总最低分": 65,
            "题目统计": [
                {"题号": "1", "平均分": 8.5, "中位数": 9.0, "最高分": 10, "最低分": 5},
                {"题号": "2", "平均分": 7.2, "中位数": 7.5, "最高分": 10, "最低分": 4},
                {"题号": "3", "平均分": 9.1, "中位数": 9.5, "最高分": 10, "最低分": 7},
                {"题号": "4", "平均分": 6.8, "中位数": 7.0, "最高分": 10, "最低分": 3},
                {"题号": "5", "平均分": 8.9, "中位数": 9.0, "最高分": 10, "最低分": 6}
            ]
        }
    elif assignment_name == "英语作文":
        return {
            "总平均分": 92.5,
            "总中位数": 93.0,
            "总最高分": 99,
            "总最低分": 82,
            "题目统计": [
                {"题号": "作文", "平均分": 92.5, "中位数": 93.0, "最高分": 99, "最低分": 82}
            ]
        }
    else:
        return {
            "总平均分": 80.0,
            "总中位数": 82.0,
            "总最高分": 95,
            "总最低分": 60,
            "题目统计": [
                {"题号": "1", "平均分": 8.0, "中位数": 8.0, "最高分": 10, "最低分": 5},
                {"题号": "2", "平均分": 7.5, "中位数": 8.0, "最高分": 10, "最低分": 4},
                {"题号": "3", "平均分": 8.5, "中位数": 9.0, "最高分": 10, "最低分": 6}
            ]
        }

# 模拟学生作业文件列表
def get_student_submissions(assignment_name):
    return pd.DataFrame({
        '学生姓名': ['张三', '李四', '王五', '赵六', '钱七'],
        '学号': ['2021001', '2021002', '2021003', '2021004', '2021005'],
        '提交时间': ['2023-10-15 08:30', '2023-10-15 09:15', '2023-10-15 10:20', '2023-10-15 11:05', '2023-10-15 12:30'],
        '得分': ['85/100', '92/100', '78/100', '88/100', '95/100'],
        '状态': ['已批改', '已批改', '已批改', '已批改', '已批改']
    })

# 创建文件下载链接的函数
def create_download_link(content, filename, text):
    # 创建一个base64编码的文件内容
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}" class="file-link">{text}</a>'
    return href

# 登录页面
def login_page():
    st.markdown('<div class="title">📚 作业批改系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">请登录以继续</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">学生登录</div>', unsafe_allow_html=True)
        student_username = st.text_input("学号", key="student_username")
        student_password = st.text_input("密码", type="password", key="student_password")
        
        if st.button("学生登录"):
            if student_username and student_password:
                # 简单的验证（实际应用中应该连接数据库）
                st.session_state.logged_in = True
                st.session_state.user_type = 'student'
                st.session_state.username = student_username
                st.experimental_rerun()
            else:
                st.warning("请输入学号和密码")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">教师登录</div>', unsafe_allow_html=True)
        teacher_username = st.text_input("工号", key="teacher_username")
        teacher_password = st.text_input("密码", type="password", key="teacher_password")
        
        if st.button("教师登录"):
            if teacher_username and teacher_password:
                # 简单的验证（实际应用中应该连接数据库）
                st.session_state.logged_in = True
                st.session_state.user_type = 'teacher'
                st.session_state.username = teacher_username
                st.experimental_rerun()
            else:
                st.warning("请输入工号和密码")
        st.markdown('</div>', unsafe_allow_html=True)

# 个人信息页面
def profile_page():
    st.markdown('<div class="title">👤 个人信息</div>', unsafe_allow_html=True)
    
    if st.session_state.user_type == 'student':
        user_info = {
            '姓名': '张三',
            '学号': st.session_state.username,
            '班级': '高三(1)班',
            '入学时间': '2021-09-01',
            '联系电话': '138****5678',
            '邮箱': 'zhangsan@example.com'
        }
    else:
        user_info = {
            '姓名': '李老师',
            '工号': st.session_state.username,
            '科目': '数学',
            '职称': '高级教师',
            '联系电话': '139****1234',
            '邮箱': 'lilaoshi@example.com'
        }
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">基本信息</div>', unsafe_allow_html=True)
        for key, value in user_info.items():
            st.markdown(f"**{key}:** {value}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">操作</div>', unsafe_allow_html=True)
        if st.button("退出登录"):
            st.session_state.logged_in = False
            st.session_state.user_type = None
            st.session_state.username = None
            st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# 学生端主页面
def student_main_page():
    st.markdown('<div class="title">🎓 学生作业系统</div>', unsafe_allow_html=True)
    
    # 今日作业
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📝 今日作业</div>', unsafe_allow_html=True)
    assignments_df = get_mock_assignments()
    st.table(assignments_df)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 历史记录和立即批改
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">📜 历史记录</div>', unsafe_allow_html=True)
        history_df = get_mock_history()
        
        # 创建可点击的文件链接
        for i, row in history_df.iterrows():
            if row['状态'] == '已批改':
                # 为已批改的作业创建查看链接
                feedback_content = f"作业: {row['作业名称']}\n得分: {row['得分']}\n评语: 这份作业完成得很好，请继续保持！"
                link = create_download_link(feedback_content, f"{row['作业名称']}_批改反馈.txt", "查看批改")
                st.markdown(f"**{row['作业名称']}** - {row['提交时间']} - {row['状态']} - {row['得分']} - {link}", unsafe_allow_html=True)
            else:
                st.markdown(f"**{row['作业名称']}** - {row['提交时间']} - {row['状态']} - {row['得分']}", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">⚡ 立即批改</div>', unsafe_allow_html=True)
        st.markdown("上传您的作业文件进行批改")
        uploaded_file = st.file_uploader("选择文件", type=['pdf', 'doc', 'docx', 'jpg', 'png'])
        if uploaded_file is not None:
            st.success(f"已选择文件: {uploaded_file.name}")
        if st.button("提交批改"):
            if uploaded_file is not None:
                st.success("作业已提交，正在批改中...")
            else:
                st.warning("请先选择要批改的文件")
        st.markdown('</div>', unsafe_allow_html=True)

# 教师端作业详情页面
def teacher_assignment_detail_page():
    assignment_name = st.session_state.selected_assignment
    st.markdown(f'<div class="title">📊 {assignment_name} 详情</div>', unsafe_allow_html=True)
    
    # 返回按钮
    if st.button("← 返回历史记录"):
        st.session_state.current_view = "main"
        st.session_state.selected_assignment = None
        st.experimental_rerun()
    
    # 获取统计数据
    stats = get_assignment_stats(assignment_name)
    
    # 总体统计信息
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📈 总体统计</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("平均分", stats["总平均分"])
    col2.metric("中位数", stats["总中位数"])
    col3.metric("最高分", stats["总最高分"])
    col4.metric("最低分", stats["总最低分"])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 题目统计图表（使用Streamlit内置图表）
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📊 题目统计图表</div>', unsafe_allow_html=True)
    
    # 创建图表数据
    question_stats = stats["题目统计"]
    questions = [q["题号"] for q in question_stats]
    avg_scores = [q["平均分"] for q in question_stats]
    med_scores = [q["中位数"] for q in question_stats]
    
    # 使用Streamlit的内置图表功能
    chart_data = pd.DataFrame({
        '题目': questions,
        '平均分': avg_scores,
        '中位数': med_scores
    })
    
    st.bar_chart(chart_data.set_index('题目'))
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 题目详细统计表
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📋 题目详细统计</div>', unsafe_allow_html=True)
    questions_df = pd.DataFrame(question_stats)
    st.table(questions_df)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 学生作业文件列表
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📁 学生作业文件</div>', unsafe_allow_html=True)
    submissions_df = get_student_submissions(assignment_name)
    
    # 显示学生作业列表
    for i, row in submissions_df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 2])
        col1.write(row['学生姓名'])
        col2.write(row['学号'])
        col3.write(row['提交时间'])
        col4.write(row['得分'])
        with col5:
            # 创建查看链接
            feedback_content = f"学生: {row['学生姓名']}\n学号: {row['学号']}\n作业: {assignment_name}\n得分: {row['得分']}\n评语: 作业完成情况良好，继续保持！"
            link = create_download_link(feedback_content, f"{assignment_name}_{row['学生姓名']}_作业.txt", "查看")
            st.markdown(link, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 教师端主页面
def teacher_main_page():
    st.markdown('<div class="title">👨‍🏫 教师作业系统</div>', unsafe_allow_html=True)
    
    # 检查是否需要显示详情页面
    if st.session_state.current_view == "assignment_detail":
        teacher_assignment_detail_page()
        return
    
    # 历史记录
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📜 历史记录</div>', unsafe_allow_html=True)
    history_df = get_mock_teacher_history()
    
    # 显示作业列表，添加查看详情链接
    for i, row in history_df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
        col1.write(row['作业名称'])
        col2.write(row['布置时间'])
        col3.write(row['提交人数'])
        col4.write(f"{row['待批改']} 份")
        with col5:
            # 创建查看详情链接
            if st.button("查看详情", key=f"detail_{i}"):
                st.session_state.current_view = "assignment_detail"
                st.session_state.selected_assignment = row['作业名称']
                st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 布置作业
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📝 布置作业</div>', unsafe_allow_html=True)
    assignment_name = st.text_input("作业名称")
    assignment_desc = st.text_area("作业描述")
    deadline = st.date_input("截止日期", datetime.now() + timedelta(days=7))
    st.markdown("**上传答案文件:**")
    answer_key = st.file_uploader("选择答案文件", type=['pdf', 'doc', 'docx'])
    
    if st.button("发布作业"):
        if assignment_name and assignment_desc:
            st.success(f"作业 '{assignment_name}' 已成功发布！截止日期: {deadline}")
        else:
            st.warning("请填写作业名称和描述")
    st.markdown('</div>', unsafe_allow_html=True)

# 侧边栏导航
def sidebar_navigation():
    with st.sidebar:
        st.markdown(f"<h2 style='color: white;'>欢迎, {st.session_state.username}!</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        page = st.selectbox(
            "导航",
            ["主页", "个人信息"] if st.session_state.user_type == 'student' else ["主页", "个人信息"]
        )
        
        st.markdown("---")
        if st.button("退出登录"):
            st.session_state.logged_in = False
            st.session_state.user_type = None
            st.session_state.username = None
            st.session_state.current_view = "main"
            st.session_state.selected_assignment = None
            st.experimental_rerun()
        
        st.markdown("<p style='color: #ccc; font-size: 0.8rem; text-align: center;'>作业批改系统 © 2023</p>", unsafe_allow_html=True)

# 主程序逻辑
if not st.session_state.logged_in:
    login_page()
else:
    sidebar_navigation()
    
    if st.session_state.user_type == 'student':
        # 学生端
        page = st.sidebar.selectbox("页面", ["主页", "个人信息"])
        if page == "主页":
            student_main_page()
        else:
            profile_page()
    else:
        # 教师端
        page = st.sidebar.selectbox("页面", ["主页", "个人信息"])
        if page == "主页":
            teacher_main_page()
        else:
            profile_page()