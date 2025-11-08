#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scoring Agent - AI智能评分
集成现有的 calling_api.py，提供智能评分功能
"""

import os
import logging
import json
from typing import Dict, List, Any
from datetime import datetime

# 导入现有的 API 调用功能
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api_correcting.calling_api import (
    intelligent_correction_with_files,
    correction_single_group,
    correction_with_marking_scheme,
    correction_without_marking_scheme
)

from ..state import GradingState

logger = logging.getLogger(__name__)

class ScoringAgent:
    """
    AI评分代理
    集成现有的 calling_api.py 功能，提供智能评分
    """
    
    def __init__(self):
        self.supported_modes = ['efficient', 'detailed', 'batch', 'generate_scheme', 'auto']
        
    async def __call__(self, state: GradingState) -> GradingState:
        """
        执行AI评分
        """
        logger.info(f"开始AI评分 - 任务ID: {state['task_id']}")
        
        try:
            # 更新进度
            state['current_step'] = "AI智能评分"
            state['progress_percentage'] = 60.0
            
            # 获取评分参数
            mode = state.get('mode', 'auto')
            strictness_level = state.get('strictness_level', '中等')
            language = state.get('language', 'zh')
            
            # 获取文件路径
            question_files = state.get('question_files', [])
            answer_files = state.get('answer_files', [])
            marking_files = state.get('marking_files', [])
            
            # 执行评分
            scoring_results = await self._perform_scoring(
                question_files, answer_files, marking_files,
                mode, strictness_level, language
            )
            
            # 解析评分结果
            parsed_results = await self._parse_scoring_results(scoring_results)
            
            # 更新状态
            state['scoring_results'] = parsed_results
            state['final_score'] = parsed_results.get('final_score', 0)
            state['grade_level'] = parsed_results.get('grade_level', 'C')
            state['detailed_feedback'] = parsed_results.get('detailed_feedback', [])
            
            # 更新进度
            state['progress_percentage'] = 70.0
            state['step_results']['scoring'] = {
                'final_score': state['final_score'],
                'grade_level': state['grade_level'],
                'feedback_count': len(state['detailed_feedback'])
            }
            
            logger.info(f"AI评分完成 - 任务ID: {state['task_id']}, 得分: {state['final_score']}")
            return state
            
        except Exception as e:
            error_msg = f"AI评分失败: {str(e)}"
            logger.error(error_msg)
            state['errors'].append({
                'step': 'scoring',
                'error': error_msg,
                'timestamp': str(datetime.now())
            })
            raise
    
    async def _perform_scoring(
        self,
        question_files: List[str],
        answer_files: List[str], 
        marking_files: List[str],
        mode: str,
        strictness_level: str,
        language: str
    ) -> str:
        """执行评分"""
        try:
            # 使用现有的智能批改功能
            result = intelligent_correction_with_files(
                question_files=question_files,
                answer_files=answer_files,
                marking_scheme_files=marking_files,
                strictness_level=strictness_level,
                language=language,
                mode=mode
            )
            return result
            
        except Exception as e:
            logger.warning(f"智能批改失败，尝试备选方案: {e}")
            
            # 备选方案：根据是否有评分标准选择不同的方法
            if marking_files:
                # 有评分标准，使用标准批改
                marking_scheme = self._load_marking_scheme(marking_files[0])
                result = correction_with_marking_scheme(
                    marking_scheme,
                    *answer_files,
                    strictness_level=strictness_level,
                    language=language
                )
            else:
                # 无评分标准，自动生成并批改
                result = correction_without_marking_scheme(
                    *answer_files,
                    strictness_level=strictness_level,
                    language=language
                )
            
            return result
    
    def _load_marking_scheme(self, marking_file: str) -> str:
        """加载评分标准"""
        try:
            # 如果是文本文件，直接读取
            if marking_file.endswith(('.txt', '.md')):
                with open(marking_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                # 如果是图像文件，需要OCR识别
                # 这里可以调用OCR功能，暂时返回默认标准
                return "请根据标准答案进行评分"
        except Exception as e:
            logger.warning(f"加载评分标准失败: {e}")
            return "请根据标准答案进行评分"
    
    async def _parse_scoring_results(self, raw_result: str) -> Dict[str, Any]:
        """解析评分结果"""
        try:
            # 尝试解析JSON格式的结果
            if raw_result.strip().startswith('{'):
                json_result = json.loads(raw_result)
                return self._process_json_result(json_result)
            else:
                # 解析文本格式的结果
                return self._process_text_result(raw_result)
                
        except Exception as e:
            logger.warning(f"解析评分结果失败: {e}")
            return self._create_fallback_result(raw_result)
    
    def _process_json_result(self, json_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理JSON格式的评分结果"""
        return {
            'final_score': json_result.get('score', 0),
            'grade_level': json_result.get('grade', 'C'),
            'detailed_feedback': json_result.get('feedback', []),
            'errors': json_result.get('errors', []),
            'strengths': json_result.get('strengths', []),
            'suggestions': json_result.get('suggestions', []),
            'raw_result': json_result
        }
    
    def _process_text_result(self, text_result: str) -> Dict[str, Any]:
        """处理文本格式的评分结果"""
        # 提取得分
        score = self._extract_score_from_text(text_result)
        
        # 提取等级
        grade = self._extract_grade_from_text(text_result)
        
        # 提取反馈
        feedback = self._extract_feedback_from_text(text_result)
        
        return {
            'final_score': score,
            'grade_level': grade,
            'detailed_feedback': feedback,
            'errors': [],
            'strengths': [],
            'suggestions': [],
            'raw_result': text_result
        }
    
    def _extract_score_from_text(self, text: str) -> float:
        """从文本中提取得分"""
        import re
        
        # 查找得分模式
        score_patterns = [
            r'得分[：:]\s*(\d+(?:\.\d+)?)',
            r'分数[：:]\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*分',
            r'(\d+(?:\.\d+)?)/\d+',
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return 0.0
    
    def _extract_grade_from_text(self, text: str) -> str:
        """从文本中提取等级"""
        import re
        
        # 查找等级模式
        grade_patterns = [
            r'等级[：:]\s*([A-F][+-]?)',
            r'级别[：:]\s*([A-F][+-]?)',
            r'([A-F][+-]?)\s*等',
        ]
        
        for pattern in grade_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # 根据得分推断等级
        score = self._extract_score_from_text(text)
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _extract_feedback_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取反馈"""
        feedback = []
        
        # 分割文本为段落
        paragraphs = text.split('\n')
        
        current_feedback = {}
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 识别不同类型的反馈
            if any(keyword in paragraph for keyword in ['错误', '问题', '不正确']):
                if current_feedback:
                    feedback.append(current_feedback)
                current_feedback = {
                    'type': 'error',
                    'content': paragraph,
                    'severity': 'medium'
                }
            elif any(keyword in paragraph for keyword in ['正确', '很好', '优秀']):
                if current_feedback:
                    feedback.append(current_feedback)
                current_feedback = {
                    'type': 'strength',
                    'content': paragraph,
                    'severity': 'low'
                }
            elif any(keyword in paragraph for keyword in ['建议', '改进', '可以']):
                if current_feedback:
                    feedback.append(current_feedback)
                current_feedback = {
                    'type': 'suggestion',
                    'content': paragraph,
                    'severity': 'low'
                }
            else:
                # 通用反馈
                if current_feedback:
                    current_feedback['content'] += '\n' + paragraph
                else:
                    current_feedback = {
                        'type': 'general',
                        'content': paragraph,
                        'severity': 'low'
                    }
        
        if current_feedback:
            feedback.append(current_feedback)
        
        return feedback
    
    def _create_fallback_result(self, raw_result: str) -> Dict[str, Any]:
        """创建备选结果"""
        return {
            'final_score': 0.0,
            'grade_level': 'F',
            'detailed_feedback': [{
                'type': 'error',
                'content': '评分结果解析失败，请检查原始结果',
                'severity': 'high'
            }],
            'errors': ['评分结果解析失败'],
            'strengths': [],
            'suggestions': ['请重新提交进行评分'],
            'raw_result': raw_result
        }
