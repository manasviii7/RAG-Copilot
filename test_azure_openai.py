from dotenv import load_dotenv
import os
import httpx
from openai import AzureOpenAI

load_dotenv()

api_key = os.getenv("AZURE_OPENAI_API_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

print("API key loaded:", api_key is not None)
print("Endpoint:", endpoint)
print("API version:", api_version)
print("Deployment:", deployment)

http_client = httpx.Client(
    verify=False,
    timeout=60
)

client = AzureOpenAI(
    api_key=api_key,
    azure_endpoint=endpoint,
    api_version=api_version,
    http_client=http_client
)

response = client.chat.completions.create(
    model=deployment,
    messages=[
        {
            "role": "user",
            "content": "Say Azure OpenAI connection is working in one short sentence."
        }
    ],
    temperature=0.2,
    max_tokens=50
)

print(response.choices[0].message.content)