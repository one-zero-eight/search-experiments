from typing import Protocol

from pymupdf4llm._pymupdf import pymupdf


class ResolveLinksProtocol(Protocol):
    def resolve_link(self, span) -> str | None:
        """Accept a span and return the URI of the link it belongs to or None."""
        pass

    def fit(self, page: pymupdf.Page):
        """Read all links from a page and store them to be used in resolve_links."""
        pass


class DefaultLinkResolver(ResolveLinksProtocol):
    """Resolve links in PDF files."""

    links: list
    overlap: float

    def __init__(self, overlap: float = 0.7):
        self.links = []
        self.overlap = overlap

    def resolve_link(self, span: dict):
        bbox = pymupdf.Rect(span["bbox"])  # span bbox
        # a link should overlap at least xx% of the span
        bbox_area = self.overlap * abs(bbox)
        for link in self.links:
            hot = link["from"]  # the hot area of the link
            if not abs(hot & bbox) >= bbox_area:
                continue  # does not touch the bbox
            return link["uri"]
        return None

    def fit(self, page: pymupdf.Page):
        self.links = [link for link in pymupdf.utils.get_links(page) if link["kind"] == 2]
