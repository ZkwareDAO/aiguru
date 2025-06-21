import base64
import requests  
from openai import OpenAI
import re
from pathlib import Path

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
    现在也支持文本文件的检测和跳过
    """
    import io
    import os
    from pathlib import Path
    
    # 检查文件类型
    if isinstance(image_path, str):
        file_path = Path(image_path)
        if file_path.exists():
            # 检查文件扩展名
            file_ext = file_path.suffix.lower()
            if file_ext in ['.txt', '.md', '.doc', '.docx', '.rtf']:
                # 这是文本文件，不应该作为图像处理
                raise ValueError(f"文件 {image_path} 是文本文件，不能作为图像处理")
    
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

def get_file_type(file_path):
    """
    检测文件类型，返回文件类型分类
    
    返回值:
    - 'image': 图片文件
    - 'pdf': PDF文件
    - 'word': Word文档
    - 'text': 纯文本文件
    - 'unknown': 未知类型
    """
    if isinstance(file_path, str):
        file_ext = Path(file_path).suffix.lower()
        
        # 图片文件
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            return 'image'
        
        # PDF文件
        elif file_ext == '.pdf':
            return 'pdf'
        
        # Word文档
        elif file_ext in ['.doc', '.docx']:
            return 'word'
        
        # 文本文件
        elif file_ext in ['.txt', '.md', '.rtf', '.csv']:
            return 'text'
        
        # 其他可能的文本格式
        elif file_ext in ['.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml']:
            return 'text'
    
    return 'unknown'

def read_pdf_file(file_path):
    """
    读取PDF文件内容
    """
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            return text.strip()
    except ImportError:
        try:
            # 如果PyPDF2不可用，尝试使用pdfplumber
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except ImportError:
            return f"[PDF文件: {Path(file_path).name}] - 需要安装PyPDF2或pdfplumber库来读取PDF内容"
    except Exception as e:
        return f"[PDF文件读取失败: {Path(file_path).name}] - 错误: {str(e)}"

def read_word_file(file_path):
    """
    读取Word文档内容
    """
    try:
        import docx
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except ImportError:
        return f"[Word文档: {Path(file_path).name}] - 需要安装python-docx库来读取Word文档"
    except Exception as e:
        return f"[Word文档读取失败: {Path(file_path).name}] - 错误: {str(e)}"

def process_file_content(file_path):
    """
    根据文件类型处理文件内容
    
    返回:
    - (content_type, content): 内容类型和内容
      - content_type: 'text' 或 'image' 或 'error'
      - content: 文件内容或错误信息
    """
    file_type = get_file_type(file_path)
    file_name = Path(file_path).name
    
    try:
        if file_type == 'image':
            # 图片文件作为base64返回
            return 'image', file_path
        
        elif file_type == 'pdf':
            # PDF文件提取文本
            content = read_pdf_file(file_path)
            return 'text', f"[PDF文档: {file_name}]\n{content}"
        
        elif file_type == 'word':
            # Word文档提取文本
            content = read_word_file(file_path)
            return 'text', f"[Word文档: {file_name}]\n{content}"
        
        elif file_type == 'text':
            # 纯文本文件
            content = read_text_file(file_path)
            return 'text', f"[文本文件: {file_name}]\n{content}"
        
        else:
            # 未知类型，尝试作为文本读取
            try:
                content = read_text_file(file_path)
                return 'text', f"[文件: {file_name}]\n{content}"
            except:
                return 'error', f"[不支持的文件类型: {file_name}] - 无法处理此文件"
    
    except Exception as e:
        return 'error', f"[文件处理错误: {file_name}] - {str(e)}"

def is_image_file(file_path):
    """检查文件是否为图像文件"""
    return get_file_type(file_path) in ['image', 'pdf']  # PDF也可以作为图像处理

def read_text_file(file_path):
    """读取文本文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

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

