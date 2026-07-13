import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

from utils.excel_loader import load_excel
from utils.db_loader import (
    load_databricks_view,
    execute_databricks_query,
    get_databricks_columns
)
from utils.schema_detector import detect_schema
from utils.llm import ask_llm, generate_pandas_code
from utils.state_manager import save_state, load_state
from utils.intent_detector import detect_intent
from utils.chunking import (
    create_query_chunk,
    build_databricks_query_plan,
    select_chunk_columns
)

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="AI Analytics Copilot",
    layout="wide",
    page_icon="📊"
)

# ---------------- SAFE DATAFRAME RENDER ----------------
def render_dataframe(dataframe):

    try:

        st.dataframe(
            dataframe,
            width="stretch"
        )

    except TypeError:

        st.dataframe(
            dataframe,
            use_container_width=True
        )


# ---------------- SAFE CHART RENDER ----------------
def render_chart(fig, key=None):

    try:

        st.plotly_chart(
            fig,
            width="stretch",
            key=key
        )

    except TypeError:

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=key
        )


# ---------------- ERROR RESULT CHECK ----------------
def is_error_result(result):

    if not isinstance(result, str):

        return False

    error_keywords = [
        "error:",
        "databricks authentication failed",
        "authentication failed",
        "unauthorized",
        "forbidden",
        "403",
        "ssl certificate",
        "certificate verification failed",
        "unable to load",
        "not found in .env"
    ]

    result_lower = result.lower()

    return any(
        keyword in result_lower
        for keyword in error_keywords
    )


# ---------------- LOAD APP STATE ----------------
app_state = load_state()

if "workspaces" not in app_state:

    app_state["workspaces"] = {}

if "current_workspace" not in app_state:

    app_state["current_workspace"] = None

if "current_chat" not in app_state:

    app_state["current_chat"] = None

# ---------------- SIDEBAR ----------------
st.sidebar.title("AI Analytics Workspace")

data_source = st.sidebar.selectbox(
    "Select Data Source",
    ["Excel", "Databricks"]
)

uploaded_file = st.sidebar.file_uploader(
    "Upload Excel File",
    type=["xlsx", "xls"]
)

# ---------------- SAVE UPLOADED EXCEL ----------------
if uploaded_file is not None:

    os.makedirs(
        "uploaded_files",
        exist_ok=True
    )

    file_path = os.path.join(
        "uploaded_files",
        uploaded_file.name
    )

    with open(file_path, "wb") as f:

        f.write(uploaded_file.getbuffer())

    if uploaded_file.name not in app_state["workspaces"]:

        app_state["workspaces"][uploaded_file.name] = {
            "file_path": file_path,
            "chats": {}
        }

    app_state["current_workspace"] = uploaded_file.name

    save_state(app_state)

# ---------------- WORKSPACE SETUP ----------------
if data_source == "Excel":

    excel_workspaces = [
        name
        for name, value in app_state["workspaces"].items()
        if value.get("file_path")
    ]

    if not excel_workspaces:

        st.info(
            "Please upload an Excel file."
        )

        st.stop()

    selected_workspace = st.sidebar.selectbox(
        "📂 Select Workspace",
        excel_workspaces,
        index=excel_workspaces.index(app_state["current_workspace"])
        if app_state["current_workspace"] in excel_workspaces
        else 0
    )

    app_state["current_workspace"] = selected_workspace

    save_state(app_state)

    workspace = app_state["workspaces"][selected_workspace]

else:

    default_view = "gold_tt_dev.gb_dw.upgrade_export_report_view"

    databricks_workspace_key = f"databricks::{default_view}"

    if databricks_workspace_key not in app_state["workspaces"]:

        app_state["workspaces"][databricks_workspace_key] = {
            "file_path": "",
            "view_name": default_view,
            "chats": {},
            "saved_columns": []
        }

        save_state(app_state)

    selected_workspace = databricks_workspace_key

    workspace = app_state["workspaces"][databricks_workspace_key]

    app_state["current_workspace"] = databricks_workspace_key

    save_state(app_state)

