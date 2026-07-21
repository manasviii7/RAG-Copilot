from dotenv import load_dotenv
import os
import time
from databricks import sql

load_dotenv()

token = os.getenv("DATABRICKS_TOKEN")
host = os.getenv("DATABRICKS_HOST")
http_path = os.getenv("DATABRICKS_HTTP_PATH")

view_name = "gold_tt_prod.gb_dw.upgrade_export_report_view"

print("Token loaded:", token is not None)
print("Host:", host)
print("HTTP Path:", http_path)
print("View:", view_name)

with sql.connect(
    server_hostname=host,
    http_path=http_path,
    access_token=token
) as connection:

    print("\nConnected successfully.")

    with connection.cursor() as cursor:

        print("\n1. Testing simple query...")
        start = time.time()
        cursor.execute("SELECT 1 AS test_value")
        print("Result:", cursor.fetchall())
        print("Time:", round(time.time() - start, 2), "seconds")

        print("\n2. Testing current catalog/schema...")
        start = time.time()
        cursor.execute("SELECT current_catalog(), current_schema()")
        print("Result:", cursor.fetchall())
        print("Time:", round(time.time() - start, 2), "seconds")

        print("\n3. Testing schema only using DESCRIBE TABLE...")
        start = time.time()
        cursor.execute(f"DESCRIBE TABLE {view_name}")
        rows = cursor.fetchmany(10)
        print("DESCRIBE successful.")
        print("First 10 columns:")
        for row in rows:
            print(row)
        print("Time:", round(time.time() - start, 2), "seconds")

        print("\n4. Testing zero-row query...")
        start = time.time()
        cursor.execute(f"""
            SELECT `Project Number`
            FROM {view_name}
            WHERE 1 = 0
        """)
        print("Zero-row query successful.")
        print("Rows:", cursor.fetchall())
        print("Time:", round(time.time() - start, 2), "seconds")

        print("\n5. Testing one-row query...")
        start = time.time()
        cursor.execute(f"""
            SELECT `Project Number`
            FROM {view_name}
            LIMIT 1
        """)
        print("One-row query successful.")
        print("Rows:", cursor.fetchall())
        print("Time:", round(time.time() - start, 2), "seconds")

print("\nDone.")