import os
import json
import requests
from tqdm import tqdm
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import TypedDict


BASE_URL = "https://innopolis.university/sveden/document"
META_FILE = "university.meta.json"


class Document(TypedDict):
    id: str
    url: str
    name: str
    desc: str
    type: str


def save_meta(save_path: Path):
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    docs: list[Document] = []
    for link in soup.find_all("a", href=True):
        if link["href"].endswith(".pdf"):
            url = urljoin(BASE_URL, link["href"])
            doc: Document = Document(
                id=url,
                url=url,
                desc=link.text.strip(),
                name=url[url.rfind("/") + 1 :],
                type="file",
            )
            docs.append(doc)

    with open(save_path / META_FILE, "w", encoding="utf-8") as file:
        file.write(json.dumps(docs, ensure_ascii=False, indent=4))


def download_pdfs(save_path: Path):
    if not os.path.exists(save_path / "files"):
        os.mkdir(save_path / "files")

    docs: list[Document] = []
    with open(save_path / META_FILE, "r", encoding="utf-8") as file:
        docs = json.loads(file.read())

    for doc in tqdm(docs, total=len(docs), unit="doc"):
        response = requests.get(doc["url"])

        if response.status_code == 200:
            filename = save_path / "files" / doc["name"]
            with open(filename, "wb") as f:
                f.write(response.content)
        else:
            tqdm.write(f"Failed to download {BASE_URL}")


if __name__ == "__main__":
    save_path = Path("data")
    save_meta(save_path)
    download_pdfs(save_path)
    """In case of ERROR: unexpected error - attempt to write a readonly database
    https://github.com/iterative/dvc/issues/9379#issuecomment-1528145190"""
