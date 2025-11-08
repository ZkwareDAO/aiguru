#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knowledge Miner Agent - 知识点挖掘和错题分析
核心功能：分析错题原因、挖掘知识点、生成学习建议
符合原始需求中的关键功能
"""

import os
import logging
import json
from typing import Dict, List, Any, Set
from datetime import datetime
import re

# 导入现有的 API 调用功能
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api_correcting.calling_api import call_api

from ..state import GradingState, KnowledgePoint, ErrorAnalysis

logger = logging.getLogger(__name__)

class KnowledgeMiner:
    """
    知识点挖掘器
    核心功能：错题分析、知识点挖掘、学习建议生成
    这是原始需求中明确要求的核心功能
    """
    
    def __init__(self):
        # 知识点分类体系
        self.knowledge_taxonomy = {
            '数学': {
                '代数': ['方程', '不等式', '函数', '数列', '复数'],
                '几何': ['平面几何', '立体几何', '解析几何', '向量'],
                '概率统计': ['概率', '统计', '排列组合'],
                '微积分': ['极限', '导数', '积分', '微分方程']
            },
            '物理': {
                '力学': ['运动学', '动力学', '静力学', '振动波动'],
                '电磁学': ['电场', '磁场', '电磁感应', '交流电'],
                '热学': ['分子动理论', '热力学定律', '气体'],
                '光学': ['几何光学', '物理光学', '量子光学']
            },
            '化学': {
                '无机化学': ['元素化合物', '化学反应', '化学平衡'],
                '有机化学': ['烷烃', '烯烃', '芳香烃', '官能团'],
                '物理化学': ['化学热力学', '化学动力学', '电化学']
            }
        }
        
        # 错误类型分类
        self.error_types = {
            'calculation': '计算错误',
            'concept': '概念错误', 
            'method': '方法错误',
            'logic': '逻辑错误',
            'careless': '粗心错误',
            'incomplete': '解答不完整',
            'format': '格式错误'
        }
        
    async def __call__(self, state: GradingState) -> GradingState:
        """
        执行知识点挖掘和错题分析
        """
        logger.info(f"开始知识点挖掘和错题分析 - 任务ID: {state['task_id']}")
        
        try:
            # 更新进度
            state['current_step'] = "知识点分析"
            state['progress_percentage'] = 85.0
            
            # 获取评分结果和OCR结果
            scoring_results = state.get('scoring_results', {})
            ocr_results = state.get('ocr_results', {})
            coordinate_annotations = state.get('coordinate_annotations', [])
            
            # 错题分析
            error_analysis = await self._analyze_errors(scoring_results, ocr_results)
            state['error_analysis'] = error_analysis
            
            # 知识点挖掘
            knowledge_points = await self._mine_knowledge_points(
                scoring_results, ocr_results, error_analysis
            )
            state['knowledge_points'] = knowledge_points
            
            # 生成学习建议
            learning_suggestions = await self._generate_learning_suggestions(
                error_analysis, knowledge_points
            )
            state['learning_suggestions'] = learning_suggestions
            
            # 难度评估
            difficulty_assessment = await self._assess_difficulty(
                scoring_results, knowledge_points
            )
            state['difficulty_assessment'] = difficulty_assessment
            
            # 更新进度
            state['progress_percentage'] = 90.0
            state['step_results']['knowledge_miner'] = {
                'errors_analyzed': len(error_analysis.get('errors', [])),
                'knowledge_points_found': len(knowledge_points),
                'suggestions_generated': len(learning_suggestions)
            }
            
            logger.info(f"知识点挖掘和错题分析完成 - 任务ID: {state['task_id']}")
            return state
            
        except Exception as e:
            error_msg = f"知识点挖掘失败: {str(e)}"
            logger.error(error_msg)
            state['errors'].append({
                'step': 'knowledge_miner',
                'error': error_msg,
                'timestamp': str(datetime.now())
            })
            raise
    
    async def _analyze_errors(
        self, 
        scoring_results: Dict[str, Any], 
        ocr_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析错题"""
        error_analysis = {
            'errors': [],
            'error_patterns': [],
            'common_mistakes': [],
            'severity_distribution': {}
        }
        
        # 从评分结果中提取错误信息
        if 'detailed_feedback' in scoring_results:
            for feedback in scoring_results['detailed_feedback']:
                if 'errors' in feedback:
                    for error in feedback['errors']:
                        error_info = await self._analyze_single_error(error, ocr_results)
                        error_analysis['errors'].append(error_info)
        
        # 分析错误模式
        error_analysis['error_patterns'] = await self._identify_error_patterns(
            error_analysis['errors']
        )
        
        # 统计常见错误
        error_analysis['common_mistakes'] = await self._identify_common_mistakes(
            error_analysis['errors']
        )
        
        # 错误严重程度分布
        error_analysis['severity_distribution'] = self._calculate_severity_distribution(
            error_analysis['errors']
        )
        
        return error_analysis
    
    async def _analyze_single_error(
        self, 
        error: Dict[str, Any], 
        ocr_results: Dict[str, Any]
    ) -> ErrorAnalysis:
        """分析单个错误"""
        # 使用AI分析错误
        analysis_prompt = f"""
        请分析以下错误信息，并提供详细的错误分析：
        
        错误描述：{error.get('description', '')}
        错误类型：{error.get('type', '')}
        学生答案：{error.get('student_answer', '')}
        正确答案：{error.get('correct_answer', '')}
        
        请分析：
        1. 错误的根本原因
        2. 涉及的知识点
        3. 可能的知识缺陷
        4. 改进建议
        
        请以JSON格式返回分析结果。
        """
        
        try:
            # 调用AI进行错误分析
            ai_response = await self._call_ai_for_analysis(analysis_prompt)
            ai_analysis = json.loads(ai_response)
            
            error_analysis = {
                'error_id': error.get('id', f"error_{datetime.now().timestamp()}"),
                'error_type': self._classify_error_type(error, ai_analysis),
                'error_description': error.get('description', ''),
                'correct_solution': ai_analysis.get('correct_solution', ''),
                'knowledge_gaps': ai_analysis.get('knowledge_gaps', []),
                'remediation_plan': ai_analysis.get('remediation_plan', []),
                'root_cause': ai_analysis.get('root_cause', ''),
                'severity': self._assess_error_severity(error, ai_analysis),
                'confidence': error.get('confidence', 0.8)
            }
            
        except Exception as e:
            logger.warning(f"AI错误分析失败: {e}")
            # 使用规则基础的分析作为备选
            error_analysis = self._rule_based_error_analysis(error)
        
        return error_analysis
    
    def _classify_error_type(self, error: Dict[str, Any], ai_analysis: Dict[str, Any]) -> str:
        """分类错误类型"""
        # 基于AI分析和规则的错误类型分类
        description = error.get('description', '').lower()
        
        if any(word in description for word in ['计算', '算错', '数值']):
            return 'calculation'
        elif any(word in description for word in ['概念', '理解', '定义']):
            return 'concept'
        elif any(word in description for word in ['方法', '步骤', '思路']):
            return 'method'
        elif any(word in description for word in ['逻辑', '推理', '因果']):
            return 'logic'
        elif any(word in description for word in ['粗心', '马虎', '看错']):
            return 'careless'
        elif any(word in description for word in ['不完整', '缺少', '遗漏']):
            return 'incomplete'
        elif any(word in description for word in ['格式', '书写', '规范']):
            return 'format'
        else:
            return 'unknown'
    
    def _assess_error_severity(self, error: Dict[str, Any], ai_analysis: Dict[str, Any]) -> str:
        """评估错误严重程度"""
        # 基于错误类型和影响评估严重程度
        error_type = self._classify_error_type(error, ai_analysis)
        
        severity_map = {
            'concept': 'high',      # 概念错误最严重
            'method': 'high',       # 方法错误也很严重
            'logic': 'medium',      # 逻辑错误中等
            'calculation': 'medium', # 计算错误中等
            'incomplete': 'medium',  # 不完整中等
            'careless': 'low',      # 粗心错误较轻
            'format': 'low'         # 格式错误最轻
        }
        
        return severity_map.get(error_type, 'medium')
    
    async def _mine_knowledge_points(
        self, 
        scoring_results: Dict[str, Any], 
        ocr_results: Dict[str, Any],
        error_analysis: Dict[str, Any]
    ) -> List[KnowledgePoint]:
        """挖掘知识点"""
        knowledge_points = []
        
        # 从题目内容中识别知识点
        all_text = self._extract_all_text(ocr_results)
        identified_topics = await self._identify_topics_from_text(all_text)
        
        # 从错误分析中提取知识点
        error_knowledge_points = self._extract_knowledge_from_errors(error_analysis)
        
        # 合并和去重
        all_knowledge_points = identified_topics + error_knowledge_points
        unique_points = self._deduplicate_knowledge_points(all_knowledge_points)
        
        # 评估掌握状态
        for point in unique_points:
            mastery_status = await self._assess_knowledge_mastery(
                point, error_analysis, scoring_results
            )
            point['mastery_status'] = mastery_status
            knowledge_points.append(point)
        
        return knowledge_points
    
    def _extract_all_text(self, ocr_results: Dict[str, Any]) -> str:
        """提取所有OCR文本"""
        all_text = []
        for image_path, ocr_data in ocr_results.items():
            if ocr_data.get('success', False):
                text = ocr_data.get('text', '')
                if text:
                    all_text.append(text)
        return '\n'.join(all_text)
    
    async def _identify_topics_from_text(self, text: str) -> List[KnowledgePoint]:
        """从文本中识别主题和知识点"""
        knowledge_points = []
        
        # 使用关键词匹配识别知识点
        for subject, categories in self.knowledge_taxonomy.items():
            for category, topics in categories.items():
                for topic in topics:
                    if topic in text or any(keyword in text for keyword in self._get_topic_keywords(topic)):
                        knowledge_point = {
                            'point_id': f"{subject}_{category}_{topic}",
                            'subject': subject,
                            'topic': topic,
                            'concept': category,
                            'difficulty_level': 'medium',  # 默认中等难度
                            'mastery_status': 'unknown',   # 待评估
                            'related_errors': [],
                            'improvement_suggestions': []
                        }
                        knowledge_points.append(knowledge_point)
        
        return knowledge_points
    
    def _get_topic_keywords(self, topic: str) -> List[str]:
        """获取主题相关的关键词"""
        keyword_map = {
            '方程': ['方程', '解', '根', '解方程'],
            '函数': ['函数', 'f(x)', '定义域', '值域'],
            '几何': ['三角形', '圆', '角', '面积', '周长'],
            '概率': ['概率', '可能性', '随机', '事件'],
            # 可以继续扩展...
        }
        return keyword_map.get(topic, [topic])
    
    def _extract_knowledge_from_errors(self, error_analysis: Dict[str, Any]) -> List[KnowledgePoint]:
        """从错误分析中提取知识点"""
        knowledge_points = []
        
        for error in error_analysis.get('errors', []):
            knowledge_gaps = error.get('knowledge_gaps', [])
            for gap in knowledge_gaps:
                knowledge_point = {
                    'point_id': f"error_related_{gap}",
                    'subject': '未知',  # 需要进一步分析
                    'topic': gap,
                    'concept': '错误相关',
                    'difficulty_level': 'high',  # 错误相关的通常难度较高
                    'mastery_status': 'weak',    # 有错误说明掌握较弱
                    'related_errors': [error.get('error_id', '')],
                    'improvement_suggestions': error.get('remediation_plan', [])
                }
                knowledge_points.append(knowledge_point)
        
        return knowledge_points
    
    def _deduplicate_knowledge_points(self, knowledge_points: List[KnowledgePoint]) -> List[KnowledgePoint]:
        """去重知识点"""
        seen = set()
        unique_points = []
        
        for point in knowledge_points:
            key = f"{point['subject']}_{point['topic']}"
            if key not in seen:
                seen.add(key)
                unique_points.append(point)
            else:
                # 合并相同知识点的信息
                existing_point = next(p for p in unique_points if f"{p['subject']}_{p['topic']}" == key)
                existing_point['related_errors'].extend(point.get('related_errors', []))
                existing_point['improvement_suggestions'].extend(point.get('improvement_suggestions', []))
        
        return unique_points
    
    async def _assess_knowledge_mastery(
        self, 
        knowledge_point: KnowledgePoint, 
        error_analysis: Dict[str, Any],
        scoring_results: Dict[str, Any]
    ) -> str:
        """评估知识点掌握状态"""
        # 基于错误数量和得分情况评估掌握状态
        related_errors = knowledge_point.get('related_errors', [])
        
        if len(related_errors) == 0:
            return 'good'  # 没有相关错误
        elif len(related_errors) == 1:
            return 'fair'  # 有少量错误
        else:
            return 'weak'  # 有多个错误
    
    async def _generate_learning_suggestions(
        self, 
        error_analysis: Dict[str, Any],
        knowledge_points: List[KnowledgePoint]
    ) -> List[str]:
        """生成学习建议"""
        suggestions = []
        
        # 基于错误类型生成建议
        error_types = [error.get('error_type', '') for error in error_analysis.get('errors', [])]
        error_type_counts = {error_type: error_types.count(error_type) for error_type in set(error_types)}
        
        for error_type, count in error_type_counts.items():
            if count > 0:
                suggestion = self._get_suggestion_for_error_type(error_type, count)
                if suggestion:
                    suggestions.append(suggestion)
        
        # 基于知识点掌握情况生成建议
        weak_points = [kp for kp in knowledge_points if kp.get('mastery_status') == 'weak']
        if weak_points:
            topics = [kp.get('topic', '') for kp in weak_points]
            suggestions.append(f"需要加强以下知识点的学习：{', '.join(topics[:3])}")
        
        return suggestions
    
    def _get_suggestion_for_error_type(self, error_type: str, count: int) -> str:
        """根据错误类型生成建议"""
        suggestions_map = {
            'calculation': f"发现{count}个计算错误，建议加强基础运算练习",
            'concept': f"发现{count}个概念错误，建议复习相关概念和定义",
            'method': f"发现{count}个方法错误，建议学习标准解题方法",
            'logic': f"发现{count}个逻辑错误，建议加强逻辑推理训练",
            'careless': f"发现{count}个粗心错误，建议仔细检查答案",
            'incomplete': f"发现{count}个不完整解答，建议完善解题步骤",
            'format': f"发现{count}个格式错误，建议注意答题规范"
        }
        return suggestions_map.get(error_type, '')
    
    async def _assess_difficulty(
        self, 
        scoring_results: Dict[str, Any],
        knowledge_points: List[KnowledgePoint]
    ) -> Dict[str, Any]:
        """评估题目难度"""
        final_score = scoring_results.get('final_score', 0)
        
        # 基于得分评估难度
        if final_score >= 90:
            difficulty_level = 'easy'
        elif final_score >= 70:
            difficulty_level = 'medium'
        else:
            difficulty_level = 'hard'
        
        # 基于知识点数量调整难度
        knowledge_count = len(knowledge_points)
        if knowledge_count > 5:
            difficulty_level = 'hard'
        elif knowledge_count > 3:
            difficulty_level = 'medium'
        
        return {
            'overall_difficulty': difficulty_level,
            'score_based_difficulty': difficulty_level,
            'knowledge_complexity': knowledge_count,
            'difficulty_factors': [
                f"涉及{knowledge_count}个知识点",
                f"得分{final_score}分"
            ]
        }
    
    async def _call_ai_for_analysis(self, prompt: str) -> str:
        """调用AI进行分析"""
        try:
            # 使用现有的API调用功能
            response = call_api(prompt, language="zh")
            return response
        except Exception as e:
            logger.warning(f"AI分析调用失败: {e}")
            return "{}"  # 返回空JSON
    
    def _rule_based_error_analysis(self, error: Dict[str, Any]) -> ErrorAnalysis:
        """基于规则的错误分析（备选方案）"""
        return {
            'error_id': error.get('id', f"error_{datetime.now().timestamp()}"),
            'error_type': 'unknown',
            'error_description': error.get('description', ''),
            'correct_solution': '请参考标准答案',
            'knowledge_gaps': ['需要进一步分析'],
            'remediation_plan': ['建议复习相关知识点'],
            'root_cause': '未知',
            'severity': 'medium',
            'confidence': 0.5
        }
    
    async def _identify_error_patterns(self, errors: List[ErrorAnalysis]) -> List[Dict[str, Any]]:
        """识别错误模式"""
        patterns = []
        
        # 按错误类型分组
        error_by_type = {}
        for error in errors:
            error_type = error.get('error_type', 'unknown')
            if error_type not in error_by_type:
                error_by_type[error_type] = []
            error_by_type[error_type].append(error)
        
        # 分析每种类型的模式
        for error_type, type_errors in error_by_type.items():
            if len(type_errors) > 1:  # 至少2个同类型错误才算模式
                pattern = {
                    'pattern_type': error_type,
                    'frequency': len(type_errors),
                    'description': f"重复出现{self.error_types.get(error_type, error_type)}",
                    'affected_areas': list(set([e.get('knowledge_gaps', [''])[0] for e in type_errors if e.get('knowledge_gaps')]))
                }
                patterns.append(pattern)
        
        return patterns
    
    async def _identify_common_mistakes(self, errors: List[ErrorAnalysis]) -> List[Dict[str, Any]]:
        """识别常见错误"""
        common_mistakes = []
        
        # 统计错误描述的相似性
        descriptions = [error.get('error_description', '') for error in errors]
        
        # 简单的相似性检查（可以用更复杂的NLP方法）
        for i, desc1 in enumerate(descriptions):
            similar_count = 1
            for j, desc2 in enumerate(descriptions[i+1:], i+1):
                if self._calculate_similarity(desc1, desc2) > 0.7:
                    similar_count += 1
            
            if similar_count > 1:
                common_mistakes.append({
                    'mistake_description': desc1,
                    'frequency': similar_count,
                    'severity': 'medium'
                })
        
        return common_mistakes
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似性（简单实现）"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _calculate_severity_distribution(self, errors: List[ErrorAnalysis]) -> Dict[str, int]:
        """计算错误严重程度分布"""
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for error in errors:
            severity = error.get('severity', 'medium')
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        return severity_counts
