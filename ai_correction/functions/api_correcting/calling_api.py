import base64
import requests  
import openai
import re
from pathlib import Path
from datetime import datetime

# 设置OpenAI API配置 - 完全兼容新版本
try:
    # 尝试导入新版本 openai >= 1.0.0
    from openai import OpenAI
    client = OpenAI(
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay",
        base_url="https://api.siliconflow.cn/v1"
    )
    OPENAI_NEW_VERSION = True
    print("✅ 使用新版本OpenAI API (>=1.0.0)")
except ImportError:
    try:
        # 回退到旧版本 openai < 1.0.0
        import openai
        openai.api_base = "https://api.siliconflow.cn/v1"
        openai.api_key = "sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
        OPENAI_NEW_VERSION = False
        print("⚠️ 使用旧版本OpenAI API (<1.0.0)")
    except ImportError:
        print("❌ OpenAI库未安装，请运行：pip install openai")
        OPENAI_NEW_VERSION = None

# 新的智能批改提示词 - JSON格式输出
def get_json_correction_prompt():
    """获取JSON格式的批改提示词"""
    return """作为专业批改教师，请严格按照JSON格式输出批改结果。使用标准Unicode数学符号，禁用LaTeX格式。

输出JSON结构：
- 基本信息：科目、题目类型、总分、得分、得分率
- 学生答题过程：步骤编号、学生原始过程、该步骤满分、该步骤得分、正确性、扣分点
- 标准答案对比：正确解法、关键差异
- 总结：主要优点、主要问题、改进建议

重要要求：
1. 必须严格按照JSON格式输出
2. 数学符号使用Unicode：分数写成a/b，根号写成√a，三角函数写成sin x
3. 学生原始过程必须完整还原学生的解题步骤，不能添加修正
4. 分值必须是数字类型
5. 总结部分要简洁明了"""

# 🎯 专为老师批量批改设计的高效简洁提示词
efficient_correction_prompt_zh = """作为专业批改教师，请快速高效地批改这份作业。输出格式必须简洁明了，便于老师快速浏览。

📋 **批改结果**
**得分：[X]/[总分]** 
**等级：[A+/A/B+/B/C+/C/D]**

🔍 **关键问题**
• [列出1-3个最主要的错误或问题，每个不超过15字]

✅ **亮点**
• [列出1-2个答题亮点，每个不超过15字]

💡 **改进建议**
• [给出1-2条具体改进建议，每条不超过20字]

⚠️ **注意事项**
- 使用标准Unicode数学符号（× ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ）
- 分数写作"a/b"，根号写作"√a"
- 三角函数写作"sin x"，指数写作"x²"
- 严禁使用LaTeX格式

请保持批改结果简洁，总字数控制在150字以内，便于老师快速处理大量作业。"""

efficient_correction_prompt_en = """As a professional grading teacher, please efficiently grade this assignment. The output format must be concise and clear for teachers to quickly review.

📋 **Grading Result**
**Score: [X]/[Total]** 
**Grade: [A+/A/B+/B/C+/C/D]**

🔍 **Key Issues**
• [List 1-3 main errors or problems, each within 15 words]

✅ **Highlights**
• [List 1-2 answer highlights, each within 15 words]

💡 **Improvement Suggestions**
• [Give 1-2 specific improvement suggestions, each within 20 words]

⚠️ **Notes**
- Use standard Unicode math symbols (× ÷ ± √ π ∑ ∫ ≤ ≥ ≠ ∞ θ)
- Write fractions as "a/b", roots as "√a"
- Write trig functions as "sin x", exponents as "x²"
- Strictly prohibit LaTeX format

Keep grading results concise, total word count within 150 words for teachers to quickly process large volumes of assignments."""

