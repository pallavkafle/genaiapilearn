import streamlit as st
from google import genai
from google.genai import types

st.title('Geminii Chatbot app')

API_KEY = "AQ.Ab8RN6I7YKsGZUApaet-uy3x84h0apw31NOD2vQJGdzJwfPeSg"
client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-flash-latest"
SYSTEM_PROMPT = "You are a helpful assistant. Give answer in a concise and clear manner."

if 'messages' not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.get('messages', []):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("Enter your query here...")
if query:
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})

# ✅ FIXED: added system prompt in contents + fixed Part(text=...)
gemini_history = [
    types.Content(
        role="user",
        parts=[types.Part(text=SYSTEM_PROMPT)]
    )
] + [
    types.Content(
        role="user" if m["role"] == "user" else "model",
        parts=[types.Part(text=m["content"])]
    )
    for m in st.session_state.messages
]

# ✅ FIXED: removed invalid system_prompt from config
response = client.models.generate_content(
    model=MODEL_NAME,
    contents=gemini_history,
    config=types.GenerateContentConfig(
        temperature=0.3
    )
)

full_response = response.text

with st.chat_message("assistant"):
    st.markdown(full_response)

st.session_state.messages.append({"role": "assistant", "content": full_response})