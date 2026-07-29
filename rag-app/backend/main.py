import re
import hashlib
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

import fitz
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

load_dotenv()

app = FastAPI(title="AI Content Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WINDOW_SECONDS = 60
OVERLAP_SECONDS = 10
DOC_CHUNK_SIZE = 1000
DOC_CHUNK_OVERLAP = 150

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.3)

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
vector_store = PineconeVectorStore(index=idx, embedding=embeddings)

parser = StrOutputParser()

summarize_prompt = PromptTemplate(
    template="""Summarize the following content in short form.
Start with a suggested title, then add bullet points for each key idea.

content: {text}""",
    input_variables=["text"],
)
summarize_chain = summarize_prompt | llm | parser

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful tutor answering questions about the content below.
Use ONLY these excerpts — do not use outside knowledge. If they don't contain the answer, say so.

Excerpts:
{context}"""),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])
qa_chain = qa_prompt | llm | parser


def extract_youtube_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    if not match:
        raise ValueError(f"Could not extract a video ID from URL: {url}")
    return match.group(1)


def chunk_youtube_transcript(video_id: str) -> list[Document]:
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


def extract_pdf_text(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text().strip()

        if len(text) < 50:
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img).strip()

        text_parts.append(text)

    doc.close()
    return "\n".join(text_parts)


def read_uploaded_file(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    return file_bytes.decode("utf-8", errors="ignore")


def chunk_document_text(text: str, source_id: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=DOC_CHUNK_SIZE, chunk_overlap=DOC_CHUNK_OVERLAP)
    return [
        Document(page_content=chunk, metadata={"source": source_id})
        for chunk in splitter.split_text(text)
    ]


def is_already_indexed(source_id: str) -> bool:
    probe = idx.query(
        vector=[0.0] * 384,
        filter={"source": source_id},
        top_k=1,
        include_metadata=False,
    )
    return len(probe.get("matches", [])) > 0


def embed_and_store(chunks: list[Document]) -> None:
    uuids = [str(uuid4()) for _ in chunks]
    vector_store.add_documents(documents=chunks, ids=uuids)


def retrieve_context(query: str, source_id: str) -> str:
    results = vector_store.max_marginal_relevance_search(
        query, k=4, fetch_k=10, filter={"source": source_id}
    )
    return "\n\n".join(doc.page_content for doc in results)


@app.post("/ingest/youtube")
async def ingest_youtube(url: str = Form(...)):
    video_id = extract_youtube_id(url)
    chunks = chunk_youtube_transcript(video_id)
    if not is_already_indexed(video_id):
        embed_and_store(chunks)
    whole_content = " ".join(doc.page_content for doc in chunks)
    summary = summarize_chain.invoke({"text": whole_content})
    return {"source_id": video_id, "whole_content": whole_content, "summary": summary}


@app.post("/ingest/document")
async def ingest_document(file: UploadFile = File(...)):
    file_bytes = await file.read()
    text = read_uploaded_file(file_bytes, file.filename)
    source_id = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    chunks = chunk_document_text(text, source_id)
    if not is_already_indexed(source_id):
        embed_and_store(chunks)
    summary = summarize_chain.invoke({"text": text})
    return {"source_id": source_id, "whole_content": text, "summary": summary}


class ChatRequest(BaseModel):
    source_id: str
    question: str
    chat_history: list[dict]

@app.post("/chat")
async def chat(req: ChatRequest):
    context = retrieve_context(req.question, req.source_id)
    history = []
    for msg in req.chat_history:
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        else:
            history.append(AIMessage(content=msg["content"]))
    answer = qa_chain.invoke({
        "question": req.question,
        "context": context,
        "chat_history": history,
    })
    return {"answer": answer}
