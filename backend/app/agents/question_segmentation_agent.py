"""Question Segmentation Agent - 题目分段识别

使用OCR识别题号，计算边界框，截取题目图片
成本: $0.001/页 (或免费使用Tesseract)
"""

import logging
import re
import io
from typing import List, Dict, Optional, Tuple
from PIL import Image
import requests

from app.agents.state import QuestionSegment, BoundingBox

logger = logging.getLogger(__name__)


class QuestionSegmentationAgent:
    """题目分段Agent
    
    职责:
    - OCR识别题号
    - 计算题目边界框
    - 截取题目图片
    - 提取题目文字
    
    技术: Tesseract OCR (免费) 或 PaddleOCR
    成本: 免费 或 $0.001/页
    """
    
    # 题号正则表达式
    QUESTION_PATTERNS = [
        r'^(\d+)[.、)]',  # 1. 或 1、 或 1)
        r'^[(（](\d+)[)）]',  # (1) 或 （1）
        r'^第(\d+)题',  # 第1题
        r'^[一二三四五六七八九十]+[.、)]',  # 一、 或 二、
    ]
    
    # 中文数字映射
    CHINESE_NUMBERS = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    }
    
    def __init__(self, use_paddle_ocr: bool = False):
        """初始化Agent
        
        Args:
            use_paddle_ocr: 是否使用PaddleOCR (更准确但需要安装)
        """
        self.use_paddle_ocr = use_paddle_ocr
        
        if use_paddle_ocr:
            try:
                from paddleocr import PaddleOCR
                self.ocr_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    show_log=False
                )
                logger.info("QuestionSegmentationAgent initialized with PaddleOCR")
            except ImportError:
                logger.warning("PaddleOCR not installed, falling back to mock OCR")
                self.ocr_engine = None
        else:
            # 使用Tesseract或Mock OCR
            self.ocr_engine = None
            logger.info("QuestionSegmentationAgent initialized with Mock OCR")
    
    async def segment_questions(
        self,
        images: List[str]
    ) -> List[QuestionSegment]:
        """题目分段识别
        
        Args:
            images: 图片URL列表
            
        Returns:
            题目分段列表
        """
        try:
            logger.info(f"Segmenting questions from {len(images)} images")
            
            segments = []
            question_index = 0
            
            for page_index, image_url in enumerate(images):
                # 1. 加载图片
                image, image_width, image_height = await self._load_image(image_url)
                
                # 2. OCR识别
                ocr_result = await self._recognize_text(image)
                
                # 3. 识别题号
                markers = self._detect_question_markers(ocr_result)
                
                if not markers:
                    logger.warning(f"No question markers found in page {page_index}")
                    # 兜底: 将整页作为一个题目
                    segments.append(self._create_fallback_segment(
                        page_index,
                        question_index,
                        image_url,
                        image_width,
                        image_height
                    ))
                    question_index += 1
                    continue
                
                # 4. 计算边界框和截图
                for i, marker in enumerate(markers):
                    next_marker = markers[i + 1] if i + 1 < len(markers) else None
                    
                    bbox = self._calculate_bbox(
                        marker,
                        next_marker,
                        image_width,
                        image_height
                    )
                    
                    # 截取题目图片 (暂时使用原图URL)
                    cropped_image_url = image_url  # TODO: 实际截图上传
                    
                    # 提取题目文字
                    ocr_text = self._extract_text_in_bbox(ocr_result, bbox)
                    
                    segments.append(QuestionSegment(
                        question_number=marker["text"],
                        question_index=question_index,
                        page_index=page_index,
                        bbox=bbox,
                        cropped_image_url=cropped_image_url,
                        ocr_text=ocr_text,
                        confidence=marker["confidence"]
                    ))
                    
                    question_index += 1
            
            logger.info(f"Segmentation completed: {len(segments)} questions found")
            return segments
            
        except Exception as e:
            logger.error(f"Question segmentation failed: {e}", exc_info=True)
            # 返回兜底结果
            return self._create_fallback_segments(images)
    
    async def _load_image(self, image_url: str) -> Tuple[Image.Image, int, int]:
        """加载图片
        
        Args:
            image_url: 图片URL
            
        Returns:
            (图片对象, 宽度, 高度)
        """
        try:
            if image_url.startswith("http"):
                response = requests.get(image_url, timeout=10)
                image = Image.open(io.BytesIO(response.content))
            else:
                image = Image.open(image_url)
            
            width, height = image.size
            return image, width, height
            
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            # 返回默认尺寸
            return None, 800, 1200
    
    async def _recognize_text(self, image: Optional[Image.Image]) -> Dict:
        """OCR文字识别
        
        Args:
            image: 图片对象
            
        Returns:
            OCR结果
        """
        if image is None:
            return {"text": [], "boxes": [], "confidences": []}
        
        if self.use_paddle_ocr and self.ocr_engine:
            # 使用PaddleOCR
            result = self.ocr_engine.ocr(image, cls=True)
            
            text = []
            boxes = []
            confidences = []
            
            for line in result[0]:
                box, (txt, conf) = line
                text.append(txt)
                boxes.append(self._convert_box(box))
                confidences.append(conf)
            
            return {
                "text": text,
                "boxes": boxes,
                "confidences": confidences
            }
        else:
            # Mock OCR结果 (用于测试)
            return self._mock_ocr_result()
    
    def _mock_ocr_result(self) -> Dict:
        """Mock OCR结果 (用于测试)"""
        return {
            "text": [
                "1. 解方程组",
                "x + y = 10",
                "x - y = 2",
                "解: x = 6, y = 4",
                "2. 计算",
                "3 + 5 = 8",
                "3. 填空题",
                "答案: 正确"
            ],
            "boxes": [
                {"x": 50, "y": 100, "width": 200, "height": 30},
                {"x": 50, "y": 140, "width": 150, "height": 25},
                {"x": 50, "y": 170, "width": 150, "height": 25},
                {"x": 50, "y": 200, "width": 200, "height": 25},
                {"x": 50, "y": 300, "width": 150, "height": 30},
                {"x": 50, "y": 340, "width": 150, "height": 25},
                {"x": 50, "y": 450, "width": 150, "height": 30},
                {"x": 50, "y": 490, "width": 150, "height": 25},
            ],
            "confidences": [0.95, 0.92, 0.93, 0.91, 0.94, 0.96, 0.93, 0.90]
        }
    
    def _convert_box(self, box: List) -> Dict:
        """转换PaddleOCR的box格式"""
        x_coords = [point[0] for point in box]
        y_coords = [point[1] for point in box]
        
        return {
            "x": int(min(x_coords)),
            "y": int(min(y_coords)),
            "width": int(max(x_coords) - min(x_coords)),
            "height": int(max(y_coords) - min(y_coords))
        }
    
    def _detect_question_markers(self, ocr_result: Dict) -> List[Dict]:
        """识别题号
        
        Args:
            ocr_result: OCR结果
            
        Returns:
            题号标记列表
        """
        markers = []
        
        for i, text in enumerate(ocr_result["text"]):
            text_stripped = text.strip()
            
            for pattern in self.QUESTION_PATTERNS:
                match = re.match(pattern, text_stripped)
                if match:
                    number = self._extract_number(match, text_stripped)
                    markers.append({
                        "text": text_stripped,
                        "number": number,
                        "box": ocr_result["boxes"][i],
                        "confidence": ocr_result["confidences"][i]
                    })
                    break
        
        # 按y坐标排序
        markers.sort(key=lambda m: m["box"]["y"])
        
        return markers
    
    def _extract_number(self, match: re.Match, text: str) -> int:
        """提取题号数字"""
        try:
            # 尝试提取数字
            num_str = match.group(1)
            return int(num_str)
        except (ValueError, IndexError):
            # 尝试中文数字
            for chinese, num in self.CHINESE_NUMBERS.items():
                if chinese in text:
                    return num
            return 0
    
    def _calculate_bbox(
        self,
        marker: Dict,
        next_marker: Optional[Dict],
        image_width: int,
        image_height: int
    ) -> BoundingBox:
        """计算题目边界框
        
        Args:
            marker: 当前题号标记
            next_marker: 下一个题号标记
            image_width: 图片宽度
            image_height: 图片高度
            
        Returns:
            边界框
        """
        # 起始位置: 题号的y坐标
        start_y = marker["box"]["y"]
        
        # 结束位置: 下一个题号的y坐标 或 图片底部
        if next_marker:
            end_y = next_marker["box"]["y"]
        else:
            end_y = image_height
        
        # 左右边界: 整个图片宽度
        start_x = 0
        end_x = image_width
        
        # 添加边距
        padding = 10
        
        return BoundingBox(
            x=max(0, start_x),
            y=max(0, start_y - padding),
            width=min(end_x, image_width),
            height=min(end_y - start_y + padding, image_height - start_y)
        )
    
    def _extract_text_in_bbox(
        self,
        ocr_result: Dict,
        bbox: BoundingBox
    ) -> str:
        """提取边界框内的文字"""
        texts = []
        
        for i, box in enumerate(ocr_result["boxes"]):
            # 检查box是否在bbox内
            if (box["y"] >= bbox["y"] and
                box["y"] + box["height"] <= bbox["y"] + bbox["height"]):
                texts.append(ocr_result["text"][i])
        
        return "\n".join(texts)
    
    def _create_fallback_segment(
        self,
        page_index: int,
        question_index: int,
        image_url: str,
        image_width: int,
        image_height: int
    ) -> QuestionSegment:
        """创建兜底分段 (整页作为一个题目)"""
        return QuestionSegment(
            question_number=f"第{question_index + 1}题",
            question_index=question_index,
            page_index=page_index,
            bbox=BoundingBox(
                x=0,
                y=0,
                width=image_width,
                height=image_height
            ),
            cropped_image_url=image_url,
            ocr_text="",
            confidence=0.5
        )
    
    def _create_fallback_segments(self, images: List[str]) -> List[QuestionSegment]:
        """创建兜底分段列表"""
        segments = []
        for i, image_url in enumerate(images):
            segments.append(self._create_fallback_segment(
                page_index=i,
                question_index=i,
                image_url=image_url,
                image_width=800,
                image_height=1200
            ))
        return segments

