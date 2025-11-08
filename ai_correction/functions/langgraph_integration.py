#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph Integration - 集成 LangGraph 到现有的 Streamlit 应用
提供与现有 calling_api.py 兼容的接口
"""

import os
import logging
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入 LangGraph 工作流
from .langgraph.workflow import run_ai_grading, get_grading_progress

logger = logging.getLogger(__name__)

class LangGraphIntegration:
    """
    LangGraph 集成类
    提供与现有 Streamlit 应用的集成接口
    """
    
    def __init__(self):
        self.active_tasks = {}  # 活跃任务记录
        
    async def intelligent_correction_with_langgraph(
        self,
        question_files: List[str],
        answer_files: List[str],
        marking_scheme_files: Optional[List[str]] = None,
        strictness_level: str = "中等",
        language: str = "zh",
        mode: str = "auto",
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        使用 LangGraph 进行智能批改
        兼容现有的 intelligent_correction_with_files 接口
        
        Args:
            question_files: 题目文件列表
            answer_files: 答案文件列表
            marking_scheme_files: 评分标准文件列表
            strictness_level: 严格程度
            language: 语言
            mode: 批改模式
            user_id: 用户ID
            
        Returns:
            批改结果字典
        """
        # 生成任务ID
        task_id = f"task_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        
        logger.info(f"开始LangGraph批改 - 任务ID: {task_id}")
        
        try:
            # 记录任务开始
            self.active_tasks[task_id] = {
                'status': 'running',
                'start_time': datetime.now(),
                'progress': 0
            }
            
            # 运行 LangGraph 工作流
            result = await run_ai_grading(
                task_id=task_id,
                user_id=user_id,
                question_files=question_files,
                answer_files=answer_files,
                marking_files=marking_scheme_files or [],
                mode=mode,
                strictness_level=strictness_level,
                language=language
            )
            
            # 更新任务状态
            self.active_tasks[task_id]['status'] = 'completed'
            self.active_tasks[task_id]['result'] = result
            
            # 转换为兼容格式
            compatible_result = self._convert_to_compatible_format(result)
            
            logger.info(f"LangGraph批改完成 - 任务ID: {task_id}, 得分: {result.get('final_score', 0)}")
            return compatible_result
            
        except Exception as e:
            error_msg = f"LangGraph批改失败: {str(e)}"
            logger.error(error_msg)
            
            # 更新任务状态
            self.active_tasks[task_id]['status'] = 'failed'
            self.active_tasks[task_id]['error'] = error_msg
            
            # 返回错误结果
            return {
                'success': False,
                'error': error_msg,
                'task_id': task_id,
                'score': 0,
                'grade': 'F',
                'feedback': error_msg
            }
    
    def _convert_to_compatible_format(self, langgraph_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 LangGraph 结果转换为与现有接口兼容的格式
        """
        # 提取基本信息
        final_score = langgraph_result.get('final_score', 0)
        grade_level = langgraph_result.get('grade_level', 'F')
        
        # 提取详细反馈
        detailed_feedback = langgraph_result.get('detailed_feedback', [])
        feedback_text = self._format_feedback_text(detailed_feedback)
        
        # 提取错误信息
        errors = langgraph_result.get('errors', [])
        error_text = '; '.join([err.get('error', '') for err in errors]) if errors else ''
        
        # 构建兼容格式
        compatible_result = {
            'success': langgraph_result.get('completion_status') == 'completed',
            'task_id': langgraph_result.get('task_id', ''),
            'score': final_score,
            'grade': grade_level,
            'feedback': feedback_text,
            'error': error_text,
            
            # 扩展信息（保留 LangGraph 的优势）
            'langgraph_result': langgraph_result,
            'coordinate_annotations': langgraph_result.get('coordinate_annotations', []),
            'error_regions': langgraph_result.get('error_regions', []),
            'cropped_regions': langgraph_result.get('cropped_regions', []),
            'knowledge_points': langgraph_result.get('knowledge_points', []),
            'learning_suggestions': langgraph_result.get('learning_suggestions', []),
            'final_report': langgraph_result.get('final_report', {}),
            'visualization_data': langgraph_result.get('visualization_data', {})
        }
        
        return compatible_result
    
    def _format_feedback_text(self, detailed_feedback: List[Dict[str, Any]]) -> str:
        """格式化反馈文本"""
        if not detailed_feedback:
            return "批改完成，请查看详细结果。"
        
        feedback_parts = []
        for feedback in detailed_feedback:
            feedback_type = feedback.get('type', 'general')
            content = feedback.get('content', '')
            
            if feedback_type == 'error':
                feedback_parts.append(f"❌ 错误：{content}")
            elif feedback_type == 'strength':
                feedback_parts.append(f"✅ 优点：{content}")
            elif feedback_type == 'suggestion':
                feedback_parts.append(f"💡 建议：{content}")
            else:
                feedback_parts.append(content)
        
        return '\n'.join(feedback_parts)
    
    async def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度"""
        try:
            # 从 LangGraph 获取进度
            progress_info = await get_grading_progress(task_id)
            
            # 更新本地记录
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['progress'] = progress_info.get('progress_percentage', 0)
                self.active_tasks[task_id]['current_step'] = progress_info.get('current_step', 'unknown')
            
            return progress_info
            
        except Exception as e:
            logger.error(f"获取任务进度失败: {e}")
            return {
                'task_id': task_id,
                'current_step': 'error',
                'progress_percentage': 0,
                'completion_status': 'error',
                'errors': [{'error': str(e)}]
            }
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """获取活跃任务列表"""
        return self.active_tasks.copy()
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的任务"""
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, task_info in self.active_tasks.items():
            start_time = task_info.get('start_time', current_time)
            age_hours = (current_time - start_time).total_seconds() / 3600
            
            if age_hours > max_age_hours and task_info.get('status') in ['completed', 'failed']:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.active_tasks[task_id]
        
        logger.info(f"清理了 {len(tasks_to_remove)} 个过期任务")

# 全局集成实例
_integration_instance = None

def get_langgraph_integration() -> LangGraphIntegration:
    """获取 LangGraph 集成实例（单例模式）"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = LangGraphIntegration()
    return _integration_instance

# 兼容性函数：与现有 calling_api.py 接口保持一致
def intelligent_correction_with_files_langgraph(
    question_files: List[str],
    answer_files: List[str],
    marking_scheme_files: Optional[List[str]] = None,
    strictness_level: str = "中等",
    language: str = "zh",
    mode: str = "auto"
) -> str:
    """
    LangGraph 版本的智能批改函数
    与现有的 intelligent_correction_with_files 接口兼容
    
    Returns:
        批改结果的文本格式（为了兼容现有代码）
    """
    integration = get_langgraph_integration()
    
    # 运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            integration.intelligent_correction_with_langgraph(
                question_files=question_files,
                answer_files=answer_files,
                marking_scheme_files=marking_scheme_files,
                strictness_level=strictness_level,
                language=language,
                mode=mode
            )
        )
        
        # 转换为文本格式（兼容现有代码）
        if result.get('success', False):
            feedback_text = result.get('feedback', '')
            score = result.get('score', 0)
            grade = result.get('grade', 'F')
            
            return f"""
批改完成！

得分：{score}/100
等级：{grade}

详细反馈：
{feedback_text}

任务ID：{result.get('task_id', '')}
            """.strip()
        else:
            error_msg = result.get('error', '批改失败')
            return f"批改失败：{error_msg}"
            
    except Exception as e:
        error_msg = f"LangGraph批改异常: {str(e)}"
        logger.error(error_msg)
        return f"批改失败：{error_msg}"
    finally:
        loop.close()

