import re
from difflib import SequenceMatcher


# ---------------- NORMALIZE TEXT ----------------
def normalize_text(text):

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return text.strip()


# ---------------- SIMILARITY SCORE ----------------
def similarity_score(a, b):

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ---------------- GENERIC BUSINESS SYNONYMS ----------------
GENERIC_SYNONYMS = {
    "project": [
        "project",
        "project number",
        "project id",
        "project no"
    ],

    "site": [
        "site",
        "site id",
        "global site",
        "global site id",
        "location"
    ],

    "tenant": [
        "tenant",
        "tenancy",
        "tenancy id",
        "customer"
    ],

    "vendor": [
        "vendor",
        "build entity",
        "contractor",
        "partner",
        "supplier"
    ],

    "sap": [
        "sap",
        "sap id",
        "erp",
        "erp id"
    ],

    "region": [
        "region",
        "zone",
        "area"
    ],

    "circle": [
        "circle",
        "telecom circle",
        "market"
    ],

    "status": [
        "status",
        "stage",
        "state",
        "progress"
    ],

    "date": [
        "date",
        "created date",
        "updated date",
        "start date",
        "end date",
        "month",
        "year"
    ],

    "amount": [
        "amount",
        "cost",
        "price",
        "revenue",
        "value",
        "charge"
    ],

    "count": [
        "count",
        "number",
        "total",
        "quantity"
    ]
}


# ---------------- EXPAND QUESTION TERMS ----------------
def expand_question_terms(question):

    question_norm = normalize_text(
        question
    )

    tokens = set(
        token
        for token in question_norm.split()
        if len(token) > 2
    )

    expanded_terms = set(tokens)

    for key, synonyms in GENERIC_SYNONYMS.items():

        for synonym in synonyms:

            synonym_norm = normalize_text(
                synonym
            )

            if (
                key in tokens
                or synonym_norm in question_norm
                or any(
                    token in synonym_norm
                    for token in tokens
                )
            ):

                expanded_terms.update(
                    normalize_text(s).strip()
                    for s in synonyms
                )

                expanded_terms.add(key)

    return expanded_terms


# ---------------- SELECT RELEVANT COLUMNS ----------------
def select_relevant_columns(
    question,
    columns,
    max_columns=15
):

    if question is None:

        return []

    question_norm = normalize_text(
        question
    )

    expanded_terms = expand_question_terms(
        question
    )

    stopwords = {
        "show",
        "give",
        "tell",
        "what",
        "which",
        "where",
        "when",
        "how",
        "many",
        "count",
        "total",
        "top",
        "highest",
        "lowest",
        "least",
        "most",
        "chart",
        "graph",
        "plot",
        "records",
        "rows",
        "data",
        "value",
        "values",
        "wise",
        "list",
        "all",
        "by",
        "of",
        "for",
        "from",
        "with",
        "and"
    }

    expanded_terms = {
        term
        for term in expanded_terms
        if term not in stopwords
        and len(term) > 1
    }

    scored_columns = []

    for col in columns:

        col_norm = normalize_text(
            col
        )

        col_tokens = set(
            token
            for token in col_norm.split()
            if len(token) > 1
        )

        score = 0

        # Exact full column match
        if col_norm in question_norm:

            score += 100

        # Direct token overlap
        for term in expanded_terms:

            term_norm = normalize_text(
                term
            )

            if not term_norm:

                continue

            if term_norm == col_norm:

                score += 80

            elif term_norm in col_norm:

                score += 30

            elif col_norm in term_norm:

                score += 25

            else:

                for col_token in col_tokens:

                    if term_norm == col_token:

                        score += 20

                    elif term_norm in col_token:

                        score += 8

                    elif similarity_score(
                        term_norm,
                        col_token
                    ) > 0.82:

                        score += 6

        # Column token overlap with question tokens
        question_tokens = set(
            question_norm.split()
        )

        overlap = question_tokens.intersection(
            col_tokens
        )

        score += len(overlap) * 15

        if score > 0:

            scored_columns.append(
                (
                    score,
                    col
                )
            )

    scored_columns = sorted(
        scored_columns,
        key=lambda x: x[0],
        reverse=True
    )

    selected_columns = []

    for score, col in scored_columns:

        if col not in selected_columns:

            selected_columns.append(col)

        if len(selected_columns) >= max_columns:

            break

    return selected_columns