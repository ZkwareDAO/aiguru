import base64
import requests  
from openai import OpenAI
import re
from pathlib import Path
import fitz  # PyMuPDF
import json
import os
import prompts

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
      - content_type: 'text' , 'image', 'pdf'或 'error'
      - content: 文件内容或错误信息
    """
    file_type = get_file_type(file_path)
    file_name = Path(file_path).name
    
    try:
        if file_type == 'image':
            # 图片文件作为base64返回
            return 'image', file_path
        
        elif file_type == 'pdf':
            
            return 'pdf', file_path
        
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

def pdf_pages_to_base64_images(pdf_path, zoom=3.0):
    """
    将 PDF 每页转换为 Base64 编码的图像数据列表
    
    参数:
        pdf_path (str): PDF 文件路径
        zoom (float): 缩放因子 (提高分辨率)
    
    返回:
        list: 包含每页 Base64 编码图像数据的列表
    """
    base64_images = []
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # 创建变换矩阵（缩放提高分辨率）
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        # 转换为 PNG 图像数据
        img_data = pix.tobytes("png")
        # 编码为 Base64
        base64_str = base64.b64encode(img_data).decode("utf-8")
        base64_images.append(base64_str)
    
    doc.close()
    return base64_images

def call_tongyiqianwen_api(input_text, *input_contents,system_message="", language="zh"):
    ##########
    #input("Callingtyqw:\n"+input_text+str(input_contents))
    """
    调用API进行多类型文件处理，支持批改严格程度和语言设置
    增强版：支持图像、PDF、Word文档、文本文件等多种类型
    
    参数:
    input_text: 字符串，提示文本
    input_contents: 一系列文件路径（支持图像、PDF、Word、文本等多种格式）/str
    
    
    返回:
    字符串，API响应内容
    """
    client = OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
    )
    
    content = [{"type": "text", "text": input_text}]
    
    # 处理文件
    for single_content in input_contents:
        if os.path.isfile(single_content):
            content_type, processed_content = process_file_content(single_content)
        
            
            if content_type == 'text':
                content.append({
                    "type": "text",
                    "text":processed_content
                })
            elif content_type=='image':
                # 普通图像文件
                base_64_image = img_to_base64(single_content)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base_64_image}"
                    }
                })    
            # 检查是否是PDF文件
            elif content_type == 'pdf':
                # PDF文件作为图像处理
                base_64_images = pdf_pages_to_base64_images(single_content)
                for base_64_image in base_64_images:
                    content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base_64_image}"
                    }})
            else:
                raise ValueError(f"The file {single_content} could not be processed.")
        else:
            content.append({
                    "type": "text",
                    "text":single_content
                })

    # 调用API
    try:
        final_message=[]
        if system_message:
            final_message.append({"role": "system", "content": system_message})
        final_message.append({"role": "user", "content": content})
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-VL-72B-Instruct",
            messages=final_message,
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
        return result
        
    except Exception as e:
        error_msg = f"API调用失败: {str(e)}" if language == "zh" else f"API call failed: {str(e)}"
        print(f"API调用错误: {e}")
        return error_msg

# 标准API调用函数
default_api = call_tongyiqianwen_api

def extract_json_from_str(string):
    
        json_match = re.search(r'\{.*\}', string, re.DOTALL)
        if not json_match:
            raise ValueError("返回字符串中未找到有效JSON")
        
        # 解析返回结果
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"返回内容不是有效JSON: {str(e)}") from e

def generate_json_marking_scheme(image_files, api=default_api, language="zh"):
    """生成评分方案
    image_files:tuple(stdent answer)
    """
    try:
        prompt = prompts.marking_scheme_prompts[language]
        return extract_json_from_str(api(prompt, *image_files, language=language,system_message=prompts.system_messages[language]))
    except Exception as e:
        error_msg = "生成评分方案失败" if language == "zh" else "Failed to generate marking scheme"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_json_marking_scheme(json_marking_scheme, image_files, strictness_level="中等", api=default_api, language="zh"):
    """使用提供的评分方案进行批改，返回json形式"""
    try:
        # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = prompts.correction_prompts[language] + "\n"
        prompt+=prompts.strictness_descriptions[language][strictness_level]+'\n'
        # Add appropriate language text for marking scheme reference
        if language == "zh":
            prompt += "参考的评分标准如下（必须严格遵守）：\n\n"
        else:
            prompt += "Reference marking scheme below (must be strictly followed):\n\n"
        prompt += str(json_marking_scheme)
        student_answer_notice="""以下是学生作答:\n"""if language=='zh'else"Student's answer is shown below:\n"
        result=api(prompt,student_answer_notice, *image_files, language=language,system_message=prompts.system_messages[language])
        return extract_json_from_str(result)
    except Exception as e:
        error_msg = "批改失败" if language == "zh" else "Correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_with_marking_scheme(marking_schemes:tuple[str],student_answers:tuple[str], strictness_level="中等", api=default_api, language="zh"):
    """使用图像中的评分方案进行批改，返json形式
    marking_schemes,student_answers:tuple(path)
    """
    try:
        # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = prompts.correction_prompts[language] + "\n\n"
        prompt+=prompts.strictness_descriptions[language][strictness_level]+'\n\n'
         # Add appropriate language text for marking scheme reference
        if language == "zh":
            prompt += "以下将先输入参考的评分标准（必须严格遵守）：\n\n"
        else:
            prompt += "Reference marking scheme below (must be strictly followed):\n\n"
        student_answer_notice="""以下是学生作答:\n"""if language=='zh'else"Student's answer is shown below:\n"
        result=api(prompt, *marking_schemes,student_answer_notice,*student_answers, language=language,system_message=prompts.system_messages[language])
        return extract_json_from_str(result)
    except Exception as e:
        error_msg = "批改失败" if language == "zh" else "Correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def correction_without_marking_scheme(student_answer:tuple[str], strictness_level="中等", api=default_api, language="zh"):
    """自动生成评分方案并批改，返回纯json形式"""
    marking_scheme = generate_json_marking_scheme(student_answer, api=api,language=language)
    return correction_with_json_marking_scheme(marking_scheme, student_answer, strictness_level=strictness_level, api=api, language=language)

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
        
        return force_natural_language(api(prompt,prompts.strictness_descriptions[language][strictness_level], *image_files, system_message=prompts.system_messages[language], language=language))
    except Exception as e:
        error_msg = f"第{group_index}题批改失败" if language == "zh" else f"Problem {group_index} correction failed"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

def generate_comprehensive_summary(all_results, language="zh", total_groups=1,api=default_api):
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
        
        # 系统消息
        system_message = """你是一位资深教育专家，擅长分析学生的学习情况并提供综合性的学习建议。
在回复中，你必须使用标准Unicode数学符号，而非LaTeX格式。
请基于提供的批改结果进行深入分析，给出客观、准确、有建设性的综合评价。""" if language == "zh" else """You are an experienced education expert, skilled in analyzing student learning situations and providing comprehensive learning advice.
In your responses, you must use standard Unicode mathematical symbols, not LaTeX format.
Please conduct in-depth analysis based on the provided grading results and give objective, accurate, and constructive comprehensive evaluations."""

        result = api(prompt,system_message=system_message,language=language)
        return result
        
    except Exception as e:
        error_msg = "生成综合总结失败" if language == "zh" else "Failed to generate comprehensive summary"
        raise RuntimeError(f"{error_msg}: {str(e)}") from e

if __name__ == "__main__":
    print(str(correction_without_marking_scheme(('D:/Robin/Project/paper/l3.jpg',),language='en')))
    pass