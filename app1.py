import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import NotFound, Unauthenticated
import PyPDF2          # ===== NEW: For reading PDFs
import io              # ===== NEW: For handling byte streams

st.set_page_config(page_title="Document Q&A Bot", page_icon="📚")
st.title("📚 Document Q&A Bot")

# ---------- Get API key ----------
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("🚨 API key not found! Please set the 'GEMINI_API_KEY' secret.")
    st.stop()

try:
    genai.configure(api_key=API_KEY)
    list(genai.list_models())
except Unauthenticated:
    st.error("🚨 Invalid API key! Check your secret.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Connection error: {e}")
    st.stop()

# ---------- Model selection ----------
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
            model.generate_content("test")
            return name
        except NotFound:
            continue
        except Exception:
            continue
    available = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
    raise RuntimeError(f"No working model. Available: {available}")

try:
    MODEL_NAME = get_working_model()
except RuntimeError as e:
    st.error(f"🚨 {e}")
    st.stop()

# ============================================
# ===== NEW: Document Upload & Processing =====
# ============================================

# Initialize chunks in session state
if "doc_chunks" not in st.session_state:
    st.session_state.doc_chunks = []

# File uploader
uploaded_file = st.file_uploader(
    "Upload a PDF or TXT file to ask questions about it",
    type=["pdf", "txt"],
    label_visibility="collapsed"
)

if uploaded_file:
    # Show file name and size
    st.info(f"📄 Loaded: **{uploaded_file.name}** ({uploaded_file.size // 1024} KB)")
    
    # Extract text based on file type
    text = ""
    if uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    else:  # TXT file
        text = uploaded_file.read().decode("utf-8")
    
    # Chunk the text (split into ~2000 character pieces)
    chunk_size = 2000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    st.session_state.doc_chunks = chunks
    st.success(f"✅ Document processed! Split into {len(chunks)} chunks.")
    
    # Optional: Show a preview
    with st.expander("📖 Preview first 500 characters"):
        st.write(text[:500] + "...")

# ============================================
# ===== NEW: Helper function to find relevant chunks =====
# ============================================

def get_relevant_chunks(query, chunks, top_k=3):
    """Find the most relevant chunks based on word overlap."""
    query_words = set(query.lower().split())
    scored = []
    for chunk in chunks:
        chunk_words = chunk.lower().split()
        # Count how many query words appear in the chunk
        score = sum(1 for word in query_words if word in chunk_words)
        scored.append((score, chunk))
    
    # Sort by score (highest first) and take top_k
    scored.sort(reverse=True, key=lambda x: x[0])
    relevant = [chunk for score, chunk in scored if score > 0][:top_k]
    
    # If no matches found, return the first 2 chunks as fallback
    if not relevant and chunks:
        return chunks[:2]
    return relevant

# ---------- Session state for chat ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Display chat history ----------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- User input ----------
query = st.chat_input("Ask about your document (or anything else)...")
if query:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # ============================================
    # ===== NEW: Build context if document is loaded =====
    # ============================================
    
    context = ""
    if st.session_state.doc_chunks:
        relevant_chunks = get_relevant_chunks(query, st.session_state.doc_chunks)
        if relevant_chunks:
            context = "\n\n---\n\n".join(relevant_chunks)
            context_prompt = (
                f"You are a document Q&A assistant. Answer the user's question **only** using the provided context. "
                f"If the answer is not in the context, politely say 'I couldn't find that information in the document.'\n\n"
                f"### Context:\n{context}\n\n"
                f"### Question:\n{query}"
            )
        else:
            context_prompt = query  # Fallback to normal chat if no context found
    else:
        context_prompt = query  # No document loaded, normal chat

    # Build history for Gemini
    # If we have context, we override the last user message with the context_prompt
    # We only send the last few messages to keep it clean, OR we just send the new prompt.
    # For simplicity, we'll just send the context_prompt as a single user turn (no history),
    # but we keep the history in the UI for the user.
    # This avoids token limit issues and keeps the AI focused.
    
    if context:  # Document mode
        history = [
            {"role": "user", "parts": [context_prompt]}
        ]
    else:  # Normal chat mode
        # Use the last 5 messages to keep token usage low
        history = [
            {"role": "user" if m["role"] == "user" else "model",
             "parts": [m["content"]]}
            for m in st.session_state.messages[-5:]  # take last 5 turns
        ]

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT
        )
        response = model.generate_content(contents=history)
        full_response = response.text

        # Display assistant response
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        with st.chat_message("assistant"):
            st.markdown(full_response)

        # If document mode, show which chunks were used (optional)
        if context and relevant_chunks:
            with st.expander("📄 Sources used for this answer"):
                for i, chunk in enumerate(relevant_chunks):
                    st.write(f"**Chunk {i+1}:**")
                    st.write(chunk[:300] + "...")

    except NotFound:
        st.error(f"🚨 Model '{MODEL_NAME}' stopped working. Check available models.")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Generation error: {e}")
        st.stop()