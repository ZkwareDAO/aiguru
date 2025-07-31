#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评分标准编辑器组件
实现可视化的评分标准编辑界面，支持拖拽排序和动态添加
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Callable
import json
import uuid
from datetime import datetime

from src.models.grading_config import ScoringRule, GradingConfig, GradingTemplate
from src.services.grading_config_service import GradingConfigService


class CriteriaEditor:
    """评分标准编辑器"""
    
    def __init__(self, config_service: GradingConfigService):
        self.config_service = config_service
    
    def render(self, 
               criteria: List[ScoringRule], 
               on_change: Optional[Callable[[List[ScoringRule]], None]] = None,
               templates: Optional[List[GradingTemplate]] = None) -> List[ScoringRule]:
        """渲染评分标准编辑器"""
        st.markdown("### 📏 评分标准编辑器")
        st.markdown("创建和编辑详细的评分标准，支持多维度评分和权重分配")
        
        # 初始化会话状态
        if 'criteria_editor_data' not in st.session_state:
            st.session_state.criteria_editor_data = criteria.copy()
        
        # 工具栏
        self._render_toolbar(templates)
        
        # 主编辑区域
        updated_criteria = self._render_criteria_list()
        
        # 添加新标准区域
        self._render_add_criteria_section()
        
        # 预览和验证
        self._render_preview_section(updated_criteria)
        
        # 如果有变化，调用回调
        if on_change and updated_criteria != criteria:
            on_change(updated_criteria)
        
        return updated_criteria
    
    def _render_toolbar(self, templates: Optional[List[GradingTemplate]] = None):
        """渲染工具栏"""
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        
        with col1:
            if st.button("➕ 添加标准"):
                self._add_new_criteria()
        
        with col2:
            if st.button("📋 从模板导入"):
                self._show_template_import_dialog(templates)
        
        with col3:
            if st.button("💾 导出标准"):
                self._export_criteria()
        
        with col4:
            if st.button("📁 导入标准"):
                self._show_import_dialog()
        
        st.markdown("---")
    
    def _render_criteria_list(self) -> List[ScoringRule]:
        """渲染评分标准列表"""
        criteria = st.session_state.criteria_editor_data
        
        if not criteria:
            st.info("📝 暂无评分标准，请添加新的评分标准")
            return []
        
        st.write(f"**当前评分标准** ({len(criteria)}个)")
        
        # 显示总分
        total_score = sum(rule.max_score for rule in criteria)
        st.metric("总分", f"{total_score}分")
        
        # 排序选项
        sort_options = ["默认顺序", "按分数排序", "按权重排序", "按名称排序"]
        sort_by = st.selectbox("排序方式", sort_options)
        
        if sort_by == "按分数排序":
            criteria.sort(key=lambda x: x.max_score, reverse=True)
        elif sort_by == "按权重排序":
            criteria.sort(key=lambda x: x.weight, reverse=True)
        elif sort_by == "按名称排序":
            criteria.sort(key=lambda x: x.name)
        
        # 渲染每个评分标准
        criteria_to_remove = []
        for i, rule in enumerate(criteria):
            if self._render_criteria_item(rule, i):
                criteria_to_remove.append(i)
        
        # 删除标记的标准
        for i in reversed(criteria_to_remove):
            criteria.pop(i)
            st.rerun()
        
        return criteria
    
    def _render_criteria_item(self, rule: ScoringRule, index: int) -> bool:
        """渲染单个评分标准项"""
        should_delete = False
        
        # 使用expander显示每个标准
        with st.expander(f"📏 {rule.name} ({rule.max_score}分 | 权重: {rule.weight:.1%})", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 基本信息
                rule.name = st.text_input(
                    "标准名称", 
                    value=rule.name, 
                    key=f"criteria_name_{index}",
                    help="简洁明确的标准名称"
                )
                
                rule.description = st.text_area(
                    "标准描述", 
                    value=rule.description, 
                    key=f"criteria_desc_{index}",
                    help="详细描述这个评分标准的要求"
                )
                
                # 分数和权重
                col_score, col_weight = st.columns(2)
                with col_score:
                    rule.max_score = st.number_input(
                        "最大分数", 
                        value=rule.max_score, 
                        min_value=0.0, 
                        key=f"criteria_score_{index}"
                    )
                
                with col_weight:
                    rule.weight = st.slider(
                        "权重", 
                        min_value=0.0, 
                        max_value=1.0, 
                        value=rule.weight, 
                        step=0.05,
                        format="%.0f%%",
                        key=f"criteria_weight_{index}"
                    )
                
                # 评分细则
                st.write("**评分细则**:")
                criteria_text = "\n".join(rule.criteria)
                new_criteria_text = st.text_area(
                    "每行一个细则", 
                    value=criteria_text, 
                    key=f"criteria_details_{index}",
                    help="每行输入一个具体的评分细则",
                    height=100
                )
                rule.criteria = [c.strip() for c in new_criteria_text.split('\n') if c.strip()]
                
                # 自动评分选项
                rule.auto_grading = st.checkbox(
                    "启用AI自动评分", 
                    value=rule.auto_grading, 
                    key=f"criteria_auto_{index}",
                    help="是否允许AI系统自动对此标准进行评分"
                )
                
                # 评分等级设置
                self._render_grading_levels(rule, index)
            
            with col2:
                st.write("")  # 空行对齐
                st.write("")
                
                # 操作按钮
                if st.button("⬆️", key=f"move_up_{index}", help="上移"):
                    self._move_criteria(index, -1)
                
                if st.button("⬇️", key=f"move_down_{index}", help="下移"):
                    self._move_criteria(index, 1)
                
                if st.button("📋", key=f"copy_{index}", help="复制"):
                    self._copy_criteria(rule)
                
                if st.button("🗑️", key=f"delete_{index}", help="删除"):
                    should_delete = True
        
        return should_delete
    
    def _render_grading_levels(self, rule: ScoringRule, index: int):
        """渲染评分等级设置"""
        st.write("**评分等级** (可选):")
        
        # 初始化评分等级数据
        levels_key = f"grading_levels_{index}"
        if levels_key not in st.session_state:
            st.session_state[levels_key] = [
                {"name": "优秀", "min_score": rule.max_score * 0.9, "max_score": rule.max_score, "description": "完全符合要求"},
                {"name": "良好", "min_score": rule.max_score * 0.7, "max_score": rule.max_score * 0.9, "description": "基本符合要求"},
                {"name": "及格", "min_score": rule.max_score * 0.6, "max_score": rule.max_score * 0.7, "description": "部分符合要求"},
                {"name": "不及格", "min_score": 0, "max_score": rule.max_score * 0.6, "description": "不符合要求"}
            ]
        
        levels = st.session_state[levels_key]
        
        # 显示等级
        for i, level in enumerate(levels):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 3])
            
            with col1:
                level["name"] = st.text_input(
                    f"等级名称", 
                    value=level["name"], 
                    key=f"level_name_{index}_{i}"
                )
            
            with col2:
                level["min_score"] = st.number_input(
                    f"最低分", 
                    value=level["min_score"], 
                    min_value=0.0,
                    max_value=rule.max_score,
                    key=f"level_min_{index}_{i}"
                )
            
            with col3:
                level["max_score"] = st.number_input(
                    f"最高分", 
                    value=level["max_score"], 
                    min_value=level["min_score"],
                    max_value=rule.max_score,
                    key=f"level_max_{index}_{i}"
                )
            
            with col4:
                level["description"] = st.text_input(
                    f"等级描述", 
                    value=level["description"], 
                    key=f"level_desc_{index}_{i}"
                )
    
    def _render_add_criteria_section(self):
        """渲染添加新标准区域"""
        st.markdown("---")
        st.markdown("### ➕ 添加新评分标准")
        
        with st.form("add_criteria_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("标准名称", placeholder="例如：内容准确性")
                new_description = st.text_area("标准描述", placeholder="描述这个评分标准的具体要求")
                new_score = st.number_input("最大分数", value=10.0, min_value=0.0)
            
            with col2:
                new_weight = st.slider("权重", min_value=0.0, max_value=1.0, value=0.2, step=0.05, format="%.0f%%")
                new_criteria = st.text_area("评分细则（每行一个）", placeholder="细则1\n细则2\n细则3")
                new_auto = st.checkbox("启用AI自动评分", value=True)
            
            if st.form_submit_button("➕ 添加标准", type="primary"):
                if new_name.strip():
                    criteria_list = [c.strip() for c in new_criteria.split('\n') if c.strip()]
                    new_rule = ScoringRule(
                        name=new_name,
                        description=new_description,
                        max_score=new_score,
                        criteria=criteria_list,
                        auto_grading=new_auto,
                        weight=new_weight
                    )
                    
                    st.session_state.criteria_editor_data.append(new_rule)
                    st.success(f"✅ 已添加评分标准：{new_name}")
                    st.rerun()
                else:
                    st.error("❌ 请填写标准名称")
    
    def _render_preview_section(self, criteria: List[ScoringRule]):
        """渲染预览和验证区域"""
        st.markdown("---")
        st.markdown("### 👀 预览和验证")
        
        if not criteria:
            st.info("暂无评分标准")
            return
        
        # 验证
        errors = self._validate_criteria(criteria)
        if errors:
            st.error("❌ 发现以下问题：")
            for error in errors:
                st.write(f"- {error}")
        else:
            st.success("✅ 评分标准验证通过")
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("标准数量", len(criteria))
        
        with col2:
            total_score = sum(rule.max_score for rule in criteria)
            st.metric("总分", f"{total_score}分")
        
        with col3:
            total_weight = sum(rule.weight for rule in criteria)
            st.metric("总权重", f"{total_weight:.1%}")
        
        with col4:
            auto_count = sum(1 for rule in criteria if rule.auto_grading)
            st.metric("自动评分", f"{auto_count}/{len(criteria)}")
        
        # 权重分布图
        if criteria:
            st.write("**权重分布**:")
            weight_data = {rule.name: rule.weight for rule in criteria}
            st.bar_chart(weight_data)
        
        # 详细预览表格
        with st.expander("📊 详细预览", expanded=False):
            preview_data = []
            for rule in criteria:
                preview_data.append({
                    "名称": rule.name,
                    "描述": rule.description[:50] + "..." if len(rule.description) > 50 else rule.description,
                    "最大分数": rule.max_score,
                    "权重": f"{rule.weight:.1%}",
                    "细则数量": len(rule.criteria),
                    "自动评分": "是" if rule.auto_grading else "否"
                })
            
            st.dataframe(preview_data, use_container_width=True)
    
    def _add_new_criteria(self):
        """添加新的评分标准"""
        new_rule = ScoringRule(
            name="新评分标准",
            description="请填写标准描述",
            max_score=10.0,
            criteria=["请添加评分细则"],
            auto_grading=True,
            weight=0.1
        )
        
        st.session_state.criteria_editor_data.append(new_rule)
        st.rerun()
    
    def _move_criteria(self, index: int, direction: int):
        """移动评分标准位置"""
        criteria = st.session_state.criteria_editor_data
        new_index = index + direction
        
        if 0 <= new_index < len(criteria):
            criteria[index], criteria[new_index] = criteria[new_index], criteria[index]
            st.rerun()
    
    def _copy_criteria(self, rule: ScoringRule):
        """复制评分标准"""
        new_rule = ScoringRule(
            name=f"{rule.name}_副本",
            description=rule.description,
            max_score=rule.max_score,
            criteria=rule.criteria.copy(),
            auto_grading=rule.auto_grading,
            weight=rule.weight
        )
        
        st.session_state.criteria_editor_data.append(new_rule)
        st.success(f"✅ 已复制评分标准：{rule.name}")
        st.rerun()
    
    def _validate_criteria(self, criteria: List[ScoringRule]) -> List[str]:
        """验证评分标准"""
        errors = []
        
        if not criteria:
            errors.append("至少需要一个评分标准")
            return errors
        
        # 检查每个标准
        names = []
        for i, rule in enumerate(criteria):
            if not rule.name.strip():
                errors.append(f"第{i+1}个标准的名称不能为空")
            
            if rule.name in names:
                errors.append(f"标准名称重复：{rule.name}")
            names.append(rule.name)
            
            if rule.max_score <= 0:
                errors.append(f"标准'{rule.name}'的最大分数必须大于0")
            
            if not rule.criteria:
                errors.append(f"标准'{rule.name}'至少需要一个评分细则")
        
        # 检查权重总和
        total_weight = sum(rule.weight for rule in criteria)
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"权重总和应为100%，当前为{total_weight:.1%}")
        
        return errors
    
    def _show_template_import_dialog(self, templates: Optional[List[GradingTemplate]] = None):
        """显示模板导入对话框"""
        if not templates:
            templates = self.config_service.load_all_templates()
        
        st.markdown("#### 📋 从模板导入评分标准")
        
        if not templates:
            st.info("暂无可用模板")
            return
        
        template_options = [f"{t.name} - {t.description}" for t in templates]
        selected_template_name = st.selectbox("选择模板", template_options)
        
        if selected_template_name:
            template_index = template_options.index(selected_template_name)
            selected_template = templates[template_index]
            
            # 显示模板详情
            with st.expander("模板详情", expanded=True):
                st.write(f"**名称**: {selected_template.name}")
                st.write(f"**描述**: {selected_template.description}")
                st.write(f"**评分标准数量**: {len(selected_template.config.scoring_rules)}")
                
                for rule in selected_template.config.scoring_rules:
                    st.write(f"- {rule.name}: {rule.max_score}分")
            
            import_mode = st.radio(
                "导入模式",
                ["替换现有标准", "追加到现有标准"],
                help="选择如何处理现有的评分标准"
            )
            
            if st.button("导入标准"):
                if import_mode == "替换现有标准":
                    st.session_state.criteria_editor_data = [
                        ScoringRule(
                            name=rule.name,
                            description=rule.description,
                            max_score=rule.max_score,
                            criteria=rule.criteria.copy(),
                            auto_grading=rule.auto_grading,
                            weight=rule.weight
                        ) for rule in selected_template.config.scoring_rules
                    ]
                else:
                    for rule in selected_template.config.scoring_rules:
                        new_rule = ScoringRule(
                            name=rule.name,
                            description=rule.description,
                            max_score=rule.max_score,
                            criteria=rule.criteria.copy(),
                            auto_grading=rule.auto_grading,
                            weight=rule.weight
                        )
                        st.session_state.criteria_editor_data.append(new_rule)
                
                st.success("✅ 评分标准导入成功")
                st.rerun()
    
    def _export_criteria(self):
        """导出评分标准"""
        criteria = st.session_state.criteria_editor_data
        
        if not criteria:
            st.warning("暂无评分标准可导出")
            return
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "criteria": [rule.to_dict() for rule in criteria]
        }
        
        export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="📥 下载评分标准",
            data=export_json,
            file_name=f"grading_criteria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def _show_import_dialog(self):
        """显示导入对话框"""
        st.markdown("#### 📁 导入评分标准")
        
        uploaded_file = st.file_uploader(
            "选择评分标准文件",
            type=['json'],
            help="上传之前导出的评分标准JSON文件"
        )
        
        if uploaded_file:
            try:
                import_data = json.loads(uploaded_file.read().decode('utf-8'))
                
                if 'criteria' in import_data:
                    criteria_data = import_data['criteria']
                    imported_criteria = [ScoringRule.from_dict(data) for data in criteria_data]
                    
                    st.write(f"**文件信息**:")
                    st.write(f"- 版本: {import_data.get('version', '未知')}")
                    st.write(f"- 导出时间: {import_data.get('exported_at', '未知')}")
                    st.write(f"- 评分标准数量: {len(imported_criteria)}")
                    
                    # 预览导入的标准
                    with st.expander("预览导入内容", expanded=True):
                        for rule in imported_criteria:
                            st.write(f"- {rule.name}: {rule.max_score}分")
                    
                    import_mode = st.radio(
                        "导入模式",
                        ["替换现有标准", "追加到现有标准"]
                    )
                    
                    if st.button("确认导入"):
                        if import_mode == "替换现有标准":
                            st.session_state.criteria_editor_data = imported_criteria
                        else:
                            st.session_state.criteria_editor_data.extend(imported_criteria)
                        
                        st.success("✅ 评分标准导入成功")
                        st.rerun()
                else:
                    st.error("❌ 文件格式不正确，缺少criteria字段")
                    
            except json.JSONDecodeError:
                st.error("❌ 文件格式不正确，请上传有效的JSON文件")
            except Exception as e:
                st.error(f"❌ 导入失败：{e}")