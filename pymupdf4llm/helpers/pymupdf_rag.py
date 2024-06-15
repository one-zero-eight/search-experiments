"""
This script accepts a PDF document filename and converts it to a text file
in Markdown format, compatible with the GitHub standard.

It must be invoked with the filename like this:

python pymupdf_rag.py input.pdf [-pages PAGES]

The "PAGES" parameter is a string (containing no spaces) of comma-separated
page numbers to consider. Each item is either a single page number or a
number range "m-n". Use "N" to address the document's last page number.
Example: "-pages 2-15,40,43-N"

It will produce a markdown text file called "input.md".

Text will be sorted in Western reading order. Any table will be included in
the text in markdwn format as well.

Dependencies
-------------
PyMuPDF v1.24.2 or later

Copyright and License
----------------------
Copyright 2024 Artifex Software, Inc.
License GNU Affero GPL 3.0
"""

import os
from pathlib import Path
from typing import overload, Literal, TypedDict, Callable, TypeAlias

from pymupdf4llm._pymupdf import pymupdf
from pymupdf4llm.elements import TextElement, TableElement
from pymupdf4llm.helpers.multi_column import column_boxes
from pymupdf4llm.identify_headers import IdentifyHeadersProtocol, DefaultHeadersIdentifier
from pymupdf4llm.process_graphics import ProcessGraphicsProtocol, DefaultGraphicsProcessor
from pymupdf4llm.resolve_links import ResolveLinksProtocol, DefaultLinkResolver
from pymupdf4llm.write_markdown import DefaultMarkdownWriter, WriteMarkdownProtocol

ImageFilterer = Callable[[pymupdf.Pixmap], bool]
M: TypeAlias = float | int
MarginsType: TypeAlias = tuple[M, M, M, M]


class ChunkData(TypedDict):
    images: list
    metadata: dict
    tables: list
    text: str
    toc_items: list


@overload
def to_markdown(
    doc: str | Path | pymupdf.Document,
    *,
    pages: list = None,
    page_chunks: Literal[True] = True,  # return a list of page dictionaries
    margins: MarginsType = (0, 0, 0, 0),
    header_identifier: IdentifyHeadersProtocol = DefaultHeadersIdentifier(),
    link_resolver: ResolveLinksProtocol = DefaultLinkResolver(),
    markdown_writer: WriteMarkdownProtocol = None,
    graphics_processor: ProcessGraphicsProtocol = DefaultGraphicsProcessor(),
) -> list[ChunkData]:
    pass


@overload
def to_markdown(
    doc: str | Path | pymupdf.Document,
    *,
    pages: list = None,
    page_chunks: Literal[False] = False,  # return a single string
    margins: MarginsType = (0, 0, 0, 0),
    header_identifier: IdentifyHeadersProtocol = DefaultHeadersIdentifier(),
    link_resolver: ResolveLinksProtocol = DefaultLinkResolver(),
    markdown_writer: WriteMarkdownProtocol = None,
    graphics_processor: ProcessGraphicsProtocol = DefaultGraphicsProcessor(),
) -> str:
    pass


@overload
def to_markdown(
    doc: str | Path | pymupdf.Document,
    *,
    pages: list = None,
    page_chunks: bool = False,  # fallback
    margins: MarginsType = (0, 0, 0, 0),
    header_identifier: IdentifyHeadersProtocol = DefaultHeadersIdentifier(),
    link_resolver: ResolveLinksProtocol = DefaultLinkResolver(),
    markdown_writer: WriteMarkdownProtocol = None,
    graphics_processor: ProcessGraphicsProtocol = DefaultGraphicsProcessor(),
) -> str | list[ChunkData]:
    pass


