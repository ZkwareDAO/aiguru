#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Annotation Builder Agent - 坐标标注生成器
核心功能：生成坐标标注和局部图卡片，供前端可视化展示
符合原始需求中的关键功能
"""

import os
import logging
import json
from typing import Dict, List, Any, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from datetime import datetime

from ..state import GradingState, AnnotationData

logger = logging.getLogger(__name__)

class AnnotationBuilder:
    """
    坐标标注构建器
    核心功能：生成坐标标注和局部图卡片
    这是原始需求中明确要求的核心功能
    """
    
    def __init__(self):
        self.annotation_types = {
            'error': {'color': (255, 0, 0), 'label': '错误'},
            'correct': {'color': (0, 255, 0), 'label': '正确'},
            'highlight': {'color': (255, 255, 0), 'label': '重点'},
            'comment': {'color': (0, 0, 255), 'label': '批注'},
            'suggestion': {'color': (255, 165, 0), 'label': '建议'}
        }
        
    async def __call__(self, state: GradingState) -> GradingState:
        """
        执行坐标标注生成
        """
        logger.info(f"开始生成坐标标注 - 任务ID: {state['task_id']}")
        
        try:
            # 更新进度
            state['current_step'] = "生成坐标标注"
            state['progress_percentage'] = 70.0
            
            # 获取评分结果和OCR结果
            scoring_results = state.get('scoring_results', {})
            ocr_results = state.get('ocr_results', {})
            image_regions = state.get('image_regions', {})
            
            # 生成坐标标注
            coordinate_annotations = await self._generate_coordinate_annotations(
                scoring_results, ocr_results, image_regions
            )
            state['coordinate_annotations'] = coordinate_annotations
            
            # 生成错误区域标注
            error_regions = await self._generate_error_regions(scoring_results, ocr_results)
            state['error_regions'] = error_regions
            
            # 生成裁剪区域数据
            cropped_regions = await self._generate_cropped_regions(
                coordinate_annotations, state.get('preprocessed_images', {})
            )
            state['cropped_regions'] = cropped_regions
            
            # 生成可视化图像
            await self._generate_visualization_images(state)
            
            # 更新进度
            state['progress_percentage'] = 80.0
            state['step_results']['annotation_builder'] = {
                'annotations_count': len(coordinate_annotations),
                'error_regions_count': len(error_regions),
                'cropped_regions_count': len(cropped_regions)
            }
            
            logger.info(f"坐标标注生成完成 - 任务ID: {state['task_id']}")
            return state
            
        except Exception as e:
            error_msg = f"坐标标注生成失败: {str(e)}"
            logger.error(error_msg)
            state['errors'].append({
                'step': 'annotation_builder',
                'error': error_msg,
                'timestamp': str(datetime.now())
            })
            raise
    
    async def _generate_coordinate_annotations(
        self, 
        scoring_results: Dict[str, Any], 
        ocr_results: Dict[str, Any],
        image_regions: Dict[str, List[Dict]]
    ) -> List[AnnotationData]:
        """生成坐标标注数据"""
        annotations = []
        
        # 从评分结果中提取错误信息
        if 'detailed_feedback' in scoring_results:
            for feedback in scoring_results['detailed_feedback']:
                if 'error_locations' in feedback:
                    for error_loc in feedback['error_locations']:
                        annotation = {
                            'region_id': f"error_{len(annotations)}",
                            'coordinates': error_loc.get('coordinates', {}),
                            'annotation_type': 'error',
                            'content': error_loc.get('description', ''),
                            'confidence': error_loc.get('confidence', 0.8),
                            'source_image': error_loc.get('source_image', '')
                        }
                        annotations.append(annotation)
        
        # 从OCR结果中生成文本区域标注
        for image_path, ocr_data in ocr_results.items():
            if ocr_data.get('success', False):
                for i, word in enumerate(ocr_data.get('words', [])):
                    if word.get('confidence', 0) > 0.7:  # 高置信度的文本
                        # 将像素坐标转换为归一化坐标
                        coords = word.get('coordinates', {})
                        if coords:
                            # 获取图像尺寸
                            img_width, img_height = self._get_image_dimensions(image_path)
                            
                            normalized_coords = {
                                'x1': coords.get('left', 0) / img_width,
                                'y1': coords.get('top', 0) / img_height,
                                'x2': (coords.get('left', 0) + coords.get('width', 0)) / img_width,
                                'y2': (coords.get('top', 0) + coords.get('height', 0)) / img_height
                            }
                            
                            annotation = {
                                'region_id': f"text_{image_path}_{i}",
                                'coordinates': normalized_coords,
                                'annotation_type': 'highlight',
                                'content': word.get('text', ''),
                                'confidence': word.get('confidence', 0),
                                'source_image': image_path
                            }
                            annotations.append(annotation)
        
        return annotations
    
    async def _generate_error_regions(
        self, 
        scoring_results: Dict[str, Any], 
        ocr_results: Dict[str, Any]
    ) -> List[Dict]:
        """生成错误区域数据"""
        error_regions = []
        
        # 从评分结果中提取错误区域
        if 'errors' in scoring_results:
            for error in scoring_results['errors']:
                error_region = {
                    'error_id': error.get('id', f"error_{len(error_regions)}"),
                    'error_type': error.get('type', 'unknown'),
                    'description': error.get('description', ''),
                    'coordinates': error.get('coordinates', {}),
                    'severity': error.get('severity', 'medium'),
                    'suggested_correction': error.get('correction', ''),
                    'confidence': error.get('confidence', 0.8)
                }
                error_regions.append(error_region)
        
        # 基于OCR结果推断可能的错误区域
        for image_path, ocr_data in ocr_results.items():
            if ocr_data.get('success', False):
                # 查找低置信度的文本区域（可能是错误或模糊的地方）
                for i, word in enumerate(ocr_data.get('words', [])):
                    if word.get('confidence', 1.0) < 0.5:  # 低置信度
                        coords = word.get('coordinates', {})
                        if coords:
                            img_width, img_height = self._get_image_dimensions(image_path)
                            
                            normalized_coords = {
                                'x1': coords.get('left', 0) / img_width,
                                'y1': coords.get('top', 0) / img_height,
                                'x2': (coords.get('left', 0) + coords.get('width', 0)) / img_width,
                                'y2': (coords.get('top', 0) + coords.get('height', 0)) / img_height
                            }
                            
                            error_region = {
                                'error_id': f"low_confidence_{image_path}_{i}",
                                'error_type': 'unclear_text',
                                'description': f"文本识别置信度低: {word.get('text', '')}",
                                'coordinates': normalized_coords,
                                'severity': 'low',
                                'suggested_correction': '请检查此处文字是否清晰',
                                'confidence': word.get('confidence', 0)
                            }
                            error_regions.append(error_region)
        
        return error_regions
    
    async def _generate_cropped_regions(
        self, 
        annotations: List[AnnotationData], 
        preprocessed_images: Dict[str, str]
    ) -> List[Dict]:
        """生成裁剪区域数据（局部图卡片）"""
        cropped_regions = []
        
        for annotation in annotations:
            try:
                source_image = annotation.get('source_image', '')
                if source_image and source_image in preprocessed_images:
                    image_path = preprocessed_images[source_image]
                    coords = annotation.get('coordinates', {})
                    
                    if coords and all(k in coords for k in ['x1', 'y1', 'x2', 'y2']):
                        # 生成裁剪图像
                        cropped_path = await self._crop_image_region(image_path, coords, annotation['region_id'])
                        
                        if cropped_path:
                            cropped_region = {
                                'region_id': annotation['region_id'],
                                'original_image': source_image,
                                'cropped_image': cropped_path,
                                'coordinates': coords,
                                'annotation_type': annotation.get('annotation_type', ''),
                                'content': annotation.get('content', ''),
                                'confidence': annotation.get('confidence', 0),
                                'created_at': str(datetime.now())
                            }
                            cropped_regions.append(cropped_region)
                            
            except Exception as e:
                logger.warning(f"生成裁剪区域失败: {annotation.get('region_id', '')} - {e}")
        
        return cropped_regions
    
    async def _crop_image_region(self, image_path: str, coords: Dict[str, float], region_id: str) -> str:
        """裁剪图像区域"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # 转换归一化坐标为像素坐标
                x1 = int(coords['x1'] * width)
                y1 = int(coords['y1'] * height)
                x2 = int(coords['x2'] * width)
                y2 = int(coords['y2'] * height)
                
                # 添加边距
                margin = 10
                x1 = max(0, x1 - margin)
                y1 = max(0, y1 - margin)
                x2 = min(width, x2 + margin)
                y2 = min(height, y2 + margin)
                
                # 裁剪图像
                cropped_img = img.crop((x1, y1, x2, y2))
                
                # 保存裁剪后的图像
                output_dir = Path(image_path).parent / "cropped_regions"
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"{region_id}_cropped.jpg"
                
                cropped_img.save(output_path, 'JPEG', quality=95)
                return str(output_path)
                
        except Exception as e:
            logger.warning(f"裁剪图像失败: {image_path} - {e}")
            return ""
    
    async def _generate_visualization_images(self, state: GradingState) -> None:
        """生成可视化图像（带标注的完整图像）"""
        try:
            annotations = state.get('coordinate_annotations', [])
            preprocessed_images = state.get('preprocessed_images', {})
            
            for source_image, processed_path in preprocessed_images.items():
                # 获取该图像的所有标注
                image_annotations = [
                    ann for ann in annotations 
                    if ann.get('source_image') == source_image
                ]
                
                if image_annotations:
                    await self._create_annotated_image(processed_path, image_annotations)
                    
        except Exception as e:
            logger.warning(f"生成可视化图像失败: {e}")
    
    async def _create_annotated_image(self, image_path: str, annotations: List[AnnotationData]) -> str:
        """创建带标注的图像"""
        try:
            with Image.open(image_path) as img:
                draw = ImageDraw.Draw(img)
                width, height = img.size
                
                # 尝试加载字体
                try:
                    font = ImageFont.truetype("arial.ttf", 16)
                except:
                    font = ImageFont.load_default()
                
                for annotation in annotations:
                    coords = annotation.get('coordinates', {})
                    if coords and all(k in coords for k in ['x1', 'y1', 'x2', 'y2']):
                        # 转换为像素坐标
                        x1 = int(coords['x1'] * width)
                        y1 = int(coords['y1'] * height)
                        x2 = int(coords['x2'] * width)
                        y2 = int(coords['y2'] * height)
                        
                        # 获取标注类型的颜色
                        annotation_type = annotation.get('annotation_type', 'highlight')
                        color = self.annotation_types.get(annotation_type, {}).get('color', (255, 255, 0))
                        
                        # 绘制边框
                        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                        
                        # 绘制标签
                        label = annotation.get('content', '')[:20]  # 限制标签长度
                        if label:
                            draw.text((x1, y1-20), label, fill=color, font=font)
                
                # 保存标注后的图像
                output_dir = Path(image_path).parent / "annotated"
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"{Path(image_path).stem}_annotated.jpg"
                
                img.save(output_path, 'JPEG', quality=95)
                return str(output_path)
                
        except Exception as e:
            logger.warning(f"创建标注图像失败: {image_path} - {e}")
            return ""
    
    def _get_image_dimensions(self, image_path: str) -> Tuple[int, int]:
        """获取图像尺寸"""
        try:
            with Image.open(image_path) as img:
                return img.size
        except:
            return (1920, 1080)  # 默认尺寸
