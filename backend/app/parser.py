import re
from typing import Dict, List, Optional


def normalize(text: str) -> str:
    return text.lower().strip()


def parse_price_filters(q: str) -> Dict:
    filters = {}
    cleaned = re.sub(r"\b\d+\s*(bed|beds|bedroom|bedrooms|room|rooms)\b", "", q)

    # Check for foreign currencies first
    currency_pattern = r"(\d+(?:\.\d+)?)\s*(usd|eur|gbp|inr|sar|qar|omr|kwd|bhd)"
    currency_match = re.search(currency_pattern, cleaned, re.IGNORECASE)

    if currency_match:
        amount = currency_match.group(1)
        currency = currency_match.group(2).upper()
        # Return special flag for foreign currency
        return {"foreign_currency": True, "amount": amount, "currency": currency}
    def to_aed(amount: str, unit: Optional[str]) -> int:
        n = float(amount)
        if unit == "m":
            return int(n * 1_000_000)
        if unit == "k":
            return int(n * 1_000)
        return int(n)

    match = re.search(
        r"between\s+(\d+(?:\.\d+)?)\s*(m|k)?\s+and\s+(\d+(?:\.\d+)?)\s*(m|k)?",
        cleaned
    )
    if match:
        low, lu, high, hu = match.groups()
        filters["unit_price_from"] = to_aed(low, lu)
        filters["unit_price_to"] = to_aed(high, hu)
        return filters

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(m|k)?\s*(?:-|to|ŌĆō)\s*(\d+(?:\.\d+)?)\s*(m|k)?",
        cleaned
    )
    if match:
        low, lu, high, hu = match.groups()
        filters["unit_price_from"] = to_aed(low, lu)
        filters["unit_price_to"] = to_aed(high, hu)
        return filters

    match = re.search(r"(under|below|less than)\s+(\d+(?:\.\d+)?)\s*(m|k)?", cleaned)
    if match:
        _, amt, unit = match.groups()
        filters["unit_price_to"] = to_aed(amt, unit)
        return filters

    match = re.search(r"(over|above|more than)\s+(\d+(?:\.\d+)?)\s*(m|k)?", cleaned)
    if match:
        _, amt, unit = match.groups()
        filters["unit_price_from"] = to_aed(amt, unit)
        return filters

    match = re.search(r"(\d+(?:\.\d+)?)\s*(m|k)", cleaned)
    if match:
        amt, unit = match.groups()
        filters["unit_price_to"] = to_aed(amt, unit)

    return filters


def parse_bedrooms(q: str) -> Dict:
    filters = {}
    if "studio" in q:
        filters["unit_bedrooms"] = "Studio"
        return filters

    match = re.search(r"(\d+)\s*(bed|beds|bedroom|bedrooms|br|room|rooms)", q)
    if match:
        n = int(match.group(1))
        if 1 <= n <= 10:
            filters["unit_bedrooms"] = f"{n} bedroom"
    return filters


PROPERTY_TYPES = {
    "villa": "Villa",
    "townhouse": "Townhouse",
    "apartment": "Apartment",
    "flat": "Apartment",
    "penthouse": "Penthouse",
    "duplex": "Duplex",
    "studio": "Studio",
    "plot": "Plot"
}


def parse_property_type(q: str) -> Dict:
    for key, val in PROPERTY_TYPES.items():
        if key in q:
            return {"unit_types": [val]}
    return {}


STATUS_WORDS = {
    "completed": "Completed",
    "ready": "Completed",
    "handed over": "Completed",
    "off-plan": "Presale",
    "off plan": "Presale",
    "construction": "Under Construction",
    "under construction": "Under Construction"
}


def parse_status(q: str) -> Dict:
    for word, mapped in STATUS_WORDS.items():
        if word in q:
            return {"status": [mapped]}
    return {}


SALE_STATUS_WORDS = {
    "available": "On Sale",
    "on sale": "On Sale",
    "sold out": "Out of Stock",
    "stock": "Out of Stock",
    "announced": "Announced",
}


def parse_sale_status(q: str) -> Dict:
    for word, mapped in SALE_STATUS_WORDS.items():
        if word in q:
            return {"sale_status": [mapped]}
    return {}


DEVELOPERS = [
    "emaar", "sobha", "nakheel", "meraas", "damac", "danube", "ellington",
    "tiger", "azizi", "samana", "nshe", "omniyat"
]


def parse_developer(q: str) -> Dict:
    found = []
    for dev in DEVELOPERS:
        if dev in q:
            found.append(dev.capitalize())
    if found:
        return {"developer_name_nlp": found}
    return {}


AREAS = [
    "dubai marina", "dubai hills", "dubai hills estate", "business bay",
    "jvc", "jumeirah village circle", "jlt", "downtown", "arjan",
    "dubai south", "mbr city"
]


def parse_area(q: str) -> Dict:
    for area in AREAS:
        if area in q:
            return {"search_query": area}
    return {}


def parse_general_location(q: str) -> Dict:
    """Parse general location mentions from query."""
    location_keywords = {
        "dubai": "dubai",
        "abu dhabi": "abu dhabi",
        "sharjah": "sharjah",
        "ajman": "ajman",
        "ras al khaimah": "ras al khaimah",
        "fujairah": "fujairah",
        "umm al quwain": "umm al quwain",
        "uae": "dubai",
        "emirates": "dubai"
    }

    for keyword, location in location_keywords.items():
        if keyword in q:
            return {"search_query": location}
    return {}


def parse_query_to_filters(query: str) -> Dict:
    q = normalize(query)
    if not q:
        return {}

    filters = {}

    # First check for specific areas
    area_filters = parse_area(q)
    if area_filters:
        filters.update(area_filters)
    else:
        # If no specific area, check for general location
        location_filters = parse_general_location(q)
        if location_filters:
            filters.update(location_filters)

    # Parse other filters
    filters.update(parse_price_filters(q))
    filters.update(parse_bedrooms(q))
    filters.update(parse_property_type(q))
    filters.update(parse_status(q))
    filters.update(parse_sale_status(q))
    filters.update(parse_developer(q))

    return filters


# Add a new function to parser.py for currency detection:
def detect_foreign_currency(q: str) -> Dict:
    """Detect if query contains foreign currency."""
    q_lower = q.lower()

    # Common currency symbols and abbreviations
    currency_patterns = {
        "usd": [r"\$\s*(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*usd", r"(\d+(?:\.\d+)?)\s*dollar"],
        "eur": [r"€\s*(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*eur", r"(\d+(?:\.\d+)?)\s*euro"],
        "gbp": [r"£\s*(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*gbp", r"(\d+(?:\.\d+)?)\s*pound"],
        "inr": [r"₹\s*(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*inr", r"(\d+(?:\.\d+)?)\s*rupee"],
    }

    for currency, patterns in currency_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, q_lower)
            if match:
                amount = match.group(1)
                return {
                    "foreign_currency": True,
                    "amount": amount,
                    "currency": currency.upper()
                }

    return {}