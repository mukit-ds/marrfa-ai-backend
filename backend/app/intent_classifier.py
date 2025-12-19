# backend/app/intent_classifier.py
import re
from typing import Dict, Any
from openai import OpenAI

# --- Intent Detection Keywords ---
_GREETINGS = {
    "hi", "hello", "hey", "yo",
    "assalamualaikum", "assalamu alaikum", "as-salamu alaykum",
    "good morning", "good afternoon", "good evening",
}

_PROPERTY_KEYWORDS = {
    "property", "properties", "apartment", "apartments", "villa", "villas",
    "townhouse", "townhouses", "home", "homes", "house", "houses",
    "flat", "flats", "studio", "studios", "penthouse", "penthouses",
    "duplex", "duplexes", "real estate", "rent", "rental", "buy", "sale",
    "price", "prices", "bedroom", "bedrooms", "bathroom", "bathrooms",
    "area", "location", "dubai", "marina", "jvc", "jlt", "downtown",
    "business bay", "dubai hills", "arjan", "mbr city", "dubai south",
    "emaar", "sobha", "nakheel", "damac", "off-plan", "ready", "completed",
    "suggest", "show", "find", "search", "looking for"
}

_COMPANY_KEYWORDS = {
    "marrfa", "ceo", "founder", "owner", "team", "about", "contact",
    "privacy", "policy", "terms", "conditions", "partnership", "company",
    "who is", "what is", "history", "values", "mission", "vision"
}

_LEGAL_KEYWORDS = {
    "privacy", "privacy policy",
    "terms", "terms and conditions",
    "t&c", "tos"
}


def _clean(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_greeting(text: str) -> bool:
    t = _clean(text)
    if not t:
        return False
    if t in _GREETINGS:
        return True
    for g in _GREETINGS:
        if t.startswith(g + " "):
            return True
    return False


def is_legal_query(text: str) -> bool:
    t = _clean(text)
    return any(keyword in t for keyword in _LEGAL_KEYWORDS)


def rule_based_intent(query: str) -> str:
    """Rule-based intent detection."""
    q = _clean(query)

    # Check for property keywords
    property_matches = [keyword for keyword in _PROPERTY_KEYWORDS if keyword in q]
    if property_matches:
        print(f"Property keywords found: {property_matches}")
        return "PROPERTY"

    # Check for company keywords
    company_matches = [keyword for keyword in _COMPANY_KEYWORDS if keyword in q]
    if company_matches:
        print(f"Company keywords found: {company_matches}")
        return "COMPANY"

    # Default to out of context
    print("No keywords matched, defaulting to OUT_OF_CONTEXT")
    return "OUT_OF_CONTEXT"


def llm_route(query: str, client: OpenAI) -> str:
    """LLM-based intent routing."""
    if not client:
        # Fallback to rule-based if OpenAI is not available
        return rule_based_intent(query)

    system_prompt = (
        "You are an intent router for a chatbot trained on Marrfa Real Estate.\n"
        "Classify the user query into ONE label:\n"
        "- PROPERTY: searching for properties, apartments, villas, prices, filters in Dubai.\n"
        "- COMPANY: questions about Marrfa company info, team, CEO, owner, policies, terms.\n"
        "- OUT_OF_CONTEXT: unrelated queries.\n"
        "Return ONLY one word: PROPERTY or COMPANY or OUT_OF_CONTEXT."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0,
        )
        out = (resp.choices[0].message.content or "").strip().upper()
        if out in {"PROPERTY", "COMPANY", "OUT_OF_CONTEXT"}:
            return out
        # If LLM returns something unexpected, fall back to rule-based
        return rule_based_intent(query)
    except Exception as e:
        print(f"LLM intent routing failed: {e}")
        # Fallback to rule-based if LLM fails
        return rule_based_intent(query)


def classify_intent(query: str, client: OpenAI = None) -> Dict[str, Any]:
    """
    Classify the intent of a user query.

    Returns:
        Dict with keys:
        - intent: One of "GREETING", "PROPERTY", "COMPANY", "OUT_OF_CONTEXT"
        - method: How the intent was determined ("rule_based", "llm_based", "hardcoded")
    """
    query_text = (query or "").strip()
    print(f"Classifying intent for query: '{query_text}'")

    # 1️⃣ Greeting
    if is_greeting(query_text):
        print("Intent classified as GREETING")
        return {"intent": "GREETING", "method": "rule_based"}

    # 2️⃣ HARD rule: legal & policy queries → COMPANY
    if is_legal_query(query_text):
        print("Intent classified as COMPANY (legal query)")
        return {"intent": "COMPANY", "method": "hardcoded"}

    # 3️⃣ Use rule-based intent first for reliability
    intent = rule_based_intent(query_text)

    # 4️⃣ If rule-based is uncertain, use LLM
    if intent == "OUT_OF_CONTEXT" and client:
        intent = llm_route(query_text, client)
        print(f"Intent classified as {intent} (LLM-based)")
        return {"intent": intent, "method": "llm_based"}

    print(f"Intent classified as {intent} (rule-based)")
    return {"intent": intent, "method": "rule_based"}