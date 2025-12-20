import streamlit as st
import requests
import uuid
from streamlit_mic_recorder import mic_recorder
import re

BASE_API = ("http://127.0.0.1:9000/api")

st.set_page_config(page_title="Marrfa AI", page_icon="🏙️", layout="wide")

# --- Initialize Session State ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_data" not in st.session_state: st.session_state.user_data = None
if "messages" not in st.session_state: st.session_state.messages = []
if "user_uuid" not in st.session_state: st.session_state.user_uuid = str(uuid.uuid4())
if "uploaded_files" not in st.session_state: st.session_state.uploaded_files = []

# --- Professional CSS Styling ---
st.markdown("""
    <style>
      .block-container { max-width: 1200px; padding-bottom: 10rem; }

      /* Card Container */
      .prop-card {
          background-color: #ffffff;
          border: 1px solid #e0e0e0;
          border-radius: 12px;
          overflow: hidden;
          height: 440px; 
          margin-bottom: 10px;
          display: flex;
          flex-direction: column;
          transition: transform 0.2s, box-shadow 0.2s;
      }
      .prop-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 10px 20px rgba(0,0,0,0.1);
      }
      .prop-img {
          width: 100%;
          height: 180px;
          object-fit: cover;
          border-bottom: 1px solid #f0f0f0;
      }
      .prop-content { padding: 16px; flex-grow: 1; display: flex; flex-direction: column; }
      .prop-title {
          font-size: 1.05rem; font-weight: 700; color: #1a1a1a;
          height: 48px; overflow: hidden; margin-bottom: 8px; line-height: 1.4;
      }
      .prop-details { font-size: 0.9rem; color: #666; margin-bottom: 4px; display: flex; align-items: center; }
      .prop-price { font-size: 1.1rem; font-weight: 700; color: #0046be; margin: 12px 0; }

      /* Fixed Input Dock */
      .footer-container {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background: white;
          padding: 20px 0;
          border-top: 1px solid #eee;
          z-index: 999;
      }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar: Login/Signup Logic ---
with st.sidebar:
    st.title("👤 Marrfa Account")
    if not st.session_state.authenticated:
        t1, t2 = st.tabs(["Login", "Sign Up"])
        with t1:
            lid = st.text_input("Username/Email", key="l_id")
            lpw = st.text_input("Password", type="password", key="l_pw")
            if st.button("Log In", use_container_width=True):
                res = requests.post(f"{BASE_API}/login", json={"identifier": lid, "password": lpw})
                if res.status_code == 200:
                    st.session_state.authenticated = True
                    st.session_state.user_data = res.json()["user"]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        with t2:
            sun = st.text_input("Username", key="s_un")
            sem = st.text_input("Email", key="s_em")
            spw = st.text_input("Password", type="password", key="s_pw")
            if st.button("Create Account", use_container_width=True):
                res = requests.post(f"{BASE_API}/signup",
                                    json={"username": sun, "email": sem, "phone": "N/A", "password": spw})
                if res.status_code == 200:
                    st.success("Account created! Log In.")
    else:
        st.write(f"Logged in as: **{st.session_state.user_data['username']}**")

        if st.button("Log Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.rerun()


def is_likely_english(text):
    """Check if the text is likely English with more lenient rules."""
    if not text or not text.strip():
        return False

    text = text.strip()

    # If it's very short (less than 3 characters), accept it
    if len(text) < 3:
        return True

    # Convert to lowercase for easier checking
    text_lower = text.lower()

    # Check for CLEARLY non-English scripts (very strict regex)
    # Arabic characters range
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
        return False

    # Chinese/Japanese/Korean characters
    if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text):
        return False

    # Cyrillic characters
    if re.search(r'[\u0400-\u04FF\u0500-\u052F]', text):
        return False

    # Hindi/Devanagari characters
    if re.search(r'[\u0900-\u097F]', text):
        return False

    # If text contains any of these patterns, assume it's English:
    # 1. Common English letters only (a-z, A-Z, spaces, basic punctuation)
    english_pattern = r'^[a-zA-Z0-9\s\.,\?!\-\'"]+$'

    # 2. Contains common English words
    common_english_words = [
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
        'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which',
        'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just',
        'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good',
        'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now',
        'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back',
        'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well',
        'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give',
        'day', 'most', 'us'
    ]

    # Check if text matches basic English pattern
    if re.match(english_pattern, text):
        return True

    # Check for common English words (even partial matches)
    for word in common_english_words:
        if word in text_lower:
            return True

    # Check for common real estate terms
    estate_words = [
        'property', 'properties', 'real estate', 'dubai', 'apartment', 'villa',
        'price', 'location', 'bedroom', 'bathroom', 'square', 'feet', 'meter',
        'view', 'pool', 'gym', 'parking', 'balcony', 'kitchen', 'living', 'room',
        'for sale', 'for rent', 'buy', 'rent', 'lease', 'agent', 'developer',
        'project', 'community', 'neighborhood', 'amenities', 'facilities',
        'marrfa', 'house', 'home', 'investment', 'luxury', 'modern', 'new'
    ]

    for word in estate_words:
        if word in text_lower:
            return True

    # If text is mostly ASCII characters and doesn't contain clearly non-English scripts,
    # assume it's English (Whisper is good at transcribing English)
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text)
    if ascii_ratio > 0.8:  # 80% ASCII characters
        return True

    return False


def send_message(text: str, files=None):
    """Send a message to the chatbot with optional files"""
    if not text and not files:
        return

    # Check if text is likely English (more lenient check)
    if text and not is_likely_english(text):
        st.session_state.messages.append({
            "role": "assistant",
            "content": "I apologize, but I'm having trouble understanding that. I can only understand and respond to English. Could you please repeat your question in English about Marrfa properties?"
        })
        return

    # Add user message
    user_content = text if text else "📎 Uploaded file"
    if files:
        file_names = ", ".join([f.name for f in files])
        user_content = f"📎 {file_names}" + (f": {text}" if text else "")

    st.session_state.messages.append({"role": "user", "content": user_content})

    try:
        # Prepare data
        data = {
            "query": text,
            "session_id": st.session_state.user_uuid,
            "is_logged_in": st.session_state.authenticated
        }

        # Prepare files
        request_files = []
        if files:
            for file in files:
                request_files.append(("files", (file.name, file.getvalue(), file.type)))

        # Make request
        if request_files:
            # Send with files
            response = requests.post(
                f"{BASE_API}/chat",
                data=data,
                files=request_files
            )
        else:
            # Send without files
            response = requests.post(f"{BASE_API}/chat", json=data)

        if response.status_code == 200:
            result = response.json()
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["reply"],
                "properties": result.get("properties", [])
            })

            # Track uploaded files
            if files:
                for file in files:
                    st.session_state.uploaded_files.append(file.name)
        else:
            st.error(f"Server error: {response.status_code}")
    except Exception as e:
        st.error(f"Connection error: {str(e)}")


# --- Chat Area ---
chat_container = st.container()
with chat_container:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])
            if m["role"] == "assistant" and m.get("properties"):
                cols = st.columns(3)
                for i, p in enumerate(m["properties"]):
                    with cols[i % 3]:
                        p_from = f"{p['price_from']:,.0f}" if p.get('price_from') else "On Request"
                        img_url = p.get("cover_image") or "https://via.placeholder.com/400x300?text=Marrfa"

                        st.markdown(f"""
                            <div class="prop-card">
                                <img src="{img_url}" class="prop-img">
                                <div class="prop-content">
                                    <div class="prop-title">{p['title']}</div>
                                    <div class="prop-details">📍 {p.get('location') or 'Dubai'}</div>
                                    <div class="prop-price">{p_from} {p.get('currency', 'AED')}</div>
                                    <div class="prop-details">🗓️ Completion: {p.get('completion_year') or 'TBD'}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        if p.get("listing_url"):
                            st.link_button("View details", p["listing_url"], use_container_width=True)

# --- Gemini-style Chat Input with File Upload ---
st.markdown('<div class="footer-container">', unsafe_allow_html=True)

# Create columns for the input area
col_input, col_mic = st.columns([5, 1])

with col_input:
    # Gemini-style chat input with built-in file upload
    chat_data = st.chat_input(
        "Ask about properties, Marrfa company info, or upload files...",
        accept_file=True,  # This adds the '+' icon automatically
        file_type=["pdf", "txt", "docx", "doc", "png", "jpg", "jpeg", "csv", "xlsx", "pptx"],
        key="chat_input"
    )

with col_mic:
    # Voice recording button
    audio = mic_recorder(
        start_prompt="🎤",
        stop_prompt="🛑",
        just_once=True,
        key="mic"
    )

st.markdown('</div>', unsafe_allow_html=True)

# --- Process Chat Input ---
if chat_data:
    # Extract text and files from chat_data
    user_text = chat_data.text
    uploaded_files = chat_data.files if hasattr(chat_data, 'files') else []

    # Check authentication for file uploads
    if uploaded_files and not st.session_state.authenticated:
        st.warning("Please log in to upload files.")
    else:
        send_message(user_text, uploaded_files)
        st.rerun()

# --- Process Voice Input ---
if audio and audio.get("bytes"):
    try:
        # Send audio to backend for transcription
        files = {"file": ("audio.wav", audio["bytes"], "audio/wav")}
        response = requests.post(f"{BASE_API}/transcribe", files=files)

        if response.status_code == 200:
            result = response.json()
            transcript = result.get("text", "")
            error_msg = result.get("error", "")

            if error_msg:
                # Show error but don't add to chat history to avoid repetition
                st.error(f"Voice transcription error: {error_msg}")
                st.rerun()
            elif transcript:
                # Check if transcript is likely English (lenient check)
                if not is_likely_english(transcript):
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "I apologize, but I'm having trouble understanding that. I can only understand and respond to English. Could you please repeat your question in English about Marrfa properties?"
                    })
                    st.rerun()
                else:
                    send_message(transcript)
                    st.rerun()
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "I couldn't detect any speech. Could you please speak clearly in English about Marrfa properties?"
                })
                st.rerun()
        else:
            st.error("Voice transcription service unavailable")
    except Exception as e:
        st.error(f"Voice transcription failed: {str(e)}")

# --- Display Recently Analyzed Files ---
if st.session_state.uploaded_files:
    with st.expander("📁 Recently Uploaded Files", expanded=False):
        for file_name in st.session_state.uploaded_files[-5:]:  # Show last 5
            st.text(f"• {file_name}")