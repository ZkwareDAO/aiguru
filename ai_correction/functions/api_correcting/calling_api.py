import base64
import requests  
from openai import OpenAI
import re

# 中文版评分标准提示词
marking_scheme_prompt_zh = """作为一位专业教师，请为上传的题目创建一份详细的评分标准。使用清晰的自然语言描述，确保所有数学符号使用标准Unicode字符（如 × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ），严禁使用LaTeX格式如\\sin或\\frac{}{}。

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

# English version of marking scheme prompt
marking_scheme_prompt_en = """As a professional teacher, please create a detailed marking scheme for the uploaded problem. Use clear natural language descriptions, ensuring all mathematical symbols use standard Unicode characters (such as × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ), strictly prohibiting LaTeX formats like \\sin or \\frac{}{}.

Your marking scheme should include:
1. Subject and type of the problem
2. Total score and detailed breakdown of points for each step
3. Key scoring points for each step
4. Common errors and corresponding point deductions
5. Analysis of core knowledge points

For mathematics problems, ensure:
- Fractions are presented as "a/b" rather than using fraction notation
- Exponents are written as "a^b" or using superscript forms like "a²"
- Equations use standard symbols, such as "2x² + 3x = 5"
- Trigonometric functions are written as "sin x", "cos θ", etc., without using LaTeX

For essays/discussion questions, please detail:
- Content points and corresponding scores
- Structural organization scoring criteria
- Language expression scoring points
- Creative thinking scoring points

Please organize the content using headings and numbering, and output in natural language format!"""

# 中文版批改提示词
correction_prompt_zh = """作为一位专业批改教师，请批改学生的答案。使用标准Unicode数学符号（如 × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ），不使用LaTeX格式。

# 基本信息
- 科目：[填写科目]
- 题目类型：[填写类型]

# 学生答案批改如下:

1. 第1步：[步骤描述] - [该步得分]/[该步满分]
- ✓ 正确点：[列出正确之处]
- ✗ 错误点：[列出错误之处]
- 扣分原因：[详细解释]

2. 第2步：[步骤描述] - [该步得分]/[该步满分]
- ✓ 正确点：[列出正确之处]
- ✗ 错误点：[列出错误之处]
- 扣分原因：[详细解释]

[继续列出所有步骤...]

总分：[得分]/[满分]

注意：
- 分数表示为"a/b"，如"1/2"
- 根号表示为"√a"，如"√2"
- 三角函数表示为"sin x"等
- 指数表示为"x²"或"e^x"
- 积分表示为"∫f(x)dx"
- 极限表示为"lim x→∞"

请严格按照评分标准执行批改！"""

# English version of correction prompt
correction_prompt_en = """As a professional teacher grading student answers, please evaluate the student's response. In your answer, you must use standard Unicode mathematical symbols (such as × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ), strictly prohibiting LaTeX formats (like \\sin or \\frac{}{}), even if the student used non-standard notation.

Strictly organize your grading according to the following structure:

# Grading Result

## Problem Information and Total Score
- Subject: [Fill in subject]
- Problem type: [Fill in type]
- Total score: [Score]/[Full marks]

