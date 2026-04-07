
from openai import OpenAI
import os
from dotenv import load_dotenv

# 👇 ESTO ES CLAVE
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "user", "content": "Decime hola desde la IA"}
    ]
)

print(response.choices[0].message.content)
