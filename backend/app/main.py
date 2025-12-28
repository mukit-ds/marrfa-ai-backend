import os
import tempfile
import hashlib
import pymongo
import json
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
import io
import time
import asyncio
from functools import lru_cache

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

from .schemas import ChatRequest, ChatResponse, Property, LoginRequest, SignupRequest
from .intent_classifier import classify_intent
from .property_search import handle_property_query
from .company_kb import handle_company_query
from .file_processor import process_uploaded_file, analyze_files_with_ai
from .audio_transcription import transcribe_audio
from .auth import hash_password, check_and_update_limit, handle_signup, handle_login
from .parser import parse_query_to_filters

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["marrfa_chatbot"]
users_col = db["users"]
usage_col = db["usage"]

# --- Config ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
CACHE_TIMEOUT = 60 * 5  # 5 minutes

QUERY_CACHE = {}
PROPERTY_CACHE = {}

def get_cache_key(query: str, cache_type: str) -> str:
    return hashlib.md5(f"{cache_type}:{query.lower().strip()}".encode()).hexdigest()

def clear_old_cache():
    now = time.time()
    for cache in (QUERY_CACHE, PROPERTY_CACHE):
        old_keys = [k for k, (ts, _) in cache.items() if now - ts > CACHE_TIMEOUT]
        for k in old_keys:
            del cache[k]

@lru_cache(maxsize=200)
def classify_intent_cached(query: str) -> Dict[str, Any]:
    return classify_intent(query)

def get_greeting_response(intent_result: Dict[str, Any]) -> str:
    return "Hello! 👋 I'm Marrfa AI. Ask me about properties, Marrfa company info, or upload files for analysis."

# -----------------------------
# AUTH
# -----------------------------
@app.post("/api/signup")
def signup(data: SignupRequest):
    return handle_signup(data, users_col)

@app.post("/api/login")
def login(data: LoginRequest):
    return handle_login(data, users_col)

