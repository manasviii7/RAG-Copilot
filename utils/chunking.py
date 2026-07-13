# utils/chunking.py

import re


# ---------------- NORMALIZE TEXT ----------------
def normalize_text(text):

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return text.strip()


# ---------------- SAFE SQL VALUE ----------------
def safe_sql_value(value):

    return (
        str(value)
        .replace("'", "''")
        .strip()
    )


# ---------------- QUOTE IDENTIFIER ----------------
def quote_sql_identifier(column_name):

    safe_column = (
        str(column_name)
        .replace("`", "``")
    )

    return f"`{safe_column}`"


# ---------------- EXTRACT LIMIT ----------------
def extract_limit_from_question(
    question,
    default_limit=10,
    max_limit=500
):

    numbers = re.findall(
        r"\d+",
        str(question)
    )

    if numbers:

        try:

            return min(
                int(numbers[0]),
                max_limit
            )

        except Exception:

            return default_limit

    return default_limit


# ---------------- RESOLVE COLUMN ----------------
def resolve_column_from_question(
    question,
    columns
):

    if not columns:

        return None

    q = normalize_text(question)

    normalized_columns = {
        normalize_text(col): col
        for col in columns
    }

    # 1. Exact full column match
    for normalized_col, original_col in normalized_columns.items():

        if normalized_col in q:

            return original_col

    # 2. Handle "by column" pattern
    if " by " in f" {q} ":

        after_by = q.split(" by ", 1)[1].strip()

        for normalized_col, original_col in normalized_columns.items():

            if (
                after_by in normalized_col
                or normalized_col in after_by
            ):

                return original_col

    # 3. Semantic mapping
    semantic_map = {
        "project": [
            "Project Number",
            "Project Name",
            "Project Status",
            "Project Type",
            "Project Internal Status"
        ],
        "workflow": [
            "Workflow Type"
        ],
        "build": [
            "Build Entity"
        ],
        "vendor": [
            "Build Entity"
        ],
        "customer": [
            "Customer",
            "Customer ID",
            "Customer Type (Anchor/Colo)"
        ],
        "circle": [
            "Circle",
            "Circle As Per Customer"
        ],
        "region": [
            "Region"
        ],
        "state": [
            "State"
        ],
        "city": [
            "City"
        ],
        "district": [
            "District"
        ],
        "status": [
            "Project Status",
            "Site Status",
            "Milestone Status",
            "Primary Milestone Status",
            "Tenancy Milestone Status"
        ],
        "milestone": [
            "Milestone Status",
            "Primary Milestone Status",
            "Tenancy Milestone Status"
        ],
        "sap": [
            "SAP ID"
        ],
        "tenancy": [
            "Tenancy ID"
        ],
        "tenant": [
            "Tenancy ID",
            "Customer",
            "Customer ID"
        ],
        "site": [
            "Global Site ID",
            "ATC Site ID",
            "Site Name",
            "Site Status"
        ],
        "tower": [
            "Tower Type",
            "Tower Sub Type",
            "Tower height (m)"
        ],
        "technology": [
            "Network Technology",
            "BTS Technology",
            "Overall Network Technology"
        ],
        "cancellation": [
            "Cancellation Status",
            "Cancellation Type",
            "Cancellation Date"
        ],
        "termination": [
            "TERMINATION REASON",
            "TERMINATION DATE",
            "Termination Project Current Status"
        ],
        "dg": [
            "DG Required",
            "DG Feasible",
            "DG_KVA",
            "DG Removal Cost"
        ],
        "fiber": [
            "Fiber Product",
            "Fiber Product Type",
            "Fiber Cost",
            "Fiber Distance in Meters"
        ],
        "battery": [
            "Battery Type",
            "Additional Battery Required",
            "Additional Battery Backup Hours"
        ],
        "capex": [
            "Capex Amount in INR",
            "Capex Cost to be Recovered (INR)"
        ],
        "opex": [
            "Other Opex Amount in INR",
            "Security Guard Opex Amount in INR"
        ],
        "rent": [
            "Land Rent per Month",
            "Additional Landlord Rental"
        ],
        "height": [
            "Tower height (m)",
            "Customer Requested Tower Height (Mtrs)"
        ],
        "cost": [
            "Capex Amount in INR",
            "Fiber Cost",
            "DG Removal Cost",
            "Actual cost for Raised Platform",
            "Estimated cost for Raised Platform",
            "Total Electrification/EB Connection Cost (INR)"
        ]
    }

    for keyword, possible_columns in semantic_map.items():

        if keyword in q:

            for possible_col in possible_columns:

                if possible_col in columns:

                    return possible_col

    # 4. Token overlap fallback
    q_tokens = set(
        normalize_text(question).split()
    )

    best_col = None
    best_score = 0

    for col in columns:

        col_tokens = set(
            normalize_text(col).split()
        )

        overlap = q_tokens.intersection(
            col_tokens
        )

        score = len(overlap)

        if score > best_score:

            best_score = score
            best_col = col

    if best_score > 0:

        return best_col

    return None


