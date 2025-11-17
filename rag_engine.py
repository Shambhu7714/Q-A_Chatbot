# from embedding_client import get_embeddings
# from vector_store_sqlite import VectorStoreSQLite
# import numpy as np

# def build_vector_store_from_chunks(vector_store: VectorStoreSQLite, pdf_id: str, chunks: list):
#     """
#     For each chunk produce embeddings and store them in sqlite via vector_store.add_embeddings
#     """
#     # process in batches if needed
#     embeddings = get_embeddings(chunks)
#     vector_store.add_embeddings(pdf_id, chunks, embeddings)

# def retrieve_similar_chunks(vector_store: VectorStoreSQLite, query: str, pdf_id: str, top_k: int = 5):
#     q_emb = get_embeddings(query)[0]
#     results = vector_store.similarity_search(q_emb, pdf_id, top_k=top_k)
#     # return list of dicts with text+score
#     return results

from embedding_client import get_embeddings

def build_vector_store_from_chunks(vector_store, pdf_id, chunks):
    embeddings = get_embeddings(chunks)
    vector_store.add_embeddings(pdf_id, chunks, embeddings)


def retrieve_similar_chunks(vector_store, query, pdf_id, top_k=5):
    q_emb = get_embeddings(query)[0]
    return vector_store.similarity_search(q_emb, pdf_id, top_k=top_k)
