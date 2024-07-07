from pathlib import Path

import torch
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from .search import search, embed, chunk
from .types import SearchQuery, SearchResult
# from .preprocess import file_to_text
# from .minio import upload_files


if __name__ == "__main__":
    texts_path = Path("./texts")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=150,
        chunk_overlap=20,
        length_function=lambda x: len(x.split()),  # 150 words, not characters
        add_start_index=True,
    )
    chunks = chunk(text_splitter)
    texts = [chunk.text for chunk in chunks]

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(MODEL_NAME, device=device)
    embeddings = embed(texts, model)

    query = SearchQuery(text="Burmykov Networks course lecture 11")
    query_embedding = embed([query.text], model)

    results: list[SearchResult] = search(query_embedding, embeddings, chunks)
