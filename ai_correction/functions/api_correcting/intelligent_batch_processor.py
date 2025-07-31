#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能批量处理器 - 支持题目识别、学生分组和并发批改
基于asyncio实现高效并发处理
三步骤清晰分离：识别分析 → 批改 → 总结
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import re
from pathlib import Path
import time

from .calling_api import (
    call_tongyiqianwen_api,
    process_file_content,
    convert_latex_to_unicode,
    detect_loop_and_cleanup,
    enforce_strict_format,
    clean_grading_output,
    convert_to_html_markdown,
    pdf_pages_to_base64_images,
    img_to_base64
)

# 导入简化版提示词
from .prompts_simplified import (
    get_core_grading_prompt,
    get_batch_processing_prompt,
    get_summary_generation_prompt,
    get_question_analysis_prompt,
    ULTIMATE_SYSTEM_MESSAGE,
    QUESTION_ANALYSIS_PROMPT,
    MARKING_SCHEME_DEEP_LEARNING_PROMPT,
    MARKING_CONSISTENCY_CHECK_PROMPT
)

logger = logging.getLogger(__name__)

@dataclass
class Question:
    """题目信息"""
    number: int
    content: str = ""
    max_score: float = 0
    student_answer: str = ""
    
@dataclass
class Student:
    """学生信息"""
    id: str
    name: str
    questions: List[Question]
    total_score: float = 0
    grade: str = ""
    comments: str = ""

@dataclass
class BatchTask:
    """批次任务"""
    batch_id: int
    student_id: str
    student_name: str
    question_numbers: List[int]  # 只存题号
    start_index: int
    end_index: int
    file_content: str  # 原始文件内容