# 新的智能批改函数
def intelligent_correction_with_files(question_files=None, answer_files=None, marking_scheme_files=None, 
                                    strictness_level="中等", language="zh", mode="auto"):
    """
    智能批改函数，根据提供的文件类型自动调整批改策略
    
    参数:
    question_files: 题目文件列表
    answer_files: 学生答案文件列表  
    marking_scheme_files: 批改标准文件列表
    strictness_level: 批改严格程度
    language: 输出语言
    mode: 批改模式
    """
    try:
        # 构建文件列表
        all_files = []
        file_types_info = []
        
        # 添加题目文件
        if question_files:
            all_files.extend(question_files)
            file_types_info.extend([f"题目文件: {Path(f).name}" for f in question_files])
            
        # 添加学生答案文件
        if answer_files:
            all_files.extend(answer_files)
            file_types_info.extend([f"学生答案: {Path(f).name}" for f in answer_files])
            
        # 添加批改标准文件
        if marking_scheme_files:
            all_files.extend(marking_scheme_files)
            file_types_info.extend([f"批改标准: {Path(f).name}" for f in marking_scheme_files])
        
        # 构建智能提示词
        base_prompt = get_json_correction_prompt()
        
        # 根据文件类型调整提示词
        if marking_scheme_files:
            base_prompt += "\n\n【特别注意】已提供批改标准文件，请严格按照标准进行评分。"
            
        if question_files:
            base_prompt += "\n\n【特别注意】已提供题目文件，请结合题目要求进行批改。"
            
        # 添加文件类型说明
        files_info = "上传文件类型说明：\n" + "\n".join(file_types_info)
        final_prompt = base_prompt + "\n\n" + files_info
        
        # 调用API
        result = call_api(final_prompt, *all_files, strictness_level=strictness_level, language=language)
        
        return result
        
    except Exception as e:
        error_msg = f"智能批改失败: {str(e)}"
        raise RuntimeError(error_msg) from e

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
    # 使用旧版本的openai库，配置已在文件顶部设置
    
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
        if OPENAI_NEW_VERSION is None:
            return "❌ OpenAI库未安装，无法进行批改。请运行：pip install openai"
        
        if OPENAI_NEW_VERSION:
            # 新版本API调用
            response = client.chat.completions.create(
                model="Qwen/Qwen2.5-VL-72B-Instruct",
                messages=[
                    {"role": "system", "content": system_messages[language]},
                    {"role": "user", "content": content}
                ],
                max_tokens=4096,
                temperature=0.7
            )
            result = response.choices[0].message.content
        else:
            # 旧版本API调用
            response = openai.ChatCompletion.create(
                model="Qwen/Qwen2.5-VL-72B-Instruct",
                messages=[
                    {"role": "system", "content": system_messages[language]},
                    {"role": "user", "content": content}
                ],
                max_tokens=4096,
                temperature=0.7
            )
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

