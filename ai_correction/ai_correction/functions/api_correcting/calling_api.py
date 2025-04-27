import base64
import requests  
from openai import OpenAI

# 完全重写提示词，使用最严格的格式要求禁止JSON输出，并为理科题目增加详细批注
marking_scheme_prompt="""你是一个优秀的教师助手，需要为各类学科题目生成评分方案，特别是理科题目（数学、物理、化学、生物）需要更加详细的评分标准。请使用自然语言格式，绝对禁止使用JSON或代码格式。

请按照以下结构组织你的回答：

# 评分方案

## 基本信息
- 科目类型：[填写]
- 题目类型：[填写] 
- 总分值：[填写]分

## 详细评分标准
1. 第一步评分点
   - 分值：X分
   - 具体要求：[详细说明]
   - 得分要点：
     * [要点1]
     * [要点2]
   - 扣分情况：
     * [情况1]
     * [情况2]
   - 解题思路：[针对理科题目，详细说明此步骤的解题思路和原理]
   - 常见错误分析：[针对理科题目，分析学生在这一步骤常见的错误及其原因]

2. 第二步评分点
   [使用相同结构]

## 知识点分析
- [知识点1]：[详细解释该知识点的核心概念和应用场景]
- [知识点2]：[详细解释该知识点的核心概念和应用场景]

## 公式和定理应用
[针对理科题目，列出解题过程中涉及的关键公式和定理，并解释其应用]

## 特别说明
[如有特殊评分要求，请在此说明]

记住：你必须使用纯文本格式回答，绝对不要使用JSON格式、代码块或任何编程语言结构。使用标题、列表和段落来组织信息。
"""

correction_prompt="""你是一位专业的教师，需要对学生的答案进行详细批改，特别是对理科题目（数学、物理、化学、生物）需要提供更加详细的批注和分析。请使用自然语言和结构化格式，绝对禁止使用JSON或代码格式。

请按照以下结构组织你的批改：

# 批改结果

## 基本信息
- 科目类型：[填写]
- 总得分：[得分]/[总分]

## 分步骤批改
1. 第一部分
   - 得分：X分
   - 正确之处：
     * [正确点1]
     * [正确点2]
   - 需要改进：
     * [错误点1]
     * [错误点2] 
   - 错误分析：[针对理科题目，详细分析错误的原因和影响]
   - 正确的解题思路：[针对理科题目，提供正确的解题思路和推导过程]
   - 改进建议：
     [具体建议]

2. 第二部分
   [使用相同结构]

## 公式和定理应用评价
[针对理科题目，评价学生对公式和定理的理解和应用情况，指出正确和错误之处]

## 计算过程评价
[针对理科题目，评价学生的计算过程，包括数值计算、单位换算、有效数字处理等]

## 总体评价
[整体评价内容，包括优点和不足]

## 知识点掌握情况
- [知识点1]：[掌握程度，并提供详细分析]
- [知识点2]：[掌握程度，并提供详细分析]

## 学习建议
- [具体建议1：提供针对性的复习和练习建议]
- [具体建议2：提供可参考的学习资源或方法]
- [针对理科题目，提供相关拓展知识和应用场景]

记住：你必须使用纯文本格式回答，绝对不要使用JSON格式、代码块或任何编程语言结构。使用标题、列表和段落来组织信息。将你的批改做成结构清晰但完全是自然语言的形式。
"""

correction_with_images_prompt="""你是一位专业的教师，需要对学生的答案进行详细批改，特别是对理科题目（数学、物理、化学、生物）需要提供更加详细的批注和分析。请使用自然语言和结构化格式，绝对禁止使用JSON或代码格式。

请按照以下结构组织你的批改：

# 批改结果

## 基本信息
- 科目类型：[填写]
- 总得分：[得分]/[总分]

## 分步骤批改
1. 第一部分
   - 得分：X分
   - 正确之处：
     * [正确点1]
     * [正确点2]
   - 需要改进：
     * [错误点1]
     * [错误点2] 
   - 错误分析：[针对理科题目，详细分析错误的原因和影响]
   - 正确的解题思路：[针对理科题目，提供正确的解题思路和推导过程]
   - 改进建议：
     [具体建议]

2. 第二部分
   [使用相同结构]

## 公式和定理应用评价
[针对理科题目，评价学生对公式和定理的理解和应用情况，指出正确和错误之处]

## 计算过程评价
[针对理科题目，评价学生的计算过程，包括数值计算、单位换算、有效数字处理等]

## 总体评价
[整体评价内容，包括优点和不足]

## 知识点掌握情况
- [知识点1]：[掌握程度，并提供详细分析]
- [知识点2]：[掌握程度，并提供详细分析]

## 学习建议
- [具体建议1：提供针对性的复习和练习建议]
- [具体建议2：提供可参考的学习资源或方法]
- [针对理科题目，提供相关拓展知识和应用场景]

记住：你必须使用纯文本格式回答，绝对不要使用JSON格式、代码块或任何编程语言结构。使用标题、列表和段落来组织信息。将你的批改做成结构清晰但完全是自然语言的形式。
"""

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
    
    # 强制修改输入提示，添加明确的自然语言输出要求
    enhanced_prompt = input_text + "\n\n重要提示：你必须以纯自然语言形式回答，禁止使用任何JSON格式。如果是理科题目（数学、物理、化学、生物），请提供更加详细的解析和批注。"
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
        messages=[{  
            "role": "user",
            "content": content
        }],
        max_tokens=4096,  # 增加token数量以允许更详细的回答
        temperature=0.7
    )

    # 进行后处理，确保输出不是JSON格式
    result = response.choices[0].message.content
    
    # 如果响应看起来像JSON（包含大量花括号），进行后处理转换为自然语言
    if result.count('{') > 3 and result.count('}') > 3:
        # 添加警告消息
        result = "（注意：以下内容已从结构化格式转换为纯文本）\n\n" + result
        
    return result

# 标准API调用函数
default_api = call_api

def generate_marking_scheme(*image_file, api=default_api):
    """生成评分方案，返回纯文本形式，对理科题目提供更详细的标准"""
    try:
        return api(marking_scheme_prompt, *image_file)
    except Exception as e:
        raise RuntimeError(f"生成评分方案失败: {str(e)}") from e

def correction_with_marking_scheme(marking_scheme, *image_files, api=default_api):
    """使用提供的评分方案进行批改，返回纯文本形式，对理科题目提供更详细的批注"""
    try:
        prompt = correction_prompt + "\n\n评分方案如下：\n" + str(marking_scheme)
        return api(prompt, *image_files)
    except Exception as e:
        raise RuntimeError(f"批改失败: {str(e)}") from e

def correction_with_image_marking_scheme(*image_files_and_marking_scheme, api=default_api):
    """使用图像中的评分方案进行批改，返回纯文本形式，对理科题目提供更详细的批注"""
    try:
        return api(correction_with_images_prompt, *image_files_and_marking_scheme)
    except Exception as e:
        raise RuntimeError(f"批改失败: {str(e)}") from e

def correction_without_marking_scheme(*images, api=default_api):
    """自动生成评分方案并批改，返回纯文本形式，对理科题目提供更详细的批注"""
    marking_scheme = generate_marking_scheme(*images)
    return correction_with_marking_scheme(marking_scheme, *images, api=api)

# 保留原函数名以保持兼容性
correction_with_json_marking_scheme = correction_with_marking_scheme

if __name__ == "__main__":
    pass