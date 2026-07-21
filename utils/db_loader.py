import streamlit as st
import pandas as pd
import os
import time
import re

from dotenv import load_dotenv
from databricks import sql

# ---------------- LOAD ENV ----------------
load_dotenv()


# ---------------- CONNECT DATABRICKS ----------------
def connect_databricks():

    token = os.getenv("DATABRICKS_TOKEN")
    host = os.getenv("DATABRICKS_HOST")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")

    if not token:
        raise Exception("DATABRICKS_TOKEN not found in .env file.")

    if not host:
        raise Exception("DATABRICKS_HOST not found in .env file.")

    if not http_path:
        raise Exception("DATABRICKS_HTTP_PATH not found in .env file.")

    return sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token
    )


# ---------------- VALIDATE VIEW NAME ----------------
def validate_view_name(view_name):

    if not view_name:
        raise ValueError("View name cannot be empty.")

    pattern = r"^[a-zA-Z0-9_`.`]+$"

    if not re.match(pattern, view_name):
        raise ValueError(
            "Invalid view name. Only letters, numbers, underscores, dots and backticks are allowed."
        )

    return view_name


# ---------------- QUOTE IDENTIFIER ----------------
def quote_identifier(column_name):

    safe_column = str(column_name).replace("`", "``")

    return f"`{safe_column}`"


# ---------------- CURSOR TO DATAFRAME ----------------
def cursor_to_dataframe(cursor):

    rows = cursor.fetchall()

    columns = [
        description[0]
        for description in cursor.description
    ]

    df = pd.DataFrame(
        rows,
        columns=columns
    )

    return df


# ---------------- LOAD LOCAL SCHEMA CACHE ----------------
def load_local_schema_cache():

    possible_files = [
        "schema_columns.csv",
        "2026-06-30T08-41_export.csv"
    ]

    for file_name in possible_files:

        if os.path.exists(file_name):

            try:

                schema_df = pd.read_csv(file_name)

                if "Columns" in schema_df.columns:
                    column_series = schema_df["Columns"]
                else:
                    column_series = schema_df.iloc[:, -1]

                columns = (
                    column_series
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .tolist()
                )

                columns = [
                    col
                    for col in columns
                    if col
                    and col.lower() not in [
                        "columns",
                        "col_name",
                        "data_type"
                    ]
                ]

                if columns:
                    print(
                        f"Loaded schema from local file: {file_name} | Columns: {len(columns)}"
                    )
                    return columns

            except Exception as e:
                print(f"Local schema file read failed for {file_name}: {e}")

    return None


# ---------------- SAVE LOCAL SCHEMA CACHE ----------------
def save_local_schema_cache(columns):

    try:

        pd.DataFrame(
            {
                "Columns": columns
            }
        ).to_csv(
            "schema_columns.csv",
            index=False
        )

        print(f"Saved schema_columns.csv | Columns: {len(columns)}")

    except Exception as e:
        print(f"Could not save schema cache: {e}")


# ---------------- EXECUTE DATABRICKS QUERY ----------------
@st.cache_data(ttl=900)
def execute_databricks_query(query):

    connection = None
    cursor = None

    try:

        start = time.time()

        connection = connect_databricks()

        cursor = connection.cursor()

        cursor.execute(query)

        df = cursor_to_dataframe(cursor)

        elapsed = round(time.time() - start, 2)

        print(
            f"Databricks query completed in {elapsed}s | Rows: {df.shape[0]} | Columns: {df.shape[1]}"
        )

        return df

    except Exception as e:

        print(f"Databricks query error: {e}")

        raise

    finally:

        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


# ---------------- GET COLUMNS ONLY ----------------
@st.cache_data(ttl=1800)
def get_databricks_columns(view_name):

    local_columns = load_local_schema_cache()

    if local_columns:
        return local_columns

    connection = None
    cursor = None

    try:

        view_name = validate_view_name(view_name)

        start = time.time()

        connection = connect_databricks()

        cursor = connection.cursor()

        cursor.execute(f"""
        DESCRIBE TABLE {view_name}
        """)

        rows = cursor.fetchall()

        columns = []

        for row in rows:

            col_name = row[0]

            if (
                col_name
                and not str(col_name).startswith("#")
                and str(col_name).strip() != ""
            ):
                columns.append(str(col_name))

        elapsed = round(time.time() - start, 2)

        print(
            f"Loaded Databricks schema in {elapsed}s | Columns: {len(columns)}"
        )

        if columns:
            save_local_schema_cache(columns)

        return columns

    except Exception as e:

        print(f"Databricks schema load error: {e}")

        raise Exception(f"Unable to load Databricks schema: {e}")

    finally:

        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


# ---------------- LOAD SAMPLE VIEW ONLY WHEN NEEDED ----------------
@st.cache_data(ttl=1800)
def load_databricks_view(
    view_name,
    limit=50,
    selected_columns=None
):

    connection = None
    cursor = None

    try:

        view_name = validate_view_name(view_name)

        try:
            limit = int(limit)
        except Exception:
            limit = 50

        limit = max(1, min(limit, 1000))

        if selected_columns:

            safe_columns = ", ".join(
                [
                    quote_identifier(col)
                    for col in selected_columns
                ]
            )

        else:

            safe_columns = "*"

        query = f"""
        SELECT {safe_columns}
        FROM {view_name}
        LIMIT {limit}
        """

        start = time.time()

        connection = connect_databricks()

        cursor = connection.cursor()

        cursor.execute(query)

        df = cursor_to_dataframe(cursor)

        elapsed = round(time.time() - start, 2)

        print(
            f"Databricks sample loaded in {elapsed}s | Rows: {df.shape[0]} | Columns: {df.shape[1]}"
        )

        return df

    except Exception as e:

        print(f"Databricks sample load error: {e}")

        raise

    finally:

        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass