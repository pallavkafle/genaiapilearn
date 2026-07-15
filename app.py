import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import NotFound, Unauthenticated

st.title("Gemini Chatbot App")

# ---------- Get API key ----------
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("🚨 API key not found! Please set the 'GEMINI_API_KEY' secret.")
    st.stop()

try:
    genai.configure(api_key=API_KEY)

    # ---------- DEBUG (remove after fixing) ----------
with st.expander("🔍 Debug Secrets"):
    if "GEMINI_API_KEY" in st.secrets:
        st.success("✅ Secret 'GEMINI_API_KEY' is present.")
        st.write(f"Key starts with: {st.secrets['GEMINI_API_KEY'][:10]}...")
    else:
        st.error("❌ Secret 'GEMINI_API_KEY' NOT found!")
        
    list(genai.list_models())
except Unauthenticated:
    st.error("🚨 Invalid API key! Check your secret.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Connection error: {e}")
    st.stop()

# ---------- Updated model list (based on your region's availability) ----------
MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
    "gemini-2.5-pro",
]
SYSTEM_PROMPT = "You are a helpful assistant. Give concise and clear answers."

def get_working_model():
    for name in MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name=name)
            model.generate_content("test")  # quick check
            return name
        except NotFound:
            continue
        except Exception:
            continue
    # If none work, show the full list
    available = []
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            available.append(m.name)
    raise RuntimeError(f"No working model. Available models: {available}")

try:
    MODEL_NAME = get_working_model()
except RuntimeError as e:
    st.error(f"🚨 {e}")
    st.stop()

# ---------- Session state and conversation ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("Enter your query here...")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    history = [
        {"role": "user" if m["role"] == "user" else "model",
         "parts": [m["content"]]}
        for m in st.session_state.messages
    ]

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT
        )
        response = model.generate_content(contents=history)
        full_response = response.text

        st.session_state.messages.append({"role": "assistant", "content": full_response})
        with st.chat_message("assistant"):
            st.markdown(full_response)
    except NotFound:
        st.error(f"🚨 Model '{MODEL_NAME}' stopped working. Run debug to see available models.")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Generation error: {e}")
        st.stop()