## Step-by-Step Scoring
(This section must show the student's full solution process with scoring for each step)

1. Step 1: [Step description] - [Step score]/[Step full marks]
   (Record the student's complete answer process here, ensure you show the original solution in full)
   - ✓ Correct points: [List correct aspects, including formulas, calculations, etc.]
   - ✗ Error points: [List errors]
   - Reason for deduction: [Detailed explanation of why points were deducted]

2. Step 2: [Step description] - [Step score]/[Step full marks]
   (Record the student's complete answer process here, ensure you show the original solution in full)
   - ✓ Correct points: [List correct aspects]
   - ✗ Error points: [List errors]
   - Reason for deduction: [Detailed explanation of why points were deducted]

[Continue listing all steps...]

## Detailed Analysis
[In this section, provide complete problem-solving ideas and analysis, including the correct approach for each step]
[Include a comparison between the standard answer and the student's answer]

Grading strictness: 【STRICTNESS_LEVEL】

Note: In your grading response, all mathematical expressions must use standard Unicode symbols, for example:
- Fractions: must be written as "a/b", such as "1/2"
- Square roots: must be written as "√a", such as "√2"
- Trigonometric functions: must be written as "sin x", "cos θ", etc.
- Exponents: must be written as "x²", "e^x", etc.
- Integrals: must be written as "∫f(x)dx"
- Limits: must be written as "lim x→∞"

If the user has provided a marking scheme, please strictly follow that standard for grading, and ensure compliance with all requirements in the standard!

Please output the result in natural language format, ensuring all mathematical expressions are clear and readable!"""

# 中文版带图片的批改提示词
correction_with_images_prompt_zh = correction_prompt_zh + """

看到上传的图片后，请仔细分析所有内容，包括：
- 题目要求和条件
- 学生解答步骤
- 评分标准要求（如有）

尤其要注意学生解答中的数学符号、计算过程和最终结果，确保您的批改准确无误。"""

# English version of correction with images prompt
correction_with_images_prompt_en = correction_prompt_en + """

After seeing the uploaded images, please carefully analyze all content, including:
- Problem requirements and conditions
- Student answer steps
- Marking scheme requirements (if any)

Pay special attention to mathematical symbols, calculation processes, and final results in the student's answer to ensure your grading is accurate."""

# Mapping for language selection
marking_scheme_prompts = {
    "zh": marking_scheme_prompt_zh,
    "en": marking_scheme_prompt_en
}

correction_prompts = {
    "zh": correction_prompt_zh,
    "en": correction_prompt_en
}

correction_with_images_prompts = {
    "zh": correction_with_images_prompt_zh,
    "en": correction_with_images_prompt_en
}

# Set default prompts
marking_scheme_prompt = marking_scheme_prompt_zh
correction_prompt = correction_prompt_zh
correction_with_images_prompt = correction_with_images_prompt_zh

def img_to_base64(image_path):
    """
    将图片文件转换为base64编码
    支持本地文件路径、URL和Streamlit上传的文件对象
    """
    import io
    
    # 处理URL
    if isinstance(image_path, str) and image_path.startswith(('http://', 'https://')):
        response = requests.get(image_path)
        response.raise_for_status()  
        image_data = response.content
    # 处理Streamlit上传的文件对象
    elif hasattr(image_path, 'read') and callable(image_path.read):
        try:
            # 保存当前文件位置
            if hasattr(image_path, 'tell') and callable(image_path.tell):
                current_position = image_path.tell()
            else:
                current_position = 0
                
            # 读取文件数据
            image_data = image_path.read()
            
            # 恢复文件位置
            if hasattr(image_path, 'seek') and callable(image_path.seek):
                image_path.seek(current_position)
        except Exception as e:
            raise Exception(f"Failed to read uploaded file: {str(e)}")
    # 处理本地文件路径
    elif isinstance(image_path, str):
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
    else:
        raise Exception(f"Unsupported image source type: {type(image_path)}")
        
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

def call_api(input_text, *input_images, strictness_level="中等", language="zh"):
    """
    调用API进行图像识别和处理，支持批改严格程度和语言设置
    
    参数:
    input_text: 字符串，提示文本
    input_images: 一系列图片文件路径
    strictness_level: 批改严格程度，可选值："宽松"、"中等"、"严格"
    language: 输出语言，可选值："zh"(中文)、"en"(英文)
    
    返回:
    字符串，API响应内容
    """
    client = OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
    )
    
    # 根据严格程度调整提示词
    strictness_descriptions = {
        "zh": {
            "宽松": "请温和地批改，对小错误给予适当宽容，主要关注学生的理解程度。评分应相对宽松，着重肯定学生的正确点，提供积极鼓励。",
            "中等": "请公正地批改，关注主要概念和步骤，对关键错误扣分，但对小瑕疵给予一定宽容。保持客观评价态度，既指出问题也肯定优点。",
            "严格": "请严格批改，严格按照标准评分，对任何错误都要指出并合理扣分。评分标准高，要求精确的解题过程和结果，详细分析每个错误。"
        },
        "en": {
            "宽松": "Please grade gently, showing appropriate tolerance for minor errors, focusing mainly on the student's level of understanding. Scoring should be relatively lenient, emphasizing the student's correct points and providing positive encouragement.",
            "中等": "Please grade fairly, focusing on main concepts and steps, deducting points for key errors but showing some tolerance for minor flaws. Maintain an objective evaluation attitude, both pointing out problems and affirming strengths.",
            "严格": "Please grade strictly, strictly following the standard scoring, pointing out and reasonably deducting points for any errors. The scoring standard is high, requiring precise solution processes and results, with detailed analysis of each error."
        }
    }
    
    # Get the appropriate strictness description based on language
    strictness_desc = strictness_descriptions.get(language, strictness_descriptions["zh"])
    strictness_text = strictness_desc.get(strictness_level, strictness_desc["中等"])
    
    # 替换提示词中的严格程度标记
    enhanced_prompt = input_text.replace("【STRICTNESS_LEVEL】", strictness_text)
    
    # 修改数学符号使用强调部分 - 根据语言选择
    math_notation_emphasis = {
        "zh": """
【极其重要】你必须严格遵守以下要求：
1. 绝对禁止输出任何 LaTeX 语法（如 \\sqrt、\\frac、\\sum、$...$、\\( ... \\) 等），即使学生答案中有这些内容，也不能原样输出。
2. 所有数学表达式必须直接用标准 Unicode 数学符号。例如：
   - 根号：√2，不要写成 \\sqrt{2} 或 $\\sqrt{2}$
   - 分数：1/2，不要写成 \\frac{1}{2}
   - 上标：x²，不要写成 x^2 或 x^{2}
   - 三角函数：sin x，不要写成 \\sin x
   - 积分：∫f(x)dx，不要写成 \\int f(x)dx
   - 求和：Σx_i，不要写成 \\sum x_i
   - 希腊字母：π、θ，不要写成 \\pi、\\theta
3. 如果你输出了任何 LaTeX 语法，将被判为错误输出。
4. 只允许输出标准 Unicode 数学符号和自然语言，不能有任何 LaTeX 代码或美元符号包裹的公式。

请严格按照上述要求输出，否则视为不合格！
""",
        "en": """
[CRITICALLY IMPORTANT] You must strictly follow these rules:
1. Absolutely DO NOT output any LaTeX syntax (such as \\sqrt, \\frac, \\sum, $...$, \\( ... \\), etc.), even if the student's answer contains them. Do NOT output them as-is.
2. All mathematical expressions MUST use standard Unicode math symbols directly. For example:
   - Square root: √2, NOT \\sqrt{2} or $\\sqrt{2}$
   - Fraction: 1/2, NOT \\frac{1}{2}
   - Superscript: x², NOT x^2 or x^{2}
   - Trigonometric: sin x, NOT \\sin x
   - Integral: ∫f(x)dx, NOT \\int f(x)dx
   - Summation: Σx_i, NOT \\sum x_i
   - Greek letters: π, θ, NOT \\pi, \\theta
3. If you output any LaTeX syntax, it will be considered an incorrect output.
4. Only standard Unicode math symbols and natural language are allowed. No LaTeX code or formulas wrapped in dollar signs.

STRICTLY follow these requirements, or your output will be considered invalid!
"""
    }
    
    # 系统消息 - 根据语言选择
    system_messages = {
        "zh": """你是一位资深教育专家，擅长批改学生答案。
在回复中，你必须使用标准Unicode数学符号，而非LaTeX格式。
即使学生在答案中使用了不标准的表示法，你在批改中也必须使用标准Unicode符号。
例如：使用 "√2/2" 而非 "\\sqrt{2}/2"，使用 "sin θ" 而非 "\\sin\\theta"。
所有数学符号必须使用Unicode标准字符，包括×, ÷, ±, √, π, ∑, ∫, ≤, ≥, ≠, ∞, ∈, ∉, ∩, ∪等。
请严格按照用户提供的结构组织你的批改。
你的输出语言必须是中文。""",
        "en": """You are an experienced education expert, skilled in grading student answers.
In your responses, you must use standard Unicode mathematical symbols, not LaTeX format.
Even if students use non-standard notation in their answers, you must use standard Unicode symbols in your grading.
For example: use "√2/2" rather than "\\sqrt{2}/2", use "sin θ" rather than "\\sin\\theta".
All mathematical symbols must use Unicode standard characters, including ×, ÷, ±, √, π, ∑, ∫, ≤, ≥, ≠, ∞, ∈, ∉, ∩, ∪, etc.
Please strictly follow the structure provided by the user in organizing your grading.
Your output language must be English."""
    }
    
    # 组合最终提示
    final_prompt = enhanced_prompt + math_notation_emphasis[language]
    
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
            {"role": "system", "content": system_messages[language]},
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

def generate_marking_scheme(*image_file, api=default_api, language="zh"):
    """生成评分方案，返回纯文本形式"""
    try:
        prompt = marking_scheme_prompts[language]
        return api(prompt, *image_file, language=language)
    except Exception as e:
        error_msg = "生成评分方案失败" if language == "zh" else "Failed to generate marking scheme"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_marking_scheme(marking_scheme, *image_files, strictness_level="中等", api=default_api, language="zh"):
    """使用提供的评分方案进行批改，返回纯文本形式"""
    try:
        # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = correction_prompts[language] + "\n\n"
        
        # Add appropriate language text for marking scheme reference
        if language == "zh":
            prompt += "参考的评分标准如下（必须严格遵守）：\n\n"
        else:
            prompt += "Reference marking scheme below (must be strictly followed):\n\n"
            
        prompt += str(marking_scheme)
        
        return api(prompt, *image_files, strictness_level=strictness_level, language=language)
    except Exception as e:
        error_msg = "批改失败" if language == "zh" else "Correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_image_marking_scheme(*image_files_and_marking_scheme, strictness_level="中等", api=default_api, language="zh"):
    """使用图像中的评分方案进行批改，返回纯文本形式"""
    try:
        return api(correction_with_images_prompts[language], *image_files_and_marking_scheme, strictness_level=strictness_level, language=language)
    except Exception as e:
        error_msg = "批改失败" if language == "zh" else "Correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_without_marking_scheme(*images, strictness_level="中等", api=default_api, language="zh"):
    """自动生成评分方案并批改，返回纯文本形式"""
    marking_scheme = generate_marking_scheme(*images, language=language)
    return correction_with_marking_scheme(marking_scheme, *images, strictness_level=strictness_level, api=api, language=language)

# 保留原函数名以保持兼容性
correction_with_json_marking_scheme = correction_with_marking_scheme

if __name__ == "__main__":
    pass