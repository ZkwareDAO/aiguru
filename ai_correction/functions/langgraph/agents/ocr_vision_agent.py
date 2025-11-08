#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR & Vision Agent - 图像预处理、OCR、区域检测
集成现有的 ai_recognition.py，符合原始需求
"""

import os
import logging
import json
from typing import Dict, List, Any, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from datetime import datetime

# 导入现有的 OCR 功能
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from ai_recognition import ocr_space_file

from ..state import GradingState

logger = logging.getLogger(__name__)

class OCRVisionAgent:
    """
    OCR & Vision Agent
    集成现有的 ai_recognition.py，提供图像预处理、OCR、区域检测功能
    """
    
    def __init__(self):
        self.ocr_api_key = os.getenv('OCR_SPACE_API_KEY', 'K81037081488957')
        self.supported_languages = ['eng', 'chs', 'cht']  # 英文、简体中文、繁体中文
        
    async def __call__(self, state: GradingState) -> GradingState:
        """
        执行 OCR 和视觉分析
        """
        logger.info(f"开始 OCR 和视觉分析 - 任务ID: {state['task_id']}")
        
        try:
            # 更新进度
            state['current_step'] = "图像分析和OCR"
            state['progress_percentage'] = 30.0
            
            # 获取所有有效的图像文件
            all_image_files = self._get_all_image_files(state)
            
            # 图像预处理
            preprocessed_images = await self._preprocess_images(all_image_files)
            state['preprocessed_images'] = preprocessed_images
            
            # OCR 文本识别
            ocr_results = await self._perform_ocr(preprocessed_images, state['language'])
            state['ocr_results'] = ocr_results
            
            # 图像区域检测
            image_regions = await self._detect_regions(preprocessed_images)
            state['image_regions'] = image_regions
            
            # 更新进度
            state['progress_percentage'] = 50.0
            state['step_results']['ocr_vision'] = {
                'preprocessed_count': len(preprocessed_images),
                'ocr_success_count': len([r for r in ocr_results.values() if r.get('success', False)]),
                'regions_detected': sum(len(regions) for regions in image_regions.values())
            }
            
            logger.info(f"OCR 和视觉分析完成 - 任务ID: {state['task_id']}")
            return state
            
        except Exception as e:
            error_msg = f"OCR 和视觉分析失败: {str(e)}"
            logger.error(error_msg)
            state['errors'].append({
                'step': 'ocr_vision',
                'error': error_msg,
                'timestamp': str(datetime.now())
            })
            raise
    
    def _get_all_image_files(self, state: GradingState) -> List[str]:
        """获取所有图像文件"""
        all_files = []
        
        # 从验证结果中获取有效文件
        if 'step_results' in state and 'upload_validation' in state['step_results']:
            validation_results = state['step_results']['upload_validation']
            
            for file_type in ['question_files', 'answer_files', 'marking_files']:
                if file_type in validation_results:
                    valid_files = validation_results[file_type].get('valid_files', [])
                    # 只选择图像文件
                    image_files = [f for f in valid_files if self._is_image_file(f)]
                    all_files.extend(image_files)
        
        return all_files
    
    def _is_image_file(self, file_path: str) -> bool:
        """检查是否为图像文件"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        return Path(file_path).suffix.lower() in image_extensions
    
    async def _preprocess_images(self, image_files: List[str]) -> Dict[str, str]:
        """图像预处理"""
        preprocessed_images = {}
        
        for image_path in image_files:
            try:
                # 创建预处理后的文件路径
                base_name = Path(image_path).stem
                output_dir = Path(image_path).parent / "preprocessed"
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"{base_name}_preprocessed.jpg"
                
                # 图像预处理
                with Image.open(image_path) as img:
                    # 转换为RGB模式
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 图像增强
                    enhanced_img = self._enhance_image(img)
                    
                    # 保存预处理后的图像
                    enhanced_img.save(output_path, 'JPEG', quality=95)
                    preprocessed_images[image_path] = str(output_path)
                    
                logger.info(f"图像预处理完成: {image_path}")
                
            except Exception as e:
                logger.warning(f"图像预处理失败: {image_path} - {e}")
                # 如果预处理失败，使用原始图像
                preprocessed_images[image_path] = image_path
        
        return preprocessed_images
    
    def _enhance_image(self, img: Image.Image) -> Image.Image:
        """图像增强"""
        # 调整对比度
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(1.2)
        
        # 调整锐度
        sharpness_enhancer = ImageEnhance.Sharpness(img)
        img = sharpness_enhancer.enhance(1.1)
        
        # 去噪
        img = img.filter(ImageFilter.MedianFilter(size=3))
        
        return img
    
    async def _perform_ocr(self, preprocessed_images: Dict[str, str], language: str) -> Dict[str, Any]:
        """执行 OCR 文本识别"""
        ocr_results = {}
        
        # 语言映射
        lang_map = {
            'zh': 'chs',  # 中文简体
            'en': 'eng',  # 英文
            'cht': 'cht'  # 中文繁体
        }
        ocr_language = lang_map.get(language, 'eng')
        
        for original_path, preprocessed_path in preprocessed_images.items():
            try:
                logger.info(f"开始 OCR 识别: {preprocessed_path}")
                
                # 使用现有的 OCR 功能
                ocr_response = ocr_space_file(
                    filename=preprocessed_path,
                    overlay=True,  # 获取坐标信息
                    api_key=self.ocr_api_key,
                    language=ocr_language
                )
                
                # 解析 OCR 结果
                ocr_data = json.loads(ocr_response)
                
                if ocr_data.get('IsErroredOnProcessing', False):
                    raise Exception(f"OCR 处理错误: {ocr_data.get('ErrorMessage', 'Unknown error')}")
                
                # 提取文本和坐标信息
                parsed_results = self._parse_ocr_results(ocr_data)
                
                ocr_results[original_path] = {
                    'success': True,
                    'text': parsed_results['text'],
                    'words': parsed_results['words'],
                    'lines': parsed_results['lines'],
                    'confidence': parsed_results['confidence'],
                    'raw_response': ocr_data
                }
                
                logger.info(f"OCR 识别完成: {preprocessed_path}")
                
            except Exception as e:
                logger.warning(f"OCR 识别失败: {preprocessed_path} - {e}")
                ocr_results[original_path] = {
                    'success': False,
                    'error': str(e),
                    'text': '',
                    'words': [],
                    'lines': []
                }
        
        return ocr_results
    
    def _parse_ocr_results(self, ocr_data: Dict) -> Dict[str, Any]:
        """解析 OCR 结果"""
        all_text = []
        all_words = []
        all_lines = []
        total_confidence = 0
        word_count = 0
        
        if 'ParsedResults' in ocr_data:
            for result in ocr_data['ParsedResults']:
                # 提取整体文本
                if 'ParsedText' in result:
                    all_text.append(result['ParsedText'])
                
                # 提取单词级别的信息
                if 'TextOverlay' in result and 'Lines' in result['TextOverlay']:
                    for line in result['TextOverlay']['Lines']:
                        line_words = []
                        line_text = []
                        
                        if 'Words' in line:
                            for word in line['Words']:
                                word_info = {
                                    'text': word.get('WordText', ''),
                                    'confidence': float(word.get('Confidence', 0)),
                                    'coordinates': {
                                        'left': word.get('Left', 0),
                                        'top': word.get('Top', 0),
                                        'width': word.get('Width', 0),
                                        'height': word.get('Height', 0)
                                    }
                                }
                                all_words.append(word_info)
                                line_words.append(word_info)
                                line_text.append(word_info['text'])
                                
                                total_confidence += word_info['confidence']
                                word_count += 1
                        
                        if line_words:
                            all_lines.append({
                                'text': ' '.join(line_text),
                                'words': line_words,
                                'coordinates': {
                                    'left': line.get('MinLeft', 0),
                                    'top': line.get('MinTop', 0),
                                    'width': line.get('MaxWidth', 0),
                                    'height': line.get('MaxHeight', 0)
                                }
                            })
        
        # 计算平均置信度
        avg_confidence = total_confidence / word_count if word_count > 0 else 0
        
        return {
            'text': '\n'.join(all_text),
            'words': all_words,
            'lines': all_lines,
            'confidence': avg_confidence
        }
    
    async def _detect_regions(self, preprocessed_images: Dict[str, str]) -> Dict[str, List[Dict]]:
        """图像区域检测"""
        image_regions = {}
        
        for original_path, preprocessed_path in preprocessed_images.items():
            try:
                regions = await self._detect_image_regions(preprocessed_path)
                image_regions[original_path] = regions
                logger.info(f"区域检测完成: {preprocessed_path}, 检测到 {len(regions)} 个区域")
                
            except Exception as e:
                logger.warning(f"区域检测失败: {preprocessed_path} - {e}")
                image_regions[original_path] = []
        
        return image_regions
    
    async def _detect_image_regions(self, image_path: str) -> List[Dict]:
        """检测单个图像的区域"""
        regions = []
        
        try:
            # 使用 OpenCV 进行区域检测
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 边缘检测
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # 查找轮廓
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 过滤和处理轮廓
            height, width = gray.shape
            min_area = (width * height) * 0.01  # 最小区域面积
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > min_area:
                    # 获取边界框
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # 归一化坐标
                    normalized_coords = {
                        'x1': x / width,
                        'y1': y / height,
                        'x2': (x + w) / width,
                        'y2': (y + h) / height
                    }
                    
                    regions.append({
                        'region_id': f"region_{i}",
                        'type': 'detected_area',
                        'coordinates': normalized_coords,
                        'area': area,
                        'confidence': min(area / (width * height), 1.0)
                    })
            
        except Exception as e:
            logger.warning(f"OpenCV 区域检测失败: {image_path} - {e}")
        
        return regions
