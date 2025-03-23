import streamlit as st 
import os 
import json 
from datetime import datetime 
 

from PIL import Image, ImageTk
import io

import json
import re

marking_scheme_prompt="""你是一个专业数学教师，需要根据用户提供的题目生成详细的评分方案。请严格按以下规则执行：

1. **输入内容**：用户上传的圖片中的原題（無需參考學生作答部分）。
2. **任务要求**：
   - 分析题目类型（代数、几何、微积分等）和知识点。
   - 網上搜索類似題目的評分方案。
   - 根據網上類似題目的評分方案，拆解解题的**关键步骤**，并为每个步骤分配分值（总分不超过题目标注分值）。
   - 列出每个步骤的**得分点**（如公式正确、计算无误）和**扣分点**（如符号错误、单位缺失）。
   - 标注常见错误及对应的扣分比例（如计算错误扣1分，缺少关键步骤扣2分）。
   - 若题目有多个解法，需为每种解法单独生成评分方案。
3. **输出格式**：
   - 使用JSON格式，包含以下字段：
     ```json
     {
       "题目类型": "分类（如代数方程）",
       "总分值": "N分",
       "评分方案": [
         {
           "步骤序号": 1,
           "步骤描述": "解方程的第一步变形",
           "分值": "X分",
           "得分点": ["变形正确", "符号规范"],
           "扣分点": ["符号错误（扣1分）", "未写出变形依据（扣0.5分）"]
         },
         // ...其他步骤
       ],
       "备注": "特殊说明（如允许误差范围、多解法标识）"
     }
     ```
4. **注意事项**：
   - 若题目信息不完整（如图片模糊），直接返回错误类型和所需补充信息。
   - 避免主观判断，仅基于数学规则和题目要求生成方案。"""
correction_prompt="""你是一个数学题自动批改系统，需根据提供的评分方案严格评估学生答案。请按以下规则执行：

1. **输入内容**：
   - 圖片中的學生作答。
   - 參考知識庫裏的Marking Scheme（JSON格式）。
2. **任务要求**：
   - 逐项对比学生答案与评分方案的每个步骤：
     - 确认是否完成该步骤。
     - 检查得分点和扣分点，记录具体错误。
   - 计算总分并生成反馈：
     - 若某步骤部分正确，按比例给分（如公式正确但计算错误，得该步骤50%分值）。
     - 若发现评分方案未覆盖的新错误，暂标记为“待人工复核”。
3. **输出格式**：
   - 使用JSON格式，包含以下字段：
     ```json
     {
       "总分": "M分（基于评分方案计算）",
       "分项批改": [
         {
           "步骤序号": 1,
           "得分": "X分",
           "正确点": ["变形正确"],
           "错误点": ["符号错误（扣1分）"],
           "建议": "注意符号规范，建议复习等式性质"
         },
         // ...其他步骤
       ],
       "总评": "整体反馈（如‘计算能力优秀，但需注意单位转换’）",
       "异常标记": ["待人工复核项（如有）"]
     }
     ```
4. **注意事项**：
   - 优先匹配步骤逻辑而非文字顺序（如学生调换步骤顺序但逻辑正确，仍给分）。
   - 对模糊内容（如无法识别的符号）标注“OCR识别失败”，不猜测扣分。
   - 禁止修改原始评分方案，仅基于其执行批改。"""

def testing_api(prompt,*file):
    print("Testing api is called.promt is:"+prompt)
    if prompt==marking_scheme_prompt:
        return '''以下为marking_scheme
{
    "题目类型": "分类（如代数方程）",
    "总分值": "N分",
    "评分方案": [
        {
            "步骤序号": 1,
            "步骤描述": "解方程的第一步变形",
            "分值": "X分",
            "得分点": ["变形正确", "符号规范"],
            "扣分点": ["符号错误（扣1分）", "未写出变形依据（扣0.5分）"]
        }
    ],
    "备注": "特殊说明（如允许误差范围、多解法标识）"
}
以上为marking_scheme'''
    return '''以下为评分{
  "总分": "M分（基于评分方案计算）",
  "分项批改": [
    {
      "步骤序号": 1,
      "得分": "X分",
      "正确点": ["变形正确"],
      "错误点": ["符号错误（扣1分）"],
      "建议": "注意符号规范，建议复习等式性质"
    }
  ],
  "总评": "整体反馈（如‘计算能力优秀，但需注意单位转换’）",
  "异常标记": ["待人工复核项（如有）"]
}
以上为评分'''

#调用的API,接收一个str和文件，返回一个字符串
default_api=testing_api

