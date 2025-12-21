from typing import Dict, Any, Optional, Set, FrozenSet
from openai import OpenAI
import re

# --- Pre-compiled sets for fast membership checking ---
GREETING_PATTERNS = frozenset({
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "greetings", "hi there", "hey there", "how are you", "how's it going",
    "what's up", "sup", "yo", "hello there", "hiya", "hola", "bonjour",
    "namaste", "salaam", "konnichiwa"
})

LISTENING_PATTERNS = frozenset({
    "do you listen", "can you listen", "can you hear", "do you hear",
    "are you listening", "can you understand me", "do you understand",
    "can you hear me", "do you hear me", "are you there", "can you respond"
})

# Split property keywords into categories for faster checking
PROPERTY_BASIC = frozenset({
    "property", "properties", "real estate", "apartment", "villa", "house", "home"
})

PROPERTY_ACTION = frozenset({
    "buy", "purchase", "rent", "lease", "sale", "for sale", "for rent"
})

PROPERTY_ATTRIBUTES = frozenset({
    "price", "cost", "budget", "affordable", "luxury", "premium", "location", "area"
})

PROPERTY_MEASUREMENTS = frozenset({
    "square feet", "sq ft", "square meters", "sq m", "bedroom", "bathroom"
})

PROPERTY_TYPES = frozenset({
    "studio", "penthouse", "townhouse", "duplex"
})

PROPERTY_FEATURES = frozenset({
    "developer", "construction", "completion", "ready", "off-plan", "handover",
    "floor plan", "amenities", "gym", "pool", "parking", "balcony", "view",
    "sea view", "city view"
})

PROPERTY_LOCATIONS = frozenset({
    "dubai", "dubai marina", "business bay", "jumeirah", "palm", "burj"
})

PROPERTY_DEVELOPERS = frozenset({
    "emaar", "nakheel", "damac", "sohba", "ellinton", "meraas"
})

PROPERTY_QUERIES = frozenset({
    "how much", "price range", "available", "listing", "listings"
})

# Combine all property keywords for simple checking
ALL_PROPERTY_KEYWORDS = (
        PROPERTY_BASIC | PROPERTY_ACTION | PROPERTY_ATTRIBUTES |
        PROPERTY_MEASUREMENTS | PROPERTY_TYPES | PROPERTY_FEATURES |
        PROPERTY_LOCATIONS | PROPERTY_DEVELOPERS | PROPERTY_QUERIES
)

# Company keywords - EXPANDED to include more leadership terms
COMPANY_BASIC = frozenset({
    "marrfa", "marfa", "company", "team", "about", "what is", "who is"
})

COMPANY_PEOPLE = frozenset({
    "founder", "founders", "ceo", "director", "management", "leadership",
    "owner", "owners", "head", "boss", "chief", "executive", "president",
    "chairman", "chairperson", "md", "managing director"
})

COMPANY_INFO = frozenset({
    "history", "story", "mission", "vision", "values", "culture", "background"
})

COMPANY_CONTACT = frozenset({
    "contact", "email", "phone", "address", "location", "office", "number"
})

COMPANY_WEB = frozenset({
    "website", "social media", "facebook", "instagram", "twitter",
    "linkedin", "youtube", "web", "site"
})

COMPANY_CAREER = frozenset({
    "career", "job", "employment", "work", "hire", "hiring", "vacancy"
})

COMPANY_DOCS = frozenset({
    "policy", "policies", "terms", "conditions", "privacy", "legal"
})

COMPANY_SERVICES = frozenset({
    "service", "services", "offer", "offering", "product", "products"
})

# Combine all company keywords
ALL_COMPANY_KEYWORDS = (
        COMPANY_BASIC | COMPANY_PEOPLE | COMPANY_INFO | COMPANY_CONTACT |
        COMPANY_WEB | COMPANY_CAREER | COMPANY_DOCS | COMPANY_SERVICES
)

# Question words that indicate asking about something
QUESTION_WORDS = frozenset({
    "who", "what", "when", "where", "why", "how", "which", "tell", "explain", "describe"
})

# Chatbot self-reference patterns
CHATBOT_SELF_QUESTIONS = frozenset({
    "are you", "can you", "do you", "will you", "would you", "could you",
    "should you", "have you", "has you", "did you", "does you", "is you"
})

# Short queries that are definitely greetings
SHORT_GREETINGS = frozenset({"?", "??", "???", "....", "...", "!", "!!"})

