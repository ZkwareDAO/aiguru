import json
import re

from openai import OpenAI
import base64
import requests  

marking_scheme_prompt="""你是一个专业数学教师，需要根据用户提供的题目生成详细的评分方案。请严格按以下规则执行：

1. **输入内容**：用户上传的圖片中的原題（無需參考學生作答部分）。
2. **任务要求**：
   - 分析题目类型（代数、几何、微积分等）和知识点。
   - 網上搜索類似題目的評分方案。
   - 根據網上類似題目的評分方案，拆解解题的**关键步骤**，并为每个步骤分配分值（总分不超过题目标注分值）。
   - 列出每个步骤的**得分点**（如公式正确、计算无误）和**扣分点**（如符号错误、单位缺失）。
   - 标注常见错误及对应的扣分比例（如计算错误扣1分，缺少关键步骤扣2分）。
   - 若题目有多个解法，需为每种解法单独生成评分方案。
3. **输出格式**：
   - 使用JSON格式，包含以下字段：
     ```json
     {
       "题目类型": "分类（如代数方程）",
       "总分值": "N分",
       "评分方案": [
         {
           "步骤序号": 1,
           "步骤描述": "解方程的第一步变形",
           "分值": "X分",
           "得分点": ["变形正确", "符号规范"],
           "扣分点": ["符号错误（扣1分）", "未写出变形依据（扣0.5分）"]
         },
         // ...其他步骤
       ],
       "备注": "特殊说明（如允许误差范围、多解法标识）"
     }
     ```
4. **注意事项**：
   - 若题目信息不完整（如图片模糊），直接返回错误类型和所需补充信息。
   - 避免主观判断，仅基于数学规则和题目要求生成方案。"""
correction_prompt="""你是一个数学题自动批改系统，需根据提供的评分方案严格评估学生答案。请按以下规则执行：

1. **输入内容**：
   - 圖片中的學生作答。
   - 參考知識庫裏的Marking Scheme（JSON格式）。
2. **任务要求**：
   - 逐项对比学生答案与评分方案的每个步骤：
     - 确认是否完成该步骤。
     - 检查得分点和扣分点，记录具体错误。
   - 计算总分并生成反馈：
     - 若某步骤部分正确，按比例给分（如公式正确但计算错误，得该步骤50%分值）。
     - 若发现评分方案未覆盖的新错误，暂标记为“待人工复核”。
3. **输出格式**：
   - 使用JSON格式，包含以下字段：
     ```json
     {
       "总分": "M分（基于评分方案计算）",
       "分项批改": [
         {
           "步骤序号": 1,
           "得分": "X分",
           "正确点": ["变形正确"],
           "错误点": ["符号错误（扣1分）"],
           "建议": "注意符号规范，建议复习等式性质"
         },
         // ...其他步骤
       ],
       "总评": "整体反馈（如‘计算能力优秀，但需注意单位转换’）",
       "异常标记": ["待人工复核项（如有）"]
     }
     ```
4. **注意事项**：
   - 优先匹配步骤逻辑而非文字顺序（如学生调换步骤顺序但逻辑正确，仍给分）。
   - 对模糊内容（如无法识别的符号）标注“OCR识别失败”，不猜测扣分。
   - 禁止修改原始评分方案，仅基于其执行批改。"""

#用图片批改的提示词
correction_with_images_prompt='''你是一个数学题自动批改系统，需根据提供的评分方案严格评估学生答案。请按以下规则执行：

1. **输入内容**：
   - 图片中的學生作答。
   - 图片中的批改方案。
2. **任务要求**：
   - 逐项对比学生答案与评分方案的每个步骤：
     - 确认是否完成该步骤。
     - 检查得分点和扣分点，记录具体错误。
   - 计算总分并生成反馈：
     - 若某步骤部分正确，按比例给分（如公式正确但计算错误，得该步骤50%分值）。
     - 若发现评分方案未覆盖的新错误，暂标记为“待人工复核”。
   - 评价学生作答并总结要点
3. **输出格式**：
   - 使用JSON格式,按照以下格式：
     {
       "总分": "M分（基于评分方案计算）",
       "分项批改": [
         {
           "步骤序号": 1,
           "得分": "X分",
           "正确点": ["变形正确"],
           "错误点": ["符号错误（扣1分）"],
           "建议": "注意符号规范，建议复习等式性质"
         },
         // ...其他步骤
       ],
       "总评": "整体反馈（如‘计算能力优秀，但需注意单位转换’）",
       "异常标记": ["待人工复核项（如有）"]
     }
     ```
4. **注意事项**：
   - 优先匹配步骤逻辑而非文字顺序（如学生调换步骤顺序但逻辑正确，仍给分）。
   - 对模糊内容（如无法识别的符号）标注“OCR识别失败”，不猜测扣分。
   - 禁止修改原始评分方案，仅基于其执行批改。'''


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

def call_tongyi_api(input_text,*input_images):
    client = OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
    )
    content=[{"type": "text", "text": input_text}]
    for images in input_images:
        try:
            base_64_image = img_to_base64(images)
            content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base_64_image}"
                        }
                 })
        except:
            raise Exception("Failed to convert imege path.")

    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-VL-72B-Instruct",
        messages=[
            {  
                "role": "user",
                "content":content
            }
        ],
        max_tokens=2048,
        temperature=0.7
    )

    #可以在此处理调用结果

    return response.choices[0].message.content

# 使用缓存装饰器来存储API调用结果
from functools import lru_cache

#调用的API,接收一个str和文件paths，返回一个字符串
default_api=call_tongyi_api

def extract_json_from_str(string):
    
        json_match = re.search(r'\{.*\}', string, re.DOTALL)
        if not json_match:
            raise ValueError("返回字符串中未找到有效JSON")
        
        # 解析返回结果
        try:
            return json.loads(json_match.group(0))
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