def call_api(input_text, *input_files, strictness_level="中等", language="zh"):
    """
    调用API进行多类型文件处理，支持批改严格程度和语言设置
    增强版：支持图像、PDF、Word文档、文本文件等多种类型
    
    参数:
    input_text: 字符串，提示文本
    input_files: 一系列文件路径（支持图像、PDF、Word、文本等多种格式）
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
    
    # 处理所有文件
    text_contents = []
    image_files = []
    processing_summary = []
    
    for file_path in input_files:
        content_type, content = process_file_content(file_path)
        file_name = Path(file_path).name
        
        if content_type == 'image':
            image_files.append(file_path)
            processing_summary.append(f"✓ 图像文件: {file_name}")
        elif content_type == 'text':
            text_contents.append(content)
            processing_summary.append(f"✓ 文本内容: {file_name}")
        elif content_type == 'error':
            text_contents.append(content)
            processing_summary.append(f"⚠ 处理失败: {file_name}")
    
    # 添加文件处理摘要到提示中
    if processing_summary:
        summary_text = "文件处理摘要：\n" + "\n".join(processing_summary) + "\n" + "="*50 + "\n"
        final_prompt += "\n\n" + summary_text
    
    # 如果有文本内容，将其添加到提示中
    if text_contents:
        text_separator = "\n" + "="*50 + "\n"
        final_prompt += text_separator + "文件内容：\n\n" + "\n\n".join(text_contents)
    
    content = [{"type": "text", "text": final_prompt}]
    
    # 处理图片文件
    for image_path in image_files:
        try:
            # 检查是否是PDF文件
            if get_file_type(image_path) == 'pdf':
                # PDF文件作为图像处理
                base_64_image = img_to_base64(image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:application/pdf;base64,{base_64_image}"
                    }
                })
            else:
                # 普通图像文件
                base_64_image = img_to_base64(image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base_64_image}"
                    }
                })
        except Exception as e:
            print(f"警告：处理图像文件 {image_path} 失败: {e}")
            # 如果图像处理失败，尝试作为文本处理
            try:
                fallback_type, fallback_content = process_file_content(image_path)
                if fallback_type == 'text':
                    content[0]["text"] += f"\n\n[图像处理失败，改为文本处理]\n{fallback_content}"
            except Exception as e2:
                print(f"错误：无法处理文件 {image_path}: {e2}")
                content[0]["text"] += f"\n\n[文件处理失败: {Path(image_path).name}] - {str(e2)}"

    # 调用API
    try:
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
        
        # 验证结果不为空
        if not result or not result.strip():
            fallback_msg = "API返回了空结果。可能的原因：文件内容无法识别或API服务暂时不可用。" if language == "zh" else "API returned empty result. Possible reasons: file content unrecognizable or API service temporarily unavailable."
            print(f"警告: API返回空结果，使用fallback消息")
            return fallback_msg
        
        # 强制处理以确保自然语言
        processed_result = force_natural_language(result)
        
        # 再次验证处理后的结果
        if not processed_result or not processed_result.strip():
            fallback_msg = "处理后的结果为空。请检查上传的文件内容是否清晰可读。" if language == "zh" else "Processed result is empty. Please check if the uploaded file content is clear and readable."
            return fallback_msg
            
        return processed_result
        
    except Exception as e:
        error_msg = f"API调用失败: {str(e)}" if language == "zh" else f"API call failed: {str(e)}"
        print(f"API调用错误: {e}")
        return error_msg

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

def correction_single_group(*image_files, strictness_level="中等", api=default_api, language="zh", group_index=1):
    """
    对单个文件组（通常对应一道题）进行批改，返回纯文本形式
    
    参数:
    image_files: 图像文件列表，通常包含题目、学生答案、评分标准
    strictness_level: 批改严格程度
    api: API调用函数
    language: 输出语言
    group_index: 组索引，用于标识是第几道题
    """
    try:
        # 根据语言选择合适的提示词
        if language == "zh":
            prompt = f"""作为一位专业批改教师，请批改这道题的学生答案。使用标准Unicode数学符号（如 × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ），不使用LaTeX格式。

# 第{group_index}题批改结果

## 1. 学生答题过程纯净版
[请完整还原学生的解题过程，使用标准数学符号，不添加任何评价或修正]
步骤1：[学生的原始解题步骤1]
步骤2：[学生的原始解题步骤2]
步骤3：[学生的原始解题步骤3]
...
最终答案：[学生的最终答案]

## 2. 步骤对错分析
### 步骤1分析
- 学生做法：[描述学生在此步骤的具体做法]
- 判断结果：✓正确 / ✗错误 / △部分正确
- 错误原因：[如果有错误，详细说明错误原因]
- 正确做法：[说明正确的解题方法]

