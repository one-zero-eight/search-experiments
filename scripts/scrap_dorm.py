import os
import json
import requests
from tqdm import tqdm
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import TypedDict


BASE_URL = "https://hotel.innopolis.university/dokumenty/"
META_FILE = "dorm.meta.json"


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
    for link in soup.find_all("a", href=True, target="_self"):  # target because of Правила пользования велокомнатой
        if link["href"].endswith(".pdf"):
            url = urljoin(BASE_URL, link["href"])
            doc: Document = Document(
                id=url,
                url=url,
                desc=link.text.strip(),
                name=url[url.rfind("/") + 1 :].replace("%20", " "),  # a bit of a crutch
                type="file",
            )
            docs.append(doc)

    # crutch, to replace incorrect view of cyrillic letters
    for doc in docs:
        if doc["desc"] == "Перечень документов для несовершеннолетних гостей (до 18 лет)":
            doc["id"] = doc[
                "url"
            ] = "https://hotel.innopolis.university/upload/docs-hotel/Формы_документов_для_размещения_в_Жилом_комплексе_несовершеннолетние.pdf"
            doc["name"] = "Формы_документов_для_размещения_в_Жилом_комплексе_несовершеннолетние.pdf"
            break

    with open(save_path / META_FILE, "w", encoding="utf-8") as file:
        file.write(json.dumps(docs, ensure_ascii=False, indent=4))


def download_pdfs(save_path: Path, replace: bool = False):
    if not os.path.exists(save_path / "files"):
        os.mkdir(save_path / "files")

    docs: list[Document] = []
    with open(save_path / META_FILE, "r", encoding="utf-8") as file:
        docs = json.loads(file.read())

    for doc in tqdm(docs, total=len(docs), unit="doc"):
        filename = save_path / "files" / doc["name"]

        # skip if file is present and replace is set to False
        if os.path.exists(filename) and not replace:
            continue

        response = requests.get(doc["url"])
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
        else:
            tqdm.write(f"Failed to download {BASE_URL}")


if __name__ == "__main__":
    save_path = Path("data")
    save_meta(save_path)
    download_pdfs(save_path, replace=False)
