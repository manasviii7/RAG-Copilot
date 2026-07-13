import pandas as pd

def load_excel(file_path):
    xls = pd.ExcelFile(file_path)
    sheets = {sheet: xls.parse(sheet) for sheet in xls.sheet_names}
    return sheets