def extract_json_from_str(string):
    
        json_match = re.search(r'\{.*\}', string, re.DOTALL)
        if not json_match:
            raise ValueError("返回字符串中未找到有效JSON")
        
        # 解析返回结果
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"返回内容不是有效JSON: {str(e)}") from e

def generate_marking_scheme(image_file, api=default_api):
    try:
        # 执行AI函数调用
        response_str = api(marking_scheme_prompt, image_file)
        
        # 解析返回结果
        return extract_json_from_str(response_str)
    except Exception as e:
        # 捕获所有API函数可能抛出的异常
        raise RuntimeError(f"API函数调用失败: {str(e)}") from e

#批改
def correction_with_json_marking_scheme(json_marking_scheme, image_file, api=default_api):
    """
    调用API函数，发送JSON数据和图片文件，并解析返回的JSON数据

    参数：
    image_file (file对象): 以二进制模式打开的图片文件对象
    api (callable): 接收(string, file)并返回string的AI函数

    返回：
    dict: 解析后的JSON数据

    异常：
    RuntimeError: API函数调用失败时抛出
    ValueError: 未找到有效JSON或解析失败时抛出
    """
    try: 
        # 执行API函数调用
        response_str = api(correction_prompt+"\n5.一下是评分标准:\n"+str(json_marking_scheme), image_file)
        
        return extract_json_from_str(response_str)
            
    except Exception as e:
        # 捕获所有AI函数可能抛出的异常
        raise RuntimeError(f"API函数调用失败: {str(e)}") from e

def correction_with_image_marking_scheme(marking_scheme, image_file, api=default_api):
    try:    
        # 执行AI函数调用
        response_str = api(correction_prompt,marking_scheme, image_file)

        return extract_json_from_str(response_str)
            
    except Exception as e:
        # 捕获所有AI函数可能抛出的异常
        raise RuntimeError(f"API函数调用失败: {str(e)}") from e

def correction_without_marking_scheme(image,api=default_api):
    marking_scheme=generate_marking_scheme(image)
    return correction_with_json_marking_scheme(marking_scheme,image,api)


# 初始化存储路径 
UPLOAD_DIR = "user_uploads"
DATA_FILE = "user_data.json"   
 
# 定义测试账户及其初始密码 
TEST_ACCOUNTS = {
    "test_user_1": "password1",
    "test_user_2": "password2"
}
 
# 初始化存储结构 
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
    """ 迁移旧数据结构到新格式 """
    for user in list(user_data.keys()): 
        # 如果存储的是列表形式（旧格式）
        if isinstance(user_data[user], list):
            user_data[user] = {
                "password": TEST_ACCOUNTS.get(user,  "default_password"),
                "records": user_data[user]
            }
    return user_data 
 
def account_management():
    """ 侧边栏账户管理 """
    with st.sidebar.expander("🔑    账户管理", expanded=True):
        st.subheader("   用户信息")
        st.write(f"   当前用户：{st.session_state.current_user}")   
        
        # 修改密码功能 
        with st.form("   修改密码"):
            new_password = st.text_input("   新密码", type="password")
            if st.form_submit_button("   更新密码"):
                user_data = read_user_data()
                user_data[st.session_state.current_user]['password'] = new_password 
                write_user_data(user_data)
                st.success("   密码已更新")
 
def history_panel():
    """ 侧边栏历史记录查询 """
    with st.sidebar.expander("🕒    历史记录", expanded=True):
        user_data = read_user_data()
        user_records = user_data.get(st.session_state.current_user,  {}).get('records', [])
        
        if user_records:
            st.subheader("   最近上传记录")
            for record in user_records[-3:]:  # 显示最近3条 
                st.caption(f"{record['filename']}")   
                st.markdown(f"🗓️    {record['upload_time']}  📏 {record['file_size']}KB")
                st.progress(float(record.get('progress',  0)))
        else:
            st.info("   暂无历史记录")
 
