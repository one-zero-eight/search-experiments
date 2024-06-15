from pathlib import Path
from typing import Any

from pymupdf4llm import to_markdown
from pymupdf4llm.helpers.pymupdf_rag import ChunkData


def use_pymupdf4llm(
    path: str | Path, page_chunks: bool = False
) -> str | list[ChunkData]:
    return to_markdown(
        path,
        page_chunks=page_chunks,
        margins=(0, 0, 0, 0),
    )


def use_pymupdf(path: str | Path, text_splitter: Any = None):
    import pymupdf
    from langchain_community.document_loaders import PyMuPDFLoader

    extractions_flags = (
        0  # disable all
        | (0 & pymupdf.TEXT_PRESERVE_LIGATURES)  # dont preserve ligatures
        | (0 & pymupdf.TEXT_PRESERVE_WHITESPACE)  # dont preserve whitespace
        | (0 & pymupdf.TEXT_PRESERVE_IMAGES)  # dont preserve images
        | (0 & pymupdf.TEXT_INHIBIT_SPACES)  # generate spaces in place of large gaps
        | (0 | pymupdf.TEXT_DEHYPHENATE)  # "alterna-\n tive" -> "alternative"
        | (0 & pymupdf.TEXT_PRESERVE_SPANS)  # not used
        | (0 & pymupdf.TEXT_MEDIABOX_CLIP)  # do not clip text to mediabox
        | (0 & pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE)  # replace unknown unicode with CID
    )

    _ = PyMuPDFLoader(
        path,
        text_splitter=text_splitter,
        extractions_flags=extractions_flags,
        extract_images=True,
    )
    return _.load()
