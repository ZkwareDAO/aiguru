import json
import re

from openai import OpenAI
import base64
import requests  

marking_scheme_prompt="""你是一个全科目评分方案生成系统，可以处理包括数学、物理、化学、生物、语文、英语等各个学科的试题。请按以下规则执行：

1. **输入内容**：
   - 用户上传的试题图片

2. **任务要求**：
   A. 通用要求：
      - 识别题目类型和所属学科
      - 分析考察的知识点
      - 设计合理的评分标准
   
   B. 学科特殊要求：
      数学类：
      - 拆解解题步骤和关键点
      - 设置计算过程的得分点
      - 注意推导过程的完整性
      
      物理化学类：
      - 关注实验步骤和数据分析
      - 重视原理解释和公式应用
      - 考虑单位换算的准确性
      
      语言类（中英文）：
      - 评估语言表达的准确性
      - 关注文章结构和逻辑性
      - 考虑创新性和思维深度
      
      生物类：
      - 重视概念理解和应用
      - 关注实验设计和分析
      - 评估推理能力

3. **输出格式**：
   {
     "科目类型": "具体学科",
     "题目类型": "题目形式",
     "总分值": "N分",
     "评分方案": [
       {
         "步骤序号": 1,
         "步骤描述": "具体要求",
         "分值": "X分",
         "得分点": ["具体得分标准"],
         "扣分点": ["具体扣分情况"]
       }
     ],
     "知识点": ["涉及的主要知识点"],
     "备注": "特殊说明"
   }

4. **注意事项**：
   - 评分标准要客观合理
   - 考虑多种可能的答题思路
   - 预设常见错误和对应扣分
   - 适当兼顾创新思维的评估"""
correction_prompt="""你是一个全科目自动批改系统，可以处理包括数学、物理、化学、生物、语文、英语等各个学科的试题。请按以下规则执行：

1. **输入内容**：
   - 图片中的学生作答
   - 参考的评分方案（JSON格式）

2. **批改规则**：
   A. 通用规则：
      - 根据评分方案逐项检查答案
      - 计算总分并给出详细反馈
      
   B. 学科特殊规则：
      数学类：
      - 关注计算过程和推导步骤
      - 检查公式使用的正确性
      - 注意单位换算和数值精度
      
      物理化学类：
      - 验证定律定理的应用
      - 检查实验步骤和数据处理
      - 注意单位一致性
      
      语言类（中英文）：
      - 评估语法和句式结构
      - 检查词汇使用和表达准确性
      - 考虑上下文连贯性
      
      生物类：
      - 关注概念准确性
      - 检查实验过程描述
      - 评估分析推理能力

3. **输出格式**：
   {
     "科目类型": "识别的具体科目",
     "总分": "得分/总分",
     "分项批改": [
       {
         "步骤序号": 1,
         "得分": "X分",
         "正确点": ["具体正确之处"],
         "错误点": ["具体错误之处"],
         "建议": "改进建议"
       }
     ],
     "总评": "整体评价，包括优点和需改进之处",
     "知识点": ["涉及的主要知识点"],
     "学习建议": "针对性的学习建议"
   }

4. **注意事项**：
   - 给出具体的改进建议和学习方向
   - 指出答案中的创新思维或独特见解
   - 对模糊内容标注"无法识别"，不随意推测
   - 保持评分标准的一致性和客观性"""

