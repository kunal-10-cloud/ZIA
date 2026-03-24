"""
Zia Internal Testing UI
========================
Streamlit app for internal team to test Zia conversations.

Features:
  - Clean chat interface
  - Thumbs up/down feedback per response
  - New conversation button
  - Tester identified by their Streamlit login email

Deploy to Streamlit Community Cloud:
  1. Push this file to your repo root (or streamlit/)
  2. Connect repo to Streamlit Community Cloud
  3. Set secrets in the Streamlit Cloud dashboard:
       BACKEND_URL = "https://your-backend-url.com"
  4. Under app Settings → Sharing → set to "Only specific people"
     and add tester email addresses

Auth: handled by Streamlit Community Cloud viewer authentication.
No password code needed here — Streamlit manages it.
"""

import streamlit as st
import requests
import json
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zia — Internal Testing",
    page_icon="💬",
    layout="centered",
)

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# ── Get tester identity ────────────────────────────────────────────────────────
# Streamlit Community Cloud provides st.experimental_user.email
# Falls back gracefully if running locally
try:
    tester_email = st.experimental_user.email or "local-tester"
except Exception:
    tester_email = "local-tester"

# ── Session state init ─────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []   # list of {role, content, meta}
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = set()  # set of turn_numbers already rated


# ── API helpers ────────────────────────────────────────────────────────────────

def send_message(message: str) -> dict | None:
    """Sends a message to the Zia backend and returns the response dict."""
    try:
        payload = {"message": message}
        if st.session_state.session_id:
            payload["session_id"] = st.session_state.session_id

        r = requests.post(
            f"{BACKEND_URL}/chat",
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        st.error("Request timed out. The backend may be slow — try again.")
        return None
    except Exception as e:
        st.error(f"Backend error: {e}")
        return None


def submit_feedback(turn_number: int, message: str, response: str,
                    active_skill: str, rating: str, note: str = "") -> bool:
    """Sends feedback to the backend."""
    try:
        r = requests.post(
            f"{BACKEND_URL}/feedback",
            json={
                "session_id"  : st.session_state.session_id,
                "turn_number" : turn_number,
                "message"     : message,
                "response"    : response,
                "active_skill": active_skill,
                "rating"      : rating,
                "tester_email": tester_email,
                "note"        : note,
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def reset_session():
    """Clears the current session and starts fresh."""
    if st.session_state.session_id:
        try:
            requests.post(
                f"{BACKEND_URL}/chat/reset",
                params={"session_id": st.session_state.session_id},
                timeout=5,
            )
        except Exception:
            pass
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.feedback_given = set()


# ── Header ─────────────────────────────────────────────────────────────────────

col1, col2 = st.columns([5, 1])
with col1:
    st.markdown("### Zia — Internal Testing")
    st.caption(f"Logged in as: {tester_email}")
with col2:
    if st.button("New chat", type="secondary"):
        reset_session()
        st.rerun()

st.divider()

# ── Conversation display ───────────────────────────────────────────────────────

for msg in st.session_state.messages:
    role    = msg["role"]
    content = msg["content"]
    meta    = msg.get("meta", {})

    with st.chat_message(role):
        st.write(content)

        # Feedback buttons — only on assistant messages, only once per turn
        if role == "assistant" and meta:
            turn_number  = meta.get("turn_number", 0)
            active_skill = meta.get("active_skill", "")
            user_message = meta.get("user_message", "")

            if turn_number not in st.session_state.feedback_given:
                fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 8])

                with fb_col1:
                    if st.button("👍", key=f"up_{turn_number}", help="Good response"):
                        if submit_feedback(
                            turn_number=turn_number,
                            message=user_message,
                            response=content,
                            active_skill=active_skill,
                            rating="up",
                        ):
                            st.session_state.feedback_given.add(turn_number)
                            st.rerun()

                with fb_col2:
                    if st.button("👎", key=f"down_{turn_number}", help="Bad response"):
                        if submit_feedback(
                            turn_number=turn_number,
                            message=user_message,
                            response=content,
                            active_skill=active_skill,
                            rating="down",
                        ):
                            st.session_state.feedback_given.add(turn_number)
                            st.rerun()

            else:
                st.caption("Feedback recorded.")

# ── Chat input ─────────────────────────────────────────────────────────────────

if prompt := st.chat_input("Talk to Zia..."):

    # Show user message immediately
    st.session_state.messages.append({
        "role"   : "user",
        "content": prompt,
    })

    with st.chat_message("user"):
        st.write(prompt)

    # Call backend
    with st.chat_message("assistant"):
        with st.spinner(""):
            result = send_message(prompt)

        if result:
            # Update session ID
            st.session_state.session_id = result["session_id"]

            response_text = result["response"]
            st.write(response_text)

            # Store with metadata for feedback buttons
            st.session_state.messages.append({
                "role"   : "assistant",
                "content": response_text,
                "meta"   : {
                    "turn_number" : result["turn_number"],
                    "active_skill": result["active_skill"],
                    "user_message": prompt,
                },
            })

            st.rerun()