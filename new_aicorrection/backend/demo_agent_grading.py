"""演示Agent批改系统."""

import asyncio
import sys
import os
from uuid import uuid4
from datetime import datetime, UTC

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from app.agents.unified_grading_agent import UnifiedGradingAgent
from app.agents.complexity_assessor import ComplexityAssessor
from app.agents.state import GradingState


async def demo_simple_grading():
    """演示简单批改"""
    print("=" * 80)
    print("演示1: 简单数学题批改")
    print("=" * 80)
    
    agent = UnifiedGradingAgent()
    
    state = GradingState(
        submission_id=uuid4(),
        assignment_id=uuid4(),
        status="preprocessed",
        grading_mode="fast",
        config={
            "grading_standard": {
                "criteria": "检查计算过程和最终答案",
                "answer": """
解: 
设两个数为x和y
x + y = 10
x - y = 2
解得: x = 6, y = 4
答: 这两个数是6和4
"""
            },
            "strictness": "standard"
        },
        max_score=10.0,
        preprocessed_files=[],
        extracted_text="""
解:
x + y = 10
x - y = 2
x = 6, y = 4
答: 6和4
""",
        file_metadata={},
        score=None,
        errors=[],
        annotations=[],
        confidence=0.0,
        feedback_text="",
        suggestions=[],
        knowledge_points=[],
        processing_start_time=datetime.now(UTC),
        processing_end_time=None,
        processing_time_ms=None,
        from_cache=False,
        error_message=None,
        messages=[],
    )
    
    print("\n【学生答案】")
    print(state["extracted_text"])
    
    print("\n【开始批改...】")
    result = await agent.process(state)
    
    print(f"\n【批改结果】")
    print(f"状态: {result['status']}")
    print(f"得分: {result['score']}/{result['max_score']}")
    print(f"置信度: {result['confidence']:.2%}")
    
    print(f"\n【错误列表】({len(result['errors'])}个)")
    for i, error in enumerate(result['errors'], 1):
        print(f"\n错误{i}:")
        print(f"  类型: {error.get('type')}")
        print(f"  位置: {error.get('location')}")
        print(f"  说明: {error.get('description')}")
        print(f"  严重程度: {error.get('severity')}")
        print(f"  扣分: {error.get('deduction')}")
    
    print(f"\n【总体反馈】")
    print(result['feedback_text'])
    
    print(f"\n【改进建议】")
    for i, suggestion in enumerate(result['suggestions'], 1):
        print(f"{i}. {suggestion}")
    
    print(f"\n【知识点分析】")
    for kp in result['knowledge_points']:
        print(f"- {kp.get('name')}: 掌握程度 {kp.get('mastery_level')}/100")
        print(f"  建议: {kp.get('suggestion')}")


async def demo_complexity_assessment():
    """演示复杂度评估"""
    print("\n\n" + "=" * 80)
    print("演示2: 任务复杂度评估")
    print("=" * 80)
    
    assessor = ComplexityAssessor()
    
    # 测试用例
    test_cases = [
        {
            "name": "简单任务",
            "state": GradingState(
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
                processing_start_time=datetime.now(UTC),
                processing_end_time=None,
                processing_time_ms=None,
                from_cache=False,
                error_message=None,
                messages=[],
            )
        },
        {
            "name": "中等任务",
            "state": GradingState(
                submission_id=uuid4(),
                assignment_id=uuid4(),
                status="preprocessed",
                grading_mode="auto",
                config={"question_count": 5},
                max_score=100.0,
                preprocessed_files=[{"type": "text"}, {"type": "pdf"}],
                extracted_text="这是一个中等长度的答案。" * 50,
                file_metadata={},
                score=None,
                errors=[],
                annotations=[],
                confidence=0.0,
                feedback_text="",
                suggestions=[],
                knowledge_points=[],
                processing_start_time=datetime.now(UTC),
                processing_end_time=None,
                processing_time_ms=None,
                from_cache=False,
                error_message=None,
                messages=[],
            )
        },
        {
            "name": "复杂任务",
            "state": GradingState(
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
                extracted_text="这是一个很长的答案。" * 200,
                file_metadata={},
                score=None,
                errors=[],
                annotations=[],
                confidence=0.0,
                feedback_text="",
                suggestions=[],
                knowledge_points=[],
                processing_start_time=datetime.now(UTC),
                processing_end_time=None,
                processing_time_ms=None,
                from_cache=False,
                error_message=None,
                messages=[],
            )
        }
    ]
    
    print("\n【复杂度评估结果】")
    for case in test_cases:
        complexity = assessor.assess(case["state"])
        recommended_mode = assessor.get_recommended_mode(complexity)
        
        print(f"\n{case['name']}:")
        print(f"  复杂度: {complexity}")
        print(f"  推荐模式: {recommended_mode}")
        print(f"  文件数: {len(case['state']['preprocessed_files'])}")
        print(f"  文本长度: {len(case['state']['extracted_text'])} 字符")


async def demo_cost_comparison():
    """演示成本对比"""
    print("\n\n" + "=" * 80)
    print("演示3: 成本对比")
    print("=" * 80)
    
    print("\n【批改模式成本对比】")
    print(f"{'模式':<15} {'预估成本':<15} {'适用场景'}")
    print("-" * 60)
    print(f"{'快速模式':<15} {'$0.005':<15} {'简单选择题、填空题'}")
    print(f"{'标准模式':<15} {'$0.009':<15} {'一般主观题'}")
    print(f"{'完整模式':<15} {'$0.015':<15} {'复杂论述题、作文'}")
    
    print("\n【成本优化效果】")
    print(f"原设计 (多Agent分离): $0.013/次")
    print(f"优化后 (Agent融合):   $0.009/次")
    print(f"节省比例: 31%")
    
    print("\n【月度成本估算】(假设每月10,000次批改)")
    print(f"原设计: $130")
    print(f"优化后: $90")
    print(f"每月节省: $40")


async def main():
    """主函数"""
    print("\n🚀 AI批改系统 - Agent架构演示\n")
    
    try:
        # 演示1: 简单批改
        await demo_simple_grading()
        
        # 演示2: 复杂度评估
        await demo_complexity_assessment()
        
        # 演示3: 成本对比
        await demo_cost_comparison()
        
        print("\n\n" + "=" * 80)
        print("✅ 演示完成!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置环境变量 (演示用)
    os.environ.setdefault("OPENROUTER_API_KEY", "your-api-key-here")
    os.environ.setdefault("SECRET_KEY", "demo-secret-key-at-least-32-characters-long")
    os.environ.setdefault("JWT_SECRET_KEY", "demo-jwt-secret-key-at-least-32-chars")
    
    asyncio.run(main())

