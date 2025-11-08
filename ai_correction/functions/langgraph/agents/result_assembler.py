#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Result Assembler Agent - 结果汇总器
汇总所有Agent的结果，生成最终的批改报告
"""

import os
import logging
import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from ..state import GradingState

logger = logging.getLogger(__name__)

class ResultAssembler:
    """
    结果汇总器
    汇总所有Agent的结果，生成最终的批改报告
    """
    
    def __init__(self):
        self.report_template = {
            'basic_info': {},
            'scoring_summary': {},
            'detailed_analysis': {},
            'visual_annotations': {},
            'knowledge_analysis': {},
            'recommendations': {},
            'export_data': {}
        }
        
    async def __call__(self, state: GradingState) -> GradingState:
        """
        执行结果汇总
        """
        logger.info(f"开始结果汇总 - 任务ID: {state['task_id']}")
        
        try:
            # 更新进度
            state['current_step'] = "汇总结果"
            state['progress_percentage'] = 95.0
            
            # 生成最终报告
            final_report = await self._generate_final_report(state)
            state['final_report'] = final_report
            
            # 生成导出数据
            export_data = await self._generate_export_data(state)
            state['export_data'] = export_data
            
            # 生成可视化数据
            visualization_data = await self._generate_visualization_data(state)
            state['visualization_data'] = visualization_data
            
            # 更新完成状态
            state['completion_status'] = 'completed'
            state['progress_percentage'] = 100.0
            state['completed_at'] = str(datetime.now())
            
            # 记录汇总结果
            state['step_results']['result_assembler'] = {
                'report_sections': len(final_report),
                'export_items': len(export_data),
                'visualization_items': len(visualization_data)
            }
            
            logger.info(f"结果汇总完成 - 任务ID: {state['task_id']}")
            return state
            
        except Exception as e:
            error_msg = f"结果汇总失败: {str(e)}"
            logger.error(error_msg)
            state['errors'].append({
                'step': 'result_assembler',
                'error': error_msg,
                'timestamp': str(datetime.now())
            })
            state['completion_status'] = 'failed'
            raise
    
    async def _generate_final_report(self, state: GradingState) -> Dict[str, Any]:
        """生成最终报告"""
        report = self.report_template.copy()
        
        # 基本信息
        report['basic_info'] = {
            'task_id': state.get('task_id', ''),
            'user_id': state.get('user_id', ''),
            'timestamp': state.get('timestamp', datetime.now()),
            'completed_at': state.get('completed_at', str(datetime.now())),
            'processing_time': self._calculate_processing_time(state),
            'file_count': {
                'questions': len(state.get('question_files', [])),
                'answers': len(state.get('answer_files', [])),
                'marking_schemes': len(state.get('marking_files', []))
            }
        }
        
        # 评分摘要
        report['scoring_summary'] = {
            'final_score': state.get('final_score', 0),
            'grade_level': state.get('grade_level', 'F'),
            'total_possible': 100,
            'percentage': state.get('final_score', 0),
            'scoring_breakdown': self._generate_scoring_breakdown(state)
        }
        
        # 详细分析
        report['detailed_analysis'] = {
            'errors_found': len(state.get('error_analysis', {}).get('errors', [])),
            'error_summary': self._summarize_errors(state),
            'strengths': self._identify_strengths(state),
            'areas_for_improvement': self._identify_improvement_areas(state)
        }
        
        # 可视化标注
        report['visual_annotations'] = {
            'coordinate_annotations': state.get('coordinate_annotations', []),
            'error_regions': state.get('error_regions', []),
            'cropped_regions': state.get('cropped_regions', []),
            'annotation_summary': self._summarize_annotations(state)
        }
        
        # 知识点分析
        report['knowledge_analysis'] = {
            'knowledge_points': state.get('knowledge_points', []),
            'mastery_distribution': self._analyze_mastery_distribution(state),
            'difficulty_assessment': state.get('difficulty_assessment', {}),
            'learning_path': self._generate_learning_path(state)
        }
        
        # 建议和推荐
        report['recommendations'] = {
            'immediate_actions': self._generate_immediate_actions(state),
            'study_suggestions': state.get('learning_suggestions', []),
            'practice_recommendations': self._generate_practice_recommendations(state),
            'next_steps': self._generate_next_steps(state)
        }
        
        return report
    
    def _calculate_processing_time(self, state: GradingState) -> float:
        """计算处理时间"""
        try:
            start_time = state.get('timestamp')
            end_time = datetime.now()
            
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            elif isinstance(start_time, datetime):
                pass
            else:
                return 0.0
            
            return (end_time - start_time).total_seconds()
        except:
            return 0.0
    
    def _generate_scoring_breakdown(self, state: GradingState) -> Dict[str, Any]:
        """生成评分细分"""
        scoring_criteria = state.get('scoring_criteria', [])
        scoring_results = state.get('scoring_results', {})
        
        breakdown = {}
        for criterion in scoring_criteria:
            name = criterion.get('name', '')
            weight = criterion.get('weight', 0.25)
            max_score = criterion.get('max_score', 25)
            
            # 从评分结果中提取该标准的得分
            actual_score = self._extract_criterion_score(scoring_results, name, max_score)
            
            breakdown[name] = {
                'score': actual_score,
                'max_score': max_score,
                'weight': weight,
                'percentage': (actual_score / max_score * 100) if max_score > 0 else 0,
                'description': criterion.get('description', name)
            }
        
        return breakdown
    
    def _extract_criterion_score(self, scoring_results: Dict[str, Any], criterion_name: str, max_score: float) -> float:
        """从评分结果中提取特定标准的得分"""
        # 这里需要根据实际的评分结果格式来提取
        # 暂时使用简单的估算
        final_score = scoring_results.get('final_score', 0)
        return final_score * 0.25  # 假设平均分配
    
    def _summarize_errors(self, state: GradingState) -> Dict[str, Any]:
        """总结错误"""
        error_analysis = state.get('error_analysis', {})
        errors = error_analysis.get('errors', [])
        
        error_types = {}
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for error in errors:
            error_type = error.get('error_type', 'unknown')
            severity = error.get('severity', 'medium')
            
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
            
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        return {
            'total_errors': len(errors),
            'error_types': error_types,
            'severity_distribution': severity_counts,
            'most_common_error': max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }
    
    def _identify_strengths(self, state: GradingState) -> List[str]:
        """识别优势"""
        strengths = []
        
        # 从评分结果中提取优势
        scoring_results = state.get('scoring_results', {})
        if 'strengths' in scoring_results:
            strengths.extend(scoring_results['strengths'])
        
        # 基于得分识别优势
        final_score = state.get('final_score', 0)
        if final_score >= 90:
            strengths.append('整体表现优秀')
        elif final_score >= 80:
            strengths.append('整体表现良好')
        
        # 基于错误分析识别优势
        error_analysis = state.get('error_analysis', {})
        errors = error_analysis.get('errors', [])
        if len(errors) == 0:
            strengths.append('答题准确，无明显错误')
        elif len(errors) <= 2:
            strengths.append('错误较少，基础扎实')
        
        return strengths
    
    def _identify_improvement_areas(self, state: GradingState) -> List[str]:
        """识别改进领域"""
        improvement_areas = []
        
        # 从错误分析中提取改进领域
        error_analysis = state.get('error_analysis', {})
        error_patterns = error_analysis.get('error_patterns', [])
        
        for pattern in error_patterns:
            improvement_areas.append(f"需要改进{pattern.get('description', '未知领域')}")
        
        # 从知识点分析中提取改进领域
        knowledge_points = state.get('knowledge_points', [])
        weak_points = [kp for kp in knowledge_points if kp.get('mastery_status') == 'weak']
        
        if weak_points:
            topics = [kp.get('topic', '') for kp in weak_points[:3]]  # 取前3个
            improvement_areas.append(f"需要加强以下知识点：{', '.join(topics)}")
        
        return improvement_areas
    
    def _summarize_annotations(self, state: GradingState) -> Dict[str, Any]:
        """总结标注"""
        coordinate_annotations = state.get('coordinate_annotations', [])
        error_regions = state.get('error_regions', [])
        cropped_regions = state.get('cropped_regions', [])
        
        annotation_types = {}
        for annotation in coordinate_annotations:
            ann_type = annotation.get('annotation_type', 'unknown')
            if ann_type not in annotation_types:
                annotation_types[ann_type] = 0
            annotation_types[ann_type] += 1
        
        return {
            'total_annotations': len(coordinate_annotations),
            'error_regions_count': len(error_regions),
            'cropped_regions_count': len(cropped_regions),
            'annotation_types': annotation_types
        }
    
    def _analyze_mastery_distribution(self, state: GradingState) -> Dict[str, int]:
        """分析掌握程度分布"""
        knowledge_points = state.get('knowledge_points', [])
        
        mastery_counts = {'good': 0, 'fair': 0, 'weak': 0, 'unknown': 0}
        
        for kp in knowledge_points:
            mastery = kp.get('mastery_status', 'unknown')
            if mastery in mastery_counts:
                mastery_counts[mastery] += 1
        
        return mastery_counts
    
    def _generate_learning_path(self, state: GradingState) -> List[Dict[str, Any]]:
        """生成学习路径"""
        knowledge_points = state.get('knowledge_points', [])
        weak_points = [kp for kp in knowledge_points if kp.get('mastery_status') == 'weak']
        
        learning_path = []
        for i, kp in enumerate(weak_points[:5]):  # 最多5个学习目标
            step = {
                'step': i + 1,
                'topic': kp.get('topic', ''),
                'subject': kp.get('subject', ''),
                'priority': 'high' if i < 2 else 'medium',
                'estimated_time': '1-2周',
                'resources': kp.get('improvement_suggestions', [])
            }
            learning_path.append(step)
        
        return learning_path
    
    def _generate_immediate_actions(self, state: GradingState) -> List[str]:
        """生成即时行动建议"""
        actions = []
        
        # 基于错误严重程度生成建议
        error_analysis = state.get('error_analysis', {})
        severity_dist = error_analysis.get('severity_distribution', {})
        
        if severity_dist.get('high', 0) > 0:
            actions.append('立即复习基础概念，解决高严重性错误')
        
        if severity_dist.get('medium', 0) > 2:
            actions.append('加强练习，减少中等错误')
        
        # 基于得分生成建议
        final_score = state.get('final_score', 0)
        if final_score < 60:
            actions.append('寻求老师或同学帮助，制定详细学习计划')
        elif final_score < 80:
            actions.append('针对性练习，提高薄弱环节')
        
        return actions
    
    def _generate_practice_recommendations(self, state: GradingState) -> List[Dict[str, Any]]:
        """生成练习建议"""
        recommendations = []
        
        # 基于知识点生成练习建议
        knowledge_points = state.get('knowledge_points', [])
        weak_points = [kp for kp in knowledge_points if kp.get('mastery_status') == 'weak']
        
        for kp in weak_points[:3]:  # 前3个薄弱知识点
            recommendation = {
                'topic': kp.get('topic', ''),
                'type': 'targeted_practice',
                'description': f"针对{kp.get('topic', '')}进行专项练习",
                'difficulty': kp.get('difficulty_level', 'medium'),
                'estimated_problems': 10
            }
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_next_steps(self, state: GradingState) -> List[str]:
        """生成下一步建议"""
        next_steps = []
        
        final_score = state.get('final_score', 0)
        
        if final_score >= 90:
            next_steps.extend([
                '继续保持优秀表现',
                '可以尝试更有挑战性的题目',
                '帮助其他同学学习'
            ])
        elif final_score >= 70:
            next_steps.extend([
                '巩固已掌握的知识点',
                '重点攻克薄弱环节',
                '增加练习量'
            ])
        else:
            next_steps.extend([
                '回归基础，夯实基础知识',
                '寻求额外帮助和指导',
                '制定详细的学习计划'
            ])
        
        return next_steps
    
    async def _generate_export_data(self, state: GradingState) -> Dict[str, Any]:
        """生成导出数据"""
        export_data = {
            'summary': {
                'task_id': state.get('task_id', ''),
                'final_score': state.get('final_score', 0),
                'grade_level': state.get('grade_level', 'F'),
                'completion_time': state.get('completed_at', ''),
                'total_errors': len(state.get('error_analysis', {}).get('errors', []))
            },
            'detailed_results': {
                'scoring_results': state.get('scoring_results', {}),
                'error_analysis': state.get('error_analysis', {}),
                'knowledge_points': state.get('knowledge_points', []),
                'learning_suggestions': state.get('learning_suggestions', [])
            },
            'visual_data': {
                'coordinate_annotations': state.get('coordinate_annotations', []),
                'error_regions': state.get('error_regions', []),
                'cropped_regions': state.get('cropped_regions', [])
            },
            'metadata': {
                'processing_steps': state.get('step_results', {}),
                'errors_encountered': state.get('errors', []),
                'configuration': {
                    'mode': state.get('mode', 'auto'),
                    'language': state.get('language', 'zh'),
                    'strictness_level': state.get('strictness_level', '中等')
                }
            }
        }
        
        return export_data
    
    async def _generate_visualization_data(self, state: GradingState) -> Dict[str, Any]:
        """生成可视化数据"""
        visualization_data = {
            'score_chart': {
                'type': 'bar',
                'data': self._prepare_score_chart_data(state)
            },
            'error_distribution': {
                'type': 'pie',
                'data': self._prepare_error_distribution_data(state)
            },
            'knowledge_mastery': {
                'type': 'radar',
                'data': self._prepare_knowledge_mastery_data(state)
            },
            'progress_timeline': {
                'type': 'timeline',
                'data': self._prepare_progress_timeline_data(state)
            }
        }
        
        return visualization_data
    
    def _prepare_score_chart_data(self, state: GradingState) -> List[Dict[str, Any]]:
        """准备得分图表数据"""
        scoring_breakdown = self._generate_scoring_breakdown(state)
        
        chart_data = []
        for criterion, details in scoring_breakdown.items():
            chart_data.append({
                'label': details.get('description', criterion),
                'score': details.get('score', 0),
                'max_score': details.get('max_score', 25),
                'percentage': details.get('percentage', 0)
            })
        
        return chart_data
    
    def _prepare_error_distribution_data(self, state: GradingState) -> List[Dict[str, Any]]:
        """准备错误分布数据"""
        error_summary = self._summarize_errors(state)
        error_types = error_summary.get('error_types', {})
        
        chart_data = []
        for error_type, count in error_types.items():
            chart_data.append({
                'label': error_type,
                'value': count,
                'percentage': count / error_summary.get('total_errors', 1) * 100
            })
        
        return chart_data
    
    def _prepare_knowledge_mastery_data(self, state: GradingState) -> List[Dict[str, Any]]:
        """准备知识掌握雷达图数据"""
        knowledge_points = state.get('knowledge_points', [])
        
        # 按学科分组
        subjects = {}
        for kp in knowledge_points:
            subject = kp.get('subject', '未知')
            if subject not in subjects:
                subjects[subject] = {'good': 0, 'fair': 0, 'weak': 0, 'total': 0}
            
            mastery = kp.get('mastery_status', 'unknown')
            if mastery in subjects[subject]:
                subjects[subject][mastery] += 1
            subjects[subject]['total'] += 1
        
        chart_data = []
        for subject, mastery_data in subjects.items():
            total = mastery_data['total']
            if total > 0:
                mastery_score = (mastery_data['good'] * 100 + mastery_data['fair'] * 60) / total
                chart_data.append({
                    'subject': subject,
                    'mastery_score': mastery_score,
                    'total_points': total
                })
        
        return chart_data
    
    def _prepare_progress_timeline_data(self, state: GradingState) -> List[Dict[str, Any]]:
        """准备进度时间线数据"""
        step_results = state.get('step_results', {})
        
        timeline_data = []
        steps = [
            ('upload_validator', '文件验证'),
            ('ocr_vision', 'OCR识别'),
            ('rubric_interpreter', '标准解析'),
            ('scoring', 'AI评分'),
            ('annotation_builder', '标注生成'),
            ('knowledge_miner', '知识分析'),
            ('result_assembler', '结果汇总')
        ]
        
        for i, (step_key, step_name) in enumerate(steps):
            if step_key in step_results:
                timeline_data.append({
                    'step': i + 1,
                    'name': step_name,
                    'status': 'completed',
                    'details': step_results[step_key]
                })
            else:
                timeline_data.append({
                    'step': i + 1,
                    'name': step_name,
                    'status': 'skipped',
                    'details': {}
                })
        
        return timeline_data