# ---------------- SELECT MULTIPLE RELEVANT COLUMNS ----------------
def select_chunk_columns(
    question,
    columns,
    max_columns=10
):

    if not columns:

        return []

    q = normalize_text(question)

    selected = []

    primary_column = resolve_column_from_question(
        question,
        columns
    )

    if primary_column:

        selected.append(primary_column)

    q_tokens = set(q.split())

    for col in columns:

        if col in selected:

            continue

        col_norm = normalize_text(col)

        col_tokens = set(col_norm.split())

        overlap = q_tokens.intersection(
            col_tokens
        )

        if overlap:

            selected.append(col)

        if len(selected) >= max_columns:

            break

    return selected[:max_columns]


# ---------------- CHECK NUMERIC-LIKE COLUMN ----------------
def is_probably_numeric_column(column_name):

    col = str(column_name).lower()

    numeric_terms = [
        "amount",
        "cost",
        "kva",
        "height",
        "rent",
        "load",
        "power",
        "weight",
        "distance",
        "space",
        "capacity",
        "tenure",
        "hours",
        "rate",
        "charge",
        "charges",
        "area",
        "length",
        "width",
        "depth",
        "count",
        "total",
        "no of",
        "number of"
    ]

    negative_terms = [
        "id",
        "name",
        "status",
        "type",
        "customer",
        "entity",
        "circle",
        "region",
        "state",
        "city",
        "district",
        "address",
        "remarks",
        "reason",
        "date"
    ]

    has_numeric_term = any(
        term in col
        for term in numeric_terms
    )

    has_negative_term = any(
        term in col
        for term in negative_terms
    )

    if has_numeric_term:

        return True

    if has_negative_term:

        return False

    return False


# ---------------- PARSE CONTAINS FILTER ----------------
def parse_contains_filter(
    question,
    columns
):

    q = str(question).lower().strip()

    if " contains " not in q:

        return None, None

    before_contains, value = q.split(
        " contains ",
        1
    )

    value = value.strip()

    before_contains = (
        before_contains
        .replace("show records where", "")
        .replace("show rows where", "")
        .replace("records where", "")
        .replace("rows where", "")
        .replace("where", "")
        .strip()
    )

    column = resolve_column_from_question(
        before_contains,
        columns
    )

    return column, value


