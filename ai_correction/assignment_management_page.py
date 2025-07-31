# 作业管理页面
def show_assignment_management():
    """作业管理页面"""
    st.markdown("### 📚 作业管理")
    
    if not st.session_state.logged_in:
        st.warning("请先登录以使用此功能")
        return
    
    # 获取用户信息
    user_info = get_user_info(st.session_state.username)
    if not user_info:
        st.error("无法获取用户信息")
        return
    
    # 根据用户角色显示不同功能
    tab1, tab2, tab3 = st.tabs(["📝 创建作业", "📋 作业列表", "📊 作业统计"])
    
    with tab1:
        show_create_assignment()
    
    with tab2:
        show_assignment_list()
    
    with tab3:
        show_assignment_statistics()

def show_create_assignment():
    """创建作业界面"""
    st.markdown("#### 📝 创建新作业")
    
    # 获取用户的班级列表
    try:
        classes = get_user_classes(st.session_state.username)
        if not classes:
            st.info("请先创建或加入班级")
            return
    except Exception as e:
        st.error(f"获取班级列表失败：{str(e)}")
        return
    
    # 选择班级
    class_options = {cls['id']: cls['name'] for cls in classes}
    selected_class_id = st.selectbox(
        "选择班级",
        options=list(class_options.keys()),
        format_func=lambda x: class_options[x]
    )
    
    # 作业基本信息
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input("作业标题", placeholder="请输入作业标题")
        description = st.text_area("作业描述", placeholder="请输入作业描述")
    
    with col2:
        deadline = st.date_input("截止日期")
        deadline_time = st.time_input("截止时间")
    
    # 文件上传
    st.markdown("##### 📁 文件上传")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**题目文件**")
        question_files = st.file_uploader(
            "上传题目文件",
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'],
            key="question_files"
        )
    
    with col2:
        st.markdown("**批改标准文件**")
        marking_files = st.file_uploader(
            "上传批改标准文件",
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'],
            key="marking_files"
        )
    
    # 创建作业按钮
    if st.button("📝 创建作业", type="primary", use_container_width=True):
        if not title:
            st.error("请输入作业标题")
            return
        
        try:
            # 保存文件并创建作业
            question_file_paths = []
            marking_file_paths = []
            
            # 处理题目文件
            if question_files:
                for file in question_files:
                    file_path = save_uploaded_file(file, "question")
                    question_file_paths.append(file_path)
            
            # 处理批改标准文件
            if marking_files:
                for file in marking_files:
                    file_path = save_uploaded_file(file, "marking")
                    marking_file_paths.append(file_path)
            
            # 创建作业
            assignment_id = create_assignment(
                class_id=selected_class_id,
                title=title,
                description=description,
                question_files=question_file_paths,
                marking_files=marking_file_paths,
                deadline=f"{deadline} {deadline_time}"
            )
            
            st.success(f"✅ 作业创建成功！作业ID: {assignment_id}")
            
        except Exception as e:
            st.error(f"创建作业失败：{str(e)}")

def show_assignment_list():
    """作业列表界面"""
    st.markdown("#### 📋 作业列表")
    
    # 获取用户的班级列表
    try:
        classes = get_user_classes(st.session_state.username)
        if not classes:
            st.info("暂无班级")
            return
    except Exception as e:
        st.error(f"获取班级列表失败：{str(e)}")
        return
    
    # 选择班级
    class_options = {cls['id']: cls['name'] for cls in classes}
    selected_class_id = st.selectbox(
        "选择班级",
        options=list(class_options.keys()),
        format_func=lambda x: class_options[x],
        key="assignment_list_class"
    )
    
    # 获取作业列表
    try:
        assignments = get_class_assignments(selected_class_id)
        if not assignments:
            st.info("该班级暂无作业")
            return
    except Exception as e:
        st.error(f"获取作业列表失败：{str(e)}")
        return
    
    # 显示作业列表
    for assignment in assignments:
        with st.expander(f"📝 {assignment['title']}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**描述：** {assignment.get('description', '无')}")
                st.write(f"**创建时间：** {assignment['created_at']}")
                st.write(f"**截止时间：** {assignment.get('deadline', '无限制')}")
            
            with col2:
                # 获取提交统计
                try:
                    submissions = get_assignment_submissions(assignment['id'])
                    st.metric("提交数量", len(submissions))
                    
                    graded_count = len([s for s in submissions if s.get('ai_result')])
                    st.metric("已批改", graded_count)
                except:
                    st.metric("提交数量", "N/A")
            
            # 操作按钮
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"📊 查看详情", key=f"view_{assignment['id']}"):
                    st.session_state.selected_assignment_id = assignment['id']
                    # 这里可以跳转到作业详情页面
            
            with col2:
                if st.button(f"🤖 批改作业", key=f"grade_{assignment['id']}"):
                    st.session_state.selected_assignment_id = assignment['id']
                    # 这里可以跳转到批改页面
            
            with col3:
                if st.button(f"📈 统计分析", key=f"stats_{assignment['id']}"):
                    st.session_state.selected_assignment_id = assignment['id']
                    # 这里可以跳转到统计页面

def show_assignment_statistics():
    """作业统计界面"""
    st.markdown("#### 📊 作业统计")
    
    # 获取统计数据
    try:
        stats = get_user_assignment_summary(st.session_state.username)
        
        # 显示总体统计
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总班级数", stats.get('total_classes', 0))
        
        with col2:
            st.metric("总作业数", stats.get('total_assignments', 0))
        
        with col3:
            if 'total_submissions' in stats:
                st.metric("总提交数", stats['total_submissions'])
            else:
                st.metric("已完成作业", stats.get('completed_assignments', 0))
        
        with col4:
            if 'total_submissions' in stats and stats.get('total_assignments', 0) > 0:
                completion_rate = (stats['total_submissions'] / stats['total_assignments']) * 100
                st.metric("完成率", f"{completion_rate:.1f}%")
        
    except Exception as e:
        st.error(f"获取统计数据失败：{str(e)}")

def save_uploaded_file(uploaded_file, file_type):
    """保存上传的文件"""
    # 创建目录
    upload_dir = Path("class_files") / file_type
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{uploaded_file.name}"
    file_path = upload_dir / file_name
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)