"""集成测试脚本."""

import asyncio
import sys
import os
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime, UTC

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.unified_grading_agent import UnifiedGradingAgent
from app.agents.complexity_assessor import ComplexityAssessor
from app.agents.state import GradingState


class IntegrationTester:
    """集成测试器"""
    
    def __init__(self):
        """初始化"""
        self.orchestrator = SmartOrchestrator()
        self.test_results = []
    
    async def test_simple_grading(self):
        """测试简单批改"""
        print("\n" + "="*80)
        print("测试1: 简单批改流程")
        print("="*80)
        
        input_data = {
            "submission_id": uuid4(),
            "assignment_id": uuid4(),
            "mode": "fast",
            "max_score": 10.0,
            "config": {
                "grading_standard": {
                    "criteria": "检查答案是否正确",
                    "answer": "地球是圆的"
                },
                "strictness": "standard"
            }
        }
        
        # 模拟已提取的文本 (跳过文件处理)
        print("\n学生答案: 地球是圆的")
        
        try:
            start_time = time.time()
            
            # 注意: 这需要完整的文件服务
            # 这里我们直接测试Agent
            from app.agents.unified_grading_agent import UnifiedGradingAgent
            from app.agents.state import GradingState
            from datetime import datetime
            
            agent = UnifiedGradingAgent()
            state = GradingState(
                submission_id=input_data["submission_id"],
                assignment_id=input_data["assignment_id"],
                status="preprocessed",
                grading_mode=input_data["mode"],
                config=input_data["config"],
                max_score=input_data["max_score"],
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
                processing_start_time=datetime.now(UTC),
                processing_end_time=None,
                processing_time_ms=None,
                from_cache=False,
                error_message=None,
                messages=[],
            )
            
            result = await agent.process(state)
            
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000
            
            # 验证结果
            assert result["status"] == "completed", "状态应为completed"
            assert result["score"] is not None, "应该有分数"
            assert 0 <= result["score"] <= 10, "分数应在0-10之间"
            assert result["confidence"] > 0, "置信度应大于0"
            assert isinstance(result["errors"], list), "errors应为列表"
            assert isinstance(result["feedback_text"], str), "feedback_text应为字符串"
            
            print(f"\n✅ 测试通过!")
            print(f"   得分: {result['score']}/10")
            print(f"   置信度: {result['confidence']:.2%}")
            print(f"   处理时间: {processing_time:.0f}ms")
            
            self.test_results.append({
                "test": "简单批改",
                "status": "passed",
                "time_ms": processing_time,
            })
            
            return True
            
        except AssertionError as e:
            print(f"\n❌ 断言失败: {str(e)}")
            self.test_results.append({
                "test": "简单批改",
                "status": "failed",
                "error": str(e),
            })
            return False
            
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.test_results.append({
                "test": "简单批改",
                "status": "error",
                "error": str(e),
            })
            return False
    
    async def test_complexity_assessment(self):
        """测试复杂度评估"""
        print("\n" + "="*80)
        print("测试2: 复杂度评估")
        print("="*80)
        
        from app.agents.complexity_assessor import ComplexityAssessor
        from app.agents.state import GradingState
        from datetime import datetime
        
        assessor = ComplexityAssessor()
        
        test_cases = [
            {
                "name": "简单任务",
                "text": "简单答案",
                "files": [{"type": "text"}],
                "expected": "simple",
            },
            {
                "name": "中等任务",
                "text": "中等长度的答案" * 50,
                "files": [{"type": "text"}, {"type": "pdf"}],
                "expected": "medium",
            },
            {
                "name": "复杂任务",
                "text": "很长的答案" * 200,
                "files": [{"type": "text"}, {"type": "image"}, {"type": "pdf"}],
                "expected": "complex",
            },
        ]
        
        all_passed = True
        
        for case in test_cases:
            state = GradingState(
                submission_id=uuid4(),
                assignment_id=uuid4(),
                status="preprocessed",
                grading_mode="auto",
                config={"subject": "数学" if case["expected"] == "complex" else ""},
                max_score=100.0,
                preprocessed_files=case["files"],
                extracted_text=case["text"],
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
            
            complexity = assessor.assess(state)
            
            if complexity == case["expected"]:
                print(f"✅ {case['name']}: {complexity} (符合预期)")
            else:
                print(f"❌ {case['name']}: {complexity} (预期: {case['expected']})")
                all_passed = False
        
        if all_passed:
            print(f"\n✅ 所有复杂度评估测试通过!")
            self.test_results.append({
                "test": "复杂度评估",
                "status": "passed",
            })
        else:
            print(f"\n❌ 部分复杂度评估测试失败")
            self.test_results.append({
                "test": "复杂度评估",
                "status": "failed",
            })
        
        return all_passed
    
    async def test_cache_service(self):
        """测试缓存服务"""
        print("\n" + "="*80)
        print("测试3: 缓存服务")
        print("="*80)
        
        try:
            from app.services.cache_service import CacheService
            
            cache = CacheService()
            
            # 测试缓存统计
            stats = await cache.get_cache_stats()
            print(f"\n缓存统计:")
            print(f"  启用: {stats.get('enabled')}")
            print(f"  缓存数: {stats.get('total_cached', 0)}")
            print(f"  TTL: {stats.get('ttl_seconds', 0)}秒")
            print(f"  相似度阈值: {stats.get('similarity_threshold', 0)}")
            
            if stats.get("enabled"):
                print(f"\n✅ 缓存服务正常")
                self.test_results.append({
                    "test": "缓存服务",
                    "status": "passed",
                })
                return True
            else:
                print(f"\n⚠️  缓存服务未启用")
                self.test_results.append({
                    "test": "缓存服务",
                    "status": "skipped",
                    "reason": "缓存未启用",
                })
                return True
                
        except Exception as e:
            print(f"\n❌ 缓存服务测试失败: {str(e)}")
            self.test_results.append({
                "test": "缓存服务",
                "status": "error",
                "error": str(e),
            })
            return False
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*80)
        print("测试总结")
        print("="*80)
        
        passed = sum(1 for r in self.test_results if r["status"] == "passed")
        failed = sum(1 for r in self.test_results if r["status"] == "failed")
        error = sum(1 for r in self.test_results if r["status"] == "error")
        skipped = sum(1 for r in self.test_results if r["status"] == "skipped")
        total = len(self.test_results)
        
        print(f"\n总计: {total} 个测试")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  ⚠️  错误: {error}")
        print(f"  ⏭️  跳过: {skipped}")
        
        if failed == 0 and error == 0:
            print(f"\n🎉 所有测试通过!")
            return True
        else:
            print(f"\n⚠️  有测试失败,请检查")
            return False


async def main():
    """主函数"""
    print("\n🧪 集成测试\n")
    
    tester = IntegrationTester()
    
    # 运行测试
    await tester.test_simple_grading()
    await tester.test_complexity_assessment()
    await tester.test_cache_service()
    
    # 打印总结
    success = tester.print_summary()
    
    print("\n" + "="*80)
    if success:
        print("✅ 集成测试完成!")
    else:
        print("❌ 集成测试失败!")
    print("="*80 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