# 简化版兼容函数，保持向后兼容性
def generate_marking_scheme(*image_file, api=default_api, language="zh"):
    """生成评分方案，返回纯文本形式"""
    try:
        prompt = "请为上传的题目创建详细的评分标准。使用标准Unicode数学符号，明确各步骤分值。"
        return api(prompt, *image_file, language=language)
    except Exception as e:
        error_msg = "生成评分方案失败" if language == "zh" else "Failed to generate marking scheme"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_marking_scheme(marking_scheme, *image_files, strictness_level="中等", api=default_api, language="zh"):
    """使用提供的评分方案进行批改，返回纯文本形式"""
    try:
        prompt = get_json_correction_prompt() + "\n\n参考的评分标准如下（必须严格遵守）：\n\n" + str(marking_scheme)
        return api(prompt, *image_files, strictness_level=strictness_level, language=language)
    except Exception as e:
        error_msg = "批改失败" if language == "zh" else "Correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_without_marking_scheme(*images, strictness_level="中等", api=default_api, language="zh"):
    """自动生成评分方案并批改，返回纯文本形式"""
    try:
        prompt = get_json_correction_prompt() + "\n\n请先分析题目，然后按照JSON格式批改学生答案。"
        return api(prompt, *images, strictness_level=strictness_level, language=language)
    except Exception as e:
        error_msg = "批改失败" if language == "zh" else "Correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_single_group(*image_files, strictness_level="中等", api=default_api, language="zh", group_index=1):
    """
    对单个文件组（通常对应一道题）进行批改，返回JSON格式
    
    参数:
    image_files: 图像文件列表，通常包含题目、学生答案、评分标准
    strictness_level: 批改严格程度
    api: API调用函数
    language: 输出语言
    group_index: 组索引，用于标识是第几道题
    """
    try:
        prompt = get_json_correction_prompt() + f"\n\n正在批改第{group_index}题，请仔细分析上传的文件内容。"
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
        # 系统消息
        system_message = """你是一位资深教育专家，擅长分析学生的学习情况并提供综合性的学习建议。
在回复中，你必须使用标准Unicode数学符号，而非LaTeX格式。
请基于提供的批改结果进行深入分析，给出客观、准确、有建设性的综合评价。""" if language == "zh" else """You are an experienced education expert, skilled in analyzing student learning situations and providing comprehensive learning advice.
In your responses, you must use standard Unicode mathematical symbols, not LaTeX format.
Please conduct in-depth analysis based on the provided grading results and give objective, accurate, and constructive comprehensive evaluations."""

        if OPENAI_NEW_VERSION:
            # 新版本API调用
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
        else:
            # 旧版本API调用
            response = openai.ChatCompletion.create(
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

def efficient_correction_single(*image_files, strictness_level="中等", api=default_api, language="zh"):
    """
    🎯 专为老师批量批改设计的高效简洁批改函数
    输出JSON格式，便于老师快速处理大量作业
    
    参数:
    image_files: 图像文件列表
    strictness_level: 批改严格程度
    api: API调用函数
    language: 输出语言
    """
    try:
        prompt = get_json_correction_prompt() + "\n\n请进行高效批改，输出简洁的JSON格式结果。"
        
        # 根据严格程度调整提示词
        if strictness_level == "严格":
            prompt += "\n\n⚠️ 批改要求：请从严评分，对细节错误也要扣分。"
        elif strictness_level == "宽松":
            prompt += "\n\n⚠️ 批改要求：请适当宽松评分，重点关注主要错误。"
        else:
            prompt += "\n\n⚠️ 批改要求：请按标准严格程度评分，平衡准确性和鼓励性。"
        
        return api(prompt, *image_files, strictness_level=strictness_level, language=language)
    except Exception as e:
        error_msg = "高效批改失败" if language == "zh" else "Efficient correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def batch_efficient_correction(*image_files, strictness_level="中等", api=default_api, language="zh"):
    """
    🚀 批量高效批改函数，专为老师处理多份作业设计
    
    参数:
    image_files: 图像文件列表
    strictness_level: 批改严格程度
    api: API调用函数
    language: 输出语言
    """
    try:
        results = []
        total_files = len(image_files)
        
        for i, file in enumerate(image_files, 1):
            try:
                # 为每个文件调用高效批改
                result = efficient_correction_single(file, 
                                                   strictness_level=strictness_level, 
                                                   api=api, 
                                                   language=language)
                
                # 添加序号标识
                file_name = getattr(file, 'name', f'文件{i}')
                header = f"## 📄 {file_name} ({i}/{total_files})\n\n" if language == "zh" else f"## 📄 {file_name} ({i}/{total_files})\n\n"
                results.append(header + result)
                
            except Exception as e:
                error_msg = f"文件 {i} 批改失败: {str(e)}" if language == "zh" else f"File {i} correction failed: {str(e)}"
                results.append(f"## ❌ 文件 {i}\n{error_msg}")
        
        # 组合所有结果
        final_result = "\n\n---\n\n".join(results)
        
        # 添加批量批改总结
        summary_header = f"\n\n# 📊 批改总览\n**共批改 {total_files} 份作业**\n✅ 批改完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" if language == "zh" else f"\n\n# 📊 Grading Overview\n**Total {total_files} assignments graded**\n✅ Completion time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return final_result + summary_header
        
    except Exception as e:
        error_msg = "批量批改失败" if language == "zh" else "Batch correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

if __name__ == "__main__":
    pass