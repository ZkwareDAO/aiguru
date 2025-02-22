from google import genai

client = genai.Client(api_key="AIzaSyCHHE2VjvCW4H28b29XbFHZIbZ3O8lklC8")#apikey在“https://aistudio.google.com/app/apikey”申请
response = client.models.generate_content(
    model="gemini-2.0-flash", contents="Explain what is \"api\""
)#需要连接vpn
print(response.text)