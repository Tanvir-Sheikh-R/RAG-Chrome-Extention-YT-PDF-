"""
AI Content Summarizer — YouTube videos or uploaded documents.

Flow (tracked in st.session_state.stage):
    "input"   -> pick a source (Document or YouTube), submit it
    "loading" -> fetch + chunk + embed + summarize (shows progress)
    "results" -> tabs for Original Content / Summary, plus an AI Tutor chat panel

Kept intentionally simple: plain functions for each step, three small
prompt -> llm -> parser chains for the actual AI calls. No extra layers.
"""

import re
import hashlib
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from theme import apply_theme, hero_title, loading_card, content_card, tutor_header, tutor_empty_state

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

load_dotenv()

WINDOW_SECONDS = 60      # youtube chunk window
OVERLAP_SECONDS = 10
DOC_CHUNK_SIZE = 1000    # document chunk size (characters)
DOC_CHUNK_OVERLAP = 150


# --------------------------------------------------------------------------
# 1. Models & vector store — cached so they load once, not on every rerun
# --------------------------------------------------------------------------

@st.cache_resource
def get_embedding_model():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


@st.cache_resource
def get_llm():
    return ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.3)


@st.cache_resource
def get_vector_store():
    pc = Pinecone()
    index_name = "rag-extention"
    if not pc.has_index(index_name):
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    idx = pc.Index(index_name)
    return PineconeVectorStore(index=idx, embedding=get_embedding_model()), idx


llm = get_llm()
vector_store, pinecone_index = get_vector_store()
parser = StrOutputParser()


# --------------------------------------------------------------------------
# 2. Ingestion — one function per step, called in a simple sequence
# --------------------------------------------------------------------------

def extract_youtube_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    if not match:
        raise ValueError(f"Could not extract a video ID from URL: {url}")
    return match.group(1)


def chunk_youtube_transcript(video_id: str) -> list[Document]:
    """Group transcript snippets into ~60s windows with 10s overlap."""
    transcript = YouTubeTranscriptApi().fetch(video_id, languages=["en", "bn", "hi"])
    snippets = transcript.snippets

    chunks: list[Document] = []
    current_text: list[str] = []
    window_start = snippets[0].start if snippets else 0.0
    last_end = window_start

    for snippet in snippets:
        current_text.append(snippet.text)
        last_end = snippet.start + snippet.duration

        if last_end - window_start >= WINDOW_SECONDS:
            chunks.append(Document(
                page_content=" ".join(current_text).strip(),
                metadata={"source": video_id},
            ))
            overlap_start = max(window_start, last_end - OVERLAP_SECONDS)
            current_text = [s.text for s in snippets if overlap_start <= s.start < last_end]
            window_start = overlap_start

    if current_text:
        chunks.append(Document(page_content=" ".join(current_text).strip(), metadata={"source": video_id}))

    return chunks


def read_uploaded_file(uploaded_file) -> str:
    """Extract plain text from an uploaded .txt or .pdf file."""
    if uploaded_file.name.lower().endswith(".pdf"):
        if PdfReader is None:
            raise RuntimeError("PDF support requires the 'pypdf' package: pip install pypdf")
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return uploaded_file.read().decode("utf-8", errors="ignore")


def chunk_document_text(text: str, source_id: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=DOC_CHUNK_SIZE, chunk_overlap=DOC_CHUNK_OVERLAP)
    return [
        Document(page_content=chunk, metadata={"source": source_id})
        for chunk in splitter.split_text(text)
    ]


def is_already_indexed(source_id: str) -> bool:
    probe = pinecone_index.query(
        vector=[0.0] * 384,
        filter={"source": source_id},
        top_k=1,
        include_metadata=False,
    )
    return len(probe.get("matches", [])) > 0


def embed_and_store(chunks: list[Document]) -> None:
    uuids = [str(uuid4()) for _ in chunks]
    vector_store.add_documents(documents=chunks, ids=uuids)


def ingest_youtube(url: str) -> dict:
    """Returns {"source_id": video_id, "whole_content": full transcript text}."""
    video_id = extract_youtube_id(url)
    chunks = chunk_youtube_transcript(video_id)
    if not is_already_indexed(video_id):
        embed_and_store(chunks)
    whole_content = " ".join(doc.page_content for doc in chunks)
    return {"source_id": video_id, "whole_content": whole_content}


def ingest_document(uploaded_file) -> dict:
    """Returns {"source_id": content hash, "whole_content": extracted text}."""
    text = read_uploaded_file(uploaded_file)
    source_id = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    chunks = chunk_document_text(text, source_id)
    if not is_already_indexed(source_id):
        embed_and_store(chunks)
    return {"source_id": source_id, "whole_content": text}


# --------------------------------------------------------------------------
# 3. AI chains — summarize, and Q&A with chat memory
# --------------------------------------------------------------------------

