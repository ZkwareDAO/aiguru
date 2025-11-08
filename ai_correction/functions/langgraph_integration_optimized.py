#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的 LangGraph 集成模块
提供高效的批改接口，不包含OCR处理
"""

import os
import logging
import asyncio
import uuid
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入简化的 LangGraph 工作流
from .langgraph.workflow_simplified import get_workflow, run_ai_grading, get_grading_progress

logger = logging.getLogger(__name__)

class SimplifiedLangGraphIntegration:
    """
    简化的 LangGraph 集成类
    提供高效批改接口，不包含OCR处理
    """

    def __init__(self):
        self.active_tasks = {}  # 活跃任务记录
        self.performance_stats = {
            'total_requests': 0,
            'average_processing_time': 0.0,
            'successful_requests': 0,
            'failed_requests': 0
        }
        self.workflow = None
        self._initialize_workflow()
        
    def _initialize_workflow(self):
        """初始化简化工作流"""
        try:
            self.workflow = get_workflow()
            logger.info("简化 LangGraph 工作流初始化成功")
        except Exception as e:
            logger.error(f"LangGraph 工作流初始化失败: {e}")
            self.workflow = None
    
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
        使用简化的 LangGraph 进行智能批改

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
        start_time = time.time()
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        # 更新统计
        self.performance_stats['total_requests'] += 1

        try:
            logger.info(f"开始批改 - 任务ID: {task_id}")

            # 记录活跃任务
            self.active_tasks[task_id] = {
                'start_time': start_time,
                'status': 'running'
            }

            # 运行批改流程
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

            # 计算处理时间
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time

            # 更新统计
            self._update_performance_stats(processing_time, True)

            # 清理活跃任务
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

            logger.info(f"批改完成 - 任务ID: {task_id}, 耗时: {processing_time:.2f}s")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"批改失败: {str(e)}"
            logger.error(f"{error_msg} - 任务ID: {task_id}")

            # 更新统计
            self._update_performance_stats(processing_time, False)

            # 清理活跃任务
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

            return {
                'task_id': task_id,
                'success': False,
                'error': error_msg,
                'feedback': f"批改失败: {error_msg}",
                'processing_time': processing_time
            }
    
    def _update_performance_stats(self, processing_time: float, success: bool):
        """更新性能统计"""
        if success:
            self.performance_stats['successful_requests'] += 1
        else:
            self.performance_stats['failed_requests'] += 1
        
        # 更新平均处理时间
        total_successful = self.performance_stats['successful_requests']
        if total_successful > 0:
            current_avg = self.performance_stats['average_processing_time']
            self.performance_stats['average_processing_time'] = (
                (current_avg * (total_successful - 1) + processing_time) / total_successful
            )
    
    async def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度"""
        try:
            if task_id in self.active_tasks:
                # 获取 LangGraph 进度
                progress = await get_grading_progress(task_id)
                
                # 添加本地任务信息
                local_info = self.active_tasks[task_id]
                progress.update({
                    'local_start_time': local_info['start_time'],
                    'elapsed_time': time.time() - local_info['start_time'],
                    'optimization_level': local_info['optimization_level']
                })
                
                return progress
            else:
                return {
                    'task_id': task_id,
                    'status': 'not_found',
                    'message': '任务不存在或已完成'
                }
                
        except Exception as e:
            logger.error(f"获取任务进度失败: {e}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self.performance_stats,
            'active_tasks_count': len(self.active_tasks),
            'workflow_status': 'initialized' if self.workflow else 'failed',
            'workflow_type': 'simplified_no_ocr'
        }

    def clear_cache(self):
        """清理缓存"""
        logger.info("简化工作流无缓存需要清理")
        return True
    
    def reset_stats(self):
        """重置性能统计"""
        self.performance_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'average_processing_time': 0.0,
            'token_savings_percentage': 0,
            'successful_requests': 0,
            'failed_requests': 0
        }
        logger.info("性能统计已重置")

# 全局实例
_simplified_integration_instance = None

def get_simplified_langgraph_integration() -> SimplifiedLangGraphIntegration:
    """获取简化的 LangGraph 集成实例（单例模式）"""
    global _simplified_integration_instance
    if _simplified_integration_instance is None:
        _simplified_integration_instance = SimplifiedLangGraphIntegration()
    return _simplified_integration_instance

def intelligent_correction_with_files_langgraph_simplified(
    question_files: List[str],
    answer_files: List[str],
    marking_scheme_files: Optional[List[str]] = None,
    strictness_level: str = "中等",
    language: str = "zh",
    mode: str = "auto"
) -> str:
    """
    简化的兼容性函数 - 与现有 intelligent_correction_with_files 接口兼容
    返回文本格式的批改结果
    不包含OCR处理
    """
    try:
        integration = get_simplified_langgraph_integration()

        # 运行异步批改
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
        finally:
            loop.close()

        # 转换为文本格式
        if result.get('success', True):
            feedback_parts = []

            # 基本信息
            feedback_parts.append("📊 批改结果")
            feedback_parts.append(f"得分: {result.get('final_score', 0)}")
            feedback_parts.append(f"等级: {result.get('grade_level', 'N/A')}")
            feedback_parts.append(f"处理时间: {result.get('processing_time', 0):.2f}秒")
            feedback_parts.append("")

            # 详细反馈
            detailed_feedback = result.get('detailed_feedback', [])
            if detailed_feedback:
                feedback_parts.append("📝 详细反馈:")
                for feedback in detailed_feedback:
                    if isinstance(feedback, dict):
                        feedback_parts.append(feedback.get('content', str(feedback)))
                    else:
                        feedback_parts.append(str(feedback))
                feedback_parts.append("")

            # 学习建议
            suggestions = result.get('learning_suggestions', [])
            if suggestions:
                feedback_parts.append("💡 学习建议:")
                for suggestion in suggestions:
                    feedback_parts.append(f"• {suggestion}")
                feedback_parts.append("")

            # 知识点分析
            knowledge_points = result.get('knowledge_points', [])
            if knowledge_points:
                feedback_parts.append(f"🧠 知识点分析: {len(knowledge_points)} 个")

            return "\n".join(feedback_parts)
        else:
            return result.get('feedback', f"批改失败: {result.get('error', '未知错误')}")

    except Exception as e:
        error_msg = f"批改失败: {str(e)}"
        logger.error(error_msg)
        return error_msg
