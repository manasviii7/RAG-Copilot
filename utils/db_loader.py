import streamlit as st
import pyodbc
import pandas as pd
import time
import re
import os

from dotenv import load_dotenv

# ---------------- LOAD ENV ----------------
load_dotenv()


# ---------------- CONNECT DATABRICKS ----------------
def connect_databricks():

    token = os.getenv("DATABRICKS_TOKEN")
    host = os.getenv("DATABRICKS_HOST")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")

    if not token:

        raise Exception(
            "DATABRICKS_TOKEN not found in .env file."
        )

    if not host:

        raise Exception(
            "DATABRICKS_HOST not found in .env file."
        )

    if not http_path:

        raise Exception(
            "DATABRICKS_HTTP_PATH not found in .env file."
        )

    conn_str = (
        "DRIVER={Simba Spark ODBC Driver};"
        f"HOST={host};"
        "PORT=443;"
        f"HTTPPath={http_path};"
        "AuthMech=3;"
        "UID=token;"
        f"PWD={token};"
        "SSL=1;"
        "ThriftTransport=2;"
        "SparkServerType=3;"
        "AllowSelfSignedServerCert=1;"
        "AllowHostNameCNMismatch=1;"
        "CAIssuedCertNamesMismatch=1;"
        "CheckCertRevocation=0;"
        "UseSystemTrustStore=1;"
    )

    try:

        return pyodbc.connect(
            conn_str,
            autocommit=True,
            timeout=20
        )

    except pyodbc.Error as e:

        error_text = str(e)

        if (
            "403" in error_text
            or "Unauthorized" in error_text
            or "Forbidden" in error_text
        ):

            raise Exception(
                "Databricks authentication failed. Please check DATABRICKS_TOKEN in .env file and make sure it is the same valid token/password that worked in DBeaver."
            )

        if (
            "SSL_connect" in error_text
            or "certificate verify failed" in error_text
        ):

            raise Exception(
                "Databricks SSL certificate verification failed. Please check Simba ODBC SSL/certificate settings or corporate network certificate configuration."
            )

        raise


# ---------------- VALIDATE VIEW NAME ----------------
def validate_view_name(view_name):

    if not view_name:

        raise ValueError(
            "View name cannot be empty."
        )

    pattern = r"^[a-zA-Z0-9_`.`]+$"

    if not re.match(
        pattern,
        view_name
    ):

        raise ValueError(
            "Invalid view name. Only letters, numbers, underscores, dots and backticks are allowed."
        )

    return view_name


# ---------------- QUOTE IDENTIFIER ----------------
def quote_identifier(column_name):

    safe_column = (
        str(column_name)
        .replace("`", "``")
    )

    return f"`{safe_column}`"


# ---------------- CURSOR TO DATAFRAME ----------------
def cursor_to_dataframe(cursor):

    rows = cursor.fetchall()

    columns = [
        desc[0]
        for desc in cursor.description
    ]

    df = pd.DataFrame.from_records(
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

                schema_df = pd.read_csv(
                    file_name
                )

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

                print(
                    f"Local schema file read failed for {file_name}: {e}"
                )

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

        print(
            f"Saved schema_columns.csv | Columns: {len(columns)}"
        )

    except Exception as e:

        print(
            f"Could not save schema cache: {e}"
        )


# ---------------- EXECUTE DATABRICKS QUERY ----------------
@st.cache_data(ttl=900)
def execute_databricks_query(query):

    conn = None
    cursor = None

    try:

        conn = connect_databricks()

        start = time.time()

        cursor = conn.cursor()

        try:

            cursor.timeout = 60

        except Exception:

            pass

        cursor.execute(query)

        df = cursor_to_dataframe(
            cursor
        )

        elapsed = round(
            time.time() - start,
            2
        )

        print(
            f"Databricks query completed in {elapsed}s | Rows: {df.shape[0]} | Columns: {df.shape[1]}"
        )

        return df

    except Exception as e:

        print(
            f"Databricks query error: {e}"
        )

        raise

    finally:

        if cursor is not None:

            try:

                cursor.close()

            except Exception:

                pass

        if conn is not None:

            try:

                conn.close()

            except Exception:

                pass


# ---------------- GET COLUMNS ONLY ----------------
@st.cache_data(ttl=1800)
def get_databricks_columns(view_name):

    local_columns = load_local_schema_cache()

    if local_columns:

        return local_columns

    conn = None
    cursor = None

    try:

        view_name = validate_view_name(
            view_name
        )

        conn = connect_databricks()

        schema_queries = [
            f"SHOW COLUMNS IN {view_name}",
            f"DESCRIBE TABLE {view_name}",
            f"SELECT * FROM {view_name} LIMIT 0"
        ]

        for query in schema_queries:

            try:

                print(
                    f"Trying schema query: {query.strip()[:80]}"
                )

                start = time.time()

                cursor = conn.cursor()

                try:

                    cursor.timeout = 30

                except Exception:

                    pass

                cursor.execute(query)

                if query.strip().lower().startswith("select"):

                    columns = [
                        desc[0]
                        for desc in cursor.description
                    ]

                else:

                    rows = cursor.fetchall()

                    columns = []

                    for row in rows:

                        col_name = row[0]

                        if (
                            col_name
                            and not str(col_name).startswith("#")
                            and str(col_name).strip() != ""
                        ):

                            columns.append(
                                str(col_name)
                            )

                elapsed = round(
                    time.time() - start,
                    2
                )

                if columns:

                    print(
                        f"Loaded Databricks schema in {elapsed}s | Columns: {len(columns)}"
                    )

                    save_local_schema_cache(
                        columns
                    )

                    return columns

            except Exception as e:

                print(
                    f"Schema query failed: {e}"
                )

                try:

                    if cursor is not None:

                        cursor.close()

                except Exception:

                    pass

                continue

        raise Exception(
            "All schema loading methods failed."
        )

    except Exception as final_error:

        raise Exception(
            f"Unable to load Databricks schema: {final_error}"
        )

    finally:

        if cursor is not None:

            try:

                cursor.close()

            except Exception:

                pass

        if conn is not None:

            try:

                conn.close()

            except Exception:

                pass


# ---------------- LOAD SAMPLE VIEW ONLY WHEN NEEDED ----------------
@st.cache_data(ttl=1800)
def load_databricks_view(
    view_name,
    limit=50,
    selected_columns=None
):

    conn = None
    cursor = None

    try:

        view_name = validate_view_name(
            view_name
        )

        try:

            limit = int(limit)

        except Exception:

            limit = 50

        limit = max(
            1,
            min(
                limit,
                1000
            )
        )

        conn = connect_databricks()

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

        cursor = conn.cursor()

        try:

            cursor.timeout = 60

        except Exception:

            pass

        cursor.execute(query)

        df = cursor_to_dataframe(
            cursor
        )

        elapsed = round(
            time.time() - start,
            2
        )

        print(
            f"Databricks sample loaded in {elapsed}s | Rows: {df.shape[0]} | Columns: {df.shape[1]}"
        )

        return df

    except Exception as e:

        print(
            f"Databricks sample load error: {e}"
        )

        raise

    finally:

        if cursor is not None:

            try:

                cursor.close()

            except Exception:

                pass

        if conn is not None:

            try:

                conn.close()

            except Exception:

                pass