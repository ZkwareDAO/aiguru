#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph Workflow - 简化的AI批改系统工作流编排
不包含OCR，直接处理文本
使用 LangGraph StateGraph 编排所有 Agent 的协作流程
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import GradingState
from .agents.upload_validator import UploadValidator
from .agents.rubric_interpreter import RubricInterpreter
from .agents.scoring_agent import ScoringAgent
from .agents.annotation_builder import AnnotationBuilder
from .agents.knowledge_miner import KnowledgeMiner
from .agents.result_assembler import ResultAssembler

logger = logging.getLogger(__name__)

class SimplifiedAIGradingWorkflow:
    """
    简化的AI批改系统工作流
    核心流程：上传验证 → 评分标准解析 → 评分 → 标注生成 → 知识点挖掘 → 结果汇总
    不包含OCR处理
    """

    def __init__(self):
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_workflow()

    def _build_workflow(self):
        """构建简化的工作流图"""
        workflow = StateGraph(GradingState)

        # 初始化所有 Agent
        upload_validator = UploadValidator()
        rubric_interpreter = RubricInterpreter()
        scoring_agent = ScoringAgent()
        annotation_builder = AnnotationBuilder()
        knowledge_miner = KnowledgeMiner()
        result_assembler = ResultAssembler()

        # 添加节点
        workflow.add_node("upload_validator", upload_validator.validate)
        workflow.add_node("rubric_interpreter", rubric_interpreter.interpret)
        workflow.add_node("scoring", scoring_agent.score)
        workflow.add_node("annotation_builder", annotation_builder.build)
        workflow.add_node("knowledge_miner", knowledge_miner.mine)
        workflow.add_node("result_assembler", result_assembler.assemble)

        # 定义边（流程）
        # 1. 上传验证 → 评分标准解析 + 评分
        workflow.add_edge("upload_validator", "rubric_interpreter")
        workflow.add_edge("upload_validator", "scoring")

        # 2. 评分标准解析 → 评分
        workflow.add_edge("rubric_interpreter", "scoring")

        # 3. 评分 → 并行处理（标注生成 + 知识点挖掘）
        workflow.add_edge("scoring", "annotation_builder")
        workflow.add_edge("scoring", "knowledge_miner")

        # 4. 标注生成 → 结果汇总
        workflow.add_edge("annotation_builder", "result_assembler")

        # 5. 知识点挖掘 → 结果汇总
        workflow.add_edge("knowledge_miner", "result_assembler")

        # 6. 结果汇总 → 结束
        workflow.add_edge("result_assembler", END)

        # 设置入口点
        workflow.set_entry_point("upload_validator")

        # 编译图
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("简化的AI批改工作流已构建")

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行工作流
        
        Args:
            state: 初始状态字典
            
        Returns:
            最终结果字典
        """
        try:
            logger.info(f"开始执行批改流程 - 任务ID: {state.get('task_id')}")
            
            # 运行图
            result = self.graph.invoke(state)
            
            logger.info(f"批改流程完成 - 任务ID: {state.get('task_id')}")
            return result
            
        except Exception as e:
            logger.error(f"批改流程失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'task_id': state.get('task_id')
            }

    async def run_async(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步运行工作流
        
        Args:
            state: 初始状态字典
            
        Returns:
            最终结果字典
        """
        return self.run(state)

    def stream(self, state: Dict[str, Any]):
        """
        流式运行工作流，实时获取进度
        
        Args:
            state: 初始状态字典
            
        Yields:
            每个节点的执行结果
        """
        try:
            logger.info(f"开始流式执行批改流程 - 任务ID: {state.get('task_id')}")
            
            for output in self.graph.stream(state):
                yield output
                
            logger.info(f"流式执行完成 - 任务ID: {state.get('task_id')}")
            
        except Exception as e:
            logger.error(f"流式执行失败: {e}")
            yield {
                'error': {
                    'success': False,
                    'error': str(e),
                    'task_id': state.get('task_id')
                }
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'workflow_type': 'simplified',
            'nodes_count': 6,
            'has_ocr': False,
            'timestamp': datetime.now().isoformat()
        }

    def clear_cache(self):
        """清理缓存"""
        logger.info("简化工作流无缓存需要清理")
        return True

# 全局工作流实例
_workflow_instance = None

def get_workflow() -> SimplifiedAIGradingWorkflow:
    """获取工作流实例（单例模式）"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = SimplifiedAIGradingWorkflow()
    return _workflow_instance

async def run_ai_grading(
    task_id: str,
    user_id: str,
    question_files: List[str],
    answer_files: List[str],
    marking_files: List[str],
    mode: str = "auto",
    strictness_level: str = "中等",
    language: str = "zh"
) -> Dict[str, Any]:
    """
    运行AI批改流程
    
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
    workflow = get_workflow()
    
    # 构建初始状态
    state = {
        'task_id': task_id,
        'user_id': user_id,
        'question_files': question_files,
        'answer_files': answer_files,
        'marking_files': marking_files,
        'mode': mode,
        'strictness_level': strictness_level,
        'language': language,
        'timestamp': datetime.now().isoformat()
    }
    
    # 运行工作流
    result = await workflow.run_async(state)
    
    return result

async def get_grading_progress(task_id: str) -> Dict[str, Any]:
    """
    获取批改进度
    
    Args:
        task_id: 任务ID
        
    Returns:
        进度信息
    """
    return {
        'task_id': task_id,
        'status': 'completed',
        'message': '任务已完成'
    }

# 导出主要函数
__all__ = [
    'SimplifiedAIGradingWorkflow',
    'get_workflow',
    'run_ai_grading',
    'get_grading_progress'
]