# -----------------------------
# CHAT
# -----------------------------
@app.post("/chat")
async def chat_endpoint(request: Request):
    """Handle chat requests with optional file uploads.

    Supports:
    - application/json: {"query": "...", "session_id": "...", "is_logged_in": bool, "files": [...]}
    - multipart/form-data: fields query, session_id, is_logged_in, and optional repeated files under key "files"
    """
    start_time = time.time()

    # Clear old cache periodically
    if len(QUERY_CACHE) > 1000 or len(PROPERTY_CACHE) > 500:
        clear_old_cache()

    content_type = (request.headers.get("content-type") or "").lower()

    query = ""
    session_id = None
    is_logged_in = False
    files = []

    # --- Parse request payload ---
    if "multipart/form-data" in content_type:
        form = await request.form()
        query = (form.get("query") or "").strip()
        session_id = form.get("session_id")
        is_logged_in = str(form.get("is_logged_in", "false")).lower() in ("1", "true", "yes", "y")

        # Streamlit sends files under key: "files"
        try:
            files = form.getlist("files")
        except Exception:
            f = form.get("files")
            files = [f] if f else []
    else:
        # Handle JSON body
        try:
            body = await request.json()
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            try:
                raw = await request.body()
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                body = {}

        query = (body.get("query") or "").strip()
        session_id = body.get("session_id")
        is_logged_in = bool(body.get("is_logged_in", False))
        files = body.get("files", []) or []

    print(f"Received chat request: query='{query}', session_id='{session_id}', is_logged_in={is_logged_in}")

    # Check Usage Limit
    if not is_logged_in:
        if not check_and_update_limit(session_id, usage_col):
            print("User reached limit")
            return ChatResponse(
                reply="🔒 You've reached the 3-query limit. Please log in to continue.",
                filters_used={"error": "LIMIT"}
            )

    query_text = (query or "").strip()
    print(f"Query text: '{query_text}' - Processing time: {time.time() - start_time:.2f}s")

    if not query_text:
        return ChatResponse(
            reply="Please type a message.",
            properties=[],
            total=0,
            page=1,
            per_page=10,
            filters_used={"error": "EMPTY_QUERY"},
        )

    # Check cache first (only for non-file queries)
    if not files:
        cache_key = get_cache_key(query_text, "intent_only")
        if cache_key in QUERY_CACHE:
            timestamp, cached_result = QUERY_CACHE[cache_key]
            if time.time() - timestamp < CACHE_TIMEOUT:
                print(f"Cache hit for: {query_text}")
                return cached_result

    # Classify intent (using cached version)
    intent_result = classify_intent_cached(query_text)
    intent = intent_result["intent"]

    print(f"Intent result: {intent_result} - Time: {time.time() - start_time:.2f}s")

    # 1️⃣ Greeting (fast path)
    if intent == "GREETING":
        greeting_reply = get_greeting_response(intent_result)
        response = ChatResponse(
            reply=greeting_reply,
            filters_used={"intent": "GREETING", "method": intent_result["method"]}
        )
        if not files:
            QUERY_CACHE[get_cache_key(query_text, "intent_only")] = (time.time(), response)
        return response

    # Process uploaded files if any
    file_contents = []
    if files:
        print(f"Processing {len(files)} files")
        for file in files:
            if not is_logged_in:
                return ChatResponse(
                    reply="Please log in to upload and analyze files.",
                    filters_used={"error": "AUTH_REQUIRED"}
                )

            # Check file size
            if hasattr(file, "read"):
                file_bytes = await file.read()
                filename = getattr(file, "filename", "unknown")
            else:
                # Handle files sent as JSON (base64 encoded)
                file_bytes = base64.b64decode(file.get("content", ""))
                filename = file.get("name", "unknown")

            if len(file_bytes) > MAX_FILE_SIZE:
                return ChatResponse(
                    reply=f"File '{filename}' is too large. Maximum size is 10MB.",
                    filters_used={"error": "FILE_TOO_LARGE"}
                )

            # Process file content
            file_result = process_uploaded_file(file_bytes, filename)
            if file_result:
                file_contents.append(file_result)

        # If files were uploaded and processed, analyze them with AI
        if file_contents:
            analysis_reply = analyze_files_with_ai(file_contents, query_text)
            response = ChatResponse(
                reply=analysis_reply,
                filters_used={"intent": "FILE_ANALYSIS", "files": [f.get("filename") for f in file_contents]}
            )
            return response

    # 2️⃣ Property query
    if intent == "PROPERTY":
        print("Handling PROPERTY intent")
        response = await handle_property_query(query_text, intent_result)
        if not files:
            cache_key = get_cache_key(query_text, "property")
            PROPERTY_CACHE[cache_key] = (time.time(), response)
        return response

    # 3️⃣ Company info query
    if intent == "COMPANY":
        print("Handling COMPANY intent")
        response = handle_company_query(query_text)
        if not files:
            cache_key = get_cache_key(query_text, "company")
            QUERY_CACHE[cache_key] = (time.time(), response)
        return response

    # 4️⃣ Files (explicit)
    if intent == "FILE":
        print("Handling FILE intent")
        response = ChatResponse(
            reply="Please upload a file (PDF/DOCX/TXT) and ask what you want to know from it.",
            filters_used={"intent": "FILE", "method": intent_result.get("method")}
        )
        if not files:
            cache_key = get_cache_key(query_text, "intent_only")
            QUERY_CACHE[cache_key] = (time.time(), response)
        return response

    # 5️⃣ Out of context
    print("Handling OUT_OF_CONTEXT intent")
    response = ChatResponse(
        reply="I'm trained specifically on Marrfa Real Estate. Please ask about Marrfa or properties in Dubai.",
        properties=[],
        total=0,
        page=1,
        per_page=10,
        filters_used={"intent": "OUT_OF_CONTEXT", "method": intent_result.get("method")},
    )
    if not files:
        cache_key = get_cache_key(query_text, "intent_only")
        QUERY_CACHE[cache_key] = (time.time(), response)
    return response

# -----------------------------
# TRANSCRIBE
# -----------------------------
@app.post("/api/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """Transcribe an audio file."""
    try:
        audio_bytes = await file.read()
        text = transcribe_audio(audio_bytes, file.filename)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
