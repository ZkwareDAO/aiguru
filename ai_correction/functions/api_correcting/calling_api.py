import base64
import requests  
from openai import OpenAI
import re

# 修改后的评分标准提示词，确保标准数学符号输出
marking_scheme_prompt = """作为一位专业教师，请为上传的题目创建一份详细的评分标准。使用清晰的自然语言描述，确保所有数学符号使用标准Unicode字符（如 × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ），严禁使用LaTeX格式如\\sin或\\frac{}{}。

您的评分标准应包含：
1. 题目科目和类型
2. 总分值及各步骤分值明细
3. 每个步骤的关键评分点
4. 常见错误及对应扣分点
5. 核心知识点分析

对于数学题目，请确保：
- 分数表示为"a/b"而非分式
- 指数表示为"a^b"或使用如"a²"的上标形式
- 方程式使用标准符号表示，如"2x² + 3x = 5"
- 三角函数表示为"sin x"、"cos θ"等，不使用LaTeX

对于作文/论述题，请详细说明：
- 内容要点及对应分值
- 结构组织评分标准
- 语言表达评分要点
- 创新思维评分要点

请使用标题和编号组织内容，以自然语言格式输出！"""

# 修改后的批改提示词，确保标准数学符号输出和分步评分
correction_prompt = """作为一位专业批改教师，请批改学生的答案。在你的回答中，你必须使用标准Unicode数学符号（如 × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ），严禁使用LaTeX格式（如\\sin或\\frac{}{}），即使学生在答案中使用了不规范的表示法。

严格按照以下结构组织批改：

# 批改结果

## 题目信息与总分
- 科目：[填写科目]
- 题目类型：[填写类型]
- 总分：[得分]/[满分]

## 逐步评分
1. 第1步：[步骤描述] - [该步得分]/[该步满分]
   - ✓ 正确点：[列出正确之处，包括公式、计算等]
   - ✗ 错误点：[列出错误之处]
   - 扣分原因：[详细解释为何扣分]

2. 第2步：[步骤描述] - [该步得分]/[该步满分]
   - ✓ 正确点：[列出正确之处]
   - ✗ 错误点：[列出错误之处]
   - 扣分原因：[详细解释为何扣分]

[继续列出所有步骤...]

## 总体评价
[总体评价内容，对答题质量的综合评估]

## 详细解析
[在这部分提供完整的解题思路和分析，包括每一步的正确做法]

## 学习建议
[针对性学习建议，重点指出需要加强的知识点]

批改严格程度：【STRICTNESS_LEVEL】

注意：在你的批改回复中，所有数学表达式必须使用标准Unicode符号，例如：
- 分数：必须写成 "a/b"，如 "1/2"
- 根号：必须写成 "√a"，如 "√2" 
- 三角函数：必须写成 "sin x", "cos θ" 等
- 指数：必须写成 "x²", "e^x" 等
- 积分：必须写成 "∫f(x)dx"
- 极限：必须写成 "lim x→∞"

如果用户提供了评分标准，请严格按照该标准执行批改，并确保符合标准中的所有要求！

请用自然语言格式输出结果，确保所有数学表达式清晰可读！"""

# 带图片的批改提示词
correction_with_images_prompt = correction_prompt + """

看到上传的图片后，请仔细分析所有内容，包括：
- 题目要求和条件
- 学生解答步骤
- 评分标准要求（如有）

尤其要注意学生解答中的数学符号、计算过程和最终结果，确保您的批改准确无误。"""

def img_to_base64(image_path):
    """将图片文件转换为base64编码"""
    if image_path.startswith(('http://', 'https://')):
        response = requests.get(image_path)
        response.raise_for_status()  
        image_data = response.content
    else:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
    return base64.b64encode(image_data).decode('utf-8')

def force_natural_language(text):
    """强制将可能的JSON格式转换为自然语言"""
    # 如果文本包含大量的JSON特征，进行处理
    if (text.count('{') > 2 and text.count('}') > 2) or ('"' in text and ':' in text and ',' in text):
        # 尝试去除格式符号
        text = re.sub(r'[{}\[\]"]', '', text)
        text = re.sub(r':\s*', ': ', text)
        text = re.sub(r',\s*', '\n', text)
        
        # 添加警告消息
        text = "【注意：以下内容已从结构化格式转换为纯文本】\n\n" + text
    
    return text

