import streamlit as st
import requests
import uuid
import time
from datetime import datetime
import base64

st.set_page_config(page_title="Marrfa AI Chatbot", page_icon="🏠", layout="wide")

# -----------------------------
# CONFIG
# -----------------------------
BASE_API = "https://marrfa-ai-backend-1.onrender.com"  # backend base
CHAT_ENDPOINT = f"{BASE_API}/chat"  # keep as /chat (your backend uses /chat)
LOGIN_ENDPOINT = f"{BASE_API}/api/login"  # ✅ FIXED
SIGNUP_ENDPOINT = f"{BASE_API}/api/signup"  # ✅ FIXED
TRANSCRIBE_ENDPOINT = f"{BASE_API}/api/transcribe"  # ✅ FIXED

# -----------------------------
# SESSION STATE
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0


# -----------------------------
# HELPERS
# -----------------------------
def safe_post_json(url: str, payload: dict, timeout: int = 120):
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        return r
    except Exception as e:
        return None


def render_properties(properties):
    if not properties:
        return

    st.write("### 🏘️ Properties")
    for p in properties[:15]:
        name = p.get("name", "Unnamed Property")
        area = p.get("area", "")
        price = p.get("price", "")
        images = p.get("images") or []

        with st.container(border=True):
            cols = st.columns([1, 2])
            with cols[0]:
                if images and isinstance(images, list) and len(images) > 0:
                    st.image(images[0], use_container_width=True)
                else:
                    st.info("No image")

            with cols[1]:
                st.subheader(name)
                if area:
                    st.write(f"📍 **Area:** {area}")
                if price:
                    st.write(f"💰 **Price:** {price}")

                # optional "View Details" action (you can wire it later)
                if st.button("View details", key=f"view_{p.get('id', name)}"):
                    # send a followup query to backend
                    detail_query = f"Tell me details of {name}"
                    st.session_state.messages.append({"role": "user", "content": detail_query})
                    st.rerun()


# -----------------------------
# SIDEBAR AUTH
# -----------------------------
st.sidebar.title("🔐 Account")

if not st.session_state.is_logged_in:
    auth_tab = st.sidebar.radio("Choose", ["Login", "Sign up"])

    email = st.sidebar.text_input("Email", value=st.session_state.user_email)
    password = st.sidebar.text_input("Password", type="password")

    if auth_tab == "Login":
        if st.sidebar.button("Login"):
            r = safe_post_json(LOGIN_ENDPOINT, {"email": email, "password": password})
            if r is None:
                st.sidebar.error("Network error.")
            elif r.status_code == 200:
                st.sidebar.success("Logged in ✅")
                st.session_state.is_logged_in = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.sidebar.error(r.text)

    else:
        if st.sidebar.button("Create account"):
            r = safe_post_json(SIGNUP_ENDPOINT, {"email": email, "password": password})
            if r is None:
                st.sidebar.error("Network error.")
            elif r.status_code == 200:
                st.sidebar.success("Account created ✅ Please login now.")
            else:
                st.sidebar.error(r.text)

else:
    st.sidebar.success(f"Logged in as: {st.session_state.user_email}")
    if st.sidebar.button("Logout"):
        st.session_state.is_logged_in = False
        st.session_state.user_email = ""
        st.rerun()


# -----------------------------
# MAIN UI
# -----------------------------
st.title("🏠 Marrfa AI Chatbot")
st.caption("Ask about properties, Marrfa company info, or upload files.")

# Show chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])


# -----------------------------
# INPUT + FILE UPLOAD
# -----------------------------
uploaded_files = st.file_uploader(
    "Upload files (PDF/DOCX/TXT) - (Login required)",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True
)

user_msg = st.chat_input("Type your message...")

if user_msg:
    # simple client throttling
    if time.time() - st.session_state.last_request_time < 0.2:
        st.stop()
    st.session_state.last_request_time = time.time()

    st.session_state.messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # If files exist -> multipart; else -> json
            if uploaded_files and len(uploaded_files) > 0:
                if not st.session_state.is_logged_in:
                    st.error("Please login to upload and analyze files.")
                else:
                    multipart_files = []
                    for uf in uploaded_files:
                        multipart_files.append(
                            ("files", (uf.name, uf.getvalue(), uf.type or "application/octet-stream"))
                        )

                    data = {
                        "query": user_msg,
                        "session_id": st.session_state.session_id,
                        "is_logged_in": str(st.session_state.is_logged_in).lower()
                    }

                    try:
                        r = requests.post(CHAT_ENDPOINT, data=data, files=multipart_files, timeout=180)
                        if r.status_code == 200:
                            j = r.json()
                            reply = j.get("reply", "")
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})

                            props = j.get("properties", []) or []
                            render_properties(props)
                        else:
                            st.error(r.text)
                    except Exception as e:
                        st.error(str(e))
            else:
                payload = {
                    "query": user_msg,
                    "session_id": st.session_state.session_id,
                    "is_logged_in": st.session_state.is_logged_in,
                    "files": []
                }
                r = safe_post_json(CHAT_ENDPOINT, payload, timeout=180)
                if r is None:
                    st.error("Network error.")
                elif r.status_code == 200:
                    j = r.json()
                    reply = j.get("reply", "")
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                    props = j.get("properties", []) or []
                    render_properties(props)
                else:
                    st.error(r.text)
