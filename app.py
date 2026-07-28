import streamlit as st
import re
from typing import Literal

from dotenv import load_dotenv
from uuid import uuid4

from youtube_transcript_api import YouTubeTranscriptApi

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from theme import apply_youtube_theme, youtube_header

# --------------------------------------------------------------------------
# 1. Setup — models, vector store (cached so weights load once per session)
# --------------------------------------------------------------------------

load_dotenv()


@st.cache_resource
def get_embedding_model():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


@st.cache_resource
def get_llm():
    return ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.3)


@st.cache_resource
def get_llm_creative():
    return ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.7)


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


embedding_model = get_embedding_model()
llm = get_llm()
llm_creative = get_llm_creative()
vector_store, index = get_vector_store()

parser = StrOutputParser()

WINDOW_SECONDS = 60
OVERLAP_SECONDS = 10


# --------------------------------------------------------------------------
# 2. Ingestion
# --------------------------------------------------------------------------

def _extract_video_id(inputs: dict) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", inputs["url"])
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {inputs['url']}")
    return match.group(1)


def _fetch_and_chunk(video_id: str) -> list[Document]:
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
                metadata={"source": video_id, "start": round(window_start, 2), "end": round(last_end, 2)},
            ))
            overlap_start = max(window_start, last_end - OVERLAP_SECONDS)
            current_text = [s.text for s in snippets if overlap_start <= s.start < last_end]
            window_start = overlap_start

    if current_text:
        chunks.append(Document(
            page_content=" ".join(current_text).strip(),
            metadata={"source": video_id, "start": round(window_start, 2), "end": round(last_end, 2)},
        ))

    return chunks


def _is_already_indexed(video_id: str) -> bool:
    probe = index.query(
        vector=[0.0] * 384,
        filter={"source": video_id},
        top_k=1,
        include_metadata=False,
    )
    return len(probe.get("matches", [])) > 0


def _load_video(inputs: dict) -> dict:
    video_id = inputs["video_id"]
    texts = _fetch_and_chunk(video_id)
    whole_content = " ".join(doc.page_content for doc in texts)

    already_indexed = _is_already_indexed(video_id)
    if not already_indexed:
        uuids = [str(uuid4()) for _ in texts]
        vector_store.add_documents(documents=texts, ids=uuids)

    return {**inputs, "texts": texts, "whole_content": whole_content, "already_indexed": already_indexed}


# {url} -> {url, video_id, texts, whole_content, already_indexed}
ingest_chain = (
    RunnablePassthrough.assign(video_id=RunnableLambda(_extract_video_id))
    | RunnableLambda(_load_video)
)


# --------------------------------------------------------------------------
# 3. Summarize pipeline — used ONLY by the "Summarize" button
# --------------------------------------------------------------------------

prompt_summarize_short = PromptTemplate(
    template="""Summarize the following video in short form from the given text.
Start with a suggested video title, then add bullet points for each key point.

text: {text}""",
    input_variables=["text"],
)

summarize_chain = prompt_summarize_short | llm_creative | parser


# --------------------------------------------------------------------------
# 4. Question-answering pipeline — used ONLY by the "Ask a question" button
#    Includes chat memory via System / Human / AI messages.
# --------------------------------------------------------------------------

def _single_query_search(inputs: dict) -> list[Document]:
    return vector_store.max_marginal_relevance_search(
        inputs["query"],
        k=3,
        fetch_k=10,
        filter={"source": inputs["video_id"]},
    )


single_query_retriever = RunnableLambda(_single_query_search)


def _retrieve_context(inputs: dict) -> str:
    """Retrieve relevant chunks for the current question (single query — chat memory
    already carries prior context, so query expansion is less necessary turn-to-turn)."""
    results = single_query_retriever.invoke({"query": inputs["query"], "video_id": inputs["video_id"]})
    seen = set()
    deduped_chunks = []
    for doc in results:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            deduped_chunks.append(doc.page_content)
    return "\n\n".join(f"[Excerpt {i + 1}]\n{chunk}" for i, chunk in enumerate(deduped_chunks))


qa_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant answering questions about a specific YouTube video.
Use ONLY the transcript excerpts below to answer — do not use outside knowledge.
If the excerpts don't contain the answer, say so honestly.

Transcript excerpts:
{description}"""),
    MessagesPlaceholder("chat_history"),
    ("human", "{query}"),
])

qa_chain = (
    RunnablePassthrough.assign(description=RunnableLambda(_retrieve_context))
    | qa_prompt
    | llm
    | parser
)


# --------------------------------------------------------------------------
# 5. Streamlit UI
# --------------------------------------------------------------------------

# apply_youtube_theme()
youtube_header("Video Summarizer & Q&A")

if "current_video" not in st.session_state:
    st.session_state.current_video = None
if "video_state" not in st.session_state:
    st.session_state.video_state = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list[HumanMessage | AIMessage]


def get_video_state(url: str) -> dict:
    """Ingest (or reuse cached) video state. Resets chat memory on a new video."""
    if st.session_state.current_video != url or st.session_state.video_state is None:
        st.session_state.video_state = ingest_chain.invoke({"url": url})
        st.session_state.current_video = url
        st.session_state.chat_history = []
    return st.session_state.video_state


user_video_link = st.text_input("Insert your video link")

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "Summarize",
        disabled=not user_video_link,
        width="stretch",
        type="primary",
        key="summarize_button",
    ):
        with st.spinner("Fetching video and summarizing..."):
            video_state = get_video_state(user_video_link)
            summary = summarize_chain.invoke({"text": video_state["whole_content"]})
        st.markdown(summary)

with col2:
    question = st.text_input("Ask something about the video", key="qa_input")
    ask_clicked = st.button(
        "Ask a question",
        disabled=not user_video_link or not question,
        width="stretch",
        type="secondary",
        key="ask_question",
    )
    if ask_clicked:
        with st.spinner("Thinking..."):
            video_state = get_video_state(user_video_link)
            response = qa_chain.invoke({
                "query": question,
                "video_id": video_state["video_id"],
                "chat_history": st.session_state.chat_history,
            })
        st.session_state.chat_history.append(HumanMessage(content=question))
        st.session_state.chat_history.append(AIMessage(content=response))

# Render running conversation, chat-style, below both actions
for msg in st.session_state.chat_history:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.write(msg.content)