# --- Pre-compiled regex patterns ---
SHORT_QUERY_PATTERN = re.compile(r'^\s*(\S\s*){0,2}\s*$')  # 0-2 non-space chars
CHATBOT_SELF_PATTERN = re.compile(r'^(are|can|do|will|would|could|should|have|has|did|does|is)\s+you\s', re.IGNORECASE)
LEADERSHIP_PATTERN = re.compile(r'(who|what)\s+(is|are)\s+(the\s+)?(ceo|owner|founder|director|head|boss|chief|leader)',
                                re.IGNORECASE)

# --- OpenAI system prompt (static) ---
OPENAI_SYSTEM_PROMPT = """You are an intent classifier for a real estate chatbot.
Classify queries into these categories:
1. GREETING - Hello, hi, how are you, introductions, general questions about the chatbot
2. PROPERTY - Questions about buying, selling, renting properties in Dubai
3. COMPANY - Questions about Marrfa company, team, policies, contact info
4. OUT_OF_CONTEXT - Everything else not related to Marrfa or Dubai properties

Respond with only the category name: GREETING, PROPERTY, COMPANY, or OUT_OF_CONTEXT"""


# --- Optimized helper functions ---
def _contains_any_fast(text: str, keyword_set: FrozenSet[str]) -> bool:
    """Fast check if text contains any of the keywords."""
    words = set(text.split())
    return bool(words & keyword_set)


def _contains_any_substring(text: str, substring_set: FrozenSet[str]) -> bool:
    """Check if text contains any substring from set."""
    for phrase in substring_set:
        if phrase in text:
            return True
    return False


def _count_keywords_fast(text: str, keyword_set: FrozenSet[str]) -> int:
    """Fast count of keywords in text."""
    words = set(text.split())
    return len(words & keyword_set)


def _check_chatbot_self_query(query: str, query_words: list) -> bool:
    """Check if query is about chatbot itself."""
    if len(query_words) <= 5 and CHATBOT_SELF_PATTERN.match(query):
        return True

    chatbot_indicators = {"you", "your", "chatbot", "ai", "assistant", "bot"}
    query_words_set = set(query_words)
    return bool(query_words_set & chatbot_indicators) and len(query_words) <= 6


# --- Main intent classification function ---
def classify_intent(query: str, client: Optional[OpenAI] = None) -> Dict[str, Any]:
    """
    Classify query intent into: GREETING, PROPERTY, COMPANY, OUT_OF_CONTEXT
    Optimized for speed with pattern matching and caching.
    """
    query_lower = query.lower().strip()

    # 1. Fast empty/short query check
    if not query_lower:
        return {"intent": "GREETING", "method": "empty_query"}

    if query_lower in SHORT_GREETINGS or SHORT_QUERY_PATTERN.match(query_lower):
        return {"intent": "GREETING", "method": "empty_query"}

    # Split words once for reuse
    query_words = query_lower.split()

    # 2. Check for greeting patterns (fast substring check)
    if _contains_any_substring(query_lower, GREETING_PATTERNS):
        return {"intent": "GREETING", "method": "pattern"}

    # 3. Check for listening patterns
    if _contains_any_substring(query_lower, LISTENING_PATTERNS):
        return {"intent": "GREETING", "method": "listening_check"}

    # 4. Property-related keywords (optimized with word sets)
    if _contains_any_fast(query_lower, ALL_PROPERTY_KEYWORDS):
        return {"intent": "PROPERTY", "method": "keyword_count"}

    # For multi-word property terms
    if "dubai" in query_lower and any(term in query_lower for term in ["marina", "hills", "creek", "land"]):
        return {"intent": "PROPERTY", "method": "keyword_count"}

    # 5. Company-related keywords - UPDATED LOGIC
    company_word_count = _count_keywords_fast(query_lower, ALL_COMPANY_KEYWORDS)

    # 🔴 CRITICAL FIX: Handle leadership queries (CEO/owner/founder)
    # Check regex pattern for "who is the ceo" type queries
    if LEADERSHIP_PATTERN.search(query_lower):
        return {"intent": "COMPANY", "method": "leadership_pattern"}

    # Check if query contains company leadership terms with question words
    leadership_terms = {"ceo", "owner", "founder", "director", "head", "boss", "chief"}
    question_words = {"who", "what", "tell", "explain", "describe"}

    query_words_set = set(query_words)
    if (query_words_set & leadership_terms) and (query_words_set & question_words):
        return {"intent": "COMPANY", "method": "leadership_keywords"}

    # Special case: "marrfa" or "marfa" queries
    if "marrfa" in query_lower or "marfa" in query_lower:
        if company_word_count >= 1:
            return {"intent": "COMPANY", "method": "keyword_count"}
        # If it's just "marrfa" or basic questions about marrfa
        if query_lower in ["marrfa", "marfa"] or query_lower.startswith(
                ("what is marrfa", "what is marfa", "who is marrfa", "who is marfa", "about marrfa", "about marfa")):
            return {"intent": "COMPANY", "method": "company_name"}

    # Original company keyword logic
    if company_word_count >= 2:
        return {"intent": "COMPANY", "method": "keyword_count"}

    # Special case: Single strong company keyword with question
    strong_company_keywords = {"ceo", "owner", "founder", "team", "management", "leadership"}
    if (query_words_set & strong_company_keywords) and len(query_words) <= 6:
        return {"intent": "COMPANY", "method": "strong_keyword"}

    # 6. Chatbot self-reference check
    if _check_chatbot_self_query(query_lower, query_words):
        return {"intent": "GREETING", "method": "chatbot_self"}

    # 7. Common real estate patterns
    real_estate_patterns = {
        "how much for", "price of", "cost of", "budget for",
        "available in", "for rent in", "for sale in",
        "bedroom in", "bathroom in", "studio in"
    }

    for pattern in real_estate_patterns:
        if pattern in query_lower:
            return {"intent": "PROPERTY", "method": "pattern"}

    # 8. Use OpenAI only as last resort
    if client:
        try:
            # Check if query is likely ambiguous before calling OpenAI
            ambiguous_patterns = {
                "what", "how", "when", "where", "why", "which",
                "tell me", "explain", "describe", "information about"
            }

            is_ambiguous = False
            for pattern in ambiguous_patterns:
                if query_lower.startswith(pattern) and len(query_words) <= 8:
                    is_ambiguous = True
                    break

            if is_ambiguous or len(query_words) <= 3:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.1,
                    max_tokens=10
                )

                intent = response.choices[0].message.content.strip().upper()
                if intent in ["GREETING", "PROPERTY", "COMPANY", "OUT_OF_CONTEXT"]:
                    return {"intent": intent, "method": "openai"}
        except Exception as e:
            print(f"OpenAI classification failed: {e}")

    # 9. Default to out of context
    return {"intent": "OUT_OF_CONTEXT", "method": "default"}