# ---------------- BUILD SQL PLAN ----------------
def build_databricks_query_plan(
    question,
    columns,
    view_name,
    intent
):

    q = str(question).lower().strip()

    limit = extract_limit_from_question(
        question,
        default_limit=10
    )

    selected_columns = select_chunk_columns(
        question,
        columns
    )

    resolved_column = resolve_column_from_question(
        question,
        columns
    )

    if (
        resolved_column
        and resolved_column not in selected_columns
    ):

        selected_columns.insert(
            0,
            resolved_column
        )

    # Count entire view can work even without schema
    if q in [
        "count records",
        "total records",
        "row count"
    ]:

        return {
            "mode": "sql",
            "operation": "count_records",
            "sql": f"""
                SELECT COUNT(*) AS `Total Records`
                FROM {view_name}
            """,
            "selected_columns": [],
            "requires_schema": False
        }

    # If no schema loaded and not count, stop safely
    if not columns:

        return {
            "mode": "message",
            "operation": "schema_required",
            "message": (
                "Please click 'Load / Refresh Databricks Schema' first, "
                "then ask this question again."
            ),
            "selected_columns": [],
            "requires_schema": True
        }

    # Preview
    if q in [
        "show top 10 rows",
        "top 10 rows",
        "show rows",
        "preview data",
        "show first 10 rows"
    ]:

        return {
            "mode": "sample",
            "operation": "preview",
            "limit": 10,
            "selected_columns": None,
            "requires_schema": True
        }

    # Contains filter
    if " contains " in q:

        filter_col, filter_value = parse_contains_filter(
            question,
            columns
        )

        if filter_col and filter_value:

            safe_value = safe_sql_value(
                filter_value
            )

            return {
                "mode": "sql",
                "operation": "contains_filter",
                "sql": f"""
                    SELECT *
                    FROM {view_name}
                    WHERE LOWER(CAST({quote_sql_identifier(filter_col)} AS STRING))
                    LIKE '%{safe_value.lower()}%'
                    LIMIT 100
                """,
                "selected_columns": [filter_col],
                "requires_schema": True
            }

        return {
            "mode": "message",
            "operation": "filter_column_not_found",
            "message": (
                "I could not identify the column for this filter query. "
                "Please use exact column name, for example: "
                "'show records where Customer contains airtel'."
            ),
            "selected_columns": [],
            "requires_schema": True
        }

    # Missing/null
    if (
        "missing" in q
        or "null" in q
        or "blank" in q
    ):

        if selected_columns:

            col = selected_columns[0]

            return {
                "mode": "sql",
                "operation": "missing_count",
                "sql": f"""
                    SELECT COUNT(*) AS `Missing {col} Count`
                    FROM {view_name}
                    WHERE {quote_sql_identifier(col)} IS NULL
                """,
                "selected_columns": [col],
                "requires_schema": True
            }

    # Unique/distinct
    if (
        "unique" in q
        or "distinct" in q
        or intent == "unique"
    ):

        if selected_columns:

            col = selected_columns[0]

            return {
                "mode": "sql",
                "operation": "unique_count",
                "sql": f"""
                    SELECT COUNT(DISTINCT {quote_sql_identifier(col)}) AS `Unique {col} Count`
                    FROM {view_name}
                """,
                "selected_columns": [col],
                "requires_schema": True
            }

    # Count/group by
    if (
        " by " in q
        or "wise" in q
        or "group by" in q
    ):

        if selected_columns:

            col = selected_columns[0]

            return {
                "mode": "sql",
                "operation": "group_count",
                "sql": f"""
                    SELECT
                        {quote_sql_identifier(col)} AS `{col}`,
                        COUNT(*) AS `Count`
                    FROM {view_name}
                    GROUP BY {quote_sql_identifier(col)}
                    ORDER BY `Count` DESC
                    LIMIT 50
                """,
                "selected_columns": [col],
                "requires_schema": True
            }

    # Numeric aggregation
    numeric_words = [
        "total",
        "sum",
        "average",
        "avg",
        "highest",
        "maximum",
        "max",
        "lowest",
        "minimum",
        "min"
    ]

    if any(
        word in q
        for word in numeric_words
    ):

        numeric_col = (
            resolved_column
            or (
                selected_columns[0]
                if selected_columns
                else None
            )
        )

        if (
            numeric_col
            and is_probably_numeric_column(numeric_col)
        ):

            aggregation = "sum"

            if (
                "average" in q
                or "avg" in q
            ):

                aggregation = "avg"

            elif (
                "highest" in q
                or "maximum" in q
                or "max" in q
            ):

                aggregation = "max"

            elif (
                "lowest" in q
                or "minimum" in q
                or "min" in q
            ):

                aggregation = "min"

            return {
                "mode": "sql",
                "operation": "numeric_aggregation",
                "sql": f"""
                    SELECT
                        {aggregation.upper()}(
                            CAST({quote_sql_identifier(numeric_col)} AS DOUBLE)
                        ) AS `{aggregation.title()} {numeric_col}`
                    FROM {view_name}
                """,
                "selected_columns": [numeric_col],
                "requires_schema": True
            }

    # Ranking/top/chart
    if (
        intent in [
            "ranking",
            "visualization",
            "count"
        ]
        or "top" in q
        or "highest" in q
        or "most" in q
    ):

        if selected_columns:

            col = selected_columns[0]

            return {
                "mode": "sql",
                "operation": "top_count",
                "sql": f"""
                    SELECT
                        {quote_sql_identifier(col)} AS `{col}`,
                        COUNT(*) AS `Count`
                    FROM {view_name}
                    GROUP BY {quote_sql_identifier(col)}
                    ORDER BY `Count` DESC
                    LIMIT {limit}
                """,
                "selected_columns": [col],
                "requires_schema": True
            }

    # Fallback sample
    if selected_columns:

        return {
            "mode": "sample",
            "operation": "fallback_sample",
            "limit": 300,
            "selected_columns": selected_columns[:10],
            "requires_schema": True
        }

    return {
        "mode": "message",
        "operation": "no_column_found",
        "message": (
            "I could not identify the relevant column for this query. "
            "Please use the exact column name, for example: "
            "'project count by Workflow Type' or 'top Build Entity'."
        ),
        "selected_columns": [],
        "requires_schema": True
    }


# ---------------- LOCAL CHUNKING FOR EXCEL ----------------
def create_query_chunk(
    df,
    selected_columns,
    max_rows=1000
):

    if selected_columns:

        valid_columns = [
            col
            for col in selected_columns
            if col in df.columns
        ]

        if valid_columns:

            return (
                df[valid_columns]
                .head(max_rows)
                .copy()
            )

    return df.head(max_rows).copy()