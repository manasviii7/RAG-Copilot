from groq import Groq
from dotenv import load_dotenv
import httpx
import os

# ---------------- LOAD ENV ----------------
load_dotenv()
print("GROQ KEY LOADED:", os.getenv("GROQ_API_KEY") is not None)

# ---------------- HTTP CLIENT ----------------
http_client = httpx.Client(
    verify=False,
    timeout=120.0
)

# ---------------- GROQ CLIENT ----------------
client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=http_client
)


# ---------------- AI INSIGHT ----------------
def ask_llm(question, result):

    try:

        if question is None:

            question = ""

        if result is None:

            result = ""

        prompt = f"""
You are an expert business data analyst.

USER QUESTION:
{question}

ANALYTICAL RESULT:
{result}

TASK:
1. Give a direct answer based only on the analytical result.
2. Give a concise business insight.
3. Explain what this means in practical business terms.
4. Keep response professional and short.
5. If result is not enough, say that available data is insufficient.

IMPORTANT:
- Do not mention code.
- Do not mention pandas.
- Do not mention dataframe.
- Do not invent facts.
- Do not assume unavailable business meaning.
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as e:

        return f"LLM Error: {e}"


# ---------------- PANDAS CODE GENERATOR ----------------
def generate_pandas_code(
    question,
    columns,
    selected_sheet="",
    conversation_context="",
    active_filters=None
):

    try:

        if question is None:

            question = ""

        if columns is None:

            columns = []

        if active_filters is None:

            active_filters = {}

        if conversation_context is None:

            conversation_context = ""

        available_columns = columns[:50]

        prompt = f"""
You are an expert Python pandas analytics engine.

DATAFRAME NAME:
df

AVAILABLE COLUMNS:
{available_columns}

CURRENT SHEET OR VIEW:
{selected_sheet}

PREVIOUS CONVERSATION:
{conversation_context}

ACTIVE FILTERS:
{active_filters}

USER QUESTION:
{question}

TASK:
Generate executable pandas code that answers the user question.

STRICT OUTPUT RULES:
- Return only executable pandas code.
- No markdown.
- No explanation.
- No imports.
- No print statements.
- Final output must be stored in variable result.
- Use only exact columns from AVAILABLE COLUMNS.
- Never invent columns.
- If the question cannot be answered using AVAILABLE COLUMNS, return:
result = "Requested information is not available in the selected data."

COLUMN RULES:
- Column names may contain spaces.
- Always use df["Column Name"] syntax.
- Do not assume columns unless present.
- Do not use unavailable columns.

ANALYTICS RULES:
1. Count questions:
Use len(df), count(), nunique(), or groupby().size().

2. Top / most common / highest questions:
Use value_counts(), groupby().size(), or sort_values(descending).

3. Bottom / lowest / least questions:
Use ascending sort.

4. Group-wise analysis:
Use:
result = df.groupby("Column").size().reset_index(name="Count")

5. Numeric aggregation:
Use sum(), mean(), median(), min(), max() only on numeric columns.

6. Text/categorical columns:
Never use sum() on text columns.

7. Filters:
Use:
df["Column"].astype(str).str.lower().str.contains("value", na=False)

8. Missing values:
Use isnull(), notnull(), isna(), notna().

9. Unique count:
Use nunique().

10. Duplicate analysis:
Use duplicated() or value_counts().

11. Chart questions:
Return a small aggregated dataframe suitable for charting.

RESULT FORMAT:
If returning scalar value, wrap it in DataFrame.

Example:
result = pd.DataFrame({{"Total Records": [len(df)]}})

EXAMPLES:

Question:
count records

Code:
result = pd.DataFrame(
    {{
        "Total Records": [len(df)]
    }}
)

Question:
top 5 values of a column

Code:
result = (
    df["Column Name"]
    .value_counts()
    .head(5)
    .reset_index()
)
result.columns = [
    "Column Name",
    "Count"
]

Question:
missing values by column

Code:
result = (
    df.isnull()
    .sum()
    .reset_index()
)
result.columns = [
    "Column",
    "Missing Values"
]
result = result.sort_values(
    by="Missing Values",
    ascending=False
)

FINAL REMINDER:
Return only pandas code.
The code must set variable result.
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.03
        )

        code = response.choices[0].message.content

        code = (
            code.replace("```python", "")
            .replace("```", "")
            .replace("`", "")
            .strip()
        )

        if "result" not in code:

            code = '''
result = "Unable to generate a valid query for the selected data."
'''

        return code

    except Exception as e:

        return f'''
result = "LLM generation failed: {str(e)}"
'''