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
    list(genai.list_models())  # test authentication
except Unauthenticated:
    st.error("🚨 Invalid API key! Check your secret.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Connection error: {e}")
    st.stop()

# ---------- Try a list of models until one works ----------
MODEL_CANDIDATES = [
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "gemini-pro",
    "gemini-2.0-flash-exp",  # might be available in some regions
]
SYSTEM_PROMPT = "You are a helpful assistant. Give concise and clear answers."

def get_working_model():
    for name in MODEL_CANDIDATES:
        try:
            # Quick test: can we create a model and make a tiny request?
            model = genai.GenerativeModel(model_name=name)
            # Minimal test (empty prompt) to see if it's valid
            model.generate_content("test")  # might raise NotFound
            return name
        except NotFound:
            continue
        except Exception:
            continue
    # If we get here, none worked – list all available models
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

# ---------- Session state ----------
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
        st.error(f"🚨 Model '{MODEL_NAME}' stopped working. Run the debug expander to see available models.")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Generation error: {e}")
        st.stop()