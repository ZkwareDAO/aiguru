#!/usr/bin/env python3
"""
Simple AI Grading Test - Direct test of core functionality
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_direct_ai_grading():
    """Test AI grading with sample content"""
    print("🚀 Testing AI Grading Functionality")
    print("=" * 50)
    
    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    try:
        # Import core functionality
        from app.core.ai_grading_engine import call_ai_api
        from app.core.grading_prompts import ULTIMATE_SYSTEM_MESSAGE
        
        print("✅ Core modules imported successfully")
        
        # Sample grading content
        grading_prompt = """
请根据以下内容进行数学作业批改：

【题目】计算 2 + 3 × 4 的值 (5分)

【学生答案】
2 + 3 × 4 = 2 + 12 = 14

【批改标准】
- 运算顺序正确 (2分)
- 计算正确 (3分)
- 正确答案: 14

请按照以下格式批改：

### 题目1
**满分**: 5分
**得分**: [实际得分]
**批改详情**:
- [批改要点1] ✓/✗ [分值]
- [批改要点2] ✓/✗ [分值]
"""
        
        print("🔄 正在调用AI进行批改...")
        
        # Make AI grading call
        result = call_ai_api(
            prompt=grading_prompt,
            system_message="你是一位专业的数学老师，请严格按照批改标准进行评分。"
        )
        
        print("✅ AI批改完成!")
        print("=" * 50)
        print("📝 批改结果:")
        print(result)
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_file_based_grading():
    """Test file-based grading"""
    print("\n📄 测试文件批改功能")
    print("=" * 30)
    
    try:
        from app.core.ai_grading_engine import call_ai_api, process_file_content
        
        # Create test files
        test_dir = Path("simple_test_files")
        test_dir.mkdir(exist_ok=True)
        
        # Question file
        question_content = """QUESTION - 数学题目
题目1 (5分): 计算 (2+3) × 4 的值
请写出计算步骤。"""
        
        # Student answer file  
        answer_content = """ANSWER - 学生: 李明
题目1: 
(2+3) × 4 
= 5 × 4 
= 20"""
        
        # Marking scheme
        marking_content = """MARKING - 评分标准
题目1 (5分):
- 括号优先计算 (2分) 
- 乘法计算正确 (2分)
- 最终答案正确 (1分)
标准答案: 20"""
        
        # Write files
        question_file = test_dir / "question.txt"
        answer_file = test_dir / "answer.txt" 
        marking_file = test_dir / "marking.txt"
        
        question_file.write_text(question_content, encoding='utf-8')
        answer_file.write_text(answer_content, encoding='utf-8')
        marking_file.write_text(marking_content, encoding='utf-8')
        
        print("✅ 测试文件创建完成")
        
        # Process files
        question_text = process_file_content(str(question_file))
        answer_text = process_file_content(str(answer_file))
        marking_text = process_file_content(str(marking_file))
        
        # Create grading prompt
        file_prompt = f"""
请基于以下文件内容进行批改：

{question_text}

{answer_text}

{marking_text}

请严格按照MARKING标准进行评分，输出格式如下：

### 题目1
**满分**: 5分 - 📊 来源: MARKING标准
**得分**: [得分]
**批改详情**:
- [要点1]: [内容] ✓/✗ [分值]
- [要点2]: [内容] ✓/✗ [分值]
- [要点3]: [内容] ✓/✗ [分值]
"""
        
        print("🔄 正在基于文件进行AI批改...")
        
        result = call_ai_api(
            prompt=file_prompt,
            system_message="你是专业数学教师，请严格按照批改标准评分。"
        )
        
        print("✅ 文件批改完成!")
        print("=" * 30)
        print("📝 批改结果:")
        print(result)
        print("=" * 30)
        
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print("🧹 测试文件已清理")
        
        return True
        
    except Exception as e:
        print(f"❌ 文件批改测试失败: {e}")
        return False

def test_pdf_generation():
    """Test PDF generation"""
    print("\n📄 测试PDF生成功能")
    print("=" * 25)
    
    try:
        from app.core.pdf_generator import create_grading_pdf
        
        test_content = """
### 题目1
**满分**: 5分 - 📊 来源: MARKING标准
**得分**: 5分
**批改详情**:
- 括号优先计算 ✓ [2分]
- 乘法计算正确 ✓ [2分] 
- 最终答案正确 ✓ [1分]

### 总结
**总体表现**: 优秀
**总得分**: 5/5 (100%)
学生完全掌握了运算顺序，计算准确无误。
"""
        
        test_stats = {
            "total_score": 5,
            "total_full_marks": 5,
            "percentage": 100.0,
            "questions_graded": 1
        }
        
        test_student = {
            "name": "李明",
            "student_id": "2024002", 
            "class": "初二(3)班"
        }
        
        # Create output directory
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        pdf_path = reports_dir / "test_report.pdf"
        
        print("🔄 正在生成PDF报告...")
        
        success = create_grading_pdf(
            content=test_content,
            output_path=str(pdf_path),
            title="AI批改报告测试",
            student_info=test_student,
            statistics=test_stats
        )
        
        if success:
            print(f"✅ PDF报告生成成功: {pdf_path}")
            print(f"📁 文件大小: {pdf_path.stat().st_size} bytes")
            return True
        else:
            print("❌ PDF生成失败")
            return False
            
    except Exception as e:
        print(f"❌ PDF生成测试失败: {e}")
        return False

def main():
    """Main test function"""
    print("🎯 AI批改系统核心功能测试")
    print("=" * 60)
    
    tests = [
        ("直接AI批改", test_direct_ai_grading),
        ("文件批改", test_file_based_grading), 
        ("PDF生成", test_pdf_generation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("🎉 恭喜! AI批改系统所有核心功能正常!")
        print("💡 你现在可以使用以下功能:")
        print("   - AI智能批改")
        print("   - 多文件处理")
        print("   - PDF报告生成")
    elif passed > 0:
        print("⚠️  部分功能正常，可以开始使用基础的AI批改功能")
    else:
        print("❌ 系统存在问题，请检查配置")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)