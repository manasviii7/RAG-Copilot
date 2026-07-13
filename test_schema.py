from utils.schema_detector import detect_schema
from utils.excel_loader import load_excel

# load excel
sheets = load_excel("data/sample_-_superstore.xlsx")

# select sheet
df = sheets["Orders"]

# detect schema
schema = detect_schema(df)

# print result
print(schema)