### 步骤2分析
- 学生做法：[描述学生在此步骤的具体做法]
- 判断结果：✓正确 / ✗错误 / △部分正确
- 错误原因：[如果有错误，详细说明错误原因]
- 正确做法：[说明正确的解题方法]

[继续分析所有步骤...]

## 3. 得分详情
- 步骤1得分：[得分]/[满分] 分
- 步骤2得分：[得分]/[满分] 分
- 步骤3得分：[得分]/[满分] 分
...
- **总分：[总得分]/[总满分] 分**

## 4. 题目信息
- 科目：[填写科目]
- 题目类型：[填写类型]
- 难度等级：[填写难度]
- 主要考查知识点：[列出主要知识点]

## 5. 改进建议
[针对学生的错误和不足，提供具体的改进建议]

注意事项：
- 分数表示为"a/b"，如"1/2"
- 根号表示为"√a"，如"√2"
- 三角函数表示为"sin x"等
- 指数表示为"x²"或"e^x"
- 积分表示为"∫f(x)dx"
- 极限表示为"lim x→∞"

请仔细分析上传的图片内容，包括：
- 题目要求和条件
- 学生解答步骤
- 评分标准要求（如有）

特别注意学生解答中的数学符号、计算过程和最终结果，确保批改准确无误。"""
        else:
            prompt = f"""As a professional teacher grading student answers, please evaluate this problem's student response. Use standard Unicode mathematical symbols (such as × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ), strictly prohibiting LaTeX formats.

# Problem {group_index} Grading Result