# ---------------- LOAD DATA / SCHEMA ----------------
try:

    if data_source == "Excel":

        sheets = load_excel(
            workspace["file_path"]
        )

        selected_sheet = st.selectbox(
            "📄 Select Sheet",
            list(sheets.keys())
        )

        df = sheets[selected_sheet]

        view_name = None

    else:

        view_name = st.text_input(
            "Enter Databricks View",
            value=workspace.get(
                "view_name",
                "gold_tt_dev.gb_dw.upgrade_export_report_view"
            )
        )

        if not view_name:

            st.warning(
                "Please enter Databricks view."
            )

            st.stop()

        workspace["view_name"] = view_name

        if "saved_columns" not in workspace:

            workspace["saved_columns"] = []

        save_state(app_state)

        schema_cache_key = f"schema_{view_name}"

        load_schema_clicked = st.button(
            "📥 Load / Refresh Databricks Schema"
        )

        if load_schema_clicked:

            st.cache_data.clear()

            if schema_cache_key in st.session_state:

                del st.session_state[schema_cache_key]

            with st.spinner(
                "Loading Databricks schema..."
            ):

                st.session_state[schema_cache_key] = get_databricks_columns(
                    view_name
                )

            workspace["saved_columns"] = st.session_state[schema_cache_key]

            save_state(app_state)

        if schema_cache_key in st.session_state:

            databricks_columns = st.session_state[schema_cache_key]

        elif workspace.get("saved_columns"):

            databricks_columns = workspace.get("saved_columns")

        else:

            databricks_columns = []

        df = pd.DataFrame(
            columns=databricks_columns
        )

        selected_sheet = view_name

        if not databricks_columns:

            st.info(
                "Databricks view selected. Click 'Load / Refresh Databricks Schema' to load columns. Basic count queries can still work without schema."
            )

except Exception as e:

    error_text = str(e)

    if (
        "Databricks authentication failed" in error_text
        or "403" in error_text
        or "Unauthorized" in error_text
        or "Forbidden" in error_text
    ):

        st.error(
            "Databricks authentication failed. Please check DATABRICKS_TOKEN in the .env file and make sure it is the same valid token/password that worked in DBeaver. After updating it, restart Streamlit."
        )

    elif (
        "SSL" in error_text
        or "certificate" in error_text
    ):

        st.error(
            "Databricks SSL certificate verification failed. Please check Simba ODBC SSL/certificate settings or corporate network certificate configuration."
        )

    else:

        st.error(
            f"Unable to load dataset/schema: {e}"
        )

    st.stop()

# ---------------- EMPTY CHECK ----------------
if df.empty and data_source != "Databricks":

    st.warning(
        "No data available."
    )

    st.stop()

# ---------------- CLEAN COLUMNS ----------------
df = df.loc[
    :,
    ~df.columns.astype(str).str.contains("^Unnamed")
]

df = df.loc[
    :,
    ~df.columns.duplicated()
]

