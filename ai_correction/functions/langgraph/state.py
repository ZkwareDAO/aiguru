#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph 状态定义 - 集成到 ai_correction
基于原始需求：坐标标注、知识点挖掘、OCR等核心功能
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

class GradingState(TypedDict):
    """
    LangGraph 批改状态
    符合原始需求：坐标标注、错题分析、知识点挖掘
    """
    
    # 基础任务信息
    task_id: str
    user_id: str
    timestamp: datetime
    
    # 文件信息
    question_files: List[str]  # 题目文件路径
    answer_files: List[str]    # 学生答案文件路径
    marking_files: List[str]   # 评分标准文件路径
    
    # 批改参数
    strictness_level: str      # 严格程度：宽松/中等/严格
    language: str              # 语言：zh/en
    mode: str                  # 模式：efficient/detailed/batch/generate_scheme/auto
    
    # OCR & Vision 结果
    ocr_results: Dict[str, Any]           # OCR 文本识别结果
    image_regions: Dict[str, List[Dict]]  # 图像区域检测结果
    preprocessed_images: Dict[str, str]   # 预处理后的图像路径
    
    # 评分标准解析
    rubric_data: Dict[str, Any]           # 结构化评分标准
    scoring_criteria: List[Dict]          # 评分细则
    
    # AI 评分结果
    scoring_results: Dict[str, Any]       # AI 评分结果
    detailed_feedback: List[Dict]         # 详细反馈
    
    # 🎯 坐标标注（核心功能）
    coordinate_annotations: List[Dict]    # 坐标标注数据
    error_regions: List[Dict]             # 错误区域坐标
    cropped_regions: List[Dict]           # 裁剪区域数据
    
    # 🧠 知识点挖掘（核心功能）
    knowledge_points: List[Dict]          # 知识点分析
    error_analysis: Dict[str, Any]        # 错题分析
    learning_suggestions: List[str]       # 学习建议
    difficulty_assessment: Dict[str, Any]

    # 配置参数
    mode: str                          # 批改模式
    strictness_level: str              # 严格程度
    language: str                      # 语言

    # 处理状态
    current_step: str                  # 当前步骤
    progress_percentage: float         # 进度百分比
    completion_status: str             # 完成状态
    completed_at: str                  # 完成时间

    # 中间结果
    rubric_data: Dict[str, Any]        # 评分标准数据
    scoring_criteria: List[Dict[str, Any]]  # 评分细则
    scoring_results: Dict[str, Any]    # 评分结果
    detailed_feedback: List[Dict[str, Any]]  # 详细反馈

    # 最终结果
    final_report: Dict[str, Any]       # 最终报告
    export_data: Dict[str, Any]        # 导出数据
    visualization_data: Dict[str, Any] # 可视化数据

    # 错误和步骤记录
    errors: List[Dict[str, Any]]       # 错误记录
    step_results: Dict[str, Any]       # 步骤结果 # 难度评估
    
    # 最终结果
    final_score: float                    # 最终得分
    grade_level: str                      # 等级评定
    completion_status: str                # 完成状态
    
    # 进度追踪
    current_step: str                     # 当前步骤
    progress_percentage: float            # 进度百分比
    step_results: Dict[str, Any]          # 各步骤结果
    
    # 错误处理
    errors: List[Dict]                    # 错误记录
    warnings: List[str]                   # 警告信息
    
    # 元数据
    processing_time: float                # 处理时间
    model_versions: Dict[str, str]        # 使用的模型版本
    quality_metrics: Dict[str, float]     # 质量指标


class AnnotationData(TypedDict):
    """坐标标注数据结构"""
    region_id: str
    coordinates: Dict[str, float]  # {x1, y1, x2, y2} 归一化坐标
    annotation_type: str           # error/correct/highlight/comment
    content: str                   # 标注内容
    confidence: float              # 置信度
    source_image: str              # 源图像路径


class KnowledgePoint(TypedDict):
    """知识点数据结构"""
    point_id: str
    subject: str                   # 学科
    topic: str                     # 主题
    concept: str                   # 概念
    difficulty_level: str          # 难度等级
    mastery_status: str            # 掌握状态
    related_errors: List[str]      # 相关错误
    improvement_suggestions: List[str]

class ErrorAnalysis(TypedDict):
    """错误分析数据结构"""
    error_id: str
    error_type: str                    # calculation/concept/method/logic/careless/incomplete/format
    error_description: str
    correct_solution: str
    knowledge_gaps: List[str]
    remediation_plan: List[str]
    root_cause: str
    severity: str                      # high/medium/low
    confidence: float  # 改进建议


class ErrorAnalysis(TypedDict):
    """错题分析数据结构"""
    error_id: str
    error_type: str                # 计算错误/概念错误/方法错误等
    error_description: str         # 错误描述
    correct_solution: str          # 正确解法
    knowledge_gaps: List[str]      # 知识缺陷
    remediation_plan: List[str]    # 补救计划
