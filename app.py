import os
import uuid
import json
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from pdf_utils import extract_text, chunk_text
from rag_engine import build_vector_store_from_chunks, retrieve_similar_chunks
from embedding_client import generate_text_with_gemini
from session_store import SessionStore, ensure_data_dirs
from vector_store_sqlite import VectorStoreSQLite

load_dotenv()
ensure_data_dirs()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# DB files
VECTORS_DB_PATH = os.path.join("data", "vectors.db")
SESSIONS_DB_PATH = os.path.join("data", "sessions.db")

# single vectorstore instance (in-memory index will reload from sqlite)
vector_store = VectorStoreSQLite(VECTORS_DB_PATH)
session_store = SessionStore(SESSIONS_DB_PATH)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # Save uploaded file
    file_id = str(uuid.uuid4())
    filename = f"{file_id}__{file.filename}"
    upload_path = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract text and chunk
    print(f"Extracting text from {filename}...")
    text = extract_text(upload_path)
    print(f"Chunking text (length: {len(text)} chars)...")
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    print(f"Created {len(chunks)} chunks")

    # Create a pdf_id and store metadata in session DB
    pdf_id = str(uuid.uuid4())
    session_store.add_pdf(pdf_id, filename, upload_path)

    # Build vector store entries for these chunks
    print(f"Building embeddings for {len(chunks)} chunks...")
    build_vector_store_from_chunks(vector_store, pdf_id, chunks)
    print(f"Successfully indexed PDF with pdf_id: {pdf_id}")

    return JSONResponse({"status": "ok", "pdf_id": pdf_id, "message": "Uploaded and indexed"})


@app.post("/ask")
async def ask_question(pdf_id: str = Form(...), question: str = Form(...), session_id: str = Form(None)):
    # ensure session
    if session_id is None:
        session_id = session_store.create_session(pdf_id)

    # retrieve similar chunks
    print(f"Retrieving similar chunks for query: {question}")
    docs = retrieve_similar_chunks(vector_store, question, pdf_id, top_k=5)

    # create context text
    context = "\n\n".join([d["text"] for d in docs])

    # add chat history to prompt - REDUCED TO 2 EXCHANGES!
    history = session_store.get_history(session_id) or []
    history_prompt = "\n".join(history[-4:])  # last 2 exchanges = 4 lines

    prompt = f"{history_prompt}\n\nContext:\n{context}\n\nUser question: {question}\nAnswer based on context:"
    
    # FIXED: Add max_output_tokens parameter!
    resp = generate_text_with_gemini(prompt, max_output_tokens=2048)

    # save into session history
    session_store.append_history(session_id, f"User: {question}")
    session_store.append_history(session_id, f"AI: {resp}")

    return JSONResponse({"answer": resp, "session_id": session_id})


@app.post("/summarize")
async def summarize(pdf_id: str = Form(...)):
    # fetch all chunks for pdf_id
    chunks = vector_store.get_texts_for_pdf(pdf_id)
    if not chunks:
        return JSONResponse({"error": "pdf not found or not indexed"}, status_code=404)

    # If many chunks, summarize per-batch
    if len(chunks) > 20:
        partial_summaries = []
        for i in range(0, len(chunks), 10):
            batch = "\n\n".join(chunks[i:i+10])
            s = generate_text_with_gemini(f"Summarize the following in bullet points:\n\n{batch}", max_output_tokens=1024)
            partial_summaries.append(s)
        # Final summary
        final = generate_text_with_gemini("Summarize these summaries into concise bullet points:\n\n" + "\n\n".join(partial_summaries), max_output_tokens=2048)
    else:
        long_text = "\n\n".join(chunks)
        final = generate_text_with_gemini("Summarize the following in bullet points:\n\n" + long_text, max_output_tokens=2048)

    return JSONResponse({"summary": final})


@app.get("/session/{session_id}")
def get_session(session_id: str):
    history = session_store.get_history(session_id)
    return JSONResponse({"session_id": session_id, "history": history or []})

# --- debug endpoints (paste near top-level after other imports) ---
from fastapi.responses import PlainTextResponse
import sqlite3
from google import genai

# debug: list models available to your client
@app.get("/debug/models")
def debug_models():
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        models = client.models.list()
        names = [m.name for m in models]
        return {"models": names}
    except Exception as e:
        return {"error": str(e)}

# debug: list all chunk texts stored for a pdf_id (vector sqlite)
@app.get("/debug/pdf/{pdf_id}/chunks")
def debug_pdf_chunks(pdf_id: str):
    try:
        texts = vector_store.get_texts_for_pdf(pdf_id)
        return {"count": len(texts), "chunks": texts[:50]}
    except Exception as e:
        return {"error": str(e)}

# debug: list stored embeddings (shows dims and sample values)
@app.get("/debug/pdf/{pdf_id}/embeddings")
def debug_pdf_embeddings(pdf_id: str):
    try:
        rows = vector_store.get_all_embeddings_for_pdf(pdf_id)
        out = [{"chunk_index": r["chunk_index"], "dim": int(r["embedding"].shape[0]),
                "sample": r["embedding"].tolist()[:8]} for r in rows]
        return {"count": len(out), "rows": out}
    except Exception as e:
        return {"error": str(e)}

# debug: retrieval for a query (returns chunks + scores)
@app.get("/debug/retrieve")
def debug_retrieve(pdf_id: str, q: str, top_k: int = 5):
    try:
        docs = retrieve_similar_chunks(vector_store, q, pdf_id, top_k=top_k)
        return {"query": q, "results": docs}
    except Exception as e:
        return {"error": str(e)}
    
