import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://innopolis.university/sveden/document"


def get_pdf_links(url: str) -> list[str]:
    """
    Retrieve all PDF links from the given webpage.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all <a> tags that link to PDF files
    pdf_links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith(".pdf")]

    # Make sure the links are absolute URLs
    base_url = url.rstrip("/")
    full_pdf_links = [urljoin(base_url, link) for link in pdf_links]

    return full_pdf_links


def download_pdf(url, save_path="."):
    """
    Download a PDF file from the given URL and save it to the specified path.
    """
    response = requests.get(url)

    if response.status_code == 200:
        filename = os.path.join(save_path, os.path.basename(url))
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {url}")


def main():
    """
    Main function to scrape PDF links from a webpage and download them.
    """
    pdf_links = get_pdf_links(BASE_URL)

    for link in pdf_links:
        print(link)
        download_pdf(link, "data/university")


if __name__ == "__main__":
    main()
    """In case of ERROR: unexpected error - attempt to write a readonly database
    https://github.com/iterative/dvc/issues/9379#issuecomment-1528145190"""
