from pypdf import PdfReader
import re
import math

def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    texts = []
    for p in reader.pages:
        t = p.extract_text()
        if t:
            texts.append(t)
    return "\n\n".join(texts)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    # naive sentence-aware chunker
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += (chunk_size - overlap)
    return chunks
