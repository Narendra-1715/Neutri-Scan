import json
import os
import time

import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client as TwilioClient

from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

PRIMARY_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.5-flash-lite"

st.set_page_config(page_title="MacroSnap - AI Nutrition & Macros", page_icon="🥗", layout="centered")

# Read secrets safely without crashing
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
TWILIO_ACCOUNT_SID = st.secrets.get("TWILIO_ACCOUNT_SID") or os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = st.secrets.get("TWILIO_AUTH_TOKEN") or os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = st.secrets.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_CONTENT_SID = st.secrets.get("TWILIO_CONTENT_SID", "")

is_twilio_configured = bool(
    TWILIO_ACCOUNT_SID
    and not TWILIO_ACCOUNT_SID.startswith("your-")
    and TWILIO_AUTH_TOKEN
    and not TWILIO_AUTH_TOKEN.startswith("your-")
)


@st.cache_resource
def get_gemini_client():
    if not GEMINI_API_KEY:
        st.error("Missing GEMINI_API_KEY. Please configure it in .streamlit/secrets.toml")
        st.stop()
    return genai.Client(api_key=GEMINI_API_KEY)


@st.cache_resource
def get_twilio_client():
    if is_twilio_configured:
        try:
            return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except Exception:
            return None
    return None


gemini_client = get_gemini_client()
twilio_client = get_twilio_client()


def init_chat_session(model_name=PRIMARY_MODEL, history=None):
    kwargs = {
        "model": model_name,
        "config": types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    }
    if history:
        kwargs["history"] = history
    return gemini_client.chats.create(**kwargs)


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.markdown(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    if "chat" not in st.session_state:
        st.session_state.chat = init_chat_session(PRIMARY_MODEL)

    last_error = None
    # 1. Try with the existing chat session (retrying on transient 503 / 429 errors)
    for attempt in range(2):
        try:
            response = st.session_state.chat.send_message(parts)
            return response.text
        except Exception as error:
            last_error = error
            err_str = str(error)
            if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                time.sleep(1.2 * (attempt + 1))
                continue
            break

    # 2. If primary model is experiencing high demand (503), failover to fallback model
    try:
        current_history = []
        try:
            current_history = st.session_state.chat.get_history()
        except Exception:
            pass

        st.session_state.chat = init_chat_session(FALLBACK_MODEL, history=current_history)
        response = st.session_state.chat.send_message(parts)
        return response.text
    except Exception as fallback_error:
        return (
            f"⚠️ **Temporary Demand Spike**: The AI vision service is currently experiencing heavy traffic. "
            f"Please wait a few seconds and send your message again.\n\n"
            f"*(Details: {fallback_error or last_error})*"
        )


def clean_whatsapp_text(text):
    if not text:
        return "No nutrition summary available."
    # Preserve clean line breaks instead of collapsing into one line
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    cleaned = "\n".join(lines)
    return cleaned[:1500] + "..." if len(cleaned) > 1500 else cleaned


def send_whatsapp(to_number, user_name, summary):
    if not twilio_client:
        return False, "Twilio WhatsApp is not configured. Please add valid credentials to `.streamlit/secrets.toml`."
    if not to_number:
        return False, "No WhatsApp number provided during onboarding."

    try:
        content_variables = json.dumps(
            {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
        )
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_number}",
            content_sid=TWILIO_CONTENT_SID,
            content_variables=content_variables,
        )
        return True, message.sid
    except Exception as error:
        return False, str(error)


# Step 1: Onboarding
if "onboarded" not in st.session_state:
    st.title("🥗 MacroSnap")
    st.caption("Snap it. Track ingredients, protein & calories. Text yourself the results.")
    with st.form("onboarding_form"):
        name = st.text_input("Your name", placeholder="e.g. Alex")
        whatsapp_number = st.text_input(
            "WhatsApp number (optional, with country code)",
            placeholder="+91XXXXXXXXXX",
            help="Optional: MacroSnap will text your meal summary here.",
        )
        submitted = st.form_submit_button("Let's go 🚀", use_container_width=True)

    if submitted:
        user_name = name.strip() or "Friend"
        st.session_state.name = user_name
        st.session_state.whatsapp_number = whatsapp_number.strip()
        st.session_state.chat = init_chat_session(PRIMARY_MODEL)
        st.session_state.messages = []
        st.session_state.onboarded = True
        st.rerun()
    st.stop()

# Sidebar: Controls & Info
with st.sidebar:
    st.header("🥗 MacroSnap")
    st.markdown(f"**User**: {st.session_state.name}")
    if st.session_state.whatsapp_number:
        st.markdown(f"**WhatsApp**: `{st.session_state.whatsapp_number}`")
    else:
        st.caption("WhatsApp: Not provided (optional)")

    st.divider()

    if st.button("🔄 Start New Meal / Reset", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat = init_chat_session(PRIMARY_MODEL)
        st.rerun()

    st.caption("💡 **Tip**: Attach a food photo using the 📎 paperclip button in the chat input below, or simply describe what you ate.")
    st.divider()
    st.caption("⚠️ *AI estimates are approximations for informational purposes and not medical advice.*")

# Step 2: Chat Interface Header
header_col, button_col = st.columns([5, 2], vertical_alignment="center")

with header_col:
    st.title("🥗 MacroSnap")

with button_col:
    send_disabled = len(st.session_state.messages) <= 2 or not is_twilio_configured
    button_help = "Requires valid Twilio credentials in secrets.toml" if not is_twilio_configured else ""
    if st.button("📤 Send to WhatsApp", disabled=send_disabled, help=button_help, use_container_width=True):
        with st.spinner("Summarizing your meals..."):
            summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
        success, info = send_whatsapp(st.session_state.whatsapp_number, st.session_state.name, summary)
        if success:
            st.success("Sent! Check your WhatsApp.")
        else:
            st.error(f"Couldn't send: {info}")

st.caption(f"Logged in as **{st.session_state.name}**")

# Display conversation messages
if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

# Chat Input with image upload support
user_input = st.chat_input(
    "Ask a question, or attach a photo of your meal (📎)",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))

    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append(
            "Analyze this food item: identify the dish, list all visible ingredients, "
            "estimate calories and protein, breakdown other macros (carbs, fats, fiber), "
            "and provide extra nutritional highlights and allergen info."
        )

    with st.spinner("Analyzing ingredients and macros..."):
        answer = ask_gemini(parts)
    add_message("assistant", "text", answer)