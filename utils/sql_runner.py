try:

    from pandasql import sqldf

except Exception:

    sqldf = None


def run_sqldf_query(
    sql_query,
    df
):

    if sqldf is None:

        raise Exception(
            "pandasql is not installed. Run: pip install pandasql"
        )

    return sqldf(
        sql_query,
        {
            "df": df
        }
    )