# 进度查询函数
async def get_correction_progress(task_id: str) -> Dict[str, Any]:
    """获取批改进度"""
    integration = get_langgraph_integration()
    return await integration.get_task_progress(task_id)

# Streamlit 专用的进度显示函数
def show_langgraph_progress(task_id: str, placeholder=None):
    """
    在 Streamlit 中显示 LangGraph 批改进度
    可以集成到现有的进度显示组件中
    """
    import streamlit as st
    import time
    
    integration = get_langgraph_integration()
    
    if placeholder is None:
        placeholder = st.empty()
    
    # 创建异步事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        while True:
            # 获取进度
            progress_info = loop.run_until_complete(
                integration.get_task_progress(task_id)
            )
            
            current_step = progress_info.get('current_step', 'unknown')
            progress_percentage = progress_info.get('progress_percentage', 0)
            completion_status = progress_info.get('completion_status', 'unknown')
            
            # 更新显示
            with placeholder.container():
                st.write(f"**当前步骤**: {current_step}")
                st.progress(progress_percentage / 100.0)
                st.write(f"**进度**: {progress_percentage:.1f}%")
                
                if completion_status in ['completed', 'failed']:
                    if completion_status == 'completed':
                        st.success("✅ 批改完成！")
                    else:
                        st.error("❌ 批改失败")
                    break
                elif completion_status == 'error':
                    st.error("❌ 获取进度失败")
                    break
            
            # 等待一段时间再更新
            time.sleep(2)
            
    except Exception as e:
        st.error(f"进度显示异常: {str(e)}")
    finally:
        loop.close()

