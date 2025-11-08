#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph Workflow - AI批改系统工作流编排
使用 LangGraph StateGraph 编排所有 Agent 的协作流程
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import GradingState
from .agents.upload_validator import UploadValidator
from .agents.ocr_vision_agent import OCRVisionAgent
from .agents.rubric_interpreter import RubricInterpreter
from .agents.scoring_agent import ScoringAgent
from .agents.annotation_builder import AnnotationBuilder
from .agents.knowledge_miner import KnowledgeMiner
from .agents.result_assembler import ResultAssembler

logger = logging.getLogger(__name__)

class AIGradingWorkflow:
    """
    AI批改系统工作流
    使用 LangGraph 编排多个 Agent 的协作流程
    """
    
    def __init__(self):
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_workflow()
    
    def _build_workflow(self):
        """构建工作流图"""
        # 创建状态图
        workflow = StateGraph(GradingState)
        
        # 添加节点（Agent）
        workflow.add_node("upload_validator", UploadValidator())
        workflow.add_node("ocr_vision", OCRVisionAgent())
        workflow.add_node("rubric_interpreter", RubricInterpreter())
        workflow.add_node("scoring", ScoringAgent())
        workflow.add_node("annotation_builder", AnnotationBuilder())
        workflow.add_node("knowledge_miner", KnowledgeMiner())
        workflow.add_node("result_assembler", ResultAssembler())
        
        # 定义工作流边（执行顺序）
        workflow.set_entry_point("upload_validator")
        
        # 线性执行流程
        workflow.add_edge("upload_validator", "ocr_vision")
        workflow.add_edge("ocr_vision", "rubric_interpreter")
        workflow.add_edge("rubric_interpreter", "scoring")
        workflow.add_edge("scoring", "annotation_builder")
        workflow.add_edge("annotation_builder", "knowledge_miner")
        workflow.add_edge("knowledge_miner", "result_assembler")
        workflow.add_edge("result_assembler", END)
        
        # 编译图
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        
        logger.info("AI批改工作流构建完成")
    
    async def run_grading(
        self,
        task_id: str,
        user_id: str,
        question_files: List[str],
        answer_files: List[str],
        marking_files: List[str] = None,
        mode: str = "auto",
        strictness_level: str = "中等",
        language: str = "zh"
    ) -> Dict[str, Any]:
        """
        运行批改流程
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            question_files: 题目文件列表
            answer_files: 答案文件列表
            marking_files: 评分标准文件列表
            mode: 批改模式
            strictness_level: 严格程度
            language: 语言
            
        Returns:
            批改结果
        """
        logger.info(f"开始AI批改流程 - 任务ID: {task_id}")
        
        try:
            # 初始化状态
            initial_state = self._create_initial_state(
                task_id=task_id,
                user_id=user_id,
                question_files=question_files,
                answer_files=answer_files,
                marking_files=marking_files or [],
                mode=mode,
                strictness_level=strictness_level,
                language=language
            )
            
            # 运行工作流
            config = {"configurable": {"thread_id": task_id}}
            
            final_state = None
            async for state in self.graph.astream(initial_state, config=config):
                final_state = state
                
                # 记录进度
                current_step = list(state.keys())[0] if state else "unknown"
                progress = state.get(current_step, {}).get('progress_percentage', 0)
                logger.info(f"工作流进度 - 步骤: {current_step}, 进度: {progress}%")
            
            # 提取最终结果
            if final_state:
                result_key = list(final_state.keys())[0]
                result = final_state[result_key]
                
                logger.info(f"AI批改流程完成 - 任务ID: {task_id}, 得分: {result.get('final_score', 0)}")
                return result
            else:
                raise Exception("工作流执行失败，未获得最终结果")
                
        except Exception as e:
            error_msg = f"AI批改流程失败: {str(e)}"
            logger.error(error_msg)
            
            # 返回错误结果
            return {
                'task_id': task_id,
                'completion_status': 'failed',
                'errors': [{'error': error_msg, 'timestamp': str(datetime.now())}],
                'final_score': 0,
                'grade_level': 'F'
            }
    
    def _create_initial_state(
        self,
        task_id: str,
        user_id: str,
        question_files: List[str],
        answer_files: List[str],
        marking_files: List[str],
        mode: str,
        strictness_level: str,
        language: str
    ) -> GradingState:
        """创建初始状态"""
        return {
            # 基础任务信息
            'task_id': task_id,
            'user_id': user_id,
            'timestamp': datetime.now(),
            'current_step': 'initializing',
            'progress_percentage': 0.0,
            'completion_status': 'in_progress',
            
            # 配置参数
            'mode': mode,
            'strictness_level': strictness_level,
            'language': language,
            
            # 文件信息
            'question_files': question_files,
            'answer_files': answer_files,
            'marking_files': marking_files,
            
            # 处理结果（初始化为空）
            'ocr_results': {},
            'image_regions': {},
            'preprocessed_images': {},
            'rubric_data': {},
            'scoring_criteria': [],
            'scoring_results': {},
            'coordinate_annotations': [],
            'error_regions': [],
            'cropped_regions': [],
            'knowledge_points': [],
            'error_analysis': {},
            'learning_suggestions': [],
            'difficulty_assessment': {},
            
            # 最终结果
            'final_score': 0.0,
            'grade_level': 'F',
            'detailed_feedback': [],
            'final_report': {},
            'export_data': {},
            'visualization_data': {},
            
            # 错误和步骤记录
            'errors': [],
            'step_results': {}
        }
    
    async def get_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度"""
        try:
            config = {"configurable": {"thread_id": task_id}}
            
            # 获取最新状态
            state = await self.graph.aget_state(config)
            
            if state and state.values:
                current_state = state.values
                return {
                    'task_id': task_id,
                    'current_step': current_state.get('current_step', 'unknown'),
                    'progress_percentage': current_state.get('progress_percentage', 0),
                    'completion_status': current_state.get('completion_status', 'unknown'),
                    'errors': current_state.get('errors', []),
                    'step_results': current_state.get('step_results', {})
                }
            else:
                return {
                    'task_id': task_id,
                    'current_step': 'not_found',
                    'progress_percentage': 0,
                    'completion_status': 'not_found',
                    'errors': [],
                    'step_results': {}
                }
                
        except Exception as e:
            logger.error(f"获取进度失败: {e}")
            return {
                'task_id': task_id,
                'current_step': 'error',
                'progress_percentage': 0,
                'completion_status': 'error',
                'errors': [{'error': str(e), 'timestamp': str(datetime.now())}],
                'step_results': {}
            }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            # LangGraph 的取消机制（如果支持的话）
            logger.info(f"取消任务: {task_id}")
            return True
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息"""
        return {
            'name': 'AI批改系统工作流',
            'version': '1.0.0',
            'nodes': [
                'upload_validator',
                'ocr_vision', 
                'rubric_interpreter',
                'scoring',
                'annotation_builder',
                'knowledge_miner',
                'result_assembler'
            ],
            'description': '基于LangGraph的AI智能批改系统，支持多Agent协作',
            'features': [
                '文件验证和预处理',
                'OCR文字识别和图像分析',
                '评分标准解析',
                'AI智能评分',
                '坐标标注生成',
                '知识点挖掘和错题分析',
                '结果汇总和报告生成'
            ]
        }

# 全局工作流实例
_workflow_instance = None

def get_workflow() -> AIGradingWorkflow:
    """获取工作流实例（单例模式）"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = AIGradingWorkflow()
    return _workflow_instance

async def run_ai_grading(
    task_id: str,
    user_id: str,
    question_files: List[str],
    answer_files: List[str],
    marking_files: List[str] = None,
    mode: str = "auto",
    strictness_level: str = "中等",
    language: str = "zh"
) -> Dict[str, Any]:
    """
    运行AI批改（便捷函数）
    """
    workflow = get_workflow()
    return await workflow.run_grading(
        task_id=task_id,
        user_id=user_id,
        question_files=question_files,
        answer_files=answer_files,
        marking_files=marking_files,
        mode=mode,
        strictness_level=strictness_level,
        language=language
    )

async def get_grading_progress(task_id: str) -> Dict[str, Any]:
    """
    获取批改进度（便捷函数）
    """
    workflow = get_workflow()
    return await workflow.get_progress(task_id)
