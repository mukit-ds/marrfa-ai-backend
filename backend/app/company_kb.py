# backend/app/company_kb.py
from typing import Dict, Any
from .faiss_kb import MarrfaFaissKB
from .schemas import ChatResponse

# Singleton KB instance
_faiss_kb = None
_faiss_kb_error = None


def get_faiss_kb() -> MarrfaFaissKB | None:
    global _faiss_kb, _faiss_kb_error

    if _faiss_kb is None:
        try:
            _faiss_kb = MarrfaFaissKB()
            _faiss_kb_error = None
        except Exception as e:
            _faiss_kb_error = repr(e)
            print(f"[KB ERROR] Failed to init FAISS KB: {_faiss_kb_error}")
            _faiss_kb = None

    return _faiss_kb


def handle_company_query(query_text: str) -> ChatResponse:
    """
    Handle Marrfa company-related queries (CEO, team, policies, etc.)
    Always returns ChatResponse-compatible output.
    """

    kb = get_faiss_kb()

    if not kb or not kb.enabled:
        return ChatResponse(
            reply="I'm having trouble accessing Marrfa's company knowledge right now. Please try again shortly.",
            properties=[],
            total=0,
            page=1,
            per_page=10,
            filters_used={
                "intent": "COMPANY",
                "kb": "FAISS",
                "error": _faiss_kb_error,
            },
        )

    try:
        answer = kb.answer(query_text, top_k=15)
    except Exception as e:
        print(f"[KB QUERY ERROR] {e}")
        answer = None

    # 🔴 HARD GUARANTEE FOR CEO / LEADERSHIP
    q = query_text.lower()
    if (not answer or len(answer.strip()) < 10) and any(
        x in q for x in ["ceo", "owner", "founder", "managing director", "md"]
    ):
        answer = (
            "Marrfa Real Estate is led by its executive leadership team. "
            "The CEO is responsible for the company's overall strategy, operations, "
            "and growth in Dubai’s real estate market. "
            "For official confirmation, please refer to Marrfa’s website or contact their office."
        )

    if not answer:
        answer = "I couldn’t find specific information about that in Marrfa’s company knowledge base."

    return ChatResponse(
        reply=answer,
        properties=[],
        total=0,
        page=1,
        per_page=10,
        filters_used={
            "intent": "COMPANY",
            "kb": "FAISS",
        },
    )