prompt_summarize = PromptTemplate(
    template="""Summarize the following content in short form.
Start with a suggested title, then add bullet points for each key idea.

content: {text}""",
    input_variables=["text"],
)
summarize_chain = prompt_summarize | llm | parser


def retrieve_context(query: str, source_id: str) -> str:
    """Fetch the most relevant chunks for a question, scoped to this source only."""
    results = vector_store.max_marginal_relevance_search(
        query, k=4, fetch_k=10, filter={"source": source_id}
    )
    return "\n\n".join(doc.page_content for doc in results)


qa_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful tutor answering questions about the content below.
Use ONLY these excerpts — do not use outside knowledge. If they don't contain the answer, say so.

Excerpts:
{context}"""),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])
qa_chain = qa_prompt | llm | parser


# --------------------------------------------------------------------------
# 4. Streamlit app
# --------------------------------------------------------------------------

apply_theme()

if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "youtube"
if "source" not in st.session_state:
    st.session_state.source = None       # {"source_id":..., "whole_content":...}
if "summary" not in st.session_state:
    st.session_state.summary = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def start_new() -> None:
    st.session_state.stage = "input"
    st.session_state.source = None
    st.session_state.summary = None
    st.session_state.chat_history = []


# ---- Stage: INPUT ---------------------------------------------------------
if st.session_state.stage == "input":
    hero_title("AI Content", "Summarizer", "Summarize any YouTube video or document instantly with AI.")

    tab_col1, tab_col2, _ = st.columns([1, 1, 4])
    with tab_col1:
        if st.button("📄 Document", type="primary" if st.session_state.input_mode == "document" else "secondary"):
            st.session_state.input_mode = "document"
            st.rerun()
    with tab_col2:
        if st.button("▶ YouTube", type="primary" if st.session_state.input_mode == "youtube" else "secondary"):
            st.session_state.input_mode = "youtube"
            st.rerun()

    st.write("")

    if st.session_state.input_mode == "youtube":
        url_col, btn_col = st.columns([5, 1])
        with url_col:
            youtube_url = st.text_input("YouTube URL", placeholder="Paste a YouTube URL here...", label_visibility="collapsed")
        with btn_col:
            submit = st.button("Summarize →", type="primary", disabled=not youtube_url, width="stretch")
        if submit:
            st.session_state.pending_input = ("youtube", youtube_url)
            st.session_state.stage = "loading"
            st.rerun()

    else:  # document mode
        uploaded_file = st.file_uploader("Upload a document", type=["txt", "pdf"], label_visibility="collapsed")
        submit = st.button("Summarize →", type="primary", disabled=not uploaded_file)
        if submit:
            st.session_state.pending_input = ("document", uploaded_file)
            st.session_state.stage = "loading"
            st.rerun()


# ---- Stage: LOADING ---------------------------------------------------------
elif st.session_state.stage == "loading":
    placeholder = st.empty()
    with placeholder.container():
        loading_card("Generating Summary", "Creating summary...", "Concise summaries help you review faster and retain more.")

    source_type, payload = st.session_state.pending_input
    if source_type == "youtube":
        source = ingest_youtube(payload)
    else:
        source = ingest_document(payload)

    summary = summarize_chain.invoke({"text": source["whole_content"]})

    st.session_state.source = source
    st.session_state.summary = summary
    st.session_state.chat_history = []
    st.session_state.stage = "results"
    placeholder.empty()
    st.rerun()


# ---- Stage: RESULTS ---------------------------------------------------------
elif st.session_state.stage == "results":
    if st.button("← New summary"):
        start_new()
        st.rerun()

    left_col, right_col = st.columns([3, 2])

    with left_col:
        view_col1, view_col2 = st.columns(2)
        with view_col1:
            show_original = st.button("Original Content", type="secondary", key="view_original")
        with view_col2:
            show_summary = st.button("Summary", type="secondary", key="view_summary")

        if "view" not in st.session_state:
            st.session_state.view = "summary"
        if show_original:
            st.session_state.view = "original"
        if show_summary:
            st.session_state.view = "summary"

        if st.session_state.view == "original":
            content_card(st.session_state.source["whole_content"].replace("\n", "<br>"))
        else:
            content_card(st.session_state.summary.replace("\n", "<br>"))

    with right_col:
        tutor_header()
        if not st.session_state.chat_history:
            tutor_empty_state()
        else:
            for msg in st.session_state.chat_history:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                with st.chat_message(role):
                    st.write(msg.content)

        question = st.chat_input("Ask AI assistant...")
        if question:
            context = retrieve_context(question, st.session_state.source["source_id"])
            answer = qa_chain.invoke({
                "question": question,
                "context": context,
                "chat_history": st.session_state.chat_history,
            })
            st.session_state.chat_history.append(HumanMessage(content=question))
            st.session_state.chat_history.append(AIMessage(content=answer))
            st.rerun()
