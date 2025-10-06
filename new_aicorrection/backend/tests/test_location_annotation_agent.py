"""Tests for LocationAnnotationAgent"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.agents.location_annotation_agent import LocationAnnotationAgent
from app.agents.state import BoundingBox, ErrorLocation


@pytest.fixture
def location_agent():
    """创建LocationAnnotationAgent实例"""
    return LocationAnnotationAgent()


@pytest.fixture
def sample_question_bbox():
    """示例题目边界框"""
    return BoundingBox(
        x=50,
        y=100,
        width=700,
        height=300
    )


@pytest.fixture
def sample_error():
    """示例错误"""
    return {
        "type": "计算错误",
        "description": "第二步计算错误，x应该是1而不是2",
        "related_text": "x=2"
    }


class TestLocationAnnotationAgent:
    """LocationAnnotationAgent测试"""
    
    def test_init(self, location_agent):
        """测试初始化"""
        assert location_agent is not None
        assert location_agent.llm is not None
    
    def test_build_prompt(self, location_agent, sample_question_bbox, sample_error):
        """测试Prompt构建"""
        prompt = location_agent._build_prompt(
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox,
            error=sample_error
        )
        
        assert "800px" in prompt
        assert "1200px" in prompt
        assert "计算错误" in prompt
        assert "x=2" in prompt
    
    def test_parse_response_valid(self, location_agent):
        """测试解析有效响应"""
        content = '''
        根据图片分析，错误位于:
        {
          "bbox": {
            "x": 150,
            "y": 200,
            "width": 200,
            "height": 50
          },
          "type": "area",
          "confidence": 0.95,
          "reasoning": "错误位于第二行的计算结果部分"
        }
        '''
        
        result = location_agent._parse_response(content)
        
        assert result["bbox"]["x"] == 150
        assert result["bbox"]["y"] == 200
        assert result["bbox"]["width"] == 200
        assert result["bbox"]["height"] == 50
        assert result["type"] == "area"
        assert result["confidence"] == 0.95
        assert "第二行" in result["reasoning"]
    
    def test_parse_response_invalid(self, location_agent):
        """测试解析无效响应"""
        content = "这不是一个有效的JSON"
        
        with pytest.raises(ValueError):
            location_agent._parse_response(content)
    
    def test_validate_result_valid(self, location_agent, sample_question_bbox):
        """测试验证有效结果"""
        result = ErrorLocation(
            bbox=BoundingBox(x=150, y=200, width=200, height=50),
            type="area",
            confidence=0.95,
            reasoning="测试"
        )
        
        validated = location_agent._validate_result(
            result,
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox
        )
        
        # 置信度应该保持不变或略微降低
        assert validated["confidence"] >= 0.6
        assert validated["confidence"] <= 0.95
    
    def test_validate_result_out_of_bounds(self, location_agent, sample_question_bbox):
        """测试验证超出边界的结果"""
        result = ErrorLocation(
            bbox=BoundingBox(x=-10, y=200, width=200, height=50),
            type="area",
            confidence=0.95,
            reasoning="测试"
        )
        
        validated = location_agent._validate_result(
            result,
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox
        )
        
        # 置信度应该降低
        assert validated["confidence"] < 0.95
    
    def test_validate_result_far_from_question(self, location_agent, sample_question_bbox):
        """测试验证远离题目区域的结果"""
        result = ErrorLocation(
            bbox=BoundingBox(x=150, y=800, width=200, height=50),
            type="area",
            confidence=0.95,
            reasoning="测试"
        )
        
        validated = location_agent._validate_result(
            result,
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox
        )
        
        # 置信度应该降低
        assert validated["confidence"] < 0.95
    
    def test_get_fallback_location(self, location_agent, sample_question_bbox):
        """测试兜底位置"""
        fallback = location_agent._get_fallback_location(sample_question_bbox)
        
        assert fallback["confidence"] == 0.3
        assert fallback["type"] == "area"
        assert "中心位置" in fallback["reasoning"]
        
        # 检查位置是否在题目区域内
        bbox = fallback["bbox"]
        question_center_x = sample_question_bbox["x"] + sample_question_bbox["width"] / 2
        question_center_y = sample_question_bbox["y"] + sample_question_bbox["height"] / 2
        
        result_center_x = bbox["x"] + bbox["width"] / 2
        result_center_y = bbox["y"] + bbox["height"] / 2
        
        assert abs(result_center_x - question_center_x) < 10
        assert abs(result_center_y - question_center_y) < 10
    
    @pytest.mark.asyncio
    async def test_annotate_with_mock_llm(self, location_agent, sample_question_bbox, sample_error):
        """测试标注功能 (使用Mock LLM)"""
        # Mock LLM响应
        mock_response = Mock()
        mock_response.content = '''
        {
          "bbox": {"x": 150, "y": 200, "width": 200, "height": 50},
          "type": "area",
          "confidence": 0.95,
          "reasoning": "错误位于第二行"
        }
        '''
        
        location_agent.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        result = await location_agent.annotate(
            image_url="https://example.com/image.jpg",
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox,
            error=sample_error
        )
        
        assert result is not None
        assert result["confidence"] > 0
        assert result["bbox"]["x"] >= 0
        assert result["bbox"]["y"] >= 0
    
    @pytest.mark.asyncio
    async def test_annotate_with_error(self, location_agent, sample_question_bbox, sample_error):
        """测试标注失败时的兜底"""
        # Mock LLM抛出异常
        location_agent.llm.ainvoke = AsyncMock(side_effect=Exception("API Error"))
        
        result = await location_agent.annotate(
            image_url="https://example.com/image.jpg",
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox,
            error=sample_error
        )
        
        # 应该返回兜底位置
        assert result is not None
        assert result["confidence"] == 0.3
        assert "中心位置" in result["reasoning"]
    
    @pytest.mark.asyncio
    async def test_annotate_with_low_confidence(self, location_agent, sample_question_bbox, sample_error):
        """测试低置信度时的兜底"""
        # Mock LLM返回低置信度
        mock_response = Mock()
        mock_response.content = '''
        {
          "bbox": {"x": 150, "y": 200, "width": 200, "height": 50},
          "type": "area",
          "confidence": 0.3,
          "reasoning": "不确定"
        }
        '''
        
        location_agent.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        result = await location_agent.annotate(
            image_url="https://example.com/image.jpg",
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox,
            error=sample_error
        )
        
        # 应该使用兜底位置
        assert result["confidence"] == 0.3
        assert "中心位置" in result["reasoning"]
    
    @pytest.mark.asyncio
    async def test_batch_annotate(self, location_agent, sample_question_bbox):
        """测试批量标注"""
        errors = [
            {"type": "错误1", "description": "描述1", "related_text": "文本1"},
            {"type": "错误2", "description": "描述2", "related_text": "文本2"},
        ]
        
        # Mock LLM响应
        mock_response = Mock()
        mock_response.content = '''
        {
          "bbox": {"x": 150, "y": 200, "width": 200, "height": 50},
          "type": "area",
          "confidence": 0.95,
          "reasoning": "测试"
        }
        '''
        
        location_agent.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        results = await location_agent.batch_annotate(
            image_url="https://example.com/image.jpg",
            image_width=800,
            image_height=1200,
            question_bbox=sample_question_bbox,
            errors=errors
        )
        
        assert len(results) == 2
        assert all(r["confidence"] > 0 for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

