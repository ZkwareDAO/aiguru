"""成本分析工具."""

import asyncio
import sys
import os
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime, UTC
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.unified_grading_agent import UnifiedGradingAgent
from app.agents.complexity_assessor import ComplexityAssessor
from app.agents.state import GradingState


class CostAnalyzer:
    """成本分析器"""
    
    def __init__(self):
        """初始化"""
        self.agent = UnifiedGradingAgent()
        self.assessor = ComplexityAssessor()
        self.results: List[Dict] = []
    
    async def analyze_single_grading(self, test_case: Dict) -> Dict:
        """分析单次批改成本
        
        Args:
            test_case: 测试用例
            
        Returns:
            分析结果
        """
        print(f"\n{'='*80}")
        print(f"测试用例: {test_case['name']}")
        print(f"{'='*80}")
        
        # 创建状态
        state = GradingState(
            submission_id=uuid4(),
            assignment_id=uuid4(),
            status="preprocessed",
            grading_mode=test_case.get("mode", "fast"),
            config=test_case["config"],
            max_score=test_case.get("max_score", 100.0),
            preprocessed_files=test_case.get("files", []),
            extracted_text=test_case["student_answer"],
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
        
        # 评估复杂度
        complexity = self.assessor.assess(state)
        print(f"\n复杂度评估: {complexity}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行批改
        try:
            result = await self.agent.process(state)
            
            # 记录结束时间
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000
            
            # 估算成本 (基于模型和token数)
            estimated_cost = self._estimate_cost(
                state["extracted_text"],
                result.get("feedback_text", ""),
                complexity
            )
            
            # 打印结果
            print(f"\n批改结果:")
            print(f"  状态: {result['status']}")
            print(f"  得分: {result.get('score')}/{state['max_score']}")
            print(f"  置信度: {result.get('confidence', 0):.2%}")
            print(f"  错误数: {len(result.get('errors', []))}")
            print(f"  处理时间: {processing_time:.0f}ms")
            print(f"  估算成本: ${estimated_cost:.6f}")
            
            analysis = {
                "name": test_case["name"],
                "complexity": complexity,
                "mode": state["grading_mode"],
                "status": result["status"],
                "score": result.get("score"),
                "processing_time_ms": processing_time,
                "estimated_cost": estimated_cost,
                "input_length": len(state["extracted_text"]),
                "output_length": len(result.get("feedback_text", "")),
                "error_count": len(result.get("errors", [])),
            }
            
            self.results.append(analysis)
            return analysis
            
        except Exception as e:
            print(f"\n❌ 批改失败: {str(e)}")
            return {
                "name": test_case["name"],
                "complexity": complexity,
                "status": "failed",
                "error": str(e),
            }
    
    def _estimate_cost(self, input_text: str, output_text: str, complexity: str) -> float:
        """估算成本
        
        基于输入输出token数和模型定价
        
        Args:
            input_text: 输入文本
            output_text: 输出文本
            complexity: 复杂度
            
        Returns:
            估算成本 (美元)
        """
        # 估算token数 (中文约1.5字符/token, 英文约4字符/token)
        input_tokens = len(input_text) / 2  # 保守估计
        output_tokens = len(output_text) / 2
        
        # Gemini 2.0 Flash 定价 (免费版本实际为$0)
        # 这里使用假设的定价用于演示
        input_price_per_1k = 0.00015  # $0.15 per 1M tokens
        output_price_per_1k = 0.0006   # $0.60 per 1M tokens
        
        input_cost = (input_tokens / 1000) * input_price_per_1k
        output_cost = (output_tokens / 1000) * output_price_per_1k
        
        total_cost = input_cost + output_cost
        
        # 根据复杂度调整 (更复杂的任务可能需要更多token)
        complexity_multiplier = {
            "simple": 0.8,
            "medium": 1.0,
            "complex": 1.2,
        }.get(complexity, 1.0)
        
        return total_cost * complexity_multiplier
    
    def print_summary(self):
        """打印总结"""
        if not self.results:
            print("\n没有分析结果")
            return
        
        print(f"\n{'='*80}")
        print("成本分析总结")
        print(f"{'='*80}")
        
        # 按复杂度分组
        by_complexity = {}
        for result in self.results:
            complexity = result.get("complexity", "unknown")
            if complexity not in by_complexity:
                by_complexity[complexity] = []
            by_complexity[complexity].append(result)
        
        # 打印每个复杂度的统计
        print(f"\n{'复杂度':<10} {'数量':<8} {'平均成本':<12} {'平均时间':<12} {'推荐模式'}")
        print("-" * 80)
        
        total_cost = 0
        total_time = 0
        total_count = 0
        
        for complexity in ["simple", "medium", "complex"]:
            if complexity not in by_complexity:
                continue
            
            results = by_complexity[complexity]
            avg_cost = sum(r.get("estimated_cost", 0) for r in results) / len(results)
            avg_time = sum(r.get("processing_time_ms", 0) for r in results) / len(results)
            
            mode_map = {
                "simple": "快速模式",
                "medium": "标准模式",
                "complex": "完整模式",
            }
            
            print(f"{complexity:<10} {len(results):<8} ${avg_cost:<11.6f} {avg_time:<11.0f}ms {mode_map[complexity]}")
            
            total_cost += avg_cost * len(results)
            total_time += avg_time * len(results)
            total_count += len(results)
        
        # 总计
        print("-" * 80)
        avg_cost_overall = total_cost / total_count if total_count > 0 else 0
        avg_time_overall = total_time / total_count if total_count > 0 else 0
        print(f"{'总计':<10} {total_count:<8} ${avg_cost_overall:<11.6f} {avg_time_overall:<11.0f}ms")
        
        # 月度和年度估算
        print(f"\n{'='*80}")
        print("成本估算")
        print(f"{'='*80}")
        
        monthly_10k = avg_cost_overall * 10000
        yearly_120k = avg_cost_overall * 120000
        
        print(f"\n基于平均成本 ${avg_cost_overall:.6f}/次:")
        print(f"  月度成本 (10,000次):  ${monthly_10k:.2f}")
        print(f"  年度成本 (120,000次): ${yearly_120k:.2f}")
        
        # 与原设计对比
        original_cost = 0.013
        savings_per_request = original_cost - avg_cost_overall
        savings_percentage = (savings_per_request / original_cost) * 100
        monthly_savings = savings_per_request * 10000
        yearly_savings = savings_per_request * 120000
        
        print(f"\n与原设计对比 (${original_cost}/次):")
        print(f"  单次节省: ${savings_per_request:.6f} ({savings_percentage:.1f}%)")
        print(f"  月度节省: ${monthly_savings:.2f}")
        print(f"  年度节省: ${yearly_savings:.2f}")


async def main():
    """主函数"""
    print("\n💰 成本分析工具\n")
    
    # 测试用例
    test_cases = [
        {
            "name": "简单选择题",
            "mode": "fast",
            "max_score": 10,
            "student_answer": "答案: B",
            "config": {
                "grading_standard": {
                    "criteria": "检查答案是否正确",
                    "answer": "B"
                },
                "strictness": "standard"
            },
            "files": [{"type": "text"}],
        },
        {
            "name": "中等主观题",
            "mode": "standard",
            "max_score": 20,
            "student_answer": """
解答:
1. 光合作用是植物利用光能的过程
2. 需要二氧化碳和水
3. 产生葡萄糖和氧气
4. 发生在叶绿体中
""",
            "config": {
                "grading_standard": {
                    "criteria": "检查答案的完整性和准确性",
                    "answer": "光合作用是植物利用光能将二氧化碳和水转化为葡萄糖和氧气的过程,发生在叶绿体中。"
                },
                "strictness": "standard",
                "question_count": 1,
            },
            "files": [{"type": "text"}],
        },
        {
            "name": "复杂论述题",
            "mode": "premium",
            "max_score": 50,
            "student_answer": """
论述题答案:

一、引言
本文将从多个角度分析这个问题...

二、主要观点
1. 第一个观点是...
   - 支持论据1
   - 支持论据2
   
2. 第二个观点是...
   - 支持论据1
   - 支持论据2

三、案例分析
通过具体案例可以看出...

四、结论
综上所述...
""" * 3,  # 长文本
            "config": {
                "grading_standard": {
                    "criteria": "评估论述的逻辑性、完整性、论据充分性",
                    "answer": "标准答案包含引言、主要观点、案例分析和结论四个部分..."
                },
                "strictness": "strict",
                "subject": "语文",
                "question_count": 1,
            },
            "files": [{"type": "text"}, {"type": "pdf"}],
        },
    ]
    
    analyzer = CostAnalyzer()
    
    # 分析每个测试用例
    for test_case in test_cases:
        try:
            await analyzer.analyze_single_grading(test_case)
        except Exception as e:
            print(f"\n❌ 分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 打印总结
    analyzer.print_summary()
    
    print(f"\n{'='*80}")
    print("✅ 成本分析完成!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # 设置环境变量 (如果未设置)
    if not os.getenv("OPENROUTER_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("⚠️  警告: 未设置API密钥,请设置 OPENROUTER_API_KEY 或 OPENAI_API_KEY")
        print("示例: export OPENROUTER_API_KEY=your-key-here\n")
    
    asyncio.run(main())