# --- Cached version for frequent use ---
from functools import lru_cache


@lru_cache(maxsize=500)
def classify_intent_cached(query: str, client: Optional[OpenAI] = None) -> Dict[str, Any]:
    """
    Cached version of classify_intent for repeated queries.
    """
    return classify_intent(query, client)


# --- Fast classification without OpenAI ---
def classify_intent_fast(query: str) -> Dict[str, Any]:
    """
    Fast intent classification without OpenAI fallback.
    """
    query_lower = query.lower().strip()

    # 1. Fast empty/short query check
    if not query_lower or query_lower in SHORT_GREETINGS or SHORT_QUERY_PATTERN.match(query_lower):
        return {"intent": "GREETING", "method": "empty_query"}

    # 2. Check for greeting patterns
    if _contains_any_substring(query_lower, GREETING_PATTERNS):
        return {"intent": "GREETING", "method": "pattern"}

    # 3. Check for listening patterns
    if _contains_any_substring(query_lower, LISTENING_PATTERNS):
        return {"intent": "GREETING", "method": "listening_check"}

    # 4. Property-related keywords
    if _contains_any_fast(query_lower, ALL_PROPERTY_KEYWORDS):
        return {"intent": "PROPERTY", "method": "keyword_count"}

    # 5. Company-related keywords - UPDATED
    company_word_count = _count_keywords_fast(query_lower, ALL_COMPANY_KEYWORDS)

    # 🔴 CRITICAL FIX: Handle leadership queries
    if LEADERSHIP_PATTERN.search(query_lower):
        return {"intent": "COMPANY", "method": "leadership_pattern"}

    # Check for leadership terms with questions
    query_words = query_lower.split()
    query_words_set = set(query_words)
    leadership_terms = {"ceo", "owner", "founder", "director"}
    question_words = {"who", "what", "tell"}

    if (query_words_set & leadership_terms) and (query_words_set & question_words):
        return {"intent": "COMPANY", "method": "leadership_keywords"}

    # Special case for "marrfa"/"marfa"
    if ("marrfa" in query_lower or "marfa" in query_lower) and company_word_count >= 1:
        return {"intent": "COMPANY", "method": "keyword_count"}

    if company_word_count >= 2:
        return {"intent": "COMPANY", "method": "keyword_count"}

    # 6. Chatbot self-reference
    if _check_chatbot_self_query(query_lower, query_words):
        return {"intent": "GREETING", "method": "chatbot_self"}

    # 7. Default
    return {"intent": "OUT_OF_CONTEXT", "method": "default"}