# ---------------- CLEAN DATA FOR EXCEL ONLY ----------------
if data_source != "Databricks":

    for col in df.columns:

        try:

            if df[col].dtype == "object":

                df[col] = (
                    df[col]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

                cleaned = (
                    df[col]
                    .str.replace(",", "", regex=False)
                    .str.replace("$", "", regex=False)
                    .str.replace("%", "", regex=False)
                )

                converted = pd.to_numeric(
                    cleaned,
                    errors="coerce"
                )

                if converted.notnull().sum() > len(df) * 0.7:

                    df[col] = converted

        except Exception:

            pass

# ---------------- SCHEMA ----------------
schema = detect_schema(df)

numeric_columns = schema["numeric"]
categorical_columns = schema["categorical"]
date_columns = schema["date"]
binary_columns = schema["binary"]

# ---------------- CHAT INIT ----------------
if "chats" not in workspace:

    workspace["chats"] = {}

if st.sidebar.button("➕ Start New Chat"):

    chat_name = f"Chat {len(workspace['chats']) + 1}"

    workspace["chats"][chat_name] = {
        "chat_history": [],
        "query_history": [],
        "active_filters": {}
    }

    app_state["current_chat"] = chat_name

    save_state(app_state)

if not workspace["chats"]:

    workspace["chats"]["Chat 1"] = {
        "chat_history": [],
        "query_history": [],
        "active_filters": {}
    }

    app_state["current_chat"] = "Chat 1"

    save_state(app_state)

chat_names = list(
    workspace["chats"].keys()
)

selected_chat = st.sidebar.selectbox(
    "💬 Select Chat",
    chat_names,
    index=chat_names.index(app_state["current_chat"])
    if app_state["current_chat"] in chat_names
    else 0
)

app_state["current_chat"] = selected_chat

save_state(app_state)

chat_data = workspace["chats"][selected_chat]

chat_history = chat_data["chat_history"]
query_history = chat_data["query_history"]
active_filters = chat_data["active_filters"]

# ---------------- HEADER ----------------
st.title("AI Analytics Copilot")

st.write(
    f"### Workspace: {selected_workspace}"
)

st.write(
    f"### Current Sheet/View: {selected_sheet}"
)

st.write(
    f"### Chat: {selected_chat}"
)

# ---------------- CONTROLS ----------------
st.sidebar.title("⚙️ Controls")

show_data = st.sidebar.checkbox(
    "📄 Preview Dataset"
)

show_schema = st.sidebar.checkbox(
    "🧠 Show Dataset Schema"
)

show_profile = st.sidebar.checkbox(
    "📊 Data Profile"
)

# ---------------- HISTORY ----------------
st.sidebar.subheader("🕘 Query History")

if query_history:

    for q in reversed(query_history[-10:]):

        st.sidebar.write(f"• {q}")

else:

    st.sidebar.write("No queries yet")

# ---------------- FILTERS ----------------
st.sidebar.subheader("🎯 Active Filters")

if active_filters:

    for k, v in active_filters.items():

        st.sidebar.write(f"{k}: {v}")

else:

    st.sidebar.write("No active filters")

# ---------------- DATA PREVIEW ----------------
if show_data:

    st.subheader("📄 Dataset Preview")

    if data_source == "Databricks":

        st.info(
            "Databricks data is loaded on demand. Use 'show top 10 rows' to preview live rows."
        )

    render_dataframe(
        df.head(50)
    )

# ---------------- PROFILE ----------------
if show_profile:

    st.subheader("📊 Dataset Profile")

    c1, c2, c3 = st.columns(3)

    if data_source == "Databricks":

        c1.metric(
            "Loaded Rows",
            "Schema Only"
        )

    else:

        c1.metric(
            "Loaded Rows",
            df.shape[0]
        )

    c2.metric(
        "Columns",
        df.shape[1]
    )

    c3.metric(
        "Missing Values",
        int(df.isnull().sum().sum())
    )

# ---------------- SHOW SCHEMA ----------------
if show_schema:

    st.subheader("🧠 Dataset Schema")

    st.write("### Numeric Columns")
    st.write(numeric_columns)

    st.write("### Categorical Columns")
    st.write(categorical_columns)

    st.write("### Date Columns")
    st.write(date_columns)

    st.write("### Binary Columns")
    st.write(binary_columns)

# ---------------- HELPERS ----------------
def is_safe_code(code):

    blocked_keywords = [
        "import os",
        "import sys",
        "open(",
        "eval(",
        "__"
    ]

    code_lower = code.lower()

    for keyword in blocked_keywords:

        if keyword in code_lower:

            return False

    return True


def detect_filter_context(question):

    if question is None:

        return {}

    question_lower = str(question).lower()

    filters = {}

    regions = [
        "west",
        "east",
        "south",
        "north",
        "central"
    ]

    for region in regions:

        if region in question_lower:

            filters["Region"] = region

    return filters


def apply_filters(df, active_filters):

    filtered_df = df.copy()

    try:

        for column, value in active_filters.items():

            if column in filtered_df.columns:

                filtered_df = filtered_df[
                    filtered_df[column]
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        str(value).lower(),
                        na=False
                    )
                ]

    except Exception:

        pass

    return filtered_df


def validate_columns(code, columns):

    matches = re.findall(
        r'df\["(.*?)"\]',
        code
    )

    invalid_columns = []

    for col in matches:

        if col not in columns:

            invalid_columns.append(col)

    return list(set(invalid_columns))


