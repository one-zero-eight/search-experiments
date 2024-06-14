from pathlib import Path
from typing import Any

import pymupdf
from langchain_community.document_loaders import PyMuPDFLoader

from experiments.to_markdown import to_markdown, Page


def usepymupdf4llm(path: str | Path | pymupdf.Document) -> list[Page]:
    return to_markdown(
        path,
        write_images=lambda x: x.h > 10 and x.w > 10,
        page_chunks=True,
        margins=(0, 0, 0, 0),
    )


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


def usepymupdf(path: str | Path, text_splitter: Any = None):
    _ = PyMuPDFLoader(
        path,
        text_splitter=text_splitter,
        extractions_flags=extractions_flags,
        extract_images=True,
    )
    return _.load()
