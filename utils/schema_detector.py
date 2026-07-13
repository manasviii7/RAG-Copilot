import pandas as pd

# ---------------- SCHEMA DETECTOR ----------------
def detect_schema(df):

    numeric_columns = []
    categorical_columns = []
    date_columns = []
    binary_columns = []

    for col in df.columns:

        try:

            # ✅ numeric detection
            if pd.api.types.is_numeric_dtype(
                df[col]
            ):

                numeric_columns.append(col)

            # ✅ datetime detection
            elif pd.api.types.is_datetime64_any_dtype(
                df[col]
            ):

                date_columns.append(col)

            else:

                categorical_columns.append(col)

                # ✅ binary detection
                unique_values = (
                    df[col]
                    .dropna()
                    .astype(str)
                    .str.lower()
                    .str.strip()
                    .unique()
                )

                binary_set = {
                    "yes",
                    "no",
                    "true",
                    "false",
                    "male",
                    "female",
                    "y",
                    "n"
                }

                if (
                    len(unique_values) <= 2
                    and set(unique_values).issubset(binary_set)
                ):

                    binary_columns.append(col)

        except:

            categorical_columns.append(col)

    return {
        "numeric": numeric_columns,
        "categorical": categorical_columns,
        "date": date_columns,
        "binary": binary_columns
    }
# ---------------- COLUMN PROFILE ----------------
# ---------------- COLUMN PROFILE ----------------
def profile_columns(df):

    profiles = {}

    for col in df.columns:

        try:

            profiles[col] = {

                "dtype": str(df[col].dtype),

                "null_count":
                int(df[col].isnull().sum()),

                "unique_count":
                int(df[col].nunique()),

                "sample_values":
                df[col]
                .dropna()
                .astype(str)
                .head(3)
                .tolist()
            }

        except:

            profiles[col] = {
                "dtype": "unknown"
            }

    return profiles