from litellm import completion
import os

## set ENV variables
os.environ["OPENAI_API_KEY"] = "sk-proj-"

messages = [{ "content": "Hello, how are you?","role": "user"}]

# openai call
response = completion(model="gpt-4o-mini", messages=messages)

print(response.choices[0].message.content)