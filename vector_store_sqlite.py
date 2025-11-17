import sqlite3
import os
import numpy as np
import struct

def ensure_db_exists(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY,
        pdf_id TEXT,
        chunk_index INTEGER,
        text TEXT,
        dim INTEGER,
        embedding BLOB
    )""")
    conn.commit()
    conn.close()

def float32_to_blob(arr: np.ndarray) -> bytes:
    # pack as little-endian floats
    return arr.astype(np.float32).tobytes()

def blob_to_float32(b: bytes, dim: int) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32).reshape((dim,))

class VectorStoreSQLite:
    def __init__(self, db_path):
        self.db_path = db_path
        ensure_db_exists(db_path)

    def add_embeddings(self, pdf_id: str, chunks: list, embeddings: list):
        """
        chunks: list of strings corresponding to embeddings
        embeddings: list of numpy arrays (float32)
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        for idx, (txt, emb) in enumerate(zip(chunks, embeddings)):
            b = float32_to_blob(np.asarray(emb, dtype=np.float32))
            dim = int(len(emb))
            cur.execute("INSERT INTO embeddings (pdf_id, chunk_index, text, dim, embedding) VALUES (?, ?, ?, ?, ?)",
                        (pdf_id, idx, txt, dim, b))
        conn.commit()
        conn.close()

    def get_all_embeddings_for_pdf(self, pdf_id: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, chunk_index, text, dim, embedding FROM embeddings WHERE pdf_id = ?", (pdf_id,))
        rows = cur.fetchall()
        conn.close()
        results = []
        for r in rows:
            vec = blob_to_float32(r[4], r[3])
            results.append({"id": r[0], "chunk_index": r[1], "text": r[2], "embedding": vec})
        return results

    def get_texts_for_pdf(self, pdf_id: str):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT text FROM embeddings WHERE pdf_id = ? ORDER BY chunk_index", (pdf_id,))
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]


    # def similarity_search(self, query_embedding: np.ndarray, pdf_id: str, top_k: int = 5):
    #     """
    #     Brute force cosine similarity search over stored embeddings for a given pdf_id.
    #     Returns list of dicts with 'id','chunk_index','text','score'
    #     """
    #     rows = self.get_all_embeddings_for_pdf(pdf_id)
    #     if not rows:
    #         return []

    #     # build matrix
    #     embs = np.stack([r["embedding"] for r in rows], axis=0)  # shape (N, dim)
    #     q = query_embedding.astype(np.float32)
    #     # cosine sim = (q dot e) / (||q|| * ||e||)
    #     q_norm = np.linalg.norm(q)
    #     e_norms = np.linalg.norm(embs, axis=1)
    #     dots = embs.dot(q)
    #     # prevent division by zero
    #     denom = (e_norms * q_norm) + 1e-12
    #     scores = dots / denom
    #     top_idx = np.argsort(scores)[-top_k:][::-1]
    #     results = []
    #     for i in top_idx:
    #         results.append({
    #             "id": rows[i]["id"],
    #             "chunk_index": rows[i]["chunk_index"],
    #             "text": rows[i]["text"],
    #             "score": float(scores[i])
    #         })
    #     return results

    def similarity_search(self, query_embedding: np.ndarray, pdf_id: str, top_k: int = 5):
        rows = self.get_all_embeddings_for_pdf(pdf_id)
        if not rows:
            return []
        embs = np.stack([r["embedding"] for r in rows], axis=0)
        q = query_embedding.astype(np.float32)
        q_norm = np.linalg.norm(q) + 1e-12
        e_norms = np.linalg.norm(embs, axis=1) + 1e-12
        dots = embs.dot(q)
        scores = dots / (e_norms * q_norm)
        top_idx = np.argsort(scores)[-top_k:][::-1]
        results = []
        for i in top_idx:
            results.append({
                "id": rows[i]["id"],
                "chunk_index": rows[i]["chunk_index"],
                "text": rows[i]["text"],
                "score": float(scores[i])
            })
        return results



