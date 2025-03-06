import streamlit as st 
import os 
import json 
from datetime import datetime 
 
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
 
def main():
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
                    
                    # 验证密码 S
                    if password == user_data[username]['password']:
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
    main()