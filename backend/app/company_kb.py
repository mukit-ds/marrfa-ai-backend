# backend/app/company_kb.py
from typing import Dict, Any
from .faiss_kb import MarrfaFaissKB

# Global variables to store the knowledge base
faiss_kb = None
faiss_kb_error = None


def get_faiss_kb():
    """Get or initialize the FAISS knowledge base."""
    global faiss_kb, faiss_kb_error
    if faiss_kb is None:
        try:
            faiss_kb = MarrfaFaissKB()
            faiss_kb_error = None
        except Exception as e:
            faiss_kb_error = repr(e)
            print(f"Error initializing knowledge base: {faiss_kb_error}")
    return faiss_kb


def handle_company_query(query_text: str) -> Dict[str, Any]:
    """
    Handle company-related queries using the knowledge base.

    Returns:
        Dict with keys:
        - reply: Response message
        - filters: Filters used for the search
    """
    kb = get_faiss_kb()
    if not kb or not kb.enabled:
        return {
            "reply": "I'm having trouble accessing the company knowledge base right now. Please try again later.",
            "filters": {"intent": "COMPANY", "kb": "FAISS", "error": faiss_kb_error},
        }

    return {
        "reply": kb.answer(query_text, top_k=12),
        "filters": {"intent": "COMPANY", "kb": "FAISS"},
    }