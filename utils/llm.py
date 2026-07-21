import os
import httpx
from dotenv import load_dotenv
from openai import AzureOpenAI

# ---------------- LOAD ENV ----------------
load_dotenv()


# ---------------- AZURE OPENAI CLIENT ----------------
def get_azure_openai_client():

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not api_key:
        raise Exception("AZURE_OPENAI_API_KEY not found in .env file.")

    if not endpoint:
        raise Exception("AZURE_OPENAI_ENDPOINT not found in .env file.")

    if not api_version:
        raise Exception("AZURE_OPENAI_API_VERSION not found in .env file.")

    # Temporary workaround for corporate SSL inspection.
    # Proper fix should be using company root CA certificate.
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

    return client


# ---------------- GET DEPLOYMENT NAME ----------------
def get_deployment_name():

    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not deployment_name:
        raise Exception("AZURE_OPENAI_DEPLOYMENT_NAME not found in .env file.")

    return deployment_name


# ---------------- BUSINESS INSIGHT GENERATION ----------------
def ask_llm(question, data_context):

    try:

        client = get_azure_openai_client()
        deployment_name = get_deployment_name()

        prompt = f"""
You are a business analytics assistant.

Use only the provided result data.
Do not hallucinate.
Do not mention SQL, Python, dataframe, code, or implementation details.
Give a concise business insight in 2-3 lines.
If the result is limited, mention that briefly.

User question:
{question}

Result data:
{data_context}
"""

        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "You generate concise and accurate business insights from analytics results."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=250
        )

        return response.choices[0].message.content.strip()

    except Exception as e:

        print("Azure OpenAI insight error:", e)

        return None


# ---------------- PANDAS CODE FALLBACK GENERATION ----------------
def generate_pandas_code(
    question,
    columns,
    selected_sheet,
    conversation_context="",
    active_filters=None
):

    try:

        client = get_azure_openai_client()
        deployment_name = get_deployment_name()

        if active_filters is None:
            active_filters = {}

        columns_text = "\n".join(
            [
                f"- {col}"
                for col in columns
            ]
        )

        prompt = f"""
You are a Python pandas code generator.

Rules:
1. Use only the dataframe named df.
2. Use only these available columns:
{columns_text}

3. Store the final answer in a variable named result.
4. Do not import libraries.
5. Do not read or write files.
6. Do not use columns that are not listed.
7. Return only valid Python code.
8. If aggregation is needed, create a dataframe result.
9. If the user asks for top/ranking, use value_counts or groupby.
10. If the user asks for unique count, use nunique.
11. Do not explain the code.

Sheet/View:
{selected_sheet}

Active filters:
{active_filters}

Conversation context:
{conversation_context}

User question:
{question}
"""

        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "You write safe pandas code only. Return only executable Python code."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=500
        )

        code = response.choices[0].message.content.strip()

        code = (
            code
            .replace("```python", "")
            .replace("```", "")
            .strip()
        )

        return code

    except Exception as e:

        print("Azure OpenAI pandas fallback error:", e)

        return "result = 'LLM fallback is currently unavailable.'"