def validate_result(result):

    warnings = []

    try:

        if isinstance(result, pd.DataFrame):

            if result.empty:

                warnings.append(
                    "No matching data found."
                )

            for col in result.columns:

                if result[col].dtype == "object":

                    avg_len = (
                        result[col]
                        .astype(str)
                        .str.len()
                        .mean()
                    )

                    if avg_len > 100:

                        warnings.append(
                            f"Possible invalid aggregation detected in column: {col}"
                        )

            total_cells = result.shape[0] * result.shape[1]

            if total_cells > 0:

                null_ratio = (
                    result.isnull().sum().sum()
                ) / total_cells

                if null_ratio > 0.7:

                    warnings.append(
                        "Result contains excessive missing values."
                    )

    except Exception:

        pass

    return warnings


def generate_friendly_error(error, columns):

    error_text = str(error)

    if "KeyError" in error_text or "'" in error_text:

        return f"""
Dataset column issue detected.

Available columns are:

{', '.join(columns)}

Requested field may not exist in dataset.
"""

    return f"Error: {error}"


# ---------------- QUERY ENGINE ----------------
def run_dynamic_query(question):

    if question is None:

        return "Please enter a valid query."

    columns = df.columns.tolist()

    simple_question = str(question).lower().strip()

    intent = detect_intent(question)

    # ---------------- SHOW COLUMNS ----------------
    if simple_question in [
        "show columns",
        "list columns"
    ]:

        return pd.DataFrame(
            {
                "Columns": columns
            }
        )

    # ---------------- DATABRICKS QUERY PLAN ----------------
    if data_source == "Databricks":

        plan = build_databricks_query_plan(
            question=question,
            columns=columns,
            view_name=view_name,
            intent=intent
        )

        print("Chunk Plan:", plan)

        if plan["mode"] == "message":

            return plan["message"]

        if plan["mode"] == "sql":

            return execute_databricks_query(
                plan["sql"]
            )

        if plan["mode"] == "sample":

            return load_databricks_view(
                view_name,
                limit=plan.get("limit", 100),
                selected_columns=plan.get("selected_columns")
            )

    # ---------------- EXCEL / LOCAL QUERIES ----------------
    selected_columns = select_chunk_columns(
        question,
        columns
    )

    if simple_question in [
        "show top 10 rows",
        "top 10 rows",
        "show rows",
        "preview data",
        "show first 10 rows"
    ]:

        return df.head(10)

    if simple_question in [
        "count records",
        "total records",
        "row count"
    ]:

        return pd.DataFrame(
            {
                "Total Records": [len(df)]
            }
        )

    if intent == "unique" and selected_columns:

        return pd.DataFrame(
            {
                f"Unique {selected_columns[0]} Count": [
                    df[selected_columns[0]].nunique()
                ]
            }
        )

    # ---------------- FALLBACK LLM EXECUTION ----------------
    conversation_context = "\n".join(
        [
            f"User: {c['user']}"
            for c in chat_history[-5:]
        ]
    )

    filtered_df = apply_filters(
        df,
        active_filters
    )

    filtered_df = create_query_chunk(
        filtered_df,
        selected_columns
    )

    if selected_columns:

        llm_columns = selected_columns[:15]

    else:

        llm_columns = columns[:20]

    print("Local Chunk Shape:", filtered_df.shape)
    print("LLM Columns:", llm_columns)

    code = generate_pandas_code(
        question,
        llm_columns,
        selected_sheet,
        conversation_context,
        active_filters
    )

    code = code.replace('"M"', '"ME"')
    code = code.replace("'M'", "'ME'")
    code = code.replace('"Y"', '"YE"')
    code = code.replace("'Y'", "'YE'")

    invalid_columns = validate_columns(
        code,
        columns
    )

    if invalid_columns:

        return f"""
Invalid columns detected:

{invalid_columns}

Available columns:

{columns}
"""

    if not is_safe_code(code):

        return "Unsafe query detected."

    local_vars = {
        "df": filtered_df,
        "pd": pd
    }

    try:

        exec(
            code,
            {},
            local_vars
        )

    except Exception as e:

        try:

            retry_prompt = f"""
Fix this pandas code.

CODE:
{code}

ERROR:
{e}

AVAILABLE COLUMNS:
{llm_columns}

Return ONLY corrected pandas code.
"""

            fixed_code = ask_llm(
                retry_prompt,
                ""
            )

            fixed_code = (
                fixed_code
                .replace("```python", "")
                .replace("```", "")
                .strip()
            )

            exec(
                fixed_code,
                {},
                local_vars
            )

        except Exception as retry_error:

            return generate_friendly_error(
                retry_error,
                columns
            )

    result = local_vars.get("result")

    return result