#用图片批改的提示词
correction_with_images_prompt='''你是一个全科目自动批改系统，可以处理包括数学、物理、化学、生物、语文、英语等各个学科的试题。请按以下规则执行：

1. **输入内容**：
   - 图片中的学生作答
   - 图片中的评分方案

2. **批改规则**：
   A. 通用规则：
      - 根据评分方案逐项检查答案
      - 计算总分并给出详细反馈
      
   B. 学科特殊规则：
      数学类：
      - 关注计算过程和推导步骤
      - 检查公式使用的正确性
      - 注意单位换算和数值精度
      
      物理化学类：
      - 验证定律定理的应用
      - 检查实验步骤和数据处理
      - 注意单位一致性
      
      语言类（中英文）：
      - 评估语法和句式结构
      - 检查词汇使用和表达准确性
      - 考虑上下文连贯性
      
      生物类：
      - 关注概念准确性
      - 检查实验过程描述
      - 评估分析推理能力

3. **输出格式**：
   {
     "科目类型": "识别的具体科目",
     "总分": "得分/总分",
     "分项批改": [
       {
         "步骤序号": 1,
         "得分": "X分",
         "正确点": ["具体正确之处"],
         "错误点": ["具体错误之处"],
         "建议": "改进建议"
       }
     ],
     "总评": "整体评价，包括优点和需改进之处",
     "知识点": ["涉及的主要知识点"],
     "学习建议": "针对性的学习建议"
   }

4. **注意事项**：
   - 给出具体的改进建议和学习方向
   - 指出答案中的创新思维或独特见解
   - 对模糊内容标注"无法识别"，不随意推测
   - 保持评分标准的一致性和客观性'''


def img_to_base64(image_path):
    # 判断是否是网络路径
    if image_path.startswith(('http://', 'https://')):
        response = requests.get(image_path)
        response.raise_for_status()  
        image_data = response.content
    else:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
    return base64.b64encode(image_data).decode('utf-8')


def call_api(input_text, *input_images):
    # 完全删除数学格式提示词部分
    client = OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
    )
    
    # 直接使用原始输入文本，不添加任何格式化提示
    content = [{"type": "text", "text": input_text}]
    
    # 处理图片文件路径
    for image_path in input_images:
        try:
            base_64_image = img_to_base64(image_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base_64_image}"
                }
            })
        except Exception as e:
            raise Exception(f"Failed to process image at {image_path}: {str(e)}")

    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-VL-72B-Instruct",
        messages=[
            {  
                "role": "user",
                "content": content
            }
        ],
        max_tokens=2048,
        temperature=0.7
    )

    return response.choices[0].message.content

# 使用缓存装饰器来存储API调用结果
from functools import lru_cache

#调用的API,接收一个str和文件paths，返回一个字符串
default_api=call_api

def extract_json_from_str(string):
    json_match = re.search(r'\{.*\}', string, re.DOTALL)
    if not json_match:
        raise ValueError("返回字符串中未找到有效JSON")
    
    try:
        json_str = json_match.group(0)
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"返回内容不是有效JSON: {str(e)}") from e

def generate_marking_scheme(*image_file, api=default_api):
    try:
        # 执行AI函数调用
        response_str = api(marking_scheme_prompt, *image_file)
        
        # 解析返回结果
        return extract_json_from_str(response_str)
    except Exception as e:
        # 捕获所有API函数可能抛出的异常
        raise RuntimeError(f"API函数调用失败: {str(e)}") from e

#批改
def correction_with_json_marking_scheme(json_marking_scheme, *image_files, api=default_api):
    """
    调用API函数，发送JSON数据和图片文件，并解析返回的JSON数据

    参数：
    image_file (file对象): 以二进制模式打开的图片文件对象
    api (callable): 接收(string, file)并返回string的AI函数

    返回：
    dict: 解析后的JSON数据

    异常：
    RuntimeError: API函数调用失败时抛出
    ValueError: 未找到有效JSON或解析失败时抛出
    """
    try: 
        # 执行API函数调用
        response_str = api(correction_prompt+"\n5.一下是评分标准:\n"+str(json_marking_scheme), *image_files)
        
        return extract_json_from_str(response_str)
            
    except Exception as e:
        # 捕获所有AI函数可能抛出的异常
        raise RuntimeError(f"API函数调用失败: {str(e)}") from e

def correction_with_image_marking_scheme(*image_files_and_marking_scheme, api=default_api):
    try:    
        # 执行AI函数调用
        response_str = api(correction_with_images_prompt,*image_files_and_marking_scheme)

        return extract_json_from_str(response_str)
            
    except Exception as e:
        # 捕获所有AI函数可能抛出的异常
        raise RuntimeError(f"API函数调用失败: {str(e)}") from e

def correction_without_marking_scheme(*images,api=default_api):
    marking_scheme=generate_marking_scheme(*images)
    return correction_with_json_marking_scheme(marking_scheme,*images,api=api)

if __name__=="__main__":
    pass