# 可视化结果显示函数
def show_langgraph_results(result: Dict[str, Any]):
    """
    在 Streamlit 中显示 LangGraph 批改结果
    包括坐标标注、知识点分析等高级功能
    """
    import streamlit as st
    
    if not result.get('success', False):
        st.error(f"批改失败: {result.get('error', '未知错误')}")
        return
    
    # 基本结果
    col1, col2 = st.columns(2)
    with col1:
        st.metric("得分", f"{result.get('score', 0)}/100")
    with col2:
        st.metric("等级", result.get('grade', 'F'))
    
    # 详细反馈
    st.subheader("📝 详细反馈")
    st.write(result.get('feedback', ''))
    
    # 坐标标注（如果有）
    coordinate_annotations = result.get('coordinate_annotations', [])
    if coordinate_annotations:
        st.subheader("🎯 坐标标注")
        st.write(f"发现 {len(coordinate_annotations)} 个标注区域")
        
        for i, annotation in enumerate(coordinate_annotations[:5]):  # 显示前5个
            with st.expander(f"标注 {i+1}: {annotation.get('annotation_type', 'unknown')}"):
                st.write(f"**内容**: {annotation.get('content', '')}")
                st.write(f"**置信度**: {annotation.get('confidence', 0):.2f}")
                st.write(f"**坐标**: {annotation.get('coordinates', {})}")
    
    # 知识点分析（如果有）
    knowledge_points = result.get('knowledge_points', [])
    if knowledge_points:
        st.subheader("🧠 知识点分析")
        
        for kp in knowledge_points[:3]:  # 显示前3个
            mastery_status = kp.get('mastery_status', 'unknown')
            status_emoji = {'good': '✅', 'fair': '⚠️', 'weak': '❌'}.get(mastery_status, '❓')
            
            st.write(f"{status_emoji} **{kp.get('topic', '')}** ({kp.get('subject', '')})")
            st.write(f"   掌握程度: {mastery_status}")
    
    # 学习建议（如果有）
    learning_suggestions = result.get('learning_suggestions', [])
    if learning_suggestions:
        st.subheader("💡 学习建议")
        for suggestion in learning_suggestions:
            st.write(f"• {suggestion}")
    
    # 显示完整的 LangGraph 结果（可折叠）
    with st.expander("🔍 查看完整结果"):
        st.json(result.get('langgraph_result', {}))