## 1. Student's Solution Process (Clean Version)
[Please completely restore the student's problem-solving process using standard mathematical symbols, without adding any evaluation or correction]
Step 1: [Student's original solution step 1]
Step 2: [Student's original solution step 2]
Step 3: [Student's original solution step 3]
...
Final Answer: [Student's final answer]

## 2. Step-by-Step Analysis
### Step 1 Analysis
- Student's approach: [Describe what the student did in this step]
- Result: ✓Correct / ✗Incorrect / △Partially correct
- Error reason: [If there are errors, explain the error reasons in detail]
- Correct approach: [Explain the correct solution method]

### Step 2 Analysis
- Student's approach: [Describe what the student did in this step]
- Result: ✓Correct / ✗Incorrect / △Partially correct
- Error reason: [If there are errors, explain the error reasons in detail]
- Correct approach: [Explain the correct solution method]

[Continue analyzing all steps...]

## 3. Scoring Details
- Step 1 score: [score]/[full marks] points
- Step 2 score: [score]/[full marks] points
- Step 3 score: [score]/[full marks] points
...
- **Total score: [total score]/[total full marks] points**

## 4. Problem Information
- Subject: [Fill in subject]
- Problem type: [Fill in type]
- Difficulty level: [Fill in difficulty]
- Main knowledge points tested: [List main knowledge points]

## 5. Improvement Suggestions
[Provide specific improvement suggestions based on the student's errors and shortcomings]

Note: All mathematical expressions must use standard Unicode symbols:
- Fractions: "a/b", such as "1/2"
- Square roots: "√a", such as "√2"
- Trigonometric functions: "sin x", "cos θ", etc.
- Exponents: "x²", "e^x", etc.
- Integrals: "∫f(x)dx"
- Limits: "lim x→∞"

Please carefully analyze the uploaded image content, including:
- Problem requirements and conditions
- Student answer steps
- Marking scheme requirements (if any)

Pay special attention to mathematical symbols, calculation processes, and final results in the student's answer to ensure accurate grading."""
        
        return api(prompt, *image_files, strictness_level=strictness_level, language=language)
    except Exception as e:
        error_msg = f"第{group_index}题批改失败" if language == "zh" else f"Problem {group_index} correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def generate_comprehensive_summary(all_results, language="zh", total_groups=1):
    """
    基于所有批改结果生成综合总结
    
    参数:
    all_results: 所有批改结果的列表
    language: 输出语言
    total_groups: 总题目数量
    """
    try:
        # 根据语言选择合适的提示词
        if language == "zh":
            prompt = f"""作为一位专业教师，请基于以下{total_groups}道题的批改结果，生成一份综合总结报告。使用标准Unicode数学符号（如 × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ），不使用LaTeX格式。

# 综合批改总结报告

## 1. 整体表现概览
- 总题数：{total_groups}题
- 总体得分：[计算总得分]/[计算总满分] 分
- 得分率：[计算得分率]%
- 整体评价：[优秀/良好/中等/需要改进]

## 2. 各题得分统计
- 第1题：[得分]/[满分] 分 - [评价]
- 第2题：[得分]/[满分] 分 - [评价]
[继续列出所有题目...]

## 3. 知识点掌握分析
### 掌握较好的知识点
- [列出学生掌握较好的知识点]
- [分析原因]

### 需要加强的知识点
- [列出需要加强的知识点]
- [分析薄弱原因]

## 4. 常见错误类型分析
### 计算错误
- [统计计算错误的题目和频率]
- [分析错误原因]

### 概念理解错误
- [统计概念错误的题目和频率]
- [分析错误原因]

### 方法选择错误
- [统计方法错误的题目和频率]
- [分析错误原因]

## 5. 学习建议
### 短期改进建议
- [针对具体错误的改进建议]
- [推荐的练习方向]

### 长期学习规划
- [基础知识巩固建议]
- [能力提升建议]

## 6. 优点与亮点
- [总结学生的优点和亮点表现]
- [鼓励性评价]

## 7. 总体评语
[给出综合性的评价和鼓励，指出学生的进步方向]

请仔细分析以下所有批改结果，提取关键信息进行综合分析：

{chr(10).join(all_results)}

注意：请确保所有数学符号使用标准Unicode字符，分析要客观准确，建议要具体可行。"""
        else:
            prompt = f"""As a professional teacher, please generate a comprehensive summary report based on the grading results of the following {total_groups} problems. Use standard Unicode mathematical symbols (such as × ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ), strictly prohibiting LaTeX formats.

# Comprehensive Grading Summary Report

## 1. Overall Performance Overview
- Total problems: {total_groups}
- Overall score: [calculate total score]/[calculate total full marks] points
- Score rate: [calculate score rate]%
- Overall evaluation: [Excellent/Good/Average/Needs Improvement]

## 2. Score Statistics by Problem
- Problem 1: [score]/[full marks] points - [evaluation]
- Problem 2: [score]/[full marks] points - [evaluation]
[Continue listing all problems...]

## 3. Knowledge Point Mastery Analysis
### Well-mastered Knowledge Points
- [List knowledge points the student has mastered well]
- [Analyze reasons]

### Knowledge Points Needing Improvement
- [List knowledge points needing strengthening]
- [Analyze weakness reasons]

## 4. Common Error Type Analysis
### Calculation Errors
- [Count calculation errors by problem and frequency]
- [Analyze error causes]

### Conceptual Understanding Errors
- [Count conceptual errors by problem and frequency]
- [Analyze error causes]

### Method Selection Errors
- [Count method errors by problem and frequency]
- [Analyze error causes]

## 5. Learning Recommendations
### Short-term Improvement Suggestions
- [Specific improvement suggestions for errors]
- [Recommended practice directions]

### Long-term Learning Plan
- [Suggestions for consolidating basic knowledge]
- [Suggestions for ability improvement]

## 6. Strengths and Highlights
- [Summarize student's strengths and highlight performances]
- [Encouraging evaluation]

## 7. Overall Comments
[Provide comprehensive evaluation and encouragement, pointing out the student's direction for progress]

Please carefully analyze all the following grading results and extract key information for comprehensive analysis:

{chr(10).join(all_results)}

Note: Please ensure all mathematical symbols use standard Unicode characters, analysis should be objective and accurate, and suggestions should be specific and feasible."""

        # 调用API生成综合总结
        client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
        )

        # 系统消息
        system_message = """你是一位资深教育专家，擅长分析学生的学习情况并提供综合性的学习建议。
在回复中，你必须使用标准Unicode数学符号，而非LaTeX格式。
请基于提供的批改结果进行深入分析，给出客观、准确、有建设性的综合评价。""" if language == "zh" else """You are an experienced education expert, skilled in analyzing student learning situations and providing comprehensive learning advice.
In your responses, you must use standard Unicode mathematical symbols, not LaTeX format.
Please conduct in-depth analysis based on the provided grading results and give objective, accurate, and constructive comprehensive evaluations."""

        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-72B-Instruct",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.7
        )

        result = response.choices[0].message.content
        return force_natural_language(result)
        
    except Exception as e:
        error_msg = "生成综合总结失败" if language == "zh" else "Failed to generate comprehensive summary"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

if __name__ == "__main__":
    pass