def file_management_page():
    """ 文件上传管理页面 """
    st.title("📁    文件管理中心")
    
    # 创建用户专属目录 
    user_dir = os.path.join(UPLOAD_DIR,  st.session_state.current_user)     
    os.makedirs(user_dir,  exist_ok=True)
 
    # 文件上传表单 
    with st.expander("➕    上传新文件", expanded=True):
        uploaded_file = st.file_uploader(     
            label="选择需要上传的文件",
            type=["pdf", "docx", "xlsx", "jpg", "png"],
            key="main_uploader"
        )
    with st.expander("➕    上传marking scheme", expanded=True):
           uploaded_MS = st.file_uploader(     
           label="选择需要上传的文件",
           type=["pdf", "docx", "xlsx", "jpg", "png"],
           key="main_loader"
    )
        
    if uploaded_file and uploaded_file.size  <= 10 * 1024 * 1024:
            # 检查文件是否已经上传过
            user_data = read_user_data()
            user_records = user_data.get(st.session_state.current_user,  {}).get('records', [])
            for record in user_records:
                if record["filename"].endswith(uploaded_file.name):  
                    st.warning(" 该文件已经上传过，请选择其他文件。")
                    return 
 
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")     
            filename = f"{timestamp}_{uploaded_file.name}"     
            save_path = os.path.join(user_dir,  filename)
            
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())   
            
            # 更新用户数据 
            user_entry = user_data.setdefault(st.session_state.current_user,  {
                "password": TEST_ACCOUNTS.get(st.session_state.current_user,  ""),
                "records": []
            })
            user_entry['records'].append({  
                "filename": filename,
                "upload_time": timestamp,
                "file_size": uploaded_file.size  // 1024,
                "processing_result": "待处理",
                "progress": 0.0 
            })
            write_user_data(user_data)
            st.rerun()   
   

 
    # 文件列表显示 
    st.subheader("   文件列表")
    user_data = read_user_data()
    user_records = user_data.get(st.session_state.current_user,  {}).get('records', [])
    for record in user_records:
        cols = st.columns([5,2,2,2,2])   
        cols[0]().write(record["filename"])
        cols[1]().metric("大小", f"{record['file_size']}KB")
        cols[2]().write(record["upload_time"])
        cols[3]().write(record["processing_result"])
        cols[4]().progress(float(record["progress"]))
        
        if cols[4]().button("删除", key=f"del_{record['filename']}"):
            file_path = os.path.join(user_dir,  record["filename"])
            if os.path.exists(file_path):   
                os.remove(file_path)   
            updated_records = [r for r in user_records if r['filename'] != record['filename']]
            user_data[st.session_state.current_user]['records'] = updated_records 
            write_user_data(user_data)
            st.rerun()   
    
    if st.button('開始批改',key='orange') and uploaded_MS:
        st.write(correction_with_image_marking_scheme(uploaded_MS, uploaded_file, api=default_api))
    else:
        st.write(correction_without_marking_scheme(uploaded_file,api=default_api))
    
def mainprocess():
    # 初始化会话状态 
    if 'logged_in' not in st.session_state:    
        st.session_state.update({  
            'logged_in': False,
            'current_user': None,
            'page': 'dashboard'
        })
 
    # 登录界面 
    if not st.session_state.logged_in:   
        st.title("🔐    用户登录")
        with st.form("login_form"):   
            username = st.text_input(" 用户名")
            password = st.text_input(" 密码", type="password")
            if st.form_submit_button(" 登录"):
                user_data = read_user_data()
                user_data = migrate_old_data(user_data)  # 数据迁移 
                
                # 检查测试账户 
                if username in TEST_ACCOUNTS:
                    # 初始化新用户数据 
                    if username not in user_data:
                        user_data[username] = {
                            "password": TEST_ACCOUNTS[username],
                            "records": []
                        }
                        write_user_data(user_data)
                    
                    # 验证密码 
                    if password:
                        st.session_state.logged_in  = True 
                        st.session_state.current_user  = username 
                        st.rerun() 
                    else:
                        st.error(" 密码错误")
                else:
                    st.error(" 只有测试账户可以登录。")
        return 
 
    # 主界面布局 
    st.title(f" 欢迎回来，{st.session_state.current_user} ！")
    
    # 左侧边栏布局 
    with st.sidebar:   
        account_management()
        history_panel()
        
        # 主导航菜单 
        st.divider()   
        page_options = {
            "🏠 仪表盘": "dashboard",
            "📤 文件管理": "file_mgmt",
            "📊 数据分析": "analytics"
        }
        selected = st.radio(" 导航菜单", page_options.keys())   
        st.session_state.page  = page_options[selected]
 
        # 退出按钮 
        st.divider()   
        if st.button(" 退出登录"):
            st.session_state.logged_in  = False 
            st.session_state.current_user  = None 
            st.rerun()   
 
    # 页面路由 
    if st.session_state.page  == "dashboard":
        st.write("##  系统仪表盘")
        
    elif st.session_state.page  == "file_mgmt":
        file_management_page()
        
    elif st.session_state.page  == "analytics":
        st.write("##  数据分析中心")
 
if __name__ == "__main__":
  mainprocess() 