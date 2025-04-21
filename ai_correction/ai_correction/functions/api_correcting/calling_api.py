from openai import OpenAI
import base64
import requests  

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

def call_api(input_jpg,input_markingscheme):
    client = OpenAI(
        base_url="https://api.siliconflow.cn/v1",
        api_key="sk-exhlpcmlvywtnrzancrdqbohmsbfbmxkkodjhqxufkbhctay"
    )

    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-VL-72B-Instruct",
        messages=[
            {  
                "role": "user",
                "content": [
                    {"type": "text", "text": '''第一個輸入的圖片為題目與學生作答，第二個輸入的圖片為改卷方案。
你是一个数学题自动批改系统，需根据提供的评分方案严格评估学生答案。请按以下规则执行：

1. **输入内容**：
   - 第一幅圖片中的學生作答。
   - 第二幅圖片中的批改方案。
2. **任务要求**：
   - 逐项对比学生答案与评分方案的每个步骤：
     - 确认是否完成该步骤。
     - 检查得分点和扣分点，记录具体错误。
   - 计算总分并生成反馈：
     - 若某步骤部分正确，按比例给分（如公式正确但计算错误，得该步骤50%分值）。
     - 若发现评分方案未覆盖的新错误，暂标记为“待人工复核”。
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
   - 禁止修改原始评分方案，仅基于其执行批改。'''},

                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_to_base64(input_jpg)}"
                        }
                 },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_to_base64(input_markingscheme)}"
                        }
                }    
                ]
            }
        ],
        max_tokens=2048,
        temperature=0.7
    )
    return response

