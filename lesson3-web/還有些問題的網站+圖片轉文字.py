import streamlit as st 
import hashlib 
import os 
from datetime import datetime 
import time

OCR_API_URL = "https://ocr.space.com"
OCR_API_KEY = "K81037081488957"
def call_ocr_api(image_path):
    """优化的OCR接口调用实现"""
    headers = {'apikey': 'K81037081488957'}
    
    for retry in range(3):  # 增加重试机制
        try:
            with open(image_path, 'rb') as image_file:
                response = requests.post(
                    OCR_API_URL,
                    files={'image': image_file},
                    data={
                        'language': 'chs',
                        'isOverlayRequired': 'False',
                        'OCREngine': 2
                    },
                    headers=headers,
                    timeout=45  # 延长超时时间
                )
            
            response.raise_for_status()
            result = response.json()
            
            if result['IsErroredOnProcessing']:
                raise Exception(result['ErrorMessage'])
                
            return '\n'.join([item['ParsedText'] for item in result['ParsedResults']])
        
        except Exception as e:
            if retry == 2:  # 最后一次重试仍失败
                st.error(f"OCR提取连续失败: {str(e)}")
                return None
            time.sleep(1.5)  # 等待后重试

# 初始化存储路径 
UPLOAD_DIR = "user_uploads"
if not os.path.exists(UPLOAD_DIR):  
    os.makedirs(UPLOAD_DIR)   

# 在原有用户系统代码基础上新增以下功能 ------------------------

def file_management_page():
    """ 文件上传管理页面 """
    st.title("📁   文件管理中心")
    
    # 安全验证 
    if not st.session_state.logged_in:  
        st.error("  请先登录")
        return 

    # 创建用户专属目录 
    user_dir = os.path.join(UPLOAD_DIR,   st.session_state.current_user)  
    if not os.path.exists(user_dir):  
        os.makedirs(user_dir)  

    # 文件上传表单 
    with st.expander("➕   上传新文件", expanded=True):
        uploaded_file = st.file_uploader(  
            label="选择需要上传的文件",
            type=["pdf", "docx", "xlsx", "jpg", "png"],
            accept_multiple_files=False,
            key="file_uploader"
        )
        
        if uploaded_file is not None:
            # 文件大小限制（10MB）
            if uploaded_file.size   > 10 * 1024 * 1024:
                st.error("  文件大小超过10MB限制")
            else:
                # 生成唯一文件名 
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  
                filename = f"{timestamp}_{uploaded_file.name}"  
                save_path = os.path.join(user_dir,   filename)
                
                # 保存文件 
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())  
                st.success(f"  文件 {uploaded_file.name}   上传成功")
            

    # 显示已上传文件列表 
    st.subheader("  已上传文件列表")
    if os.listdir(user_dir):  
        for filename in os.listdir(user_dir):  
            file_path = os.path.join(user_dir,   filename)
            file_size = os.path.getsize(file_path)   // 1024  # KB 
            col1, col2, col3 = st.columns([6,2,2])  
            with col1:
                st.code(filename)  
            with col2:
                st.text(f"{file_size}   KB")
            with col3:
                if st.button("🗑️",   key=filename):
                    os.remove(file_path)  
                    st.rerun()  
    else:
        st.info("  暂未上传任何文件")
    if st.button('提取文字'):
        st.write(call_ocr_api(user_dir))


# 修改原有main函数 ------------------------
def main():
    # 假设这里是原有的登录逻辑
    if 'logged_in' not in st.session_state: 
        st.session_state.logged_in  = False
    if 'current_user' not in st.session_state: 
        st.session_state.current_user  = None

    if not st.session_state.logged_in: 
        # 登录逻辑示例
        username = st.text_input(" 用户名")
        password = st.text_input(" 密码", type="password")
        if st.button(" 登录"):
            # 这里可以添加具体的验证逻辑
            st.session_state.logged_in  = True
            st.session_state.current_user  = username
    else:
        st.title(f"🎉   欢迎 {st.session_state.current_user}")  
        # 新增导航菜单 
        menu = ["仪表盘", "文件管理"]
        choice = st.sidebar.selectbox("  导航菜单", menu)
        
        if choice == "仪表盘":
            # 原有仪表盘内容...
            st.write(" 这里是仪表盘页面")
        elif choice == "文件管理":
            file_management_page()

        # 原有退出按钮...
        if st.button(" 退出登录"):
            st.session_state.logged_in  = False
            st.session_state.current_user  = None
            st.rerun() 

if __name__ == "__main__":
    main()