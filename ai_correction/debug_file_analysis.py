#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试文件分析功能
"""

import os
import sys
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append('functions/api_correcting')

from functions.api_correcting.calling_api import process_file_content, api_config, call_tongyiqianwen_api

def analyze_questions_debug(content_list):
    """调试版本的题目分析函数"""
    try:
        # 直接使用题目分析提示词
        analysis_prompt = """📊 题目分析任务

请分析提供的文件，识别：
1. 总共有多少道题目
2. 每道题的分值
3. 总分是多少

【输出格式】
题目总数：[X]题
题目列表：
- 题目1：[Y]分
- 题目2：[Z]分
...
总分：[总分]分

只输出上述信息，不要进行批改。"""
        
        # 读取所有文件内容
        all_contents = []
        file_paths = []
        for file_path in content_list:
            try:
                content_type, content = process_file_content(file_path)
                if content:
                    if content_type == 'text':
                        all_contents.append(content)
                        file_paths.append(None)
                    else:
                        all_contents.append(f"[文件: {os.path.basename(file_path)}]")
                        file_paths.append(file_path)
            except Exception as e:
                print(f"⚠️ 读取文件出错 {file_path}: {e}")
        
        if not all_contents:
            return None
        
        # 调用API分析题目
        print("正在调用API分析题目...")
        api_args = [analysis_prompt]
        for i, file_path in enumerate(content_list):
            if file_paths[i]:  # 如果是图片或PDF文件
                api_args.append(file_paths[i])
            else:  # 如果是文本内容
                api_args.append(all_contents[i])
        
        result = call_tongyiqianwen_api(*api_args)
        
        if result:
            print(f"API返回结果: {result}")
            
            # 解析结果
            # 提取题目总数
            total_match = re.search(r'题目总数[：:]\s*(\d+)', result)
            total_questions = int(total_match.group(1)) if total_match else 0
            
            # 提取总分
            score_match = re.search(r'总分[：:]\s*(\d+)', result)
            total_score = int(score_match.group(1)) if score_match else 0
            
            print(f"📊 解析结果：共{total_questions}题，总分{total_score}分")
            return {
                'total_questions': total_questions,
                'total_score': total_score,
                'analysis': result
            }
        
        return None
        
    except Exception as e:
        print(f"题目分析出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_file_analysis():
    """测试文件分析功能"""
    print("=== 文件分析调试 ===")
    
    # 检查API配置
    print(f"API配置状态: {api_config.get_status()}")
    print(f"API有效性: {api_config.is_valid()}")
    
    # 检查test_files目录中的文件（用于测试）
    test_dir = "test_files"
    if os.path.exists(test_dir):
        print(f"\n=== {test_dir} 目录中的文件 ===")
        test_files = []
        for file in os.listdir(test_dir):
            file_path = os.path.join(test_dir, file)
            if os.path.isfile(file_path) and file.endswith('.txt'):
                test_files.append(file_path)
                print(f"文件: {file}")
                
                # 测试文件内容读取
                try:
                    content_type, content = process_file_content(file_path)
                    print(f"  类型: {content_type}")
                    if content_type == 'text' and content:
                        preview = content[:200] + "..." if len(content) > 200 else content
                        print(f"  内容预览: {preview}")
                    else:
                        print(f"  内容: 无法读取")
                except Exception as e:
                    print(f"  错误: {e}")
                print()
        
        if test_files:
            print(f"\n=== 测试分析功能 ===")
            # 测试analyze_questions函数
            try:
                print("正在调用analyze_questions函数...")
                result = analyze_questions_debug(test_files)  # 使用调试版本
                print(f"最终分析结果: {result}")
                
                if result:
                    print(f"题目总数: {result.get('total_questions', 0)}")
                    print(f"总分: {result.get('total_score', 0)}")
                else:
                    print("分析结果为None - 可能API调用失败")
                    
            except Exception as e:
                print(f"分析出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("没有txt文件可供测试")
    else:
        print(f"{test_dir} 目录不存在")

if __name__ == "__main__":
    test_file_analysis() 