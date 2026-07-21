from dotenv import load_dotenv
import os
import pyodbc
import time

# ---------------- LOAD ENV ----------------
load_dotenv()

# ---------------- CONFIG ----------------
token = os.getenv("DATABRICKS_TOKEN")
host = os.getenv("DATABRICKS_HOST")
http_path = os.getenv("DATABRICKS_HTTP_PATH")

view_name = "gold_tt_prod.gb_dw.upgrade_export_report_view"

print("Token loaded:", token is not None)
print("Host:", host)
print("HTTP Path:", http_path)
print("View:", view_name)

if not token:
    raise Exception("DATABRICKS_TOKEN not found in .env")

if not host:
    raise Exception("DATABRICKS_HOST not found in .env")

if not http_path:
    raise Exception("DATABRICKS_HTTP_PATH not found in .env")

# ---------------- CONNECTION STRING ----------------
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

conn = None
cursor = None

try:
    print("\nConnecting to Databricks...")

    start = time.time()

    conn = pyodbc.connect(
        conn_str,
        autocommit=True,
        timeout=30
    )

    print("Connected successfully.")
    print("Connection time:", round(time.time() - start, 2), "seconds")

    cursor = conn.cursor()

    try:
        cursor.timeout = 60
    except Exception:
        pass

    # ---------------- SIMPLE QUERY TEST ----------------
    print("\nTesting simple query...")

    cursor.execute("SELECT 1 AS test_value")

    simple_result = cursor.fetchone()

    print("Simple query result:", simple_result)

    # ---------------- SCHEMA TEST ----------------
    print("\nTesting schema query...")

    schema_start = time.time()

    cursor.execute(f"""
    DESCRIBE TABLE {view_name}
    """)

    schema_rows = cursor.fetchmany(10)

    print("Schema query successful.")
    print("Schema time:", round(time.time() - schema_start, 2), "seconds")
    print("First 10 schema rows:")

    for row in schema_rows:
        print(row)

    # ---------------- LIGHTWEIGHT VIEW QUERY ----------------
    print("\nTesting lightweight view query...")

    view_start = time.time()

    cursor.execute(f"""
    SELECT
        `Project Number`,
        `Tenancy ID`,
        `Global Site ID`,
        `Customer`,
        `Build Entity`
    FROM {view_name}
    LIMIT 5
    """)

    rows = cursor.fetchall()

    print("View query successful.")
    print("View query time:", round(time.time() - view_start, 2), "seconds")
    print("Rows fetched:", len(rows))

    for row in rows:
        print(row)

    print("\nAll tests completed successfully.")

except Exception as e:
    print("\nERROR OCCURRED:")
    print(e)

finally:
    if cursor is not None:
        try:
            cursor.close()
        except Exception:
            pass

    if conn is not None:
        try:
            conn.close()
            print("\nConnection closed.")
        except Exception:
            pass