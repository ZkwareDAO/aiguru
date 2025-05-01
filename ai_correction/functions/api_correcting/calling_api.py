import base64
import requests  
from openai import OpenAI
import re

# 完全重写提示词，使用最简单的指令而非模板，避免任何可能导致JSON输出的引导
marking_scheme_prompt = """作为一名教师，请对上传的题目创建一份评分标准。请使用完全自然语言方式描述，不要使用JSON或代码格式。

您的评分标准应包含以下内容：
1. 题目属于什么科目和类型
2. 总分值
3. 每个步骤的分值和评分要点
4. 扣分点
5. 知识点分析

如果是理科题目，请特别详细说明解题思路和常见错误。请使用标题、小标题和编号来组织你的回答，但不要使用代码块格式。

严格禁止使用JSON格式输出！请仅使用自然语言和普通文本格式！"""

correction_prompt = """作为一名教师，请批改学生的答案。请使用完全自然语言方式描述，不要使用JSON或代码格式。

您的批改应包含以下内容：
1. 科目类型和总分
2. 分步骤的点评，包括得分点和扣分点
3. 对错误的分析和改进建议
4. 总体评价
5. 学习建议

如果是理科题目，请特别详细分析错误原因、正确解题思路、公式应用和计算过程。请使用标题、小标题和编号来组织你的回答，但不要使用代码块格式。

严格禁止使用JSON格式输出！请仅使用自然语言和普通文本格式！"""

correction_with_images_prompt = """作为一名教师，请批改学生的答案。请使用完全自然语言方式描述，不要使用JSON或代码格式。

您的批改应包含以下内容：
1. 科目类型和总分
2. 分步骤的点评，包括得分点和扣分点
3. 对错误的分析和改进建议
4. 总体评价
5. 学习建议

如果是理科题目，请特别详细分析错误原因、正确解题思路、公式应用和计算过程。请使用标题、小标题和编号来组织你的回答，但不要使用代码块格式。

严格禁止使用JSON格式输出！请仅使用自然语言和普通文本格式！"""

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
    if (text.count('{') > 2 and text.count('}') > 2) or '"' in text or ':' in text:
        # 尝试去除格式符号
        text = re.sub(r'[{}\[\]"]', '', text)
        text = re.sub(r':\s*', ': ', text)
        text = re.sub(r',\s*', '\n', text)
        
        # 添加警告消息
        text = "【注意：以下内容已从结构化格式转换为纯文本】\n\n" + text
    
    return text

def call_api(input_text, *input_images):
    """
    调用API进行图像识别和处理
    
    参数:
    input_text: 字符串，提示文本
    input_images: 一系列图片文件路径
    
    返回:
    字符串，API响应内容
    """
    client = OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
    )
    
    # 使用多种提示策略来强制自然语言输出
    system_message = "你是一位教育专家，擅长用清晰的自然语言解释概念。永远不要使用JSON格式，只使用普通文本。"
    
    # 强制修改输入提示
    enhanced_prompt = (
        input_text + 
        "\n\n特别注意：请用纯粹的自然语言回答，禁止使用任何JSON或代码格式。不需要遵循特定数据结构，只需清晰地表达你的分析和建议。" + 
        "\n\n如果是理科题目，请提供详细的解析和批注，但仍然使用自然语言。" +
        "\n\n最重要的一点：无论如何，都不要输出JSON格式！"
    )
    
    content = [{"type": "text", "text": enhanced_prompt}]
    
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

def correction_with_marking_scheme(marking_scheme, *image_files, api=default_api):
    """使用提供的评分方案进行批改，返回纯文本形式"""
    try:
        # 将评分方案作为正常文本附加，避免引起结构化思维
        prompt = correction_prompt + "\n\n参考的评分要点如下（仅供参考，请用自然语言回答）：\n\n" + str(marking_scheme)
        return api(prompt, *image_files)
    except Exception as e:
        raise RuntimeError(f"批改失败: {str(e)}") from e

def correction_with_image_marking_scheme(*image_files_and_marking_scheme, api=default_api):
    """使用图像中的评分方案进行批改，返回纯文本形式"""
    try:
        return api(correction_with_images_prompt, *image_files_and_marking_scheme)
    except Exception as e:
        raise RuntimeError(f"批改失败: {str(e)}") from e

def correction_without_marking_scheme(*images, api=default_api):
    """自动生成评分方案并批改，返回纯文本形式"""
    marking_scheme = generate_marking_scheme(*images)
    return correction_with_marking_scheme(marking_scheme, *images, api=api)

# 保留原函数名以保持兼容性
correction_with_json_marking_scheme = correction_with_marking_scheme

if __name__ == "__main__":
    pass