from functools import partial
from pathlib import Path
from typing import Protocol, TypedDict

from pymupdf4llm._pymupdf import pymupdf
from pymupdf4llm.elements import ImageElement
from pymupdf4llm.rectangle_utils import is_in_rects


class Output(TypedDict):
    drawings: list[dict]
    image_elements: list[ImageElement]
    clusters: list[pymupdf.Rect]


class ProcessGraphicsProtocol(Protocol):
    def fit(self, page: pymupdf.Page) -> Output:
        """Fit page graphics."""


class DefaultGraphicsProcessor(ProcessGraphicsProtocol):
    """Process graphics in PDF files."""

    write_images: Path | None

    def __init__(self, write_images: Path | None = None):
        self.write_images = write_images

    def fit(self, page: pymupdf.Page) -> Output:
        drawings = page.get_drawings()

        is_not_full_page = partial(self.is_not_full_page_drawing, page=page)
        filtered_drawings = list(filter(is_not_full_page, drawings))

        clusters = page.cluster_drawings(drawings=filtered_drawings)
        is_stroked = partial(self.is_stroked_cluster, drawings=filtered_drawings)
        filtered_clusters = list(filter(is_stroked, clusters))

        within_rect = partial(is_in_rects, rect_list=filtered_clusters)
        filtered_drawings = list(filter(lambda p: within_rect(p["rect"]), filtered_drawings))

        image_info = pymupdf.utils.get_image_info(page)
        image_elements = []
        for cursor, img in enumerate(image_info):
            element = self.create_image_element(page, img, cursor)
            image_elements.append(element)

        return {"drawings": filtered_drawings, "image_elements": image_elements, "clusters": filtered_clusters}

    def create_image_element(self, page: pymupdf.Page, img: dict, cursor: int) -> ImageElement:
        rect = pymupdf.Rect(img["bbox"])

        if self.write_images:
            filename = page.parent.name.replace("\\", "/")
            path = self.write_images / f"{filename}-{page.number}-{cursor}.png"
            alt = f"{page.number}-{img}.png"
            pix: pymupdf.Pixmap = pymupdf.utils.get_pixmap(page, clip=rect)
            pix.save(path)
            del pix
            return ImageElement(rect=rect, alt=alt, path=path)
        else:
            return ImageElement(rect=pymupdf.Rect(img["bbox"]))

    @staticmethod
    def is_not_full_page_drawing(drawing: dict, page: pymupdf.Page) -> bool:
        page_clip = page.rect + (36, 36, -36, -36)  # full page graphics

        if drawing["rect"].width < page_clip.width or drawing["rect"].height < page_clip.height:
            return True

        return False

    @staticmethod
    def is_stroked_cluster(cluster: pymupdf.Rect, drawings: list[dict]) -> bool:
        for p in drawings:
            if p["rect"] not in cluster:
                continue
            if p["type"] != "f":
                return True
            for item in p["items"]:
                if item[0] == "c":
                    return True
        return False
