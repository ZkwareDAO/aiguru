"""Preprocess Agent - 文件预处理."""

import logging
from typing import List, Dict
from pathlib import Path

from app.agents.state import GradingState
from app.services.file_service import FileService

logger = logging.getLogger(__name__)


class PreprocessAgent:
    """预处理Agent
    
    职责:
    - 获取提交的文件
    - 识别文件类型
    - 提取文本内容
    - 数据验证
    
    注意: 这个Agent不调用LLM,所以没有额外成本
    """
    
    def __init__(self, file_service: FileService = None):
        """初始化Agent"""
        self.file_service = file_service or FileService()
        logger.info("PreprocessAgent initialized")
    
    async def process(self, state: GradingState) -> GradingState:
        """执行预处理
        
        Args:
            state: 当前批改状态
            
        Returns:
            更新后的批改状态
        """
        try:
            logger.info(f"PreprocessAgent processing submission {state['submission_id']}")
            
            state["status"] = "preprocessing"
            
            # 1. 获取文件列表
            files = await self._fetch_files(state["submission_id"])
            
            if not files:
                raise ValueError("未找到提交的文件")
            
            # 2. 处理每个文件
            processed_files = []
            all_text = []
            
            for file in files:
                try:
                    processed = await self._process_file(file)
                    processed_files.append(processed)
                    
                    if processed.get("text"):
                        all_text.append(processed["text"])
                        
                except Exception as e:
                    logger.error(f"Failed to process file {file.get('id')}: {e}")
                    # 继续处理其他文件
                    continue
            
            # 3. 合并所有文本
            extracted_text = "\n\n".join(all_text)
            
            # 4. 数据验证
            validation_result = self._validate_data(extracted_text)
            
            if not validation_result["is_valid"]:
                state["status"] = "failed"
                state["error_message"] = validation_result["error"]
                return state
            
            # 5. 更新状态
            state["preprocessed_files"] = processed_files
            state["extracted_text"] = extracted_text
            state["file_metadata"] = {
                "file_count": len(processed_files),
                "total_length": len(extracted_text),
                "has_images": any(f.get("type") == "image" for f in processed_files),
            }
            state["status"] = "preprocessed"
            
            logger.info(
                f"Preprocessing completed: {len(processed_files)} files, "
                f"{len(extracted_text)} chars"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"PreprocessAgent error: {str(e)}", exc_info=True)
            state["status"] = "failed"
            state["error_message"] = f"预处理失败: {str(e)}"
            return state
    
    async def _fetch_files(self, submission_id) -> List[Dict]:
        """获取提交的文件
        
        Args:
            submission_id: 提交ID
            
        Returns:
            文件列表
        """
        try:
            # 从数据库获取文件信息
            files = await self.file_service.get_submission_files(submission_id)
            return files
        except Exception as e:
            logger.error(f"Failed to fetch files: {e}")
            return []
    
    async def _process_file(self, file: Dict) -> Dict:
        """处理单个文件
        
        Args:
            file: 文件信息
            
        Returns:
            处理后的文件信息
        """
        file_type = self._detect_file_type(file)
        
        result = {
            "file_id": file.get("id"),
            "file_name": file.get("name"),
            "file_path": file.get("path"),
            "type": file_type,
        }
        
        # 根据文件类型处理
        if file_type == "image":
            result.update(await self._process_image(file))
        elif file_type == "pdf":
            result.update(await self._process_pdf(file))
        elif file_type == "text":
            result.update(await self._process_text(file))
        else:
            logger.warning(f"Unsupported file type: {file_type}")
        
        return result
    
    def _detect_file_type(self, file: Dict) -> str:
        """检测文件类型
        
        Args:
            file: 文件信息
            
        Returns:
            文件类型: image/pdf/text/unknown
        """
        file_name = file.get("name", "").lower()
        
        if file_name.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
            return "image"
        elif file_name.endswith(".pdf"):
            return "pdf"
        elif file_name.endswith((".txt", ".doc", ".docx")):
            return "text"
        else:
            return "unknown"
    
    async def _process_image(self, file: Dict) -> Dict:
        """处理图片文件
        
        Args:
            file: 文件信息
            
        Returns:
            处理结果
        """
        # TODO: 集成OCR服务
        # 目前返回占位符
        return {
            "text": f"[图片内容: {file.get('name')}]",
            "ocr_confidence": 0.0,
            "needs_ocr": True,
        }
    
    async def _process_pdf(self, file: Dict) -> Dict:
        """处理PDF文件
        
        Args:
            file: 文件信息
            
        Returns:
            处理结果
        """
        try:
            # 使用现有的PDF处理服务
            text = await self.file_service.extract_pdf_text(file.get("path"))
            return {
                "text": text,
                "page_count": 1,  # TODO: 获取实际页数
            }
        except Exception as e:
            logger.error(f"Failed to process PDF: {e}")
            return {
                "text": f"[PDF文件: {file.get('name')}]",
                "error": str(e),
            }
    
    async def _process_text(self, file: Dict) -> Dict:
        """处理文本文件
        
        Args:
            file: 文件信息
            
        Returns:
            处理结果
        """
        try:
            # 读取文本文件
            text = await self.file_service.read_text_file(file.get("path"))
            return {
                "text": text,
            }
        except Exception as e:
            logger.error(f"Failed to process text file: {e}")
            return {
                "text": f"[文本文件: {file.get('name')}]",
                "error": str(e),
            }
    
    def _validate_data(self, text: str) -> Dict:
        """验证提取的数据
        
        Args:
            text: 提取的文本
            
        Returns:
            验证结果
        """
        # 基本验证
        if not text or len(text.strip()) == 0:
            return {
                "is_valid": False,
                "error": "未能提取到有效的文本内容"
            }
        
        # 长度验证
        if len(text) < 10:
            return {
                "is_valid": False,
                "error": "提取的文本内容过短,可能不是有效的作业"
            }
        
        # 长度上限验证
        if len(text) > 50000:
            logger.warning(f"Text too long: {len(text)} chars, truncating...")
            # 可以选择截断或返回错误
            # 这里我们允许,但记录警告
        
        return {
            "is_valid": True,
            "error": None
        }