def call_api(input_text, *input_images, strictness_level="中等"):
    """
    调用API进行图像识别和处理，支持批改严格程度设置
    
    参数:
    input_text: 字符串，提示文本
    input_images: 一系列图片文件路径
    strictness_level: 批改严格程度，可选值："宽松"、"中等"、"严格"
    
    返回:
    字符串，API响应内容
    """
    client = OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
    )
    
    # 根据严格程度调整提示词
    strictness_descriptions = {
        "宽松": "请温和地批改，对小错误给予适当宽容，主要关注学生的理解程度。评分应相对宽松，着重肯定学生的正确点，提供积极鼓励。",
        "中等": "请公正地批改，关注主要概念和步骤，对关键错误扣分，但对小瑕疵给予一定宽容。保持客观评价态度，既指出问题也肯定优点。",
        "严格": "请严格批改，严格按照标准评分，对任何错误都要指出并合理扣分。评分标准高，要求精确的解题过程和结果，详细分析每个错误。"
    }
    
    # 替换提示词中的严格程度标记
    enhanced_prompt = input_text.replace("【STRICTNESS_LEVEL】", strictness_descriptions.get(strictness_level, strictness_descriptions["中等"]))
    
    # 修改数学符号使用强调部分
    math_notation_emphasis = """
重要说明：在你的回答中，无论学生使用何种表示法，你都必须使用标准Unicode数学符号，而非LaTeX格式。

具体要求：
1. 分数表示：使用 "a/b" 格式，如 "1/2"，不要使用 "\\frac{a}{b}"
2. 根号表示：使用 "√" 符号，如 "√2"，不要使用 "\\sqrt{2}"
3. 三角函数：使用 "sin x", "cos θ", "tan α"，不要使用 "\\sin x", "\\cos \\theta"
4. 指数：使用上标 "x²", "e^x" 或 "x^n"，不要使用 "x^{2}", "e^{x}"
5. 积分：使用 "∫f(x)dx"，不要使用 "\\int f(x)dx"
6. 求和：使用 "Σx_i"，不要使用 "\\sum x_i"
7. 希腊字母：直接使用 "α, β, γ, θ, π" 等，不要使用 "\\alpha, \\beta"

确保所有数学表达式清晰可读，直接使用标准Unicode字符。
"""
    
    # 系统消息
    system_message = """你是一位资深教育专家，擅长批改学生答案。
在回复中，你必须使用标准Unicode数学符号，而非LaTeX格式。
即使学生在答案中使用了不标准的表示法，你在批改中也必须使用标准Unicode符号。
例如：使用 "√2/2" 而非 "\\sqrt{2}/2"，使用 "sin θ" 而非 "\\sin\\theta"。
所有数学符号必须使用Unicode标准字符，包括×, ÷, ±, √, π, ∑, ∫, ≤, ≥, ≠, ∞, ∈, ∉, ∩, ∪等。
请严格按照用户提供的结构组织你的批改。"""
    
    # 组合最终提示
    final_prompt = enhanced_prompt + math_notation_emphasis
    
    content = [{"type": "text", "text": final_prompt}]
    
    # 处理图片
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

    # 调用API
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-VL-72B-Instruct",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": content}
        ],
        max_tokens=4096,
        temperature=0.7
    )

    # 获取结果并处理
    result = response.choices[0].message.content
    
    # 强制处理以确保自然语言
    return force_natural_language(result)

# 标准API调用函数
default_api = call_api

def generate_marking_scheme(*image_file, api=default_api):
    """生成评分方案，返回纯文本形式"""
    try:
        return api(marking_scheme_prompt, *image_file)
    except Exception as e:
        raise RuntimeError(f"生成评分方案失败: {str(e)}") from e

def correction_with_marking_scheme(marking_scheme, *image_files, strictness_level="中等", api=default_api):
    """使用提供的评分方案进行批改，返回纯文本形式"""
    try:
        # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = correction_prompt + "\n\n参考的评分标准如下（必须严格遵守）：\n\n" + str(marking_scheme)
        return api(prompt, *image_files, strictness_level=strictness_level)
    except Exception as e:
        raise RuntimeError(f"批改失败: {str(e)}") from e

def correction_with_image_marking_scheme(*image_files_and_marking_scheme, strictness_level="中等", api=default_api):
    """使用图像中的评分方案进行批改，返回纯文本形式"""
    try:
        return api(correction_with_images_prompt, *image_files_and_marking_scheme, strictness_level=strictness_level)
    except Exception as e:
        raise RuntimeError(f"批改失败: {str(e)}") from e

def correction_without_marking_scheme(*images, strictness_level="中等", api=default_api):
    """自动生成评分方案并批改，返回纯文本形式"""
    marking_scheme = generate_marking_scheme(*images)
    return correction_with_marking_scheme(marking_scheme, *images, strictness_level=strictness_level, api=api)

# 保留原函数名以保持兼容性
correction_with_json_marking_scheme = correction_with_marking_scheme

if __name__ == "__main__":
    pass