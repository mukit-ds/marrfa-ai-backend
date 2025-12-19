# backend/app/property_search.py
from typing import Dict, List, Any
from .schemas import Property
from .parser import parse_query_to_filters
from .marrfa_client import search_properties


def handle_property_query(query_text: str) -> Dict[str, Any]:
    """
    Handle property search queries.

    Returns:
        Dict with keys:
        - reply: Response message
        - properties: List of Property objects
        - total: Total number of properties
        - filters: Filters used for the search
    """
    filters = parse_query_to_filters(query_text)
    filters.setdefault("search_query", "dubai")

    filters.update({
        "page": 1,
        "per_page": 10,
    })

    try:
        raw_props = search_properties(filters)
        props = [Property(**p) for p in raw_props]
        total = len(props)

        reply = (
            f"I found {total} properties matching your criteria."
            if total
            else "I couldn't find properties matching those details."
        )

        return {
            "reply": reply,
            "properties": props[:6],  # Return top 6 properties
            "total": total,
            "filters": {**filters, "intent": "PROPERTY"},
        }
    except Exception as e:
        # If property search fails, fall back to generic property response
        return {
            "reply": "I can help you find properties in Dubai. Please be more specific about location, price, or property type.",
            "properties": [],
            "total": 0,
            "filters": {"intent": "PROPERTY", "error": str(e)},
        }