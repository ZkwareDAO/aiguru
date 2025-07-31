#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批改配置向导组件
实现分步骤的批改配置创建和编辑界面
"""

import streamlit as st
from typing import List, Optional, Dict, Any, Callable
import uuid
from datetime import datetime

from src.models.grading_config import (
    GradingConfig, GradingTemplate, ScoringRule, WeightConfig,
    SubjectType, GradeLevel
)
from src.services.grading_config_service import GradingConfigService


class GradingWizard:
    """批改配置向导"""
    
    def __init__(self, config_service: GradingConfigService):
        self.config_service = config_service
        self.steps = [
            "基本信息",
            "选择模板",
            "评分规则",
            "权重分配",
            "自定义提示",
            "预览确认"
        ]
    
    def render(self, on_complete: Optional[Callable[[GradingConfig], None]] = None) -> Optional[GradingConfig]:
        """渲染配置向导"""
        st.markdown("### 🧙‍♂️ 批改配置向导")
        st.markdown("通过简单的步骤创建个性化的批改配置")
        
        # 初始化会话状态
        self._initialize_session_state()
        
        # 显示进度条
        self._render_progress_bar()
        
        # 渲染当前步骤
        current_step = st.session_state.wizard_step
        
        if current_step == 0:
            self._render_basic_info_step()
        elif current_step == 1:
            self._render_template_selection_step()
        elif current_step == 2:
            self._render_scoring_rules_step()
        elif current_step == 3:
            self._render_weight_distribution_step()
        elif current_step == 4:
            self._render_custom_prompts_step()
        elif current_step == 5:
            return self._render_preview_step(on_complete)
        
        # 导航按钮
        self._render_navigation_buttons()
        
        return None
    
    def _initialize_session_state(self):
        """初始化会话状态"""
        if 'wizard_step' not in st.session_state:
            st.session_state.wizard_step = 0
        
        if 'wizard_config' not in st.session_state:
            st.session_state.wizard_config = GradingConfig()
        
        if 'wizard_selected_template' not in st.session_state:
            st.session_state.wizard_selected_template = None
    
    def _render_progress_bar(self):
        """渲染进度条"""
        current_step = st.session_state.wizard_step
        progress = (current_step + 1) / len(self.steps)
        
        st.progress(progress)
        
        # 步骤指示器
        cols = st.columns(len(self.steps))
        for i, step_name in enumerate(self.steps):
            with cols[i]:
                if i < current_step:
                    st.markdown(f"✅ **{step_name}**")
                elif i == current_step:
                    st.markdown(f"🔄 **{step_name}**")
                else:
                    st.markdown(f"⏳ {step_name}")
    
    def _render_basic_info_step(self):
        """渲染基本信息步骤"""
        st.markdown("#### 📋 第1步：基本信息")
        st.markdown("请填写批改配置的基本信息")
        
        config = st.session_state.wizard_config
        
        # 配置名称
        config.name = st.text_input(
            "配置名称 *",
            value=config.name,
            placeholder="例如：语文作文批改配置",
            help="为您的批改配置起一个有意义的名称"
        )
        
        # 学科选择
        subject_options = {
            "语文": SubjectType.CHINESE,
            "数学": SubjectType.MATH,
            "英语": SubjectType.ENGLISH,
            "物理": SubjectType.PHYSICS,
            "化学": SubjectType.CHEMISTRY,
            "生物": SubjectType.BIOLOGY,
            "历史": SubjectType.HISTORY,
            "地理": SubjectType.GEOGRAPHY,
            "政治": SubjectType.POLITICS,
            "其他": SubjectType.OTHER
        }
        
        selected_subject = st.selectbox(
            "学科 *",
            options=list(subject_options.keys()),
            index=list(subject_options.values()).index(config.subject),
            help="选择适用的学科"
        )
        config.subject = subject_options[selected_subject]
        
        # 年级选择
        grade_options = {
            "小学1-3年级": GradeLevel.PRIMARY_1_3,
            "小学4-6年级": GradeLevel.PRIMARY_4_6,
            "初中7-9年级": GradeLevel.MIDDLE_7_9,
            "高中10-12年级": GradeLevel.HIGH_10_12,
            "大学": GradeLevel.UNIVERSITY,
            "其他": GradeLevel.OTHER
        }
        
        selected_grade = st.selectbox(
            "年级水平 *",
            options=list(grade_options.keys()),
            index=list(grade_options.values()).index(config.grade_level),
            help="选择适用的年级水平"
        )
        config.grade_level = grade_options[selected_grade]
        
        # 验证
        if config.name.strip():
            st.success("✅ 基本信息已填写完整")
        else:
            st.warning("⚠️ 请填写配置名称")
    
    def _render_template_selection_step(self):
        """渲染模板选择步骤"""
        st.markdown("#### 🎯 第2步：选择模板")
        st.markdown("选择一个预设模板作为起点，或从空白开始创建")
        
        config = st.session_state.wizard_config
        
        # 获取推荐模板
        recommended_templates = self.config_service.get_recommended_templates(
            config.subject, config.grade_level
        )
        
        # 模板选择选项
        template_options = ["从空白开始"] + [f"{t.name} - {t.description}" for t in recommended_templates]
        
        selected_option = st.selectbox(
            "选择模板",
            options=template_options,
            help="推荐模板基于您选择的学科和年级"
        )
        
        if selected_option == "从空白开始":
            st.session_state.wizard_selected_template = None
            st.info("💡 您将从空白配置开始创建")
        else:
            # 找到选中的模板
            template_index = template_options.index(selected_option) - 1
            selected_template = recommended_templates[template_index]
            st.session_state.wizard_selected_template = selected_template
            
            # 显示模板详情
            with st.expander("📖 模板详情", expanded=True):
                st.write(f"**名称**: {selected_template.name}")
                st.write(f"**描述**: {selected_template.description}")
                st.write(f"**学科**: {selected_template.subject.value}")
                st.write(f"**年级**: {selected_template.grade_level.value}")
                st.write(f"**使用次数**: {selected_template.usage_count}")
                
                # 显示评分规则
                st.write("**评分规则**:")
                for rule in selected_template.config.scoring_rules:
                    st.write(f"- {rule.name}: {rule.max_score}分")
            
            st.success("✅ 模板已选择，将在下一步应用")
    
    def _render_scoring_rules_step(self):
        """渲染评分规则步骤"""
        st.markdown("#### ⚖️ 第3步：评分规则")
        st.markdown("设置详细的评分规则和标准")
        
        config = st.session_state.wizard_config
        
        # 如果选择了模板，应用模板配置
        if st.session_state.wizard_selected_template and not config.scoring_rules:
            template = st.session_state.wizard_selected_template
            config.scoring_rules = [
                ScoringRule(
                    name=rule.name,
                    description=rule.description,
                    max_score=rule.max_score,
                    criteria=rule.criteria.copy(),
                    auto_grading=rule.auto_grading,
                    weight=rule.weight
                ) for rule in template.config.scoring_rules
            ]
        
        # 显示现有规则
        st.write("**当前评分规则**:")
        
        if not config.scoring_rules:
            st.info("暂无评分规则，请添加至少一个规则")
        
        # 编辑现有规则
        rules_to_remove = []
        for i, rule in enumerate(config.scoring_rules):
            with st.expander(f"📏 {rule.name} ({rule.max_score}分)", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    rule.name = st.text_input(f"规则名称", value=rule.name, key=f"rule_name_{i}")
                    rule.description = st.text_area(f"规则描述", value=rule.description, key=f"rule_desc_{i}")
                    rule.max_score = st.number_input(f"最大分数", value=rule.max_score, min_value=0.0, key=f"rule_score_{i}")
                    
                    # 评分标准
                    st.write("**评分标准**:")
                    criteria_text = "\n".join(rule.criteria)
                    new_criteria_text = st.text_area(
                        "每行一个标准", 
                        value=criteria_text, 
                        key=f"rule_criteria_{i}",
                        help="每行输入一个评分标准"
                    )
                    rule.criteria = [c.strip() for c in new_criteria_text.split('\n') if c.strip()]
                    
                    rule.auto_grading = st.checkbox("启用自动评分", value=rule.auto_grading, key=f"rule_auto_{i}")
                
                with col2:
                    if st.button("🗑️ 删除", key=f"delete_rule_{i}"):
                        rules_to_remove.append(i)
        
        # 删除标记的规则
        for i in reversed(rules_to_remove):
            config.scoring_rules.pop(i)
            st.rerun()
        
        # 添加新规则
        st.markdown("---")
        st.write("**添加新规则**:")
        
        with st.form("add_rule_form"):
            new_rule_name = st.text_input("规则名称", placeholder="例如：内容准确性")
            new_rule_desc = st.text_area("规则描述", placeholder="描述这个评分规则的具体要求")
            new_rule_score = st.number_input("最大分数", value=10.0, min_value=0.0)
            new_rule_criteria = st.text_area("评分标准（每行一个）", placeholder="标准1\n标准2\n标准3")
            new_rule_auto = st.checkbox("启用自动评分", value=True)
            
            if st.form_submit_button("➕ 添加规则"):
                if new_rule_name.strip():
                    criteria_list = [c.strip() for c in new_rule_criteria.split('\n') if c.strip()]
                    new_rule = ScoringRule(
                        name=new_rule_name,
                        description=new_rule_desc,
                        max_score=new_rule_score,
                        criteria=criteria_list,
                        auto_grading=new_rule_auto
                    )
                    config.scoring_rules.append(new_rule)
                    st.success(f"✅ 已添加规则：{new_rule_name}")
                    st.rerun()
                else:
                    st.error("❌ 请填写规则名称")
        
        # 显示总分
        if config.scoring_rules:
            total_score = sum(rule.max_score for rule in config.scoring_rules)
            st.info(f"📊 当前总分：{total_score}分")
    
    def _render_weight_distribution_step(self):
        """渲染权重分配步骤"""
        st.markdown("#### ⚖️ 第4步：权重分配")
        st.markdown("设置不同评分维度的权重分配")
        
        config = st.session_state.wizard_config
        
        st.write("**评分维度权重**:")
        st.write("调整各个维度的重要性，总和必须等于100%")
        
        col1, col2 = st.columns(2)
        
        with col1:
            content_accuracy = st.slider(
                "内容准确性",
                min_value=0.0,
                max_value=1.0,
                value=config.weight_distribution.content_accuracy,
                step=0.05,
                format="%.0f%%",
                help="内容的准确性和相关性"
            )
            
            language_quality = st.slider(
                "语言质量",
                min_value=0.0,
                max_value=1.0,
                value=config.weight_distribution.language_quality,
                step=0.05,
                format="%.0f%%",
                help="语言表达的质量和流畅性"
            )
        
        with col2:
            structure_logic = st.slider(
                "结构逻辑",
                min_value=0.0,
                max_value=1.0,
                value=config.weight_distribution.structure_logic,
                step=0.05,
                format="%.0f%%",
                help="文章结构和逻辑组织"
            )
            
            creativity = st.slider(
                "创新性",
                min_value=0.0,
                max_value=1.0,
                value=config.weight_distribution.creativity,
                step=0.05,
                format="%.0f%%",
                help="创新思维和独特见解"
            )
        
        # 更新权重配置
        config.weight_distribution = WeightConfig(
            content_accuracy=content_accuracy,
            language_quality=language_quality,
            structure_logic=structure_logic,
            creativity=creativity
        )
        
        # 检查权重总和
        total_weight = content_accuracy + language_quality + structure_logic + creativity
        
        if abs(total_weight - 1.0) < 0.01:
            st.success(f"✅ 权重分配正确 (总和: {total_weight:.1%})")
        else:
            st.warning(f"⚠️ 权重总和应为100% (当前: {total_weight:.1%})")
            if st.button("🔧 自动调整权重"):
                config.weight_distribution.normalize()
                st.rerun()
        
        # 权重可视化
        st.write("**权重分布图**:")
        weight_data = {
            "内容准确性": content_accuracy,
            "语言质量": language_quality,
            "结构逻辑": structure_logic,
            "创新性": creativity
        }
        st.bar_chart(weight_data)
    
    def _render_custom_prompts_step(self):
        """渲染自定义提示步骤"""
        st.markdown("#### 💡 第5步：自定义提示")
        st.markdown("添加特定的批改提示和要求")
        
        config = st.session_state.wizard_config
        
        # 如果选择了模板，应用模板的自定义提示
        if st.session_state.wizard_selected_template and not config.custom_prompts:
            template = st.session_state.wizard_selected_template
            config.custom_prompts = template.config.custom_prompts.copy()
        
        st.write("**当前自定义提示**:")
        
        # 显示现有提示
        prompts_to_remove = []
        for i, prompt in enumerate(config.custom_prompts):
            col1, col2 = st.columns([4, 1])
            with col1:
                new_prompt = st.text_area(f"提示 {i+1}", value=prompt, key=f"prompt_{i}")
                config.custom_prompts[i] = new_prompt
            with col2:
                st.write("")  # 空行对齐
                if st.button("🗑️", key=f"delete_prompt_{i}"):
                    prompts_to_remove.append(i)
        
        # 删除标记的提示
        for i in reversed(prompts_to_remove):
            config.custom_prompts.pop(i)
            st.rerun()
        
        # 添加新提示
        st.markdown("---")
        with st.form("add_prompt_form"):
            new_prompt = st.text_area(
                "添加新提示",
                placeholder="例如：请重点关注文章的逻辑结构和论证过程",
                help="输入具体的批改要求或注意事项"
            )
            
            if st.form_submit_button("➕ 添加提示"):
                if new_prompt.strip():
                    config.custom_prompts.append(new_prompt.strip())
                    st.success("✅ 提示已添加")
                    st.rerun()
        
        # 预设提示建议
        if config.subject != SubjectType.OTHER:
            st.markdown("---")
            st.write("**建议提示** (点击添加):")
            
            suggestions = self._get_prompt_suggestions(config.subject)
            for suggestion in suggestions:
                if st.button(f"➕ {suggestion}", key=f"suggest_{suggestion}"):
                    if suggestion not in config.custom_prompts:
                        config.custom_prompts.append(suggestion)
                        st.rerun()
    
    def _render_preview_step(self, on_complete: Optional[Callable[[GradingConfig], None]] = None) -> Optional[GradingConfig]:
        """渲染预览确认步骤"""
        st.markdown("#### 👀 第6步：预览确认")
        st.markdown("检查配置信息并完成创建")
        
        config = st.session_state.wizard_config
        
        # 验证配置
        validation_errors = config.validate()
        
        if validation_errors:
            st.error("❌ 配置验证失败，请修正以下问题：")
            for error in validation_errors:
                st.write(f"- {error}")
            return None
        
        # 显示配置预览
        st.success("✅ 配置验证通过")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**基本信息**:")
            st.write(f"- 名称: {config.name}")
            st.write(f"- 学科: {config.subject.value}")
            st.write(f"- 年级: {config.grade_level.value}")
            st.write(f"- 总分: {config.get_total_score()}分")
            
            st.write("**评分规则**:")
            for rule in config.scoring_rules:
                st.write(f"- {rule.name}: {rule.max_score}分")
        
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
        
        # 保存选项
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            save_as_template = st.checkbox("保存为模板", help="保存为模板供以后使用")
        
        with col2:
            if save_as_template:
                template_name = st.text_input("模板名称", value=f"{config.name}_模板")
        
        # 完成按钮
        if st.button("🎉 完成创建", type="primary"):
            # 设置创建时间
            config.created_at = datetime.now()
            config.updated_at = datetime.now()
            
            # 保存配置
            if self.config_service.save_config(config):
                st.success("✅ 批改配置创建成功！")
                
                # 如果选择保存为模板
                if save_as_template:
                    template = GradingTemplate(
                        name=template_name,
                        description=f"基于配置 '{config.name}' 创建的模板",
                        subject=config.subject,
                        grade_level=config.grade_level,
                        config=config,
                        is_public=False
                    )
                    
                    if self.config_service.save_template(template):
                        st.success("✅ 模板保存成功！")
                
                # 清理会话状态
                self._clear_wizard_state()
                
                # 调用完成回调
                if on_complete:
                    on_complete(config)
                
                return config
            else:
                st.error("❌ 保存配置失败，请重试")
        
        return None
    
    def _render_navigation_buttons(self):
        """渲染导航按钮"""
        current_step = st.session_state.wizard_step
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if current_step > 0:
                if st.button("⬅️ 上一步"):
                    st.session_state.wizard_step -= 1
                    st.rerun()
        
        with col3:
            if current_step < len(self.steps) - 1:
                # 检查当前步骤是否可以继续
                can_continue = self._can_continue_from_step(current_step)
                
                if st.button("下一步 ➡️", disabled=not can_continue):
                    st.session_state.wizard_step += 1
                    st.rerun()
                
                if not can_continue:
                    st.warning("⚠️ 请完成当前步骤的必填项")
    
    def _can_continue_from_step(self, step: int) -> bool:
        """检查是否可以从当前步骤继续"""
        config = st.session_state.wizard_config
        
        if step == 0:  # 基本信息
            return bool(config.name.strip())
        elif step == 2:  # 评分规则
            return len(config.scoring_rules) > 0
        
        return True
    
    def _clear_wizard_state(self):
        """清理向导状态"""
        if 'wizard_step' in st.session_state:
            del st.session_state.wizard_step
        if 'wizard_config' in st.session_state:
            del st.session_state.wizard_config
        if 'wizard_selected_template' in st.session_state:
            del st.session_state.wizard_selected_template
    
    def _get_prompt_suggestions(self, subject: SubjectType) -> List[str]:
        """获取学科相关的提示建议"""
        suggestions = {
            SubjectType.CHINESE: [
                "请重点关注文章的主题表达和思想深度",
                "注意语言表达的准确性和流畅性",
                "评价文章结构的合理性和层次性",
                "关注修辞手法的运用效果"
            ],
            SubjectType.MATH: [
                "重点检查解题方法是否正确",
                "仔细核对计算过程中的每一步",
                "确认最终答案的准确性",
                "评估解题思路的清晰度"
            ],
            SubjectType.ENGLISH: [
                "检查内容是否涵盖所有要点",
                "评估语言运用的准确性和丰富性",
                "关注文章的整体结构和逻辑",
                "注意语法和拼写的准确性"
            ]
        }
        
        return suggestions.get(subject, [
            "请根据评分标准进行客观评价",
            "注意给出具体的改进建议",
            "保持评分的一致性和公平性"
        ])