# ---------------- DISPLAY CHAT ----------------
for idx, chat in enumerate(
    chat_history
):

    with st.chat_message("user"):

        st.markdown(chat["user"])

    with st.chat_message("assistant"):

        answer = chat["answer"]

        if isinstance(
            answer,
            pd.DataFrame
        ):

            render_dataframe(
                answer
            )

        else:

            st.write(answer)

        if chat.get("chart") is not None:

            render_chart(
                chat["chart"],
                key=f"chart_{idx}"
            )

        if chat.get("insight"):

            st.info(chat["insight"])


# ---------------- CHAT INPUT ----------------
question = st.chat_input(
    "Ask your analytics question..."
)

if question:

    if (
        "clear filters"
        in str(question).lower()
        or "reset filters"
        in str(question).lower()
    ):

        active_filters.clear()

    new_filters = detect_filter_context(
        question
    )

    if new_filters:

        active_filters.update(
            new_filters
        )

    with st.chat_message("user"):

        st.markdown(question)

    try:

        result = run_dynamic_query(
            question
        )

    except Exception as e:

        error_text = str(e)

        if (
            "Databricks authentication failed" in error_text
            or "403" in error_text
            or "Unauthorized" in error_text
            or "Forbidden" in error_text
        ):

            result = (
                "Databricks authentication failed. "
                "Please check DATABRICKS_TOKEN in the .env file and make sure it is the same valid token/password that worked in DBeaver. "
                "After updating it, restart Streamlit."
            )

        elif (
            "SSL" in error_text
            or "certificate" in error_text
        ):

            result = (
                "Databricks SSL certificate verification failed. "
                "Please check Simba ODBC SSL/certificate settings or corporate network certificate configuration."
            )

        else:

            result = f"Error: {e}"

    insight = None
    fig = None

    with st.chat_message("assistant"):

        if isinstance(
            result,
            pd.DataFrame
        ):

            validation_warnings = validate_result(
                result
            )

            for warning in validation_warnings:

                st.warning(warning)

            render_dataframe(
                result
            )

            if (
                result.shape[1] >= 2
                and len(result) <= 50
            ):

                try:

                    x_col = result.columns[0]
                    y_col = result.columns[1]

                    result[y_col] = pd.to_numeric(
                        result[y_col],
                        errors="coerce"
                    )

                    chart_df = result.dropna()

                    if not chart_df.empty:

                        fig = px.bar(
                            chart_df,
                            x=x_col,
                            y=y_col,
                            color=y_col
                        )

                        render_chart(
                            fig,
                            key=f"current_chart_{len(chat_history)}"
                        )

                except Exception:

                    pass

            try:

                if str(question).lower().strip() in [
                    "show columns",
                    "list columns"
                ]:

                    insight = (
                        f"Dataset contains "
                        f"{len(df.columns)} columns."
                    )

                    st.info(insight)

                elif not result.empty:

                    insight = ask_llm(
                        question,
                        result.head(20).to_string()
                    )

                    st.info(insight)

            except Exception:

                pass

        else:

            st.write(result)

            if not is_error_result(
                result
            ):

                try:

                    insight = ask_llm(
                        question,
                        str(result)
                    )

                    st.info(insight)

                except Exception:

                    pass

    chat_history.append(
        {
            "user": question,
            "answer": result,
            "chart": fig,
            "insight": insight
        }
    )

    query_history.append(
        question
    )

    save_state(
        app_state
    )