class IntelligentBatchProcessor:
    """智能批量处理器"""
    
    def __init__(self, batch_size: int = 10, max_concurrent: int = 3):
        # 确保批次大小不超过10
        self.batch_size = min(batch_size, 10)
        self.max_concurrent = max_concurrent
        self.semaphore = None  # 延迟创建，避免在没有事件循环的线程中创建
    
    def _ensure_semaphore(self):
        """确保 semaphore 已创建，如果没有则创建"""
        if self.semaphore is None:
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_event_loop()
                self.semaphore = asyncio.Semaphore(self.max_concurrent)
            except RuntimeError:
                # 如果没有事件循环，创建一个新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
    async def step0_learn_marking_scheme(self, file_paths: List[str], file_info_list: List[Dict]) -> Dict[str, Any]:
        """
        步骤0：深度学习批改标准（新增步骤）
        让AI反复学习批改标准，确保严格参照
        """
        logger.info("📚 步骤0：深度学习批改标准...")
        
        # 提取批改标准文件
        marking_files = []
        for i, info in enumerate(file_info_list):
            file_name = info.get('name', '').upper()
            if any(prefix in file_name for prefix in ['MARKING', '批改标准', '评分标准', '标准答案']):
                marking_files.append(file_paths[i])
                logger.info(f"📋 发现批改标准文件: {info.get('name', '')}")
        
        if not marking_files:
            logger.warning("⚠️ 未发现批改标准文件，将使用一般评分原则")
            return {
                "has_marking_scheme": False,
                "learning_result": "未提供批改标准，将使用一般数学评分原则",
                "learned_standards": {}
            }
        
        # 深度学习批改标准
        learning_prompt = f"""🛑 重要提醒：你可以直接查看PDF图像内容！

📄 你已经接收到了批改标准的PDF图像内容，可以直接查看和分析其中的文字、公式和评分要求。

{MARKING_SCHEME_DEEP_LEARNING_PROMPT}

请仔细学习批改标准，这将是后续批改的绝对依据。"""
        
        try:
            # 使用多媒体API学习批改标准
            if marking_files and marking_files[0].endswith('.pdf'):
                logger.info("📄 使用多媒体API学习批改标准...")
                api_args = [learning_prompt]
                api_args.extend(marking_files)
                
                learning_result = call_tongyiqianwen_api(
                    *api_args,
                    system_message="你是批改标准学习专家，需要深入理解评分标准的每个细节。"
                )
            else:
                # 处理文本文件
                marking_content = ""
                for file_path in marking_files:
                    content = process_file_content(file_path)
                    marking_content += f"\\n\\n=== {Path(file_path).name} ===\\n{content}"
                
                learning_result = call_tongyiqianwen_api(
                    learning_prompt + f"\\n\\n批改标准内容：\\n{marking_content}",
                    system_message="你是批改标准学习专家，需要深入理解评分标准的每个细节。"
                )
            
            logger.info("✅ 批改标准学习完成")
            logger.info(f"📊 学习结果长度: {len(learning_result)} 字符")
            
            return {
                "has_marking_scheme": True,
                "learning_result": learning_result,
                "learned_standards": self.parse_learned_standards(learning_result),
                "marking_files": marking_files
            }
            
        except Exception as e:
            logger.error(f"❌ 批改标准学习失败: {e}")
            return {
                "has_marking_scheme": False,
                "learning_result": f"学习失败: {str(e)}",
                "learned_standards": {}
            }
    
    def parse_learned_standards(self, learning_result: str) -> Dict[str, Any]:
        """解析学习到的批改标准"""
        standards = {}
        
        # 提取题目分析
        import re
        question_patterns = re.findall(r'\\*\\*题目(\\d+)分析\\*\\*：([^\\*]+)', learning_result)
        for question_num, analysis in question_patterns:
            standards[f"question_{question_num}"] = {
                "analysis": analysis.strip(),
                "extracted": True
            }
        
        # 提取评分原则
        principles_match = re.search(r'\\*\\*评分原则总结\\*\\*：([^\\*]+)', learning_result)
        if principles_match:
            standards["principles"] = principles_match.group(1).strip()
        
        # 提取重点记忆
        memory_match = re.search(r'\\*\\*重点记忆\\*\\*：([^=]+)', learning_result)
        if memory_match:
            standards["key_points"] = memory_match.group(1).strip()
        
        return standards
    
    async def step1_analyze_structure(self, file_paths: List[str], file_info_list: List[Dict]) -> Dict[str, Any]:
        """
        步骤1：识别分析文件结构
        只识别有多少道题、多少学生，不处理题目内容
        """
        logger.info("📊 步骤1：识别文件结构...")
        
        # 分别收集不同类型的文件内容
        marking_contents = []
        answer_contents = []
        question_contents = []
        
        for file_path in file_paths:
            try:
                content_type, content = process_file_content(file_path)
                file_name = Path(file_path).name
                
                # 处理不同的返回类型
                if content_type == 'error':
                    logger.warning(f"⚠️ 文件处理错误: {file_path} - {content}")
                    continue
                elif content_type == 'pdf':
                    # PDF文件返回的是文件路径，需要转换为图像传递给AI
                    logger.info(f"📄 PDF文件转换为图像: {file_name}")
                    try:
                        # 使用calling_api中的PDF转图像功能
                        base64_images = pdf_pages_to_base64_images(content)
                        
                        if base64_images:
                            # 将PDF图像添加到内容中
                            image_content = f"[PDF文件包含{len(base64_images)}页图像]"
                            for i, img_base64 in enumerate(base64_images[:5]):  # 限制最多5页
                                image_content += f"\n[第{i+1}页图像: data:image/jpeg;base64,{img_base64[:100]}...]"
                            
                            if 'MARKING' in file_name.upper() or '标准' in file_name:
                                marking_contents.append(f"\n=== 批改标准文件 (PDF图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 批改标准PDF图像: {file_name}, {len(base64_images)}页")
                            elif 'ANSWER' in file_name.upper() or '答案' in file_name:
                                answer_contents.append(f"\n=== 学生答案文件 (PDF图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 学生答案PDF图像: {file_name}, {len(base64_images)}页")
                            elif 'QUESTION' in file_name.upper() or '题目' in file_name:
                                question_contents.append(f"\n=== 题目文件 (PDF图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 题目PDF图像: {file_name}, {len(base64_images)}页")
                            else:
                                answer_contents.append(f"\n=== 文件 (PDF图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 其他PDF图像（当作答案）: {file_name}, {len(base64_images)}页")
                        else:
                            # 如果PDF转图像失败，提供详细的错误信息和解决建议
                            from .calling_api import validate_pdf_file
                            
                            # 进行PDF文件验证以获取详细错误信息
                            validation_result = validate_pdf_file(file_path)
                            
                            if validation_result['is_valid']:
                                # 文件本身有效，但转换失败
                                error_msg = f"[PDF文件 {file_name} 验证通过但转换失败]\n"
                                error_msg += "可能原因：\n"
                                error_msg += "- PDF内容过于复杂\n"
                                error_msg += "- 内存不足\n"
                                error_msg += "- PDF处理库版本问题\n"
                                error_msg += "建议：请尝试重新上传或联系技术支持"
                            else:
                                # 文件本身有问题
                                error_msg = f"[PDF文件 {file_name} 处理失败]\n"
                                error_msg += f"错误原因：{validation_result['error_message']}\n"
                                if validation_result['suggestions']:
                                    error_msg += "解决建议：\n"
                                    for suggestion in validation_result['suggestions']:
                                        error_msg += f"- {suggestion}\n"
                                
                                # 添加文件信息（如果有）
                                if validation_result['file_info']:
                                    error_msg += "文件信息：\n"
                                    file_info = validation_result['file_info']
                                    if 'size_mb' in file_info:
                                        error_msg += f"- 文件大小：{file_info['size_mb']:.1f}MB\n"
                                    if 'page_count' in file_info:
                                        error_msg += f"- 页面数量：{file_info['page_count']}\n"
                                    if 'is_encrypted' in file_info:
                                        error_msg += f"- 是否加密：{'是' if file_info['is_encrypted'] else '否'}\n"
                            
                            if 'MARKING' in file_name.upper() or '标准' in file_name:
                                marking_contents.append(f"\n=== 批改标准文件 (PDF处理失败): {file_name} ===\n{error_msg}")
                            else:
                                answer_contents.append(f"\n=== 文件 (PDF处理失败): {file_name} ===\n{error_msg}")
                            logger.warning(f"⚠️ PDF转图像失败: {file_name}")
                            logger.warning(f"详细错误信息: {validation_result['error_message']}")
                    except Exception as e:
                        logger.error(f"PDF转图像异常: {e}")
                        error_msg = f"[PDF文件 {file_name} 处理异常: {str(e)}]"
                        if 'MARKING' in file_name.upper() or '标准' in file_name:
                            marking_contents.append(f"\n=== 批改标准文件 (PDF处理异常): {file_name} ===\n{error_msg}")
                        else:
                            answer_contents.append(f"\n=== 文件 (PDF处理异常): {file_name} ===\n{error_msg}")
                elif content_type == 'image':
                    # 图像文件返回的也是文件路径，需要转换为base64
                    logger.info(f"🖼️ 图像文件转换: {file_name}")
                    try:
                        # 使用calling_api中的图像处理功能
                        base64_image = img_to_base64(content)
                        
                        if base64_image:
                            image_content = f"[图像文件: data:image/jpeg;base64,{base64_image[:100]}...]"
                            
                            if 'MARKING' in file_name.upper() or '标准' in file_name:
                                marking_contents.append(f"\n=== 批改标准文件 (图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 批改标准图像: {file_name}")
                            elif 'ANSWER' in file_name.upper() or '答案' in file_name:
                                answer_contents.append(f"\n=== 学生答案文件 (图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 学生答案图像: {file_name}")
                            elif 'QUESTION' in file_name.upper() or '题目' in file_name:
                                question_contents.append(f"\n=== 题目文件 (图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 题目图像: {file_name}")
                            else:
                                answer_contents.append(f"\n=== 文件 (图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 其他图像（当作答案）: {file_name}")
                        else:
                            error_msg = f"[图像文件 {file_name} 无法转换为base64]"
                            if 'MARKING' in file_name.upper() or '标准' in file_name:
                                marking_contents.append(f"\n=== 批改标准文件 (图像处理失败): {file_name} ===\n{error_msg}")
                            else:
                                answer_contents.append(f"\n=== 文件 (图像处理失败): {file_name} ===\n{error_msg}")
                            logger.warning(f"⚠️ 图像转base64失败: {file_name}")
                    except Exception as e:
                        logger.error(f"图像转base64异常: {e}")
                        error_msg = f"[图像文件 {file_name} 处理异常: {str(e)}]"
                        if 'MARKING' in file_name.upper() or '标准' in file_name:
                            marking_contents.append(f"\n=== 批改标准文件 (图像处理异常): {file_name} ===\n{error_msg}")
                        else:
                            answer_contents.append(f"\n=== 文件 (图像处理异常): {file_name} ===\n{error_msg}")
                elif content_type == 'text' and isinstance(content, str) and content.strip():
                    # 文本内容
                    if 'MARKING' in file_name.upper() or '标准' in file_name:
                        marking_contents.append(f"\n=== 批改标准文件: {file_name} ===\n{content}")
                        logger.info(f"✅ 批改标准文件: {file_name}, 内容长度: {len(content)}")
                    elif 'ANSWER' in file_name.upper() or '答案' in file_name:
                        answer_contents.append(f"\n=== 学生答案文件: {file_name} ===\n{content}")
                        logger.info(f"✅ 学生答案文件: {file_name}, 内容长度: {len(content)}")
                    elif 'QUESTION' in file_name.upper() or '题目' in file_name:
                        question_contents.append(f"\n=== 题目文件: {file_name} ===\n{content}")
                        logger.info(f"✅ 题目文件: {file_name}, 内容长度: {len(content)}")
                    else:
                        # 未知类型，默认当作学生答案
                        answer_contents.append(f"\n=== 文件: {file_name} ===\n{content}")
                        logger.info(f"✅ 其他文件（当作答案）: {file_name}, 内容长度: {len(content)}")
                else:
                    logger.warning(f"⚠️ 文件内容为空或格式错误: {file_path} (类型: {content_type})")
            except Exception as e:
                logger.error(f"❌ 处理文件失败 {file_path}: {e}")
        
        # 构建结构化的内容字符串
        structured_content = ""
        
        if marking_contents:
            structured_content += "\n" + "="*60 + "\n"
            structured_content += "📊 批改标准文件（包含正确答案和评分标准）："
            structured_content += "\n" + "="*60 + "\n"
            structured_content += "\n".join(marking_contents)
            structured_content += "\n" + "="*60 + "\n"
        
        if question_contents:
            structured_content += "\n" + "="*60 + "\n"
            structured_content += "📋 题目文件（包含考试题目）："
            structured_content += "\n" + "="*60 + "\n"
            structured_content += "\n".join(question_contents)
            structured_content += "\n" + "="*60 + "\n"
        
        if answer_contents:
            structured_content += "\n" + "="*60 + "\n"
            structured_content += "✏️ 学生答案文件（需要批改的内容）："
            structured_content += "\n" + "="*60 + "\n"
            structured_content += "\n".join(answer_contents)
            structured_content += "\n" + "="*60 + "\n"
        
        if not structured_content:
            # 如果没有内容，尝试强制读取（保留原有的强制读取逻辑）
            logger.error("没有成功读取任何文件内容！")
            logger.error(f"文件路径列表: {file_paths}")
            
            # 尝试更强制的方式读取
            for file_path in file_paths:
                logger.info(f"尝试强制读取: {file_path}")
                try:
                    # 检查文件是否存在
                    if not Path(file_path).exists():
                        logger.error(f"文件不存在: {file_path}")
                        continue
                        
                    # 获取文件扩展名
                    ext = Path(file_path).suffix.lower()
                    
                    if ext == '.pdf':
                        # PDF文件处理
                        try:
                            import fitz
                            doc = fitz.open(file_path)
                            text_content = []
                            for page_num in range(len(doc)):
                                page = doc[page_num]
                                text_content.append(f"[第{page_num+1}页]\n{page.get_text()}")
                            doc.close()
                            content = "\n".join(text_content)
                            if content.strip():
                                file_name = Path(file_path).name
                                if 'MARKING' in file_name.upper():
                                    marking_contents.append(f"\n=== 批改标准文件: {file_name} ===\n{content}")
                                elif 'ANSWER' in file_name.upper():
                                    answer_contents.append(f"\n=== 学生答案文件: {file_name} ===\n{content}")
                                elif 'QUESTION' in file_name.upper():
                                    question_contents.append(f"\n=== 题目文件: {file_name} ===\n{content}")
                                else:
                                    answer_contents.append(f"\n=== 文件: {file_name} ===\n{content}")
                                logger.info(f"✅ PDF读取成功: {file_name}")
                            else:
                                # 如果文本为空，当作图像处理
                                try:
                                    base64_images = pdf_pages_to_base64_images(file_path)
                                    if base64_images:
                                        image_content = f"[PDF文件包含{len(base64_images)}页图像]"
                                        for i, img_base64 in enumerate(base64_images[:5]):  # 限制最多5页
                                            image_content += f"\n[第{i+1}页图像: data:image/jpeg;base64,{img_base64[:100]}...]"
                                        
                                        file_name = Path(file_path).name
                                        if 'MARKING' in file_name.upper():
                                            marking_contents.append(f"\n=== 批改标准文件 (PDF图像): {file_name} ===\n{image_content}")
                                        elif 'ANSWER' in file_name.upper():
                                            answer_contents.append(f"\n=== 学生答案文件 (PDF图像): {file_name} ===\n{image_content}")
                                        elif 'QUESTION' in file_name.upper():
                                            question_contents.append(f"\n=== 题目文件 (PDF图像): {file_name} ===\n{image_content}")
                                        else:
                                            answer_contents.append(f"\n=== 文件 (PDF图像): {file_name} ===\n{image_content}")
                                        logger.info(f"✅ PDF作为图像: {file_name}, {len(base64_images)}页")
                                    else:
                                        # PDF转图像失败 - 使用增强的错误处理
                                        file_name = Path(file_path).name
                                        from .calling_api import validate_pdf_file
                                        
                                        # 进行PDF文件验证以获取详细错误信息
                                        validation_result = validate_pdf_file(file_path)
                                        
                                        if validation_result['is_valid']:
                                            error_msg = f"[PDF文件 {file_name} 验证通过但转换失败]\n"
                                            error_msg += "可能原因：PDF内容过于复杂或内存不足\n"
                                            error_msg += "建议：请尝试重新上传或联系技术支持"
                                        else:
                                            error_msg = f"[PDF文件 {file_name} 处理失败]\n"
                                            error_msg += f"错误原因：{validation_result['error_message']}\n"
                                            if validation_result['suggestions']:
                                                error_msg += "解决建议：\n"
                                                for suggestion in validation_result['suggestions']:
                                                    error_msg += f"- {suggestion}\n"
                                        
                                        if 'MARKING' in file_name.upper():
                                            marking_contents.append(f"\n=== 批改标准文件 (PDF处理失败): {file_name} ===\n{error_msg}")
                                        else:
                                            answer_contents.append(f"\n=== 文件 (PDF处理失败): {file_name} ===\n{error_msg}")
                                        logger.warning(f"⚠️ PDF转图像失败: {file_name}")
                                        logger.warning(f"详细错误信息: {validation_result['error_message']}")
                                except Exception as img_e:
                                    logger.error(f"PDF转图像异常: {img_e}")
                                    file_name = Path(file_path).name
                                    error_msg = f"[PDF文件 {file_name} 处理异常: {str(img_e)}]"
                                    if 'MARKING' in file_name.upper():
                                        marking_contents.append(f"\n=== 批改标准文件 (PDF处理异常): {file_name} ===\n{error_msg}")
                                    else:
                                        answer_contents.append(f"\n=== 文件 (PDF处理异常): {file_name} ===\n{error_msg}")
                        except Exception as e:
                            logger.error(f"PDF读取失败: {e}")
                            # PDF处理失败，尝试转换为图像
                            try:
                                base64_images = pdf_pages_to_base64_images(file_path)
                                if base64_images:
                                    image_content = f"[PDF文件包含{len(base64_images)}页图像]"
                                    for i, img_base64 in enumerate(base64_images[:5]):  # 限制最多5页
                                        image_content += f"\n[第{i+1}页图像: data:image/jpeg;base64,{img_base64[:100]}...]"
                                    
                                    file_name = Path(file_path).name
                                    if 'MARKING' in file_name.upper():
                                        marking_contents.append(f"\n=== 批改标准文件 (PDF图像): {file_name} ===\n{image_content}")
                                    else:
                                        answer_contents.append(f"\n=== 文件 (PDF图像): {file_name} ===\n{image_content}")
                                    logger.info(f"✅ PDF作为图像: {file_name}, {len(base64_images)}页")
                                else:
                                    file_name = Path(file_path).name
                                    error_msg = f"[PDF文件 {file_name} 完全无法处理]"
                                    if 'MARKING' in file_name.upper():
                                        marking_contents.append(f"\n=== 批改标准文件 (完全失败): {file_name} ===\n{error_msg}")
                                    else:
                                        answer_contents.append(f"\n=== 文件 (完全失败): {file_name} ===\n{error_msg}")
                                    logger.error(f"❌ PDF完全无法处理: {file_name}")
                            except Exception as img_e:
                                logger.error(f"PDF图像转换也失败: {img_e}")
                                file_name = Path(file_path).name
                                error_msg = f"[PDF文件 {file_name} 完全无法处理: {str(e)} / {str(img_e)}]"
                                if 'MARKING' in file_name.upper():
                                    marking_contents.append(f"\n=== 批改标准文件 (完全失败): {file_name} ===\n{error_msg}")
                                else:
                                    answer_contents.append(f"\n=== 文件 (完全失败): {file_name} ===\n{error_msg}")
                    
                    elif ext in ['.txt', '.md']:
                        # 文本文件处理
                        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
                        for encoding in encodings:
                            try:
                                with open(file_path, 'r', encoding=encoding) as f:
                                    content = f.read()
                                if content.strip():
                                    file_name = Path(file_path).name
                                    if 'MARKING' in file_name.upper():
                                        marking_contents.append(f"\n=== 批改标准文件: {file_name} ===\n{content}")
                                    elif 'ANSWER' in file_name.upper():
                                        answer_contents.append(f"\n=== 学生答案文件: {file_name} ===\n{content}")
                                    elif 'QUESTION' in file_name.upper():
                                        question_contents.append(f"\n=== 题目文件: {file_name} ===\n{content}")
                                    else:
                                        answer_contents.append(f"\n=== 文件: {file_name} ===\n{content}")
                                    logger.info(f"✅ 文本读取成功 ({encoding}): {file_name}")
                                    break
                            except:
                                continue
                    
                    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                        # 图片文件处理
                        try:
                            base64_image = img_to_base64(file_path)
                            if base64_image:
                                image_content = f"[图像文件: data:image/jpeg;base64,{base64_image[:100]}...]"
                                
                                file_name = Path(file_path).name
                                if 'MARKING' in file_name.upper():
                                    marking_contents.append(f"\n=== 批改标准文件 (图像): {file_name} ===\n{image_content}")
                                elif 'ANSWER' in file_name.upper():
                                    answer_contents.append(f"\n=== 学生答案文件 (图像): {file_name} ===\n{image_content}")
                                elif 'QUESTION' in file_name.upper():
                                    question_contents.append(f"\n=== 题目文件 (图像): {file_name} ===\n{image_content}")
                                else:
                                    answer_contents.append(f"\n=== 文件 (图像): {file_name} ===\n{image_content}")
                                logger.info(f"✅ 图像文件: {file_name}")
                            else:
                                file_name = Path(file_path).name
                                error_msg = f"[图像文件 {file_name} 无法转换为base64]"
                                if 'MARKING' in file_name.upper():
                                    marking_contents.append(f"\n=== 批改标准文件 (图像处理失败): {file_name} ===\n{error_msg}")
                                else:
                                    answer_contents.append(f"\n=== 文件 (图像处理失败): {file_name} ===\n{error_msg}")
                                logger.warning(f"⚠️ 图像转base64失败: {file_name}")
                        except Exception as e:
                            logger.error(f"图像处理异常: {e}")
                            file_name = Path(file_path).name
                            error_msg = f"[图像文件 {file_name} 处理异常: {str(e)}]"
                            if 'MARKING' in file_name.upper():
                                marking_contents.append(f"\n=== 批改标准文件 (图像处理异常): {file_name} ===\n{error_msg}")
                            else:
                                answer_contents.append(f"\n=== 文件 (图像处理异常): {file_name} ===\n{error_msg}")
                        
                except Exception as e:
                    logger.error(f"强制读取失败: {e}")
            
            # 重新构建结构化内容
            if marking_contents or answer_contents:
                structured_content = ""
                if marking_contents:
                    structured_content += "\n" + "="*60 + "\n"
                    structured_content += "📊 批改标准文件（包含正确答案和评分标准）："
                    structured_content += "\n" + "="*60 + "\n"
                    structured_content += "\n".join(marking_contents)
                
                if answer_contents:
                    structured_content += "\n" + "="*60 + "\n"
                    structured_content += "✏️ 学生答案文件（需要批改的内容）："
                    structured_content += "\n" + "="*60 + "\n"
                    structured_content += "\n".join(answer_contents)
        
        if not structured_content:
            # 如果还是没有内容，创建一个错误消息
            error_msg = f"无法读取任何文件内容。文件路径：{', '.join(file_paths)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"📝 结构化内容总长度: {len(structured_content)}")
        logger.info(f"📊 文件分类统计: 批改标准{len(marking_contents)}个, 学生答案{len(answer_contents)}个, 题目{len(question_contents)}个")
        
        # AI分析文件结构 - 使用prompts_simplified中的提示词
        # 使用prompts_simplified.py中的QUESTION_ANALYSIS_PROMPT
        analysis_prompt = f"""{QUESTION_ANALYSIS_PROMPT}

⚠️ 重要提醒：上传的文件已经按类型分类：
- 📊 批改标准文件：包含正确答案和评分标准（如果有MARKING文件）
- ✏️ 学生答案文件：学生的作答内容（需要批改的对象）
- 📋 题目文件：考试题目（如果有QUESTION文件）

请仔细识别每个部分，特别是要利用批改标准来确定题目数量和分值。

文件内容：
{structured_content}"""

        try:
            # 检查是否有PDF图像文件需要特殊处理
            pdf_files = []
            for file_path in file_paths:
                if file_path.endswith('.pdf'):
                    pdf_files.append(file_path)
            
            if pdf_files:
                # 如果有PDF文件，使用多媒体API调用
                logger.info(f"📄 检测到PDF文件，使用多媒体API处理: {[Path(f).name for f in pdf_files]}")
                
                # 构建多媒体API调用
                api_args = [analysis_prompt]
                api_args.extend(pdf_files)  # 添加PDF文件路径
                
                # 调用多媒体API
                result = call_tongyiqianwen_api(
                    *api_args,
                    system_message="你是教育文件分析专家。请按照指定格式分析题目信息，重点关注批改标准文件中的题目数量和分值信息。你可以直接查看PDF图像内容。"
                )
            else:
                # 没有PDF文件，使用普通文本API调用
                result = call_tongyiqianwen_api(
                    analysis_prompt,
                    system_message="你是教育文件分析专家。请按照指定格式分析题目信息，重点关注批改标准文件中的题目数量和分值信息。"
                )
            
            # 解析题目分析结果
            logger.info(f"📊 第一步API返回结果：\\n{result}")
            
            # 尝试解析结果
            structure_data = self.parse_question_analysis_result(result, structured_content, file_info_list)
            
            # 添加结构化内容到返回数据中，用于后续步骤
            structure_data['structured_content'] = structured_content
            structure_data['has_marking_files'] = len(marking_contents) > 0
            structure_data['has_answer_files'] = len(answer_contents) > 0
            structure_data['has_question_files'] = len(question_contents) > 0
            
            # 确保至少有一个学生
            if not structure_data.get('students') or len(structure_data['students']) == 0:
                logger.info("📌 未识别到学生信息，添加默认学生")
                structure_data['students'] = [{
                    "id": "student_001",
                    "name": "默认学生",
                    "question_numbers": list(range(1, structure_data.get('total_questions', 1) + 1))
                }]
            
            logger.info(f"✅ 结构分析完成：{structure_data['total_questions']}道题，{len(structure_data['students'])}个学生")
            if structure_data.get('one_batch_mode'):
                logger.info("📌 一次性批改模式：将所有内容作为整体批改")
            
            return structure_data
                
        except Exception as e:
            logger.error(f"结构分析失败: {e}")
            # 失败时使用一次性批改
            return {
                "total_questions": 1,
                "students": [{
                    "id": "student_001",
                    "name": "默认学生",
                    "question_numbers": [1]
                }],
                "has_marking_scheme": any('MARKING' in f['name'].upper() for f in file_info_list),
                "structured_content": structured_content,
                "has_marking_files": len(marking_contents) > 0,
                "has_answer_files": len(answer_contents) > 0,
                "has_question_files": len(question_contents) > 0,
                "one_batch_mode": True,
                "confidence": "low"
            }
    
    def parse_question_analysis_result(self, result: str, combined_content: str, file_info_list: List[Dict]) -> Dict[str, Any]:
        """解析题目分析结果"""
        structure_data = {
            "total_questions": 0,
            "students": [],
            "has_marking_scheme": any('MARKING' in f['name'].upper() for f in file_info_list),
            "file_content": combined_content,  # 使用传入的内容
            "confidence": "low"
        }
        
        try:
            # 提取题目总数
            total_match = re.search(r'题目总数[：:]\s*(\d+)', result)
            if total_match:
                structure_data['total_questions'] = int(total_match.group(1))
                structure_data['confidence'] = "high"
            
            # 提取学生信息
            student_match = re.search(r'学生信息[：:]\s*(.+)', result)
            if student_match:
                student_info = student_match.group(1).strip()
                if student_info and student_info != '无' and student_info != '未找到':
                    structure_data['students'] = [{
                        "id": "student_001",
                        "name": student_info,
                        "question_numbers": list(range(1, structure_data['total_questions'] + 1))
                    }]
                    logger.info(f"📌 识别到学生信息: {student_info}")
            
            # 如果没有识别到题目，使用一次性批改模式
            if structure_data['total_questions'] == 0:
                logger.warning("⚠️ 未识别到题目数量，启用一次性批改模式")
                structure_data['total_questions'] = 1
                structure_data['one_batch_mode'] = True
                structure_data['confidence'] = "low"
                
                # 设置默认学生
                if not structure_data.get('students'):
                    structure_data['students'] = [{
                        "id": "student_001", 
                        "name": "默认学生",
                        "question_numbers": [1]
                    }]
                else:
                    # 为现有学生设置题目
                    for student in structure_data['students']:
                        student['question_numbers'] = [1]
            else:
                # 为学生设置题目编号
                for student in structure_data.get('students', []):
                    student['question_numbers'] = list(range(1, structure_data['total_questions'] + 1))
            
            return structure_data
            
        except Exception as e:
            logger.error(f"解析题目分析结果失败: {e}")
            # 返回一次性批改模式
            return {
                "total_questions": 1,
                "students": [{
                    "id": "student_001",
                    "name": "默认学生", 
                    "question_numbers": [1]
                }],
                "has_marking_scheme": any('MARKING' in f['name'].upper() for f in file_info_list),
                "file_content": combined_content,  # 使用传入的内容
                "one_batch_mode": True,
                "confidence": "low"
            }
    
    def create_batch_tasks(self, structure_data: Dict[str, Any]) -> List[BatchTask]:
        """根据结构创建批次任务，每批最多10道题"""
        batches = []
        batch_id = 0
        # 使用结构化内容而不是原始文件内容
        file_content = structure_data.get('structured_content', structure_data.get('file_content', ''))
        
        # 检查是否是一次性批改模式
        if structure_data.get('one_batch_mode'):
            logger.info("📌 一次性批改模式：将所有内容作为一个批次")
            # 创建单个批次处理所有内容
            for student in structure_data.get('students', []):
                batch = BatchTask(
                    batch_id=batch_id,
                    student_id=student['id'],
                    student_name=student['name'],
                    question_numbers=[1],  # 作为整体
                    start_index=0,
                    end_index=1,
                    file_content=file_content
                )
                batches.append(batch)
                batch_id += 1
        else:
            # 正常分批模式
            for student in structure_data['students']:
                student_id = student['id']
                student_name = student['name']
                question_numbers = student.get('question_numbers', [])
                
                if not question_numbers:
                    logger.warning(f"⚠️ 学生 {student_name} 没有识别到题目")
                    continue
                
                # 按批次大小分割题目编号（最多10道题）
                for i in range(0, len(question_numbers), self.batch_size):
                    batch_questions = question_numbers[i:i + self.batch_size]
                    batch = BatchTask(
                        batch_id=batch_id,
                        student_id=student_id,
                        student_name=student_name,
                        question_numbers=batch_questions,
                        start_index=i,
                        end_index=min(i + self.batch_size, len(question_numbers)),
                        file_content=file_content  # 使用结构化内容
                    )
                    batches.append(batch)
                    batch_id += 1
        
        # 输出批次分配信息
        logger.info(f"📦 创建了 {len(batches)} 个批次任务")
        if not structure_data.get('one_batch_mode'):
            logger.info(f"📊 总题目数: {structure_data.get('total_questions', 0)} 题")
            
            # 详细输出每个批次的信息
            for batch in batches:
                if len(batch.question_numbers) > 1:
                    question_range = f"{batch.question_numbers[0]}-{batch.question_numbers[-1]}"
                else:
                    question_range = str(batch.question_numbers[0])
                logger.info(f"  批次{batch.batch_id + 1}: 学生[{batch.student_name}] - 题目[{question_range}] (共{len(batch.question_numbers)}题)")
        
        return batches
    
    async def step2_grade_batch(self, batch: BatchTask, has_marking_scheme: bool, total_batches: int, total_questions: int, file_paths: List[str], learning_data: Dict[str, Any], one_batch_mode: bool = False) -> Dict[str, Any]:
        """
        步骤2：批改单个批次
        使用prompts_simplified.py中的批改提示词，严格参照批改标准
        """
        # 确保 semaphore 已创建
        self._ensure_semaphore()
        
        async with self.semaphore:
            start_time = time.time()
            
            if one_batch_mode:
                logger.info(f"🚀 步骤2：一次性批改所有内容 (学生: {batch.student_name})")
            else:
                logger.info(f"🚀 步骤2：批改批次 {batch.batch_id + 1}/{total_batches} (学生: {batch.student_name}, 题号: {batch.question_numbers})")
            
            # 构建强化的批改标准提醒
            marking_reminder = ""
            if learning_data.get("has_marking_scheme", False):
                marking_reminder = f"""
🛑 【批改标准严格参照提醒】🛑

📚 你已经学习了批改标准，现在必须严格按照标准批改！

📋 学习到的重要信息：
{learning_data.get("learning_result", "")[:500]}...

⚠️ 核心要求：
1. 每个给分点必须在批改标准中找到依据
2. 严格按照标准的分值分配给分
3. 不能给出超出标准的分数
4. 每个步骤都要引用具体的批改标准
5. 遇到疑问时选择更严格的标准

🔍 批改时请反复对照批改标准，确保每一分都有依据！
"""
            
            # 根据模式构建不同的提示词
            if one_batch_mode:
                # 一次性批改模式
                full_prompt = f"""🛑 重要提醒：你可以直接查看PDF图像内容！

📄 你已经接收到了PDF文件的图像内容，可以直接查看和分析其中的文字、公式和图表。不要说"无法查看PDF"，请直接分析图像中的内容。

{marking_reminder}

请批改以下所有内容。由于无法识别具体题目数量，请：
1. 仔细查找所有题目（可能的标记：题目1、第1题、Q1、Question 1等）
2. 为每道找到的题目进行批改
3. 🛑 严格按照批改标准批改，每个给分点都要引用标准
4. 使用规定的格式输出每道题的批改结果

学生: {batch.student_name} (ID: {batch.student_id})

文件内容：
{batch.file_content}

🛑 记住：严格参照批改标准，每个给分点都必须有"📚标准："引用！"""
            else:
                # 正常批改模式
                batch_prompt = get_batch_processing_prompt(
                    batch_number=batch.batch_id + 1,
                    current_range=[batch.question_numbers[0], batch.question_numbers[-1]]
                )
                
                full_prompt = f"""🛑 重要提醒：你可以直接查看PDF图像内容！

📄 你已经接收到了PDF文件的图像内容，可以直接查看和分析其中的文字、公式和图表。不要说"无法查看PDF"，请直接分析图像中的内容。

{marking_reminder}

{batch_prompt}

📊 批改任务：
请批改第{batch.question_numbers[0]}-{batch.question_numbers[-1]}题

📋 文件说明：
- MARKING文件：包含批改标准和答案（这是你批改的依据）
- ANSWER文件：包含学生的作答内容（这是你要批改的对象）

⚠️ 关键指示：
1. 你可以直接查看PDF图像中的所有内容
2. 请仔细对比学生答案与批改标准
3. 🛑 严格按照MARKING标准给分，每个给分点都要引用标准
4. 必须批改指定范围内的所有题目
5. 每个步骤都要包含"📚标准："引用

{batch.file_content}

🛑 开始批改！记住：每个给分点都必须有批改标准依据！"""
            
            try:
                # 检查批次内容是否包含PDF图像
                pdf_files = []
                for file_path in file_paths:
                    if file_path.endswith('.pdf'):
                        pdf_files.append(file_path)
                
                if pdf_files:
                    # 如果有PDF文件，使用多媒体API调用
                    logger.info(f"📄 批改时检测到PDF文件，使用多媒体API处理: {[Path(f).name for f in pdf_files]}")
                    
                    # 构建多媒体API调用
                    api_args = [full_prompt]
                    api_args.extend(pdf_files)  # 添加PDF文件路径
                    
                    # 调用多媒体API
                    result = call_tongyiqianwen_api(
                        *api_args,
                        system_message=ULTIMATE_SYSTEM_MESSAGE
                    )
                else:
                    # 没有PDF文件，使用普通文本API调用
                    result = call_tongyiqianwen_api(
                        full_prompt,
                        system_message=ULTIMATE_SYSTEM_MESSAGE
                    )
                
                # 验证批改结果
                if not result or not result.strip():
                    logger.error(f"❌ 批次 {batch.batch_id} 返回空结果")
                    return {
                        'batch_id': batch.batch_id,
                        'student_id': batch.student_id,
                        'student_name': batch.student_name,
                        'question_numbers': batch.question_numbers,
                        'result': "批改失败：API返回空结果",
                        'total_score': 0,
                        'processing_time': time.time() - start_time,
                        'success': False
                    }
                
                # 检查批改结果是否符合标准要求
                if learning_data.get("has_marking_scheme", False):
                    consistency_check = await self.check_marking_consistency(result, learning_data)
                    if not consistency_check.get("passed", True):
                        logger.warning(f"⚠️ 批次 {batch.batch_id} 批改结果不符合标准要求")
                        # 可以选择重新批改或添加警告
                
                logger.info(f"✅ 批次 {batch.batch_id} 批改完成，耗时: {time.time() - start_time:.2f}秒")
                
                return {
                    'batch_id': batch.batch_id,
                    'student_id': batch.student_id,
                    'student_name': batch.student_name,
                    'question_numbers': batch.question_numbers,
                    'result': result,
                    'total_score': self.extract_total_score(result),
                    'processing_time': time.time() - start_time,
                    'success': True
                }
                
            except Exception as e:
                logger.error(f"❌ 批次 {batch.batch_id} 处理异常: {e}")
                return {
                    'batch_id': batch.batch_id,
                    'student_id': batch.student_id,
                    'student_name': batch.student_name,
                    'question_numbers': batch.question_numbers,
                    'result': f"批改失败：{str(e)}",
                    'total_score': 0,
                    'processing_time': time.time() - start_time,
                    'success': False
                }
    
    async def check_marking_consistency(self, grading_result: str, learning_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查批改结果与批改标准的一致性"""
        try:
            # 构建一致性检查提示
            consistency_prompt = f"""
{MARKING_CONSISTENCY_CHECK_PROMPT}

已学习的批改标准：
{learning_data.get("learning_result", "")[:1000]}

批改结果：
{grading_result}

请检查批改结果是否严格符合批改标准。
"""
            
            # 调用API进行一致性检查
            check_result = call_tongyiqianwen_api(
                consistency_prompt,
                system_message="你是批改质量检查专家，负责确保批改结果严格符合标准。"
            )
            
            # 解析检查结果
            passed = "通过" in check_result and "需要修正" not in check_result
            
            return {
                "passed": passed,
                "check_result": check_result,
                "issues": [] if passed else ["批改结果不符合标准要求"]
            }
            
        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            return {"passed": True, "check_result": "检查失败", "issues": []}
    
    async def step3_generate_summary(self, student_id: str, student_name: str, batch_results: List[Dict]) -> str:
        """
        步骤3：生成学生总结
        使用prompts_simplified.py中的总结提示词
        """
        logger.info(f"📊 步骤3：为学生 {student_name} 生成总结...")
        
        # 合并该学生的所有批改结果
        all_results = []
        total_questions = 0
        
        for result in sorted(batch_results, key=lambda x: x.get('question_numbers', [0])[0] if x.get('question_numbers') else 0):
            if result['student_id'] == student_id and result.get('result') and '批改失败' not in result.get('result', ''):
                all_results.append(f"批次{result['batch_id'] + 1}（题目{result['question_numbers']}）:\\n{result['result']}")
                total_questions += len(result.get('question_numbers', []))
        
        if not all_results:
            return "无有效批改结果"
        
        # 使用prompts_simplified中的总结提示词
        summary_prompt = f"""{get_summary_generation_prompt()}

学生姓名：{student_name}
总题目数：{total_questions}

批改结果：
{chr(10).join(all_results)}

请基于以上批改结果生成总结。"""
        
        try:
            summary = call_tongyiqianwen_api(
                summary_prompt,
                system_message="你是教育评估专家，请基于批改结果生成专业的学习总结报告。"
            )
            return summary
        except Exception as e:
            logger.error(f"生成总结失败: {e}")
            return "总结生成失败"
    
    async def process_files(self, file_paths: List[str], file_info_list: List[Dict]) -> Dict[str, Any]:
        """
        处理所有文件的主函数
        严格按照三步骤执行
        """
        start_time = datetime.now()
        logger.info("🎯 开始智能批量处理...")
        
        # 步骤0：深度学习批改标准
        learning_result = await self.step0_learn_marking_scheme(file_paths, file_info_list)
        
        # 步骤1：识别文件结构
        structure_data = await self.step1_analyze_structure(file_paths, file_info_list)
        
        # 将学习结果合并到结构数据中
        structure_data.update(learning_result)
        
        # 输出识别结果
        logger.info(f"\n📋 步骤1完成 - 文件结构识别结果：")
        logger.info(f"  - 总题目数: {structure_data.get('total_questions', 0)} 题")
        logger.info(f"  - 学生数量: {len(structure_data.get('students', []))} 人")
        logger.info(f"  - 文件类型: {structure_data.get('content_type', '未知')}")
        logger.info(f"  - 识别置信度: {structure_data.get('confidence', 'unknown')}")
        logger.info(f"  - 批改标准: {'✅ 已学习' if structure_data.get('has_marking_scheme', False) else '❌ 未提供'}")
        
        # 如果有批改标准，输出学习摘要
        if structure_data.get('has_marking_scheme', False):
            logger.info(f"\n📚 批改标准学习摘要：")
            learned_standards = structure_data.get('learned_standards', {})
            if learned_standards.get('principles'):
                logger.info(f"  - 评分原则: {learned_standards['principles'][:100]}...")
            if learned_standards.get('key_points'):
                logger.info(f"  - 重点记忆: {learned_standards['key_points'][:100]}...")
        
        # 创建批次任务
        batches = self.create_batch_tasks(structure_data)
        
        # 计算并输出批改计划
        if len(batches) > 0:
            logger.info(f"\n📝 批改计划：")
            logger.info(f"  - 将分 {len(batches)} 批进行批改")
            logger.info(f"  - 每批最多 {self.batch_size} 道题")
            logger.info(f"  - 并发数: {self.max_concurrent}")
        
        # 步骤2：并发批改所有批次
        logger.info(f"\n⚡ 步骤2开始：并发批改 {len(batches)} 个批次...")
        batch_results = await asyncio.gather(
            *[self.step2_grade_batch(batch, structure_data['has_marking_scheme'], len(batches), structure_data['total_questions'], file_paths, structure_data, structure_data.get('one_batch_mode', False)) for batch in batches]
        )
        
        # 步骤3：为每个学生生成总结
        logger.info(f"\n📊 步骤3开始：生成学生总结...")
        student_summaries = {}
        unique_students = {}
        for batch in batches:
            unique_students[batch.student_id] = batch.student_name
        
        for student_id, student_name in unique_students.items():
            student_results = [r for r in batch_results if r['student_id'] == student_id]
            summary = await self.step3_generate_summary(student_id, student_name, student_results)
            student_summaries[student_id] = summary
        
        # 整合最终结果
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        final_result = {
            "structure": structure_data,
            "batch_results": batch_results,
            "student_summaries": student_summaries,
            "processing_time": processing_time,
            "total_batches": len(batches),
            "total_students": len(unique_students),
            "success": True
        }
        
        logger.info(f"\n✅ 批量处理完成！总耗时: {processing_time:.2f}秒")
        return final_result

    def extract_total_score(self, result: str) -> float:
        """从批改结果中提取总分"""
        try:
            # 尝试匹配各种总分格式
            patterns = [
                r'总分[：:]\\s*(\\d+(?:\\.\\d+)?)',
                r'总得分[：:]\\s*(\\d+(?:\\.\\d+)?)',
                r'得分[：:]\\s*(\\d+(?:\\.\\d+)?)',
                r'分数[：:]\\s*(\\d+(?:\\.\\d+)?)',
                r'(\\d+(?:\\.\\d+)?)\\s*分'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, result)
                if match:
                    return float(match.group(1))
            
            # 如果没有找到总分，返回0
            return 0.0
        except:
            return 0.0

# 全局处理器实例（延迟创建）
intelligent_processor = None

def get_intelligent_processor(batch_size: int = 10, max_concurrent: int = 3) -> IntelligentBatchProcessor:
    """获取智能处理器实例，如果不存在则创建"""
    global intelligent_processor
    if intelligent_processor is None:
        intelligent_processor = IntelligentBatchProcessor(batch_size, max_concurrent)
    return intelligent_processor

async def intelligent_batch_correction(file_paths: List[str], file_info_list: List[Dict],
                                     batch_size: int = 10, max_concurrent: int = 3) -> Dict[str, Any]:
    """
    智能批量批改的入口函数
    
    Args:
        file_paths: 文件路径列表
        file_info_list: 文件信息列表
        batch_size: 每批处理的题目数量
        max_concurrent: 最大并发数
    
    Returns:
        包含批改结果和总结的字典
    """
    processor = get_intelligent_processor(batch_size=batch_size, max_concurrent=max_concurrent)
    
    # 执行批量处理
    result = await processor.process_files(file_paths, file_info_list)
    
    # 格式化最终输出
    formatted_output = format_final_result(result)
    
    return {
        "status": result.get("status", "success"),  # 传递状态
        "text": formatted_output['text'],
        "html": formatted_output['html'],
        "raw_data": result,
        "format": "intelligent_batch",
        "processing_time": result.get("processing_time", 0),
        "total_batches": result.get("total_batches", 0),
        "total_students": result.get("total_students", 0)
    }

def format_final_result(result: Dict[str, Any]) -> Dict[str, str]:
    """格式化最终结果为文本和HTML（增强视觉效果版）"""
    text_output = []
    
    # 标题
    text_output.append("# 🎓 智能批改完整报告")
    text_output.append(f"\n处理时间: {result['processing_time']:.2f}秒")
    text_output.append(f"批次数量: {result['total_batches']}")
    text_output.append(f"学生数量: {result['total_students']}")
    text_output.append("\n" + "=" * 80 + "\n")
    
    # 每个学生的详细批改结果
    for batch_result in sorted(result['batch_results'], key=lambda x: (x['student_id'], x['question_numbers'][0] if x.get('question_numbers') else 0)):
        if batch_result['success']:
            question_range = batch_result['question_numbers']
            if len(question_range) > 1:
                text_output.append(f"\n## 学生: {batch_result['student_name']} - 题目 {question_range[0]}-{question_range[-1]}")
            else:
                text_output.append(f"\n## 学生: {batch_result['student_name']} - 题目 {question_range[0]}")
            text_output.append(batch_result['result'])
            text_output.append("\n" + "-" * 40)
    
    # 每个学生的总结
    text_output.append("\n\n" + "=" * 80)
    text_output.append("\n# 📊 学习总结")
    
    for student_id, summary in result['student_summaries'].items():
        student_name = next((b['student_name'] for b in result['batch_results'] if b['student_id'] == student_id), student_id)
        text_output.append(f"\n## 🎯 {student_name}")
        text_output.append(summary)
        text_output.append("\n" + "=" * 80)
    
    final_text = "\n".join(text_output)
    
    # 创建增强的HTML输出
    html_output = create_enhanced_html(result)
    
    return {
        "text": final_text,
        "html": html_output
    }

def create_enhanced_html(result: Dict[str, Any]) -> str:
    """创建简洁实用的HTML输出"""
    html_parts = []
    
    # HTML头部和样式 - 简化版
    html_parts.append("""
<div style="font-family: 'Microsoft YaHei', Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; font-size: 14px;">
    <style>
        .report-header {
            background: #4a90e2;
            color: white;
            padding: 25px 30px;
            border-radius: 8px;
            margin-bottom: 25px;
            border: 1px solid #ddd;
        }
        .report-title {
            font-size: 1.8em;
            margin-bottom: 15px;
            font-weight: 600;
        }
        .report-stats {
            display: flex;
            gap: 25px;
            font-size: 1em;
            flex-wrap: wrap;
        }
        .stat-item {
            background: rgba(255,255,255,0.15);
            padding: 8px 16px;
            border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.2);
            min-width: 120px;
            text-align: center;
        }
        .student-section {
            background: white;
            border-radius: 8px;
            padding: 25px 30px;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .student-header {
            background: #5cb85c;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 1.1em;
            font-weight: 600;
            border: 1px solid #4cae4c;
        }
        .question-box {
            background: #fafafa;
            border-left: 4px solid #4a90e2;
            padding: 20px 25px;
            margin-bottom: 18px;
            border-radius: 6px;
            border: 1px solid #e8e8e8;
        }
        .question-title {
            color: #2c3e50;
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .score-info {
            display: flex;
            gap: 15px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .score-full {
            background: #d4edda;
            color: #155724;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
            border: 1px solid #c3e6cb;
            font-size: 0.9em;
        }
        .score-actual {
            background: #fff3cd;
            color: #856404;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
            border: 1px solid #ffeaa7;
            font-size: 0.9em;
        }
        .score-low {
            background: #f8d7da;
            color: #721c24;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
            border: 1px solid #f5c6cb;
            font-size: 0.9em;
        }
        .grading-detail {
            background: white;
            padding: 15px 18px;
            border-radius: 6px;
            margin-top: 10px;
            border: 1px solid #e8e8e8;
            line-height: 1.5;
        }
        .step-correct {
            color: #28a745;
            margin: 6px 0;
            padding-left: 18px;
            position: relative;
            font-size: 0.9em;
        }
        .step-correct:before {
            content: "✓";
            position: absolute;
            left: 0;
            font-weight: bold;
            color: #28a745;
        }
        .step-wrong {
            color: #dc3545;
            margin: 6px 0;
            padding-left: 18px;
            position: relative;
            font-size: 0.9em;
        }
        .step-wrong:before {
            content: "✗";
            position: absolute;
            left: 0;
            font-weight: bold;
            color: #dc3545;
        }
        .summary-section {
            background: #f8f9fa;
            padding: 25px 30px;
            border-radius: 8px;
            margin-top: 30px;
            border: 1px solid #dee2e6;
        }
        .summary-title {
            font-size: 1.4em;
            margin-bottom: 15px;
            color: #2c3e50;
            font-weight: 600;
        }
        .summary-content {
            background: white;
            padding: 20px;
            border-radius: 6px;
            line-height: 1.6;
            border: 1px solid #e8e8e8;
        }
        .summary-stats {
            background: #e7f3ff;
            padding: 15px 18px;
            border-radius: 6px;
            margin-bottom: 15px;
            border: 1px solid #b8daff;
        }
        .performance-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 4px;
            font-weight: 600;
            margin: 3px;
            font-size: 0.85em;
        }
        .badge-excellent {
            background: #28a745;
            color: white;
        }
        .badge-good {
            background: #007bff;
            color: white;
        }
        .badge-average {
            background: #ffc107;
            color: #212529;
        }
        .badge-poor {
            background: #dc3545;
            color: white;
        }
        .divider {
            height: 1px;
            background: #dee2e6;
            margin: 25px 0;
        }
        /* 确保左右一致的容器 */
        .content-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .balanced-row {
            display: flex;
            gap: 20px;
            align-items: stretch;
        }
        .balanced-row > * {
            flex: 1;
        }
    </style>
    """)
    
    # 报告头部 - 简洁版
    html_parts.append(f"""
    <div class="report-header">
        <h1 class="report-title">📝 批改结果</h1>
        <div class="report-stats">
            <div class="stat-item">⏱️ 处理时间<br/>{result['processing_time']:.1f}秒</div>
            <div class="stat-item">📦 批次数量<br/>{result['total_batches']}</div>
            <div class="stat-item">👥 学生数量<br/>{result['total_students']}</div>
        </div>
    </div>
    """)
    
    # 批改详情部分
    html_parts.append('<div class="grading-details">')
    
    # 按学生分组显示批改结果
    student_results = {}
    for batch_result in result['batch_results']:
        if batch_result['success']:
            student_id = batch_result['student_id']
            if student_id not in student_results:
                student_results[student_id] = {
                    'name': batch_result['student_name'],
                    'batches': []
                }
            student_results[student_id]['batches'].append(batch_result)
    
    # 显示每个学生的批改结果
    for student_id, student_data in student_results.items():
        html_parts.append(f'<div class="student-section">')
        html_parts.append(f'<div class="student-header">👤 {student_data["name"]} 的批改结果</div>')
        
        # 显示该学生的所有批次
        for batch in sorted(student_data['batches'], key=lambda x: x['question_numbers'][0]):
            # 解析批改结果，转换为更好的HTML格式
            formatted_result = format_grading_result_to_html(batch['result'])
            html_parts.append(formatted_result)
        
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    
    # 总结部分
    html_parts.append('<div class="divider"></div>')
    html_parts.append('<div class="summary-section">')
    html_parts.append('<h2 class="summary-title">📊 学习总结</h2>')
    
    for student_id, summary in result['student_summaries'].items():
        student_name = student_results.get(student_id, {}).get('name', student_id)
        html_parts.append(f'<div class="summary-content">')
        html_parts.append(f'<h3 style="color: #2c3e50; margin-bottom: 15px; font-size: 1.1em;">🎯 {student_name}</h3>')
        
        # 格式化总结内容
        formatted_summary = format_summary_to_html(summary)
        html_parts.append(formatted_summary)
        
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)

def format_grading_result_to_html(result: str) -> str:
    """将批改结果转换为增强的HTML格式，突出显示扣分点"""
    html_parts = []
    
    # 解析批改结果
    lines = result.split('\n')
    current_question = None
    in_grading_detail = False
    
    for line in lines:
        line = line.strip()
        
        # 识别题目标题
        if line.startswith('### 题目') or line.startswith('**题目'):
            if current_question:
                if in_grading_detail:
                    html_parts.append('</div>')
                    in_grading_detail = False
                html_parts.append('</div>')
            html_parts.append('<div class="question-box">')
            html_parts.append(f'<div class="question-title">{line.replace("###", "").replace("**", "").strip()}</div>')
            current_question = True
        
        # 识别满分和得分
        elif line.startswith('**满分**') or line.startswith('满分'):
            match = re.search(r'(\d+(?:\.\d+)?)分', line)
            if match:
                score = match.group(1)
                html_parts.append(f'<div class="score-info">')
                html_parts.append(f'<span class="score-full">满分: {score}分</span>')
        elif line.startswith('**得分**') or line.startswith('得分'):
            match = re.search(r'(\d+(?:\.\d+)?)分', line)
            if match:
                score = float(match.group(1))
                # 根据得分比例选择颜色
                if current_question and '满分' in ''.join(html_parts[-5:]):
                    full_score_match = re.search(r'满分: (\d+(?:\.\d+)?)分', ''.join(html_parts[-5:]))
                    if full_score_match:
                        full_score = float(full_score_match.group(1))
                        ratio = score / full_score if full_score > 0 else 0
                        if ratio >= 0.8:
                            score_class = 'score-actual'
                        else:
                            score_class = 'score-low'
                    else:
                        score_class = 'score-actual'
                else:
                    score_class = 'score-actual'
                html_parts.append(f'<span class="{score_class}">得分: {score}分</span>')
                html_parts.append('</div>')
        
        # 识别批改详情
        elif line.startswith('**批改详情**') or line.startswith('批改详情'):
            if not in_grading_detail:
                html_parts.append('<div class="grading-detail">')
                html_parts.append('<strong>批改详情：</strong>')
                in_grading_detail = True
        
        # 识别批改步骤和扣分点
        elif line.startswith('- ') or line.startswith('• '):
            content = line[2:].strip()
            if '✓' in content or '正确' in content or '√' in content:
                html_parts.append(f'<div class="step-correct">{content}</div>')
            elif '✗' in content or '错误' in content or '×' in content or '扣分' in content:
                # 扣分点用红字显示
                html_parts.append(f'<div class="step-wrong"><span style="color: #dc3545; font-weight: bold;">扣分点：</span>{content}</div>')
            elif '未' in content or '缺少' in content or '遗漏' in content or '不完整' in content:
                # 其他错误也用红字显示
                html_parts.append(f'<div class="step-wrong"><span style="color: #dc3545; font-weight: bold;">问题：</span>{content}</div>')
            else:
                # 一般性评价
                html_parts.append(f'<div style="margin: 6px 0; padding-left: 18px; font-size: 0.9em;">{content}</div>')
        
        # 识别数字编号的列表项
        elif re.match(r'^\d+\.\s+', line):
            content = re.sub(r'^\d+\.\s+', '', line)
            if '✓' in content or '正确' in content or '√' in content:
                html_parts.append(f'<div class="step-correct">{content}</div>')
            elif '✗' in content or '错误' in content or '×' in content or '扣分' in content:
                html_parts.append(f'<div class="step-wrong"><span style="color: #dc3545; font-weight: bold;">扣分点：</span>{content}</div>')
            elif '未' in content or '缺少' in content or '遗漏' in content or '不完整' in content:
                html_parts.append(f'<div class="step-wrong"><span style="color: #dc3545; font-weight: bold;">问题：</span>{content}</div>')
            else:
                html_parts.append(f'<div style="margin: 6px 0; padding-left: 18px; font-size: 0.9em;">{content}</div>')
        
        # 处理其他内容
        elif line and not line.startswith('**') and not line.startswith('###'):
            if in_grading_detail:
                # 检查是否包含扣分关键词
                if any(keyword in line for keyword in ['扣分', '错误', '不正确', '未完成', '缺少', '遗漏', '不完整']):
                    html_parts.append(f'<div style="margin: 6px 0; color: #dc3545; font-weight: bold;">{line}</div>')
                else:
                    html_parts.append(f'<div style="margin: 6px 0; line-height: 1.5;">{line}</div>')
    
    # 关闭未关闭的标签
    if in_grading_detail:
        html_parts.append('</div>')
    if current_question:
        html_parts.append('</div>')
    
    return ''.join(html_parts)

def format_summary_to_html(summary: str) -> str:
    """将总结内容转换为增强的HTML格式"""
    # 转换总结中的特殊格式
    summary_html = summary
    
    # 替换标题
    summary_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', summary_html)
    summary_html = re.sub(r'### (.+)', r'<h4 style="color: #667eea; margin-top: 20px;">\1</h4>', summary_html)
    summary_html = re.sub(r'## (.+)', r'<h3 style="color: #764ba2; margin-top: 25px;">\1</h3>', summary_html)
    
    # 替换列表项
    summary_html = re.sub(r'^\* (.+)$', r'<li>\1</li>', summary_html, flags=re.MULTILINE)
    summary_html = re.sub(r'^\- (.+)$', r'<li>\1</li>', summary_html, flags=re.MULTILINE)
    summary_html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', summary_html, flags=re.MULTILINE)
    
    # 包装列表
    summary_html = re.sub(r'(<li>.*?</li>\n?)+', r'<ul style="margin: 10px 0; padding-left: 25px;">\g<0></ul>', summary_html, flags=re.DOTALL)
    
    # 添加段落标签
    lines = summary_html.split('\n')
    formatted_lines = []
    for line in lines:
        if line.strip() and not line.strip().startswith('<'):
            formatted_lines.append(f'<p style="margin: 10px 0; line-height: 1.8;">{line}</p>')
        else:
            formatted_lines.append(line)
    
    # 识别性能等级并添加徽章
    result_html = '\n'.join(formatted_lines)
    
    # 添加性能徽章
    if '优秀' in result_html:
        result_html = result_html.replace('优秀', '<span class="performance-badge badge-excellent">优秀</span>')
    if '良好' in result_html:
        result_html = result_html.replace('良好', '<span class="performance-badge badge-good">良好</span>')
    if '一般' in result_html:
        result_html = result_html.replace('一般', '<span class="performance-badge badge-average">一般</span>')
    if '需改进' in result_html or '待提高' in result_html:
        result_html = result_html.replace('需改进', '<span class="performance-badge badge-poor">需改进</span>')
        result_html = result_html.replace('待提高', '<span class="performance-badge badge-poor">待提高</span>')
    
    return result_html

def intelligent_batch_correction_sync(file_paths: List[str], file_info_list: List[Dict],
                                    batch_size: int = 10, max_concurrent: int = 3) -> Dict[str, Any]:
    """
    智能批量批改的同步入口函数（供Streamlit使用）
    """
    # 创建新的事件循环或获取现有的
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        # 运行异步函数
        return loop.run_until_complete(
            intelligent_batch_correction(file_paths, file_info_list, batch_size, max_concurrent)
        )
    except Exception as e:
        # 如果出现错误，尝试创建新的事件循环重试一次
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                intelligent_batch_correction(file_paths, file_info_list, batch_size, max_concurrent)
            )
        except Exception as retry_e:
            raise Exception(f"批改失败: {str(e)}, 重试也失败: {str(retry_e)}")