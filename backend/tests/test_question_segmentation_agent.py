"""Tests for QuestionSegmentationAgent"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.agents.question_segmentation_agent import QuestionSegmentationAgent
from app.agents.state import QuestionSegment, BoundingBox


@pytest.fixture
def segmentation_agent():
    """创建QuestionSegmentationAgent实例"""
    return QuestionSegmentationAgent(use_paddle_ocr=False)


@pytest.fixture
def sample_ocr_result():
    """示例OCR结果"""
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


class TestQuestionSegmentationAgent:
    """QuestionSegmentationAgent测试"""
    
    def test_init(self, segmentation_agent):
        """测试初始化"""
        assert segmentation_agent is not None
        assert segmentation_agent.use_paddle_ocr is False
    
    def test_detect_question_markers(self, segmentation_agent, sample_ocr_result):
        """测试题号识别"""
        markers = segmentation_agent._detect_question_markers(sample_ocr_result)
        
        assert len(markers) == 3
        assert markers[0]["text"] == "1. 解方程组"
        assert markers[0]["number"] == 1
        assert markers[1]["text"] == "2. 计算"
        assert markers[1]["number"] == 2
        assert markers[2]["text"] == "3. 填空题"
        assert markers[2]["number"] == 3
    
    def test_detect_question_markers_chinese(self, segmentation_agent):
        """测试中文题号识别"""
        ocr_result = {
            "text": ["一、选择题", "二、填空题", "三、解答题"],
            "boxes": [
                {"x": 50, "y": 100, "width": 200, "height": 30},
                {"x": 50, "y": 300, "width": 200, "height": 30},
                {"x": 50, "y": 500, "width": 200, "height": 30},
            ],
            "confidences": [0.95, 0.94, 0.93]
        }
        
        markers = segmentation_agent._detect_question_markers(ocr_result)
        
        assert len(markers) == 3
        assert markers[0]["number"] == 1
        assert markers[1]["number"] == 2
        assert markers[2]["number"] == 3
    
    def test_detect_question_markers_parentheses(self, segmentation_agent):
        """测试括号题号识别"""
        ocr_result = {
            "text": ["(1) 第一题", "(2) 第二题", "（3）第三题"],
            "boxes": [
                {"x": 50, "y": 100, "width": 200, "height": 30},
                {"x": 50, "y": 300, "width": 200, "height": 30},
                {"x": 50, "y": 500, "width": 200, "height": 30},
            ],
            "confidences": [0.95, 0.94, 0.93]
        }
        
        markers = segmentation_agent._detect_question_markers(ocr_result)
        
        assert len(markers) == 3
        assert markers[0]["number"] == 1
        assert markers[1]["number"] == 2
        assert markers[2]["number"] == 3
    
    def test_calculate_bbox(self, segmentation_agent):
        """测试边界框计算"""
        marker = {
            "text": "1. 题目",
            "number": 1,
            "box": {"x": 50, "y": 100, "width": 200, "height": 30},
            "confidence": 0.95
        }
        
        next_marker = {
            "text": "2. 题目",
            "number": 2,
            "box": {"x": 50, "y": 300, "width": 200, "height": 30},
            "confidence": 0.94
        }
        
        bbox = segmentation_agent._calculate_bbox(
            marker,
            next_marker,
            image_width=800,
            image_height=1200
        )
        
        assert bbox["x"] == 0
        assert bbox["y"] >= 90  # 100 - padding
        assert bbox["width"] == 800
        assert bbox["height"] > 0
    
    def test_calculate_bbox_last_question(self, segmentation_agent):
        """测试最后一个题目的边界框计算"""
        marker = {
            "text": "3. 题目",
            "number": 3,
            "box": {"x": 50, "y": 500, "width": 200, "height": 30},
            "confidence": 0.93
        }
        
        bbox = segmentation_agent._calculate_bbox(
            marker,
            next_marker=None,
            image_width=800,
            image_height=1200
        )
        
        assert bbox["x"] == 0
        assert bbox["y"] >= 490  # 500 - padding
        assert bbox["width"] == 800
        assert bbox["height"] > 0
        # 应该延伸到图片底部
        assert bbox["y"] + bbox["height"] <= 1200
    
    def test_extract_text_in_bbox(self, segmentation_agent, sample_ocr_result):
        """测试提取边界框内的文字"""
        bbox = BoundingBox(
            x=0,
            y=100,
            width=800,
            height=150
        )
        
        text = segmentation_agent._extract_text_in_bbox(sample_ocr_result, bbox)
        
        assert "1. 解方程组" in text
        assert "x + y = 10" in text
        assert "x - y = 2" in text
        assert "解: x = 6, y = 4" in text
    
    def test_create_fallback_segment(self, segmentation_agent):
        """测试创建兜底分段"""
        segment = segmentation_agent._create_fallback_segment(
            page_index=0,
            question_index=0,
            image_url="https://example.com/image.jpg",
            image_width=800,
            image_height=1200
        )
        
        assert segment["question_number"] == "第1题"
        assert segment["question_index"] == 0
        assert segment["page_index"] == 0
        assert segment["bbox"]["x"] == 0
        assert segment["bbox"]["y"] == 0
        assert segment["bbox"]["width"] == 800
        assert segment["bbox"]["height"] == 1200
        assert segment["confidence"] == 0.5
    
    @pytest.mark.asyncio
    async def test_segment_questions_with_mock(self, segmentation_agent):
        """测试题目分段 (使用Mock OCR)"""
        images = ["https://example.com/image1.jpg"]
        
        # Mock _load_image
        async def mock_load_image(url):
            return None, 800, 1200
        
        segmentation_agent._load_image = mock_load_image
        
        # Mock _recognize_text
        async def mock_recognize_text(image):
            return {
                "text": ["1. 题目1", "答案", "2. 题目2", "答案"],
                "boxes": [
                    {"x": 50, "y": 100, "width": 200, "height": 30},
                    {"x": 50, "y": 140, "width": 150, "height": 25},
                    {"x": 50, "y": 300, "width": 200, "height": 30},
                    {"x": 50, "y": 340, "width": 150, "height": 25},
                ],
                "confidences": [0.95, 0.92, 0.94, 0.91]
            }
        
        segmentation_agent._recognize_text = mock_recognize_text
        
        segments = await segmentation_agent.segment_questions(images)
        
        assert len(segments) == 2
        assert segments[0]["question_number"] == "1. 题目1"
        assert segments[0]["question_index"] == 0
        assert segments[1]["question_number"] == "2. 题目2"
        assert segments[1]["question_index"] == 1
    
    @pytest.mark.asyncio
    async def test_segment_questions_no_markers(self, segmentation_agent):
        """测试没有题号时的兜底"""
        images = ["https://example.com/image1.jpg"]
        
        # Mock _load_image
        async def mock_load_image(url):
            return None, 800, 1200
        
        segmentation_agent._load_image = mock_load_image
        
        # Mock _recognize_text - 返回没有题号的结果
        async def mock_recognize_text(image):
            return {
                "text": ["这是一些文字", "没有题号"],
                "boxes": [
                    {"x": 50, "y": 100, "width": 200, "height": 30},
                    {"x": 50, "y": 140, "width": 150, "height": 25},
                ],
                "confidences": [0.95, 0.92]
            }
        
        segmentation_agent._recognize_text = mock_recognize_text
        
        segments = await segmentation_agent.segment_questions(images)
        
        # 应该返回兜底分段 (整页作为一个题目)
        assert len(segments) == 1
        assert segments[0]["confidence"] == 0.5
    
    @pytest.mark.asyncio
    async def test_segment_questions_multiple_pages(self, segmentation_agent):
        """测试多页分段"""
        images = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ]
        
        # Mock _load_image
        async def mock_load_image(url):
            return None, 800, 1200
        
        segmentation_agent._load_image = mock_load_image
        
        # Mock _recognize_text
        call_count = [0]
        
        async def mock_recognize_text(image):
            call_count[0] += 1
            if call_count[0] == 1:
                # 第一页: 2个题目
                return {
                    "text": ["1. 题目1", "2. 题目2"],
                    "boxes": [
                        {"x": 50, "y": 100, "width": 200, "height": 30},
                        {"x": 50, "y": 300, "width": 200, "height": 30},
                    ],
                    "confidences": [0.95, 0.94]
                }
            else:
                # 第二页: 1个题目
                return {
                    "text": ["3. 题目3"],
                    "boxes": [
                        {"x": 50, "y": 100, "width": 200, "height": 30},
                    ],
                    "confidences": [0.93]
                }
        
        segmentation_agent._recognize_text = mock_recognize_text
        
        segments = await segmentation_agent.segment_questions(images)
        
        assert len(segments) == 3
        assert segments[0]["page_index"] == 0
        assert segments[1]["page_index"] == 0
        assert segments[2]["page_index"] == 1
        assert segments[0]["question_index"] == 0
        assert segments[1]["question_index"] == 1
        assert segments[2]["question_index"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

