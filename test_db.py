from dotenv import load_dotenv
import os
import pyodbc

load_dotenv()

token = os.getenv("DATABRICKS_TOKEN")
host = os.getenv("DATABRICKS_HOST")
http_path = os.getenv("DATABRICKS_HTTP_PATH")

print("Token loaded:", token is not None)
print("Host:", host)
print("HTTP Path:", http_path)

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

conn = pyodbc.connect(
    conn_str,
    autocommit=True,
    timeout=20
)

cursor = conn.cursor()

cursor.execute("""
SELECT COUNT(*) 
FROM gold_tt_dev.gb_dw.upgrade_export_report_view
""")

print(cursor.fetchone())

cursor.close()
conn.close()