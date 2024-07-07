import os
import logging
import json
import numpy as np
from tqdm import tqdm
from pathlib import Path
from collections import Counter
from langchain.text_splitter import TextSplitter
from sentence_transformers import util, SentenceTransformer

from .types import Chunk, Source, SearchResult


TEXTS_PATH = Path("../texts")
DATA_PATH = Path("../data")
META_PATH = DATA_PATH / "meta.json"


def get_source_by_chunk(chunk_index: str, chunks: list[Chunk]) -> Source:
    for chunk in chunks:
        if chunk.index == chunk_index:
            source_id = chunk.source_id
            break
    else:
        raise ValueError(f"Chunk {chunk_index} not found")

    # load meta data
    with open(META_PATH, "r", encoding="utf-8") as meta_file:
        meta_data = json.load(meta_file)

    sources: list[Source] = []
    for data in meta_data:
        source: Source = Source.model_validate_json(json.dumps(data), strict=True)
        sources.append(source)

    for source in sources:
        if source.id == source_id:
            return source
    else:
        raise ValueError(f"Source {source_id} not found")


def chunk(text_splitter: TextSplitter) -> list[Chunk]:
    # log missing files
    logging.basicConfig(
        filename="missing.log",
        filemode="w",
        level=logging.INFO,
        # format='%',
        encoding="utf-8",
    )

    # get sources data
    with open(META_PATH, "r", encoding="utf-8") as meta_file:
        json_data = json.load(meta_file)

    sources: list[Source] = []
    for data in json_data:
        source: Source = Source.model_validate_json(json.dumps(data), strict=True)
        sources.append(source)

    index = 0
    chunks: list[Chunk] = []
    for source in tqdm(sources, total=len(sources), unit="source"):
        source_text_path = TEXTS_PATH / (source.name + ".txt")
        if not os.path.exists(source_text_path):
            logging.info(source.id)
            continue

        with open(source_text_path, "r", encoding="utf-8") as text_file:
            text = text_file.read()

        for chunk_text in text_splitter.split_text(text):
            chunk = Chunk(index=index, source_id=source.id, text=chunk_text)
            chunks.append(chunk)
            index += 1

    return chunks


def embed(
    texts: list[str],
    model: SentenceTransformer,
) -> np.ndarray:
    embeddings: np.ndarray = model.encode(texts)
    return embeddings


def search(query_embedding: np.ndarray, embeddings: np.ndarray, chunks: list[Chunk]) -> list[SearchResult]:
    results = util.semantic_search(query_embedding, embeddings, top_k=10)

    search_results: list[SearchResult] = []
    for result in results[0]:
        chunk_index = result["corpus_id"]
        source: Source = get_source_by_chunk(chunk_index, chunks)
        search_result = SearchResult(text="", source=source, distance=result["score"])
        search_results.append(search_result)

    # apply majority vote
    counter = Counter([search_result.source for search_result in search_results])
    most_common = counter.most_common(10)

    # filter and leave unique documents (a bit of crutch O(n^2))
    new_results: list[SearchResult] = []
    for source, _ in most_common:
        for result in search_results:
            if source.id == result.source.id:
                new_results.append(result)
                break

    return new_results
