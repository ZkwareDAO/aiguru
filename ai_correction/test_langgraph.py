#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph 集成测试脚本
测试 LangGraph AI 批改系统的基本功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

async def test_langgraph_workflow():
    """测试 LangGraph 工作流"""
    print("🧪 开始测试 LangGraph AI 批改系统...")
    
    try:
        # 导入LangGraph模块
        from functions.langgraph.workflow import run_ai_grading, get_workflow
        
        print("✅ LangGraph 模块导入成功")
        
        # 获取工作流信息
        workflow = get_workflow()
        workflow_info = workflow.get_workflow_info()
        
        print(f"📋 工作流信息:")
        print(f"   名称: {workflow_info['name']}")
        print(f"   版本: {workflow_info['version']}")
        print(f"   节点数: {len(workflow_info['nodes'])}")
        print(f"   节点列表: {', '.join(workflow_info['nodes'])}")
        
        # 创建测试文件
        test_files_dir = current_dir / "test_files"
        test_files_dir.mkdir(exist_ok=True)
        
        # 创建测试题目文件
        question_file = test_files_dir / "test_question.txt"
        with open(question_file, 'w', encoding='utf-8') as f:
            f.write("""
数学测试题目

1. 计算：2 + 3 = ?
2. 解方程：x + 5 = 10
3. 求导：f(x) = x² 的导数是什么？
            """.strip())
        
        # 创建测试答案文件
        answer_file = test_files_dir / "test_answer.txt"
        with open(answer_file, 'w', encoding='utf-8') as f:
            f.write("""
学生答案

1. 2 + 3 = 5
2. x + 5 = 10，所以 x = 5
3. f'(x) = 2x
            """.strip())
        
        # 创建测试评分标准文件
        marking_file = test_files_dir / "test_marking.txt"
        with open(marking_file, 'w', encoding='utf-8') as f:
            f.write("""
评分标准

1. 计算题 (30分)：答案正确得满分
2. 方程题 (40分)：解题过程20分，答案20分
3. 求导题 (30分)：公式正确得满分

总分：100分
            """.strip())
        
        print(f"📁 测试文件已创建:")
        print(f"   题目文件: {question_file}")
        print(f"   答案文件: {answer_file}")
        print(f"   评分标准: {marking_file}")
        
        # 运行LangGraph批改
        print("\n🚀 开始运行 LangGraph 批改...")
        
        result = await run_ai_grading(
            task_id="test_task_001",
            user_id="test_user",
            question_files=[str(question_file)],
            answer_files=[str(answer_file)],
            marking_files=[str(marking_file)],
            mode="auto",
            strictness_level="中等",
            language="zh"
        )
        
        print("\n📊 批改结果:")
        print(f"   任务ID: {result.get('task_id', 'N/A')}")
        print(f"   完成状态: {result.get('completion_status', 'N/A')}")
        print(f"   最终得分: {result.get('final_score', 0)}")
        print(f"   等级: {result.get('grade_level', 'N/A')}")
        
        # 显示详细结果
        if result.get('completion_status') == 'completed':
            print("\n✅ 批改成功完成！")
            
            # 显示步骤结果
            step_results = result.get('step_results', {})
            if step_results:
                print("\n📋 各步骤执行结果:")
                for step, details in step_results.items():
                    print(f"   {step}: {details}")
            
            # 显示坐标标注
            annotations = result.get('coordinate_annotations', [])
            if annotations:
                print(f"\n🎯 坐标标注: {len(annotations)} 个")
                for i, ann in enumerate(annotations[:3]):  # 显示前3个
                    print(f"   标注{i+1}: {ann.get('annotation_type', '')} - {ann.get('content', '')[:50]}...")
            
            # 显示知识点分析
            knowledge_points = result.get('knowledge_points', [])
            if knowledge_points:
                print(f"\n🧠 知识点分析: {len(knowledge_points)} 个")
                for i, kp in enumerate(knowledge_points[:3]):  # 显示前3个
                    print(f"   知识点{i+1}: {kp.get('topic', '')} ({kp.get('mastery_status', '')})")
            
            # 显示学习建议
            suggestions = result.get('learning_suggestions', [])
            if suggestions:
                print(f"\n💡 学习建议:")
                for i, suggestion in enumerate(suggestions[:3]):  # 显示前3个
                    print(f"   {i+1}. {suggestion}")
        
        else:
            print("\n❌ 批改失败")
            errors = result.get('errors', [])
            if errors:
                print("错误信息:")
                for error in errors:
                    print(f"   - {error.get('error', 'Unknown error')}")
        
        print("\n🧪 LangGraph 测试完成！")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所有依赖包：")
        print("   pip install langgraph langchain-core")
        return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """测试集成模块"""
    print("\n🔧 测试 LangGraph 集成模块...")
    
    try:
        from functions.langgraph_integration import (
            get_langgraph_integration,
            intelligent_correction_with_files_langgraph
        )
        
        print("✅ LangGraph 集成模块导入成功")
        
        # 获取集成实例
        integration = get_langgraph_integration()
        print(f"✅ 集成实例创建成功: {type(integration).__name__}")
        
        # 测试兼容性函数
        print("\n🔄 测试兼容性函数...")
        
        # 创建简单的测试文件
        test_files_dir = Path(__file__).parent / "test_files"
        if not test_files_dir.exists():
            print("❌ 测试文件目录不存在，请先运行 test_langgraph_workflow()")
            return False
        
        question_file = test_files_dir / "test_question.txt"
        answer_file = test_files_dir / "test_answer.txt"
        
        if not (question_file.exists() and answer_file.exists()):
            print("❌ 测试文件不存在，请先运行 test_langgraph_workflow()")
            return False
        
        # 测试兼容性函数（同步版本）
        result_text = intelligent_correction_with_files_langgraph(
            question_files=[str(question_file)],
            answer_files=[str(answer_file)],
            mode="auto"
        )
        
        print("✅ 兼容性函数测试成功")
        print(f"结果长度: {len(result_text)} 字符")
        print(f"结果预览: {result_text[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 LangGraph AI 批改系统测试")
    print("=" * 50)
    
    # 测试1: LangGraph 工作流
    print("\n📋 测试 1: LangGraph 工作流")
    workflow_success = asyncio.run(test_langgraph_workflow())
    
    # 测试2: 集成模块
    print("\n📋 测试 2: 集成模块")
    integration_success = test_integration()
    
    # 总结
    print("\n" + "=" * 50)
    print("🏁 测试总结:")
    print(f"   LangGraph 工作流: {'✅ 通过' if workflow_success else '❌ 失败'}")
    print(f"   集成模块: {'✅ 通过' if integration_success else '❌ 失败'}")
    
    if workflow_success and integration_success:
        print("\n🎉 所有测试通过！LangGraph AI 批改系统已就绪。")
        print("\n📝 下一步:")
        print("   1. 启动 Streamlit 应用: streamlit run streamlit_simple.py")
        print("   2. 选择 '🧠 LangGraph智能批改' 模式")
        print("   3. 上传文件并开始批改")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息并修复问题。")

if __name__ == "__main__":
    main()
