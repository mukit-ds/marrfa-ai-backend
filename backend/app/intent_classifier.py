from typing import Dict, Any, Optional
from openai import OpenAI


def classify_intent(query: str, client: Optional[OpenAI] = None) -> Dict[str, Any]:
    """
    Classify query intent into: GREETING, PROPERTY, COMPANY, OUT_OF_CONTEXT
    """
    query = query.lower().strip()

    # 1. First check for common greeting patterns
    greeting_patterns = [
        "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "greetings", "hi there", "hey there", "how are you", "how's it going",
        "what's up", "sup", "yo", "hello there", "hiya", "hola", "bonjour",
        "namaste", "salaam", "konnichiwa"
    ]

    # Check if query contains greeting patterns
    for pattern in greeting_patterns:
        if pattern in query:
            return {"intent": "GREETING", "method": "pattern"}

    # 2. Check for "listen" or "hear" questions (common voice/audio queries)
    listening_patterns = [
        "do you listen", "can you listen", "can you hear", "do you hear",
        "are you listening", "can you understand me", "do you understand",
        "can you hear me", "do you hear me", "are you there", "can you respond"
    ]

    for pattern in listening_patterns:
        if pattern in query:
            return {"intent": "GREETING", "method": "listening_check"}

    # 3. Empty or very short queries
    if len(query) <= 2 or query in ["?", "??", "???", "....", "..."]:
        return {"intent": "GREETING", "method": "empty_query"}

    # 4. Property-related keywords
    property_keywords = [
        "property", "properties", "real estate", "apartment", "villa", "house", "home",
        "buy", "purchase", "rent", "lease", "sale", "for sale", "for rent", "price",
        "cost", "budget", "affordable", "luxury", "premium", "location", "area",
        "square feet", "sq ft", "square meters", "sq m", "bedroom", "bathroom",
        "studio", "penthouse", "townhouse", "duplex", "developer", "construction",
        "completion", "ready", "off-plan", "handover", "floor plan", "amenities",
        "gym", "pool", "parking", "balcony", "view", "sea view", "city view",
        "dubai", "dubai marina", "business bay", "jumeirah", "palm", "burj",
        "emaar", "nakheel", "damac", "sohba", "ellinton", "meraas",
        "how much", "price range", "available", "listing", "listings"
    ]

    property_count = sum(1 for keyword in property_keywords if keyword in query)
    if property_count >= 1:
        return {"intent": "PROPERTY", "method": "keyword_count"}

    # 5. Company-related keywords
    company_keywords = [
        "marrfa", "marfa", "company", "team", "about", "what is", "who is",
        "founder", "founders", "ceo", "director", "management", "leadership",
        "history", "story", "mission", "vision", "values", "culture",
        "contact", "email", "phone", "address", "location", "office",
        "website", "social media", "facebook", "instagram", "twitter",
        "linkedin", "youtube", "career", "job", "employment", "work",
        "policy", "policies", "terms", "conditions", "privacy",
        "service", "services", "offer", "offering", "product", "products"
    ]

    company_count = sum(1 for keyword in company_keywords if keyword in query)
    if company_count >= 2:  # Need at least 2 company-related words
        return {"intent": "COMPANY", "method": "keyword_count"}

    # 6. Use OpenAI if available for ambiguous queries
    if client:
        try:
            system_prompt = """You are an intent classifier for a real estate chatbot.
            Classify queries into these categories:
            1. GREETING - Hello, hi, how are you, introductions, general questions about the chatbot
            2. PROPERTY - Questions about buying, selling, renting properties in Dubai
            3. COMPANY - Questions about Marrfa company, team, policies, contact info
            4. OUT_OF_CONTEXT - Everything else not related to Marrfa or Dubai properties

            Respond with only the category name: GREETING, PROPERTY, COMPANY, or OUT_OF_CONTEXT"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
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

    # 7. Check for simple yes/no questions about the chatbot itself
    chatbot_self_questions = [
        "are you", "can you", "do you", "will you", "would you", "could you",
        "should you", "have you", "has you", "did you", "does you", "is you"
    ]

    # If it starts with chatbot self-reference and is short
    if any(query.startswith(q) for q in chatbot_self_questions) and len(query.split()) <= 5:
        return {"intent": "GREETING", "method": "chatbot_self"}

    # 8. Default to out of context
    return {"intent": "OUT_OF_CONTEXT", "method": "default"}