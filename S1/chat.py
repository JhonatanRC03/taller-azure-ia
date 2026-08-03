import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv("../.env")

openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
auth_key_or_token = os.getenv("AZURE_OPENAI_API_KEY")
model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = OpenAI(
    base_url=openai_endpoint,
    api_key=auth_key_or_token
)

# Get response using the code_interpreter tool
response = client.responses.create(
    model=model_deployment,
    instructions="You are a helpful AI assistant. When solving math problems, use the python tool to run the code and then explain the result in detail, showing the steps and reasoning behind the answer.",
    input="What is the square root of 16?",
    tools=[{"type": "code_interpreter",
            "container": {"type": "auto"}}]
)
print(response.output_text)
