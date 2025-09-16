import requests, base64, re
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}", "Content-Type": "application/json"}
payload = {
  "model": "google/gemini-2.5-flash-image-preview",
  "messages": [{
    "role":"user",
    "content":[
        {"type": "text", "text": "夕阳下的山脉与海面，电影感"},
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}}#{ "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,<你的base64字符串>" } }
    ]
  }],
  "modalities": ["image","text"]
}
res = requests.post(url, headers=headers, json=payload).json()
msg = res["choices"][0]["message"]
img_url = msg["images"][0]["image_url"]["url"]  # data:image/png;base64,...
b64 = re.sub(r"^data:image/[^;]+;base64,", "", img_url)
with open("generated.png","wb") as f:
    f.write(base64.b64decode(b64))
print("saved: generated.png")
