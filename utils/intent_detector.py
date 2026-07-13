def detect_intent(question):

    if question is None:

        return "general"

    q = str(question).lower()

    if any(
        word in q
        for word in [
            "chart",
            "graph",
            "plot",
            "visualize",
            "visualisation",
            "visualization"
        ]
    ):

        return "visualization"

    if any(
        word in q
        for word in [
            "count",
            "how many",
            "total",
            "number of"
        ]
    ):

        return "count"

    if any(
        word in q
        for word in [
            "top",
            "highest",
            "most",
            "maximum",
            "max"
        ]
    ):

        return "ranking"

    if any(
        word in q
        for word in [
            "bottom",
            "lowest",
            "least",
            "minimum",
            "min"
        ]
    ):

        return "bottom"

    if any(
        word in q
        for word in [
            "trend",
            "monthly",
            "yearly",
            "weekly",
            "daily",
            "over time"
        ]
    ):

        return "trend"

    if any(
        word in q
        for word in [
            "compare",
            "comparison",
            "versus",
            "vs"
        ]
    ):

        return "comparison"

    if any(
        word in q
        for word in [
            "missing",
            "null",
            "blank",
            "empty"
        ]
    ):

        return "missing"

    if any(
        word in q
        for word in [
            "unique",
            "distinct"
        ]
    ):

        return "unique"

    return "general"