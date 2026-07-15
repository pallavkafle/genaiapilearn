import streamlit as st
import google.generativeai as genai

st.title("Gemini Chatbot App")

# ---------- API KEY from secrets (local or cloud) ----------
API_KEY = st.secrets["GEMINI_API_KEY"]

genai.configure(api_key=API_KEY)

# ---------- Auto-select a working model ----------
def get_working_model():
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            return model.name
    raise RuntimeError("No model supports generateContent. Check your API key.")

MODEL_NAME = get_working_model()   # e.g., "models/gemini-1.5-flash-001"
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

    # Build conversation history (correct format for the old library)
    history = [
        {"role": "user" if m["role"] == "user" else "model",
         "parts": [m["content"]]}
        for m in st.session_state.messages
    ]

    # Generate response
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT
    )
    response = model.generate_content(contents=history)
    full_response = response.text

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    with st.chat_message("assistant"):
        st.markdown(full_response)