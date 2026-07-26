import os
import re
from dotenv import load_dotenv
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()
groq_api = os.getenv('GROQ_API_KEY')



def load_youtube_snippets(url: str):
    match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    video_id = match.group(1)
    transcript = YouTubeTranscriptApi().fetch(video_id, languages=['en', 'bn', 'hi'])
    return video_id, transcript.snippets


def chunk_by_time_window(video_id: str, snippets, window_seconds: int = 60, overlap_seconds: int = 10):
    chunks = []
    current_text = []
    window_start = snippets[0].start if snippets else 0.0
    last_end = window_start

    for snippet in snippets:
        current_text.append(snippet.text)
        last_end = snippet.start + snippet.duration

        if last_end - window_start >= window_seconds:
            chunks.append(Document(
                page_content=" ".join(current_text).strip(),
                metadata={"source": video_id, "start": round(window_start, 2), "end": round(last_end, 2)}
            ))
            overlap_start = max(window_start, last_end - overlap_seconds)
            current_text = [s.text for s in snippets if overlap_start <= s.start < last_end]
            window_start = overlap_start

    if current_text:
        chunks.append(Document(
            page_content=" ".join(current_text).strip(),
            metadata={"source": video_id, "start": round(window_start, 2), "end": round(last_end, 2)}
        ))

    return chunks


video_id, snippets = load_youtube_snippets("https://www.youtube.com/watch?v=tL9Lw250spc")
texts = chunk_by_time_window(video_id, snippets, window_seconds=60, overlap_seconds=10)

print(len(texts))
print(texts[0].page_content)