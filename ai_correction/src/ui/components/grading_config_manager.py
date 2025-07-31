#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批改配置管理器
整合配置向导和评分标准编辑器的主要界面
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.models.grading_config import GradingConfig, GradingTemplate, ScoringRule
from src.services.grading_config_service import GradingConfigService
from src.ui.components.grading_wizard import GradingWizard
from src.ui.components.criteria_editor import CriteriaEditor


class GradingConfigManager:
    """批改配置管理器"""
    
    def __init__(self, config_service: GradingConfigService):
        self.config_service = config_service
        self.wizard = GradingWizard(config_service)
        self.criteria_editor = CriteriaEditor(config_service)
    
    def render(self):
        """渲染配置管理界面"""
        st.markdown("## ⚙️ 批改配置管理")
        
        # 选项卡
        tab1, tab2, tab3, tab4 = st.tabs(["📋 我的配置", "🧙‍♂️ 创建配置", "📏 编辑标准", "📚 模板管理"])
        
        with tab1:
            self._render_config_list_tab()
        
        with tab2:
            self._render_create_config_tab()
        
        with tab3:
            self._render_edit_criteria_tab()
        
        with tab4:
            self._render_template_management_tab()
    
    def _render_config_list_tab(self):
        """渲染配置列表标签页"""
        st.markdown("### 📋 我的批改配置")
        
        # 加载配置列表
        configs = self.config_service.load_all_configs()
        
        if not configs:
            st.info("暂无批改配置，请创建新的配置")
            if st.button("🧙‍♂️ 创建第一个配置"):
                st.session_state.active_tab = 1
                st.rerun()
            return
        
        # 搜索和筛选
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input("🔍 搜索配置", placeholder="输入配置名称或学科")
        
        with col2:
            subject_filter = st.selectbox("学科筛选", ["全部"] + [s.value for s in set(c.subject for c in configs)])
        
        with col3:
            sort_by = st.selectbox("排序方式", ["更新时间", "创建时间", "名称", "总分"])
        
        # 筛选配置
        filtered_configs = configs
        if search_term:
            filtered_configs = [c for c in filtered_configs if search_term.lower() in c.name.lower()]
        
        if subject_filter != "全部":
            filtered_configs = [c for c in filtered_configs if c.subject.value == subject_filter]
        
        # 排序
        if sort_by == "更新时间":
            filtered_configs.sort(key=lambda x: x.updated_at, reverse=True)
        elif sort_by == "创建时间":
            filtered_configs.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "名称":
            filtered_configs.sort(key=lambda x: x.name)
        elif sort_by == "总分":
            filtered_configs.sort(key=lambda x: x.get_total_score(), reverse=True)
        
        # 显示配置卡片
        for config in filtered_configs:
            self._render_config_card(config)
    
    def _render_config_card(self, config: GradingConfig):
        """渲染配置卡片"""
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            
            with col1:
                st.markdown(f"**{config.name}**")
                st.write(f"学科: {config.subject.value} | 年级: {config.grade_level.value}")
                st.write(f"更新时间: {config.updated_at.strftime('%Y-%m-%d %H:%M')}")
            
            with col2:
                st.metric("总分", f"{config.get_total_score()}分")
            
            with col3:
                st.metric("规则数", len(config.scoring_rules))
            
            with col4:
                col_edit, col_copy, col_delete = st.columns(3)
                
                with col_edit:
                    if st.button("✏️", key=f"edit_{config.id}", help="编辑"):
                        self._edit_config(config)
                
                with col_copy:
                    if st.button("📋", key=f"copy_{config.id}", help="复制"):
                        self._copy_config(config)
                
                with col_delete:
                    if st.button("🗑️", key=f"delete_{config.id}", help="删除"):
                        self._delete_config(config)
            
            # 配置详情
            with st.expander(f"详情 - {config.name}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**评分规则**:")
                    for rule in config.scoring_rules:
                        st.write(f"- {rule.name}: {rule.max_score}分 (权重: {rule.weight:.1%})")
                
                with col2:
                    st.write("**权重分配**:")
                    st.write(f"- 内容准确性: {config.weight_distribution.content_accuracy:.1%}")
                    st.write(f"- 语言质量: {config.weight_distribution.language_quality:.1%}")
                    st.write(f"- 结构逻辑: {config.weight_distribution.structure_logic:.1%}")
                    st.write(f"- 创新性: {config.weight_distribution.creativity:.1%}")
                
                if config.custom_prompts:
                    st.write("**自定义提示**:")
                    for i, prompt in enumerate(config.custom_prompts, 1):
                        st.write(f"{i}. {prompt}")
        
        st.markdown("---")
    
    def _render_create_config_tab(self):
        """渲染创建配置标签页"""
        st.markdown("### 🧙‍♂️ 创建新配置")
        
        # 创建方式选择
        creation_mode = st.radio(
            "创建方式",
            ["使用向导创建", "从模板创建", "从空白开始"],
            help="选择最适合您的创建方式"
        )
        
        if creation_mode == "使用向导创建":
            # 使用配置向导
            result = self.wizard.render(on_complete=self._on_config_created)
            if result:
                st.success("✅ 配置创建成功！")
        
        elif creation_mode == "从模板创建":
            self._render_create_from_template()
        
        else:  # 从空白开始
            self._render_create_blank()
    
    def _render_edit_criteria_tab(self):
        """渲染编辑标准标签页"""
        st.markdown("### 📏 评分标准编辑器")
        
        # 选择要编辑的配置
        configs = self.config_service.load_all_configs()
        
        if not configs:
            st.info("暂无配置可编辑，请先创建配置")
            return
        
        config_options = [f"{c.name} ({c.subject.value})" for c in configs]
        selected_config_name = st.selectbox("选择要编辑的配置", config_options)
        
        if selected_config_name:
            config_index = config_options.index(selected_config_name)
            selected_config = configs[config_index]
            
            # 使用评分标准编辑器
            updated_criteria = self.criteria_editor.render(
                criteria=selected_config.scoring_rules,
                on_change=lambda criteria: self._update_config_criteria(selected_config, criteria)
            )
            
            # 保存按钮
            if st.button("💾 保存更改", type="primary"):
                selected_config.scoring_rules = updated_criteria
                selected_config.updated_at = datetime.now()
                
                if self.config_service.save_config(selected_config):
                    st.success("✅ 配置已保存")
                else:
                    st.error("❌ 保存失败")
    
    def _render_template_management_tab(self):
        """渲染模板管理标签页"""
        st.markdown("### 📚 模板管理")
        
        # 模板操作选项
        template_action = st.radio(
            "操作",
            ["浏览模板", "创建模板", "导入模板"],
            horizontal=True
        )
        
        if template_action == "浏览模板":
            self._render_template_browser()
        elif template_action == "创建模板":
            self._render_create_template()
        else:
            self._render_import_template()
    
    def _render_template_browser(self):
        """渲染模板浏览器"""
        templates = self.config_service.load_all_templates()
        
        if not templates:
            st.info("暂无模板")
            return
        
        # 筛选选项
        col1, col2 = st.columns(2)
        
        with col1:
            subject_filter = st.selectbox("学科筛选", ["全部"] + list(set(t.subject.value for t in templates)))
        
        with col2:
            template_type = st.selectbox("类型筛选", ["全部", "公开模板", "私有模板"])
        
        # 筛选模板
        filtered_templates = templates
        if subject_filter != "全部":
            filtered_templates = [t for t in filtered_templates if t.subject.value == subject_filter]
        
        if template_type == "公开模板":
            filtered_templates = [t for t in filtered_templates if t.is_public]
        elif template_type == "私有模板":
            filtered_templates = [t for t in filtered_templates if not t.is_public]
        
        # 显示模板
        for template in filtered_templates:
            self._render_template_card(template)
    
    def _render_template_card(self, template: GradingTemplate):
        """渲染模板卡片"""
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 2])
            
            with col1:
                st.markdown(f"**{template.name}**")
                st.write(template.description)
                st.write(f"学科: {template.subject.value} | 年级: {template.grade_level.value}")
                if template.is_public:
                    st.write("🌐 公开模板")
                else:
                    st.write("🔒 私有模板")
            
            with col2:
                st.metric("使用次数", template.usage_count)
                st.metric("规则数", len(template.config.scoring_rules))
            
            with col3:
                if st.button("📋 使用模板", key=f"use_template_{template.id}"):
                    self._use_template(template)
                
                if st.button("👀 预览", key=f"preview_template_{template.id}"):
                    self._preview_template(template)
        
        st.markdown("---")
    
    def _render_create_from_template(self):
        """渲染从模板创建界面"""
        templates = self.config_service.load_all_templates()
        
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
                st.write(f"**学科**: {selected_template.subject.value}")
                st.write(f"**年级**: {selected_template.grade_level.value}")
                
                st.write("**评分规则**:")
                for rule in selected_template.config.scoring_rules:
                    st.write(f"- {rule.name}: {rule.max_score}分")
            
            # 配置名称
            config_name = st.text_input("新配置名称", value=f"{selected_template.name}_副本")
            
            if st.button("🎯 创建配置", type="primary"):
                if config_name.strip():
                    new_config = self.config_service.create_config_from_template(
                        selected_template.id, config_name
                    )
                    
                    if new_config and self.config_service.save_config(new_config):
                        st.success(f"✅ 配置 '{config_name}' 创建成功！")
                    else:
                        st.error("❌ 创建配置失败")
                else:
                    st.error("❌ 请填写配置名称")
    
    def _render_create_blank(self):
        """渲染从空白创建界面"""
        st.info("💡 从空白开始创建配置，您需要手动设置所有参数")
        
        # 基本信息表单
        with st.form("blank_config_form"):
            config_name = st.text_input("配置名称", placeholder="例如：我的批改配置")
            
            col1, col2 = st.columns(2)
            with col1:
                subject = st.selectbox("学科", ["chinese", "math", "english", "physics", "chemistry", "biology", "history", "geography", "politics", "other"])
            
            with col2:
                grade_level = st.selectbox("年级", ["primary_1_3", "primary_4_6", "middle_7_9", "high_10_12", "university", "other"])
            
            if st.form_submit_button("创建空白配置", type="primary"):
                if config_name.strip():
                    from src.models.grading_config import SubjectType, GradeLevel
                    
                    new_config = GradingConfig(
                        name=config_name,
                        subject=SubjectType(subject),
                        grade_level=GradeLevel(grade_level)
                    )
                    
                    if self.config_service.save_config(new_config):
                        st.success(f"✅ 空白配置 '{config_name}' 创建成功！")
                        st.info("请切换到 '编辑标准' 标签页添加评分规则")
                    else:
                        st.error("❌ 创建配置失败")
                else:
                    st.error("❌ 请填写配置名称")
    
    def _render_create_template(self):
        """渲染创建模板界面"""
        st.write("从现有配置创建模板")
        
        configs = self.config_service.load_all_configs()
        
        if not configs:
            st.info("暂无配置可转换为模板")
            return
        
        config_options = [f"{c.name} ({c.subject.value})" for c in configs]
        selected_config_name = st.selectbox("选择配置", config_options)
        
        if selected_config_name:
            config_index = config_options.index(selected_config_name)
            selected_config = configs[config_index]
            
            with st.form("create_template_form"):
                template_name = st.text_input("模板名称", value=f"{selected_config.name}_模板")
                template_description = st.text_area("模板描述", placeholder="描述这个模板的用途和特点")
                is_public = st.checkbox("设为公开模板", help="公开模板可被其他用户使用")
                
                if st.form_submit_button("创建模板", type="primary"):
                    if template_name.strip():
                        template = GradingTemplate(
                            name=template_name,
                            description=template_description,
                            subject=selected_config.subject,
                            grade_level=selected_config.grade_level,
                            config=selected_config,
                            is_public=is_public
                        )
                        
                        if self.config_service.save_template(template):
                            st.success(f"✅ 模板 '{template_name}' 创建成功！")
                        else:
                            st.error("❌ 创建模板失败")
                    else:
                        st.error("❌ 请填写模板名称")
    
    def _render_import_template(self):
        """渲染导入模板界面"""
        st.write("导入外部模板文件")
        
        uploaded_file = st.file_uploader(
            "选择模板文件",
            type=['json'],
            help="上传模板JSON文件"
        )
        
        if uploaded_file:
            try:
                import json
                template_data = json.loads(uploaded_file.read().decode('utf-8'))
                
                # 验证模板数据
                if 'config' in template_data:
                    template = GradingTemplate.from_dict(template_data)
                    
                    st.write("**模板预览**:")
                    st.write(f"- 名称: {template.name}")
                    st.write(f"- 描述: {template.description}")
                    st.write(f"- 学科: {template.subject.value}")
                    st.write(f"- 年级: {template.grade_level.value}")
                    
                    if st.button("导入模板", type="primary"):
                        if self.config_service.save_template(template):
                            st.success("✅ 模板导入成功！")
                        else:
                            st.error("❌ 导入模板失败")
                else:
                    st.error("❌ 文件格式不正确")
                    
            except Exception as e:
                st.error(f"❌ 导入失败：{e}")
    
    def _edit_config(self, config: GradingConfig):
        """编辑配置"""
        st.session_state.editing_config = config
        st.session_state.active_tab = 2  # 切换到编辑标准标签页
        st.rerun()
    
    def _copy_config(self, config: GradingConfig):
        """复制配置"""
        new_config = GradingConfig(
            name=f"{config.name}_副本",
            subject=config.subject,
            grade_level=config.grade_level,
            scoring_rules=[
                ScoringRule(
                    name=rule.name,
                    description=rule.description,
                    max_score=rule.max_score,
                    criteria=rule.criteria.copy(),
                    auto_grading=rule.auto_grading,
                    weight=rule.weight
                ) for rule in config.scoring_rules
            ],
            weight_distribution=config.weight_distribution,
            custom_prompts=config.custom_prompts.copy()
        )
        
        if self.config_service.save_config(new_config):
            st.success(f"✅ 配置已复制为 '{new_config.name}'")
            st.rerun()
        else:
            st.error("❌ 复制配置失败")
    
    def _delete_config(self, config: GradingConfig):
        """删除配置"""
        if st.session_state.get(f"confirm_delete_{config.id}", False):
            if self.config_service.delete_config(config.id):
                st.success(f"✅ 配置 '{config.name}' 已删除")
                if f"confirm_delete_{config.id}" in st.session_state:
                    del st.session_state[f"confirm_delete_{config.id}"]
                st.rerun()
            else:
                st.error("❌ 删除配置失败")
        else:
            st.session_state[f"confirm_delete_{config.id}"] = True
            st.warning(f"⚠️ 确认删除配置 '{config.name}'？再次点击删除按钮确认。")
    
    def _use_template(self, template: GradingTemplate):
        """使用模板"""
        config_name = f"基于{template.name}的配置"
        new_config = self.config_service.create_config_from_template(template.id, config_name)
        
        if new_config and self.config_service.save_config(new_config):
            st.success(f"✅ 已基于模板创建配置 '{config_name}'")
        else:
            st.error("❌ 创建配置失败")
    
    def _preview_template(self, template: GradingTemplate):
        """预览模板"""
        with st.expander(f"模板预览 - {template.name}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本信息**:")
                st.write(f"- 名称: {template.name}")
                st.write(f"- 描述: {template.description}")
                st.write(f"- 学科: {template.subject.value}")
                st.write(f"- 年级: {template.grade_level.value}")
                st.write(f"- 使用次数: {template.usage_count}")
            
            with col2:
                st.write("**评分规则**:")
                for rule in template.config.scoring_rules:
                    st.write(f"- {rule.name}: {rule.max_score}分")
                
                st.write("**权重分配**:")
                st.write(f"- 内容准确性: {template.config.weight_distribution.content_accuracy:.1%}")
                st.write(f"- 语言质量: {template.config.weight_distribution.language_quality:.1%}")
                st.write(f"- 结构逻辑: {template.config.weight_distribution.structure_logic:.1%}")
                st.write(f"- 创新性: {template.config.weight_distribution.creativity:.1%}")
    
    def _on_config_created(self, config: GradingConfig):
        """配置创建完成回调"""
        st.balloons()
        st.success(f"🎉 配置 '{config.name}' 创建成功！")
    
    def _update_config_criteria(self, config: GradingConfig, criteria: List[ScoringRule]):
        """更新配置的评分标准"""
        config.scoring_rules = criteria
        config.updated_at = datetime.now()