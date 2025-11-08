#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rubric Interpreter Agent - 评分标准解析器
解析评分标准文件，生成结构化的评分规则
"""

import os
import logging
import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from ..state import GradingState

logger = logging.getLogger(__name__)

class RubricInterpreter:
    """
    评分标准解释器
    解析评分标准文件，生成结构化的评分规则
    """
    
    def __init__(self):
        self.default_criteria = {
            'accuracy': {'weight': 0.4, 'description': '答案准确性'},
            'method': {'weight': 0.3, 'description': '解题方法'},
            'process': {'weight': 0.2, 'description': '解题过程'},
            'presentation': {'weight': 0.1, 'description': '答题规范'}
        }
        
    async def __call__(self, state: GradingState) -> GradingState:
        """
        执行评分标准解析
        """
        logger.info(f"开始解析评分标准 - 任务ID: {state['task_id']}")
        
        try:
            # 更新进度
            state['current_step'] = "解析评分标准"
            state['progress_percentage'] = 40.0
            
            # 获取评分标准文件
            marking_files = state.get('marking_files', [])
            
            if marking_files:
                # 解析评分标准文件
                rubric_data = await self._parse_rubric_files(marking_files)
            else:
                # 生成默认评分标准
                rubric_data = await self._generate_default_rubric(state)
            
            # 生成评分细则
            scoring_criteria = await self._generate_scoring_criteria(rubric_data)
            
            # 更新状态
            state['rubric_data'] = rubric_data
            state['scoring_criteria'] = scoring_criteria
            
            # 更新进度
            state['progress_percentage'] = 50.0
            state['step_results']['rubric_interpreter'] = {
                'rubric_files_count': len(marking_files),
                'criteria_count': len(scoring_criteria),
                'has_custom_rubric': len(marking_files) > 0
            }
            
            logger.info(f"评分标准解析完成 - 任务ID: {state['task_id']}")
            return state
            
        except Exception as e:
            error_msg = f"评分标准解析失败: {str(e)}"
            logger.error(error_msg)
            state['errors'].append({
                'step': 'rubric_interpreter',
                'error': error_msg,
                'timestamp': str(datetime.now())
            })
            raise
    
    async def _parse_rubric_files(self, marking_files: List[str]) -> Dict[str, Any]:
        """解析评分标准文件"""
        rubric_data = {
            'source_files': marking_files,
            'total_score': 100,
            'criteria': {},
            'detailed_rubric': '',
            'parsed_sections': []
        }
        
        for file_path in marking_files:
            try:
                file_data = await self._parse_single_rubric_file(file_path)
                
                # 合并解析结果
                if file_data:
                    rubric_data['detailed_rubric'] += file_data.get('content', '') + '\n'
                    rubric_data['parsed_sections'].extend(file_data.get('sections', []))
                    
                    # 合并评分标准
                    if 'criteria' in file_data:
                        rubric_data['criteria'].update(file_data['criteria'])
                        
            except Exception as e:
                logger.warning(f"解析评分标准文件失败: {file_path} - {e}")
        
        # 如果没有解析到有效的评分标准，使用默认标准
        if not rubric_data['criteria']:
            rubric_data['criteria'] = self.default_criteria
        
        return rubric_data
    
    async def _parse_single_rubric_file(self, file_path: str) -> Dict[str, Any]:
        """解析单个评分标准文件"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.txt', '.md']:
            return await self._parse_text_rubric(file_path)
        elif file_ext == '.json':
            return await self._parse_json_rubric(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            return await self._parse_image_rubric(file_path)
        else:
            logger.warning(f"不支持的评分标准文件格式: {file_path}")
            return {}
    
    async def _parse_text_rubric(self, file_path: str) -> Dict[str, Any]:
        """解析文本格式的评分标准"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析文本内容
            sections = self._extract_sections_from_text(content)
            criteria = self._extract_criteria_from_text(content)
            
            return {
                'content': content,
                'sections': sections,
                'criteria': criteria,
                'format': 'text'
            }
            
        except Exception as e:
            logger.warning(f"解析文本评分标准失败: {file_path} - {e}")
            return {}
    
    async def _parse_json_rubric(self, file_path: str) -> Dict[str, Any]:
        """解析JSON格式的评分标准"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            return {
                'content': json.dumps(json_data, ensure_ascii=False, indent=2),
                'sections': json_data.get('sections', []),
                'criteria': json_data.get('criteria', {}),
                'format': 'json'
            }
            
        except Exception as e:
            logger.warning(f"解析JSON评分标准失败: {file_path} - {e}")
            return {}
    
    async def _parse_image_rubric(self, file_path: str) -> Dict[str, Any]:
        """解析图像格式的评分标准（需要OCR）"""
        try:
            # 这里应该调用OCR功能来识别图像中的文本
            # 暂时返回空结果，等OCR Agent处理
            logger.info(f"图像评分标准将由OCR Agent处理: {file_path}")
            return {
                'content': f"图像评分标准: {file_path}",
                'sections': [],
                'criteria': {},
                'format': 'image',
                'needs_ocr': True
            }
            
        except Exception as e:
            logger.warning(f"解析图像评分标准失败: {file_path} - {e}")
            return {}
    
    def _extract_sections_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取章节"""
        sections = []
        lines = text.split('\n')
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是标题行
            if self._is_section_header(line):
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    'title': line,
                    'content': '',
                    'type': 'section'
                }
            elif current_section:
                current_section['content'] += line + '\n'
            else:
                # 如果没有明确的章节，创建一个默认章节
                current_section = {
                    'title': '评分标准',
                    'content': line + '\n',
                    'type': 'section'
                }
        
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _is_section_header(self, line: str) -> bool:
        """判断是否是章节标题"""
        # 检查常见的标题模式
        header_patterns = [
            line.startswith('#'),  # Markdown标题
            line.endswith('：') or line.endswith(':'),  # 冒号结尾
            line.isupper() and len(line) < 50,  # 全大写短行
            any(keyword in line for keyword in ['评分', '标准', '要求', '细则'])
        ]
        
        return any(header_patterns)
    
    def _extract_criteria_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取评分标准"""
        criteria = {}
        
        # 查找分数分配
        import re
        score_patterns = [
            r'(\w+)[：:]\s*(\d+)\s*分',
            r'(\w+)\s*\((\d+)分\)',
            r'(\d+)分[：:]\s*(\w+)',
        ]
        
        total_found_score = 0
        for pattern in score_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2:
                    try:
                        if match[1].isdigit():
                            name, score = match[0], int(match[1])
                        else:
                            score, name = int(match[0]), match[1]
                        
                        criteria[name] = {
                            'weight': score / 100.0,  # 假设总分100
                            'description': name,
                            'max_score': score
                        }
                        total_found_score += score
                    except ValueError:
                        continue
        
        # 如果没有找到明确的分数分配，使用默认标准
        if not criteria or total_found_score == 0:
            criteria = self.default_criteria.copy()
        else:
            # 标准化权重
            for criterion in criteria.values():
                criterion['weight'] = criterion.get('max_score', 0) / total_found_score
        
        return criteria
    
    async def _generate_default_rubric(self, state: GradingState) -> Dict[str, Any]:
        """生成默认评分标准"""
        # 基于题目类型和学科生成默认评分标准
        subject = self._infer_subject(state)
        
        default_rubric = {
            'source_files': [],
            'total_score': 100,
            'criteria': self.default_criteria.copy(),
            'detailed_rubric': self._generate_default_rubric_text(subject),
            'parsed_sections': [
                {
                    'title': '默认评分标准',
                    'content': self._generate_default_rubric_text(subject),
                    'type': 'default'
                }
            ],
            'subject': subject
        }
        
        return default_rubric
    
    def _infer_subject(self, state: GradingState) -> str:
        """推断学科"""
        # 从文件名或OCR结果推断学科
        all_files = state.get('question_files', []) + state.get('answer_files', [])
        
        for file_path in all_files:
            filename = Path(file_path).name.lower()
            if any(keyword in filename for keyword in ['数学', 'math', '算']):
                return '数学'
            elif any(keyword in filename for keyword in ['物理', 'physics']):
                return '物理'
            elif any(keyword in filename for keyword in ['化学', 'chemistry']):
                return '化学'
            elif any(keyword in filename for keyword in ['语文', 'chinese', '作文']):
                return '语文'
            elif any(keyword in filename for keyword in ['英语', 'english']):
                return '英语'
        
        return '通用'
    
    def _generate_default_rubric_text(self, subject: str) -> str:
        """生成默认评分标准文本"""
        rubric_templates = {
            '数学': """
# 数学题目评分标准

## 答案准确性 (40分)
- 最终答案正确：40分
- 最终答案有小错误：30-35分
- 最终答案错误但思路正确：20-25分
- 最终答案完全错误：0-15分

## 解题方法 (30分)
- 方法完全正确且高效：30分
- 方法正确但不够简洁：20-25分
- 方法基本正确但有缺陷：10-15分
- 方法错误：0-5分

## 解题过程 (20分)
- 步骤完整清晰：20分
- 步骤基本完整：15分
- 步骤不够完整：10分
- 步骤混乱或缺失：0-5分

## 答题规范 (10分)
- 书写规范，格式正确：10分
- 书写较规范：7-8分
- 书写不够规范：5-6分
- 书写混乱：0-3分
            """,
            '语文': """
# 语文题目评分标准

## 内容准确性 (40分)
- 理解准确，分析深入：40分
- 理解基本准确：30-35分
- 理解有偏差：20-25分
- 理解错误：0-15分

## 表达能力 (30分)
- 表达清晰，逻辑性强：30分
- 表达较清晰：20-25分
- 表达基本清楚：10-15分
- 表达不清：0-5分

## 语言运用 (20分)
- 语言准确，词汇丰富：20分
- 语言较准确：15分
- 语言基本准确：10分
- 语言错误较多：0-5分

## 书写规范 (10分)
- 字迹工整，格式规范：10分
- 字迹较工整：7-8分
- 字迹一般：5-6分
- 字迹潦草：0-3分
            """,
            '通用': """
# 通用评分标准

## 答案准确性 (40分)
- 答案完全正确：40分
- 答案基本正确：30-35分
- 答案部分正确：20-25分
- 答案错误：0-15分

## 解题方法 (30分)
- 方法正确合理：30分
- 方法基本正确：20-25分
- 方法有问题：10-15分
- 方法错误：0-5分

## 解答过程 (20分)
- 过程完整清晰：20分
- 过程基本完整：15分
- 过程不够完整：10分
- 过程不清晰：0-5分

## 答题规范 (10分)
- 规范整洁：10分
- 较规范：7-8分
- 一般：5-6分
- 不规范：0-3分
            """
        }
        
        return rubric_templates.get(subject, rubric_templates['通用'])
    
    async def _generate_scoring_criteria(self, rubric_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成评分细则"""
        criteria_list = []
        
        criteria = rubric_data.get('criteria', {})
        for name, details in criteria.items():
            criterion = {
                'name': name,
                'description': details.get('description', name),
                'weight': details.get('weight', 0.25),
                'max_score': details.get('max_score', 25),
                'scoring_levels': self._generate_scoring_levels(name, details)
            }
            criteria_list.append(criterion)
        
        return criteria_list
    
    def _generate_scoring_levels(self, criterion_name: str, details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成评分等级"""
        max_score = details.get('max_score', 25)
        
        levels = [
            {
                'level': 'excellent',
                'description': '优秀',
                'score_range': [int(max_score * 0.9), max_score],
                'criteria': f'{criterion_name}表现优秀'
            },
            {
                'level': 'good',
                'description': '良好', 
                'score_range': [int(max_score * 0.7), int(max_score * 0.89)],
                'criteria': f'{criterion_name}表现良好'
            },
            {
                'level': 'fair',
                'description': '一般',
                'score_range': [int(max_score * 0.5), int(max_score * 0.69)],
                'criteria': f'{criterion_name}表现一般'
            },
            {
                'level': 'poor',
                'description': '较差',
                'score_range': [0, int(max_score * 0.49)],
                'criteria': f'{criterion_name}表现较差'
            }
        ]
        
        return levels
