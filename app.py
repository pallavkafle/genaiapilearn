import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import NotFound, Unauthenticated

st.title("Gemini Chatbot App")

# ---------- Get API key ----------
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("🚨 API key not found! Please set the 'GEMINI_API_KEY' secret in Streamlit Cloud (Settings → Secrets).")
    st.stop()

# ---------- Configure Gemini ----------
try:
    genai.configure(api_key=API_KEY)
    # Test authentication by listing models (optional)
    list(genai.list_models())
except Unauthenticated:
    st.error("🚨 Invalid API key! Check your secret – it must be a valid key from Google AI Studio.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Connection error: {e}")
    st.stop()

# ---------- Model selection (hardcoded to a known working model) ----------
MODEL_NAME = "gemini-1.5-flash"   # stable, widely available
SYSTEM_PROMPT = "You are a helpful assistant. Give concise and clear answers."

# ---------- Session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Display history ----------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- User input ----------
query = st.chat_input("Enter your query here...")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Build conversation history
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
        st.error(f"🚨 Model '{MODEL_NAME}' is not available in your region or API version. Try a different model (e.g., 'gemini-1.5-pro').")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Generation error: {e}")
        st.stop()