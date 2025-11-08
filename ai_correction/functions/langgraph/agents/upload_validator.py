#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload Validator Agent - 文件校验和队列管理
集成到 ai_correction，与现有系统兼容
"""

import os
import logging
from typing import Dict, List, Any
from pathlib import Path
import mimetypes
from PIL import Image

from ..state import GradingState

logger = logging.getLogger(__name__)

class UploadValidator:
    """
    文件上传验证器
    校验三件套文件：题目、学生答案、评分标准
    """
    
    def __init__(self):
        self.supported_formats = {
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
            'document': ['.pdf', '.doc', '.docx'],
            'text': ['.txt', '.md']
        }
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.max_image_dimension = 4096  # 最大图像尺寸
    
    async def __call__(self, state: GradingState) -> GradingState:
        """
        执行文件验证
        """
        logger.info(f"开始文件验证 - 任务ID: {state['task_id']}")
        
        try:
            # 更新进度
            state['current_step'] = "文件验证"
            state['progress_percentage'] = 10.0
            
            # 验证文件存在性和格式
            validation_results = {
                'question_files': await self._validate_files(state['question_files'], "题目文件"),
                'answer_files': await self._validate_files(state['answer_files'], "学生答案"),
                'marking_files': await self._validate_files(state['marking_files'], "评分标准")
            }
            
            # 检查必需文件
            if not validation_results['answer_files']['valid_files']:
                raise ValueError("至少需要一个有效的学生答案文件")
            
            # 图像质量检查
            await self._validate_image_quality(validation_results)
            
            # 更新状态
            state['step_results']['upload_validation'] = validation_results
            state['progress_percentage'] = 20.0
            
            logger.info(f"文件验证完成 - 任务ID: {state['task_id']}")
            return state
            
        except Exception as e:
            error_msg = f"文件验证失败: {str(e)}"
            logger.error(error_msg)
            state['errors'].append({
                'step': 'upload_validation',
                'error': error_msg,
                'timestamp': str(datetime.now())
            })
            raise
    
    async def _validate_files(self, file_paths: List[str], file_type: str) -> Dict[str, Any]:
        """验证文件列表"""
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            try:
                if await self._validate_single_file(file_path):
                    valid_files.append(file_path)
                else:
                    invalid_files.append(file_path)
            except Exception as e:
                logger.warning(f"文件验证失败 {file_path}: {e}")
                invalid_files.append(file_path)
        
        return {
            'file_type': file_type,
            'valid_files': valid_files,
            'invalid_files': invalid_files,
            'total_count': len(file_paths),
            'valid_count': len(valid_files)
        }
    
    async def _validate_single_file(self, file_path: str) -> bool:
        """验证单个文件"""
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return False
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            logger.warning(f"文件过大: {file_path} ({file_size} bytes)")
            return False
        
        # 检查文件格式
        file_ext = Path(file_path).suffix.lower()
        if not self._is_supported_format(file_ext):
            logger.warning(f"不支持的文件格式: {file_path}")
            return False
        
        # 如果是图像文件，进行额外验证
        if self._is_image_file(file_ext):
            return await self._validate_image_file(file_path)
        
        return True
    
    def _is_supported_format(self, file_ext: str) -> bool:
        """检查是否为支持的文件格式"""
        for format_type, extensions in self.supported_formats.items():
            if file_ext in extensions:
                return True
        return False
    
    def _is_image_file(self, file_ext: str) -> bool:
        """检查是否为图像文件"""
        return file_ext in self.supported_formats['image']
    
    async def _validate_image_file(self, file_path: str) -> bool:
        """验证图像文件"""
        try:
            with Image.open(file_path) as img:
                # 检查图像尺寸
                width, height = img.size
                if width > self.max_image_dimension or height > self.max_image_dimension:
                    logger.warning(f"图像尺寸过大: {file_path} ({width}x{height})")
                    return False
                
                # 检查图像模式
                if img.mode not in ['RGB', 'RGBA', 'L', 'P']:
                    logger.warning(f"不支持的图像模式: {file_path} ({img.mode})")
                    return False
                
                return True
        except Exception as e:
            logger.warning(f"图像文件验证失败: {file_path} - {e}")
            return False
    
    async def _validate_image_quality(self, validation_results: Dict[str, Any]) -> None:
        """验证图像质量"""
        all_image_files = []
        
        # 收集所有图像文件
        for file_type, results in validation_results.items():
            for file_path in results['valid_files']:
                if self._is_image_file(Path(file_path).suffix.lower()):
                    all_image_files.append(file_path)
        
        # 质量检查
        for file_path in all_image_files:
            try:
                with Image.open(file_path) as img:
                    # 检查图像清晰度（简单的方差检查）
                    import numpy as np
                    gray = img.convert('L')
                    img_array = np.array(gray)
                    variance = np.var(img_array)
                    
                    if variance < 100:  # 阈值可调整
                        logger.warning(f"图像可能模糊: {file_path} (方差: {variance})")
                        
            except Exception as e:
                logger.warning(f"图像质量检查失败: {file_path} - {e}")


def mark_step_complete(state: GradingState, step_name: str, result: Any = None) -> GradingState:
    """标记步骤完成"""
    if 'step_results' not in state:
        state['step_results'] = {}
    
    state['step_results'][step_name] = {
        'status': 'completed',
        'result': result,
        'timestamp': str(datetime.now())
    }
    
    return state
