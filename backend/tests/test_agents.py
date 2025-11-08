"""测试Agent架构."""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime

from app.agents.state import GradingState
from app.agents.unified_grading_agent import UnifiedGradingAgent
from app.agents.complexity_assessor import ComplexityAssessor
from app.agents.smart_orchestrator import SmartOrchestrator


class TestComplexityAssessor:
    """测试复杂度评估器"""
    
    def test_simple_task(self):
        """测试简单任务识别"""
        assessor = ComplexityAssessor()
        
        state = GradingState(
            submission_id=uuid4(),
            assignment_id=uuid4(),
            status="preprocessed",
            grading_mode="auto",
            config={},
            max_score=100.0,
            preprocessed_files=[{"type": "text"}],
            extracted_text="这是一个简单的答案",
            file_metadata={},
            score=None,
            errors=[],
            annotations=[],
            confidence=0.0,
            feedback_text="",
            suggestions=[],
            knowledge_points=[],
            processing_start_time=datetime.utcnow(),
            processing_end_time=None,
            processing_time_ms=None,
            from_cache=False,
            error_message=None,
            messages=[],
        )
        
        complexity = assessor.assess(state)
        assert complexity == "simple"
    
    def test_complex_task(self):
        """测试复杂任务识别"""
        assessor = ComplexityAssessor()
        
        # 创建复杂任务: 多文件、长文本、包含图片
        long_text = "这是一个很长的答案。" * 200  # 约2000字符
        
        state = GradingState(
            submission_id=uuid4(),
            assignment_id=uuid4(),
            status="preprocessed",
            grading_mode="auto",
            config={"subject": "数学", "question_count": 15},
            max_score=100.0,
            preprocessed_files=[
                {"type": "text"},
                {"type": "image"},
                {"type": "pdf"},
            ],
            extracted_text=long_text,
            file_metadata={},
            score=None,
            errors=[],
            annotations=[],
            confidence=0.0,
            feedback_text="",
            suggestions=[],
            knowledge_points=[],
            processing_start_time=datetime.utcnow(),
            processing_end_time=None,
            processing_time_ms=None,
            from_cache=False,
            error_message=None,
            messages=[],
        )
        
        complexity = assessor.assess(state)
        assert complexity == "complex"


@pytest.mark.asyncio
class TestUnifiedGradingAgent:
    """测试统一批改Agent"""
    
    async def test_grading_simple_answer(self):
        """测试批改简单答案"""
        agent = UnifiedGradingAgent()
        
        state = GradingState(
            submission_id=uuid4(),
            assignment_id=uuid4(),
            status="preprocessed",
            grading_mode="fast",
            config={
                "grading_standard": {
                    "criteria": "检查答案是否正确",
                    "answer": "地球是圆的"
                },
                "strictness": "standard"
            },
            max_score=10.0,
            preprocessed_files=[],
            extracted_text="地球是圆的",
            file_metadata={},
            score=None,
            errors=[],
            annotations=[],
            confidence=0.0,
            feedback_text="",
            suggestions=[],
            knowledge_points=[],
            processing_start_time=datetime.utcnow(),
            processing_end_time=None,
            processing_time_ms=None,
            from_cache=False,
            error_message=None,
            messages=[],
        )
        
        # 执行批改
        result = await agent.process(state)
        
        # 验证结果
        assert result["status"] == "completed"
        assert result["score"] is not None
        assert 0 <= result["score"] <= 10.0
        assert result["confidence"] > 0
        assert isinstance(result["errors"], list)
        assert isinstance(result["feedback_text"], str)
        assert len(result["feedback_text"]) > 0
    
    async def test_grading_wrong_answer(self):
        """测试批改错误答案"""
        agent = UnifiedGradingAgent()
        
        state = GradingState(
            submission_id=uuid4(),
            assignment_id=uuid4(),
            status="preprocessed",
            grading_mode="fast",
            config={
                "grading_standard": {
                    "criteria": "检查答案是否正确",
                    "answer": "地球是圆的"
                },
                "strictness": "standard"
            },
            max_score=10.0,
            preprocessed_files=[],
            extracted_text="地球是平的",  # 错误答案
            file_metadata={},
            score=None,
            errors=[],
            annotations=[],
            confidence=0.0,
            feedback_text="",
            suggestions=[],
            knowledge_points=[],
            processing_start_time=datetime.utcnow(),
            processing_end_time=None,
            processing_time_ms=None,
            from_cache=False,
            error_message=None,
            messages=[],
        )
        
        # 执行批改
        result = await agent.process(state)
        
        # 验证结果
        assert result["status"] == "completed"
        assert result["score"] is not None
        assert result["score"] < 10.0  # 应该扣分
        assert len(result["errors"]) > 0  # 应该有错误


@pytest.mark.asyncio
class TestSmartOrchestrator:
    """测试智能编排器"""
    
    async def test_full_workflow(self):
        """测试完整工作流"""
        orchestrator = SmartOrchestrator()
        
        input_data = {
            "submission_id": uuid4(),
            "assignment_id": uuid4(),
            "mode": "auto",
            "max_score": 100.0,
            "config": {
                "grading_standard": {
                    "criteria": "检查答案的准确性和完整性",
                    "answer": "光合作用是植物利用光能将二氧化碳和水转化为葡萄糖和氧气的过程。"
                },
                "strictness": "standard"
            }
        }
        
        # 注意: 这个测试需要实际的文件服务
        # 在实际环境中运行,或者mock文件服务
        
        # result = await orchestrator.execute(input_data)
        
        # assert result["status"] in ["completed", "failed"]
        # if result["status"] == "completed":
        #     assert result["score"] is not None
        #     assert result["processing_time_ms"] is not None
        
        # 暂时跳过,因为需要完整的环境
        pytest.skip("需要完整的环境和文件服务")


def test_state_structure():
    """测试状态结构"""
    state = GradingState(
        submission_id=uuid4(),
        assignment_id=uuid4(),
        status="pending",
        grading_mode="fast",
        config={},
        max_score=100.0,
        preprocessed_files=[],
        extracted_text="",
        file_metadata={},
        score=None,
        errors=[],
        annotations=[],
        confidence=0.0,
        feedback_text="",
        suggestions=[],
        knowledge_points=[],
        processing_start_time=datetime.utcnow(),
        processing_end_time=None,
        processing_time_ms=None,
        from_cache=False,
        error_message=None,
        messages=[],
    )
    
    # 验证必需字段
    assert state["submission_id"] is not None
    assert state["assignment_id"] is not None
    assert state["status"] == "pending"
    assert state["grading_mode"] == "fast"
    assert state["max_score"] == 100.0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])

