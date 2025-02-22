from google import genai#需要在cmd运行"pip install -q -U google-genai"才能用

client = genai.Client(api_key="AIzaSyCHHE2VjvCW4H28b29XbFHZIbZ3O8lklC8")#api_key在“https://aistudio.google.com/app/apikey”免费申请
response = client.models.generate_content(
    model="gemini-2.0-flash", contents="Explain what is \"api\""
)#contents为向ai询问的内容，需要连接vpn
print(response.text)#运行的时候点击右上角那个 三角形 旁边的那个 向下的箭头 ，然后选择运行python文件