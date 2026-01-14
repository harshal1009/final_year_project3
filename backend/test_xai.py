import requests
import os

key = os.getenv("GROQ_API_KEY")  # ⚠️ rotate this key later

url = "https://api.groq.com/openai/v1/chat/completions"

print("KEY START:", repr(key[:6]))
print("KEY END:", repr(key[-6:]))
print("KEY LENGTH:", len(key))

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}

payload = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {"role": "user", "content": "Just say hello"}
    ],
}

r = requests.post(url, headers=headers, json=payload)

print("STATUS:", r.status_code)
print("RESPONSE:", r.text)