def to_markdown(
    doc: str | Path | pymupdf.Document,
    *,
    pages: list[int] | None = None,
    page_chunks: bool = False,
    margins: MarginsType = (0, 0, 0, 0),
    header_identifier: IdentifyHeadersProtocol = DefaultHeadersIdentifier(),
    link_resolver: ResolveLinksProtocol = DefaultLinkResolver(),
    markdown_writer: WriteMarkdownProtocol = None,
    graphics_processor: ProcessGraphicsProtocol = DefaultGraphicsProcessor(),
) -> str | list[ChunkData]:
    """Process the document and return the text of its selected pages.

    Args:
        doc: a PDF filename, a Path object or a pymupdf.Document object.
        pages: list of page numbers to consider (0-based).
        page_chunks: if True, return a list of page dictionaries.
        margins: a tuple of 4 numbers (left, top, right, bottom) in points to
         crop the page.
        header_identifier: an object with a 'fit' method and a 'get_header_id' that will be used
         to identify headers in the text.
        link_resolver: an object with a 'fit' method and a 'resolve_link' that will be used
         to identify link on the text spans.
        markdown_writer: an object with a 'write_markdown' method that will be used to format layout
         elements in markdown.
        graphics_processor: an object with a 'fit' method that will be used to process pdf graphics.
    """

    if not isinstance(doc, pymupdf.Document):  # open the document
        doc: pymupdf.Document = pymupdf.open(doc)

    if pages is None:  # use all pages if no selection given
        pages: list[int] = list(range(doc.page_count))

    if len(margins) == 4:
        margins = (margins[0], margins[1], margins[2], margins[3])
    else:
        raise ValueError("Margins must have length 4.")
    if not all(isinstance(m, M) for m in margins):
        raise ValueError("Margin values must be numbers")
    margins: tuple[M, M, M, M]

    header_identifier.fit((doc.load_page(n) for n in pages))
    if markdown_writer is None:
        markdown_writer = DefaultMarkdownWriter(header_identifier, link_resolver)

    def get_metadata(doc, pno):
        meta = doc.metadata.copy()
        meta["file_path"] = doc.name
        meta["page_count"] = doc.page_count
        meta["page"] = pno + 1
        return meta

    def get_page_output(doc, pno, margins, textflags):
        """Process one page.

        Args:
            doc: pymupdf.Document
            pno: 0-based page number
            margins: tuple of 4 numbers (left, top, right, bottom) in points to crop the page
            textflags: text extraction flag bits

        Returns:
            Markdown string of page content and image, table and vector
            graphics information.
        """
        page = doc[pno]
        left, top, right, bottom = margins
        clip = page.rect + (left, top, -right, -bottom)
        # extract all links on page
        link_resolver.fit(page)

        # make a TextPage for all later extractions
        textpage = page.get_textpage(flags=textflags, clip=clip)
        _ = graphics_processor.fit(page)
        image_elements = _["image_elements"]

        drawings = _["drawings"]
        clusters = _["clusters"]

        # Locate all tables on page
        tables = page.find_tables(clip=clip, strategy="lines_strict")
        table_elements = []
        for t in tables:
            # Must include the header bbox (may exist outside tab.bbox)
            table_elements.append(TableElement(rect=pymupdf.Rect(t.bbox) | pymupdf.Rect(t.header.bbox), table=t))

        # Determine text column bboxes on page, avoiding tables and graphics
        text_rects = column_boxes(
            page,
            footer_margin=0,
            header_margin=0,
            paths=drawings,
            textpage=textpage,
            avoid=clusters,
        )
        text_elements = [TextElement(r) for r in text_rects]

        md_string = markdown_writer.write_markdown(
            page,
            textpage,
            text_elements=text_elements,
            image_elements=image_elements,
            table_elements=table_elements,
        )
        return md_string, tables

    if page_chunks is False:
        document_output = ""
    else:
        document_output = []

    # read the Table of Contents
    toc = doc.get_toc()
    textflags = pymupdf.TEXT_DEHYPHENATE | pymupdf.TEXT_MEDIABOX_CLIP
    for pno in pages:
        page_output, tables = get_page_output(doc, pno, margins, textflags)
        if page_chunks is False:
            document_output += page_output
        else:
            # build subet of TOC for this page
            page_tocs = [t for t in toc if t[-1] == pno + 1]

            metadata = get_metadata(doc, pno)
            document_output.append(
                {
                    "metadata": metadata,
                    "toc_items": page_tocs,
                    "text": page_output,
                }
            )

    return document_output


if __name__ == "__main__":
    import pathlib
    import sys
    import time

    try:
        filename = sys.argv[1]
    except IndexError:
        print(f"Usage:\npython {os.path.basename(__file__)} input.pdf")
        sys.exit()

    t0 = time.perf_counter()  # start a time

    doc = pymupdf.open(filename)  # open input file
    parms = sys.argv[2:]  # contains ["-pages", "PAGES"] or empty list
    pages = range(doc.page_count)  # default page range
    if len(parms) == 2 and parms[0] == "-pages":  # page sub-selection given
        pages = []  # list of desired page numbers

        # replace any variable "N" by page count
        pages_spec = parms[1].replace("N", f"{doc.page_count}")
        for spec in pages_spec.split(","):
            if "-" in spec:
                start, end = map(int, spec.split("-"))
                pages.extend(range(start - 1, end))
            else:
                pages.append(int(spec) - 1)

        # make a set of invalid page numbers
        wrong_pages = set([n + 1 for n in pages if n >= doc.page_count][:4])
        if wrong_pages != set():  # if any invalid numbers given, exit.
            sys.exit(f"Page number(s) {wrong_pages} not in '{doc}'.")

    # get the markdown string
    md_string = to_markdown(doc, pages=pages, page_chunks=False)

    # output to a text file with extension ".md"
    outname = doc.name.replace(".pdf", ".md")
    pathlib.Path(outname).write_bytes(md_string.encode())
    t1 = time.perf_counter()  # stop timer
    print(f"Markdown creation time for {doc.name=} {round(t1 - t0, 2)} sec.")
