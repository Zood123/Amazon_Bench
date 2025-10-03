
import os
from openai import OpenAI

openai_api_key = "xxx"
# Initialize OpenAI client (recommended way in v1+)
client = OpenAI(api_key=openai_api_key)  # or directly: api_key="your-key"

# Template function to query GPT
def ask_gpt(prompt, model="gpt-4o", temperature=0.7, max_tokens=2048):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()