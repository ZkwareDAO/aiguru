from google import genai
from google.genai import types
import PIL.Image
image = PIL.Image.open('D:/Draft/inte.png')#这是我电脑上的本地图片
client = genai.Client(api_key="(your api key)")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=["calculate this integration", image])
print(response.text)
#测试成功