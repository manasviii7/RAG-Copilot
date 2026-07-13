from utils.db_loader import (
    load_databricks_view
)

df = load_databricks_view(
    "gold_tt_dev.gb_dw.upgrade_export_report_view"
)

print(df.head())