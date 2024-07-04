import os
import bs4
import time
import json
import httpx
import shutil
import asyncio
from pathlib import Path
from httpx import Cookies
from tqdm.asyncio import tqdm_asyncio
from typing import TypedDict


MOODLE_ROOT = "https://moodle.innopolis.university"
PDF_TYPE = "application/pdf"
PPTX_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
SAVE_PATH = Path("data")
META_FILE = "moodle.meta.json"


class Document(TypedDict):
    id: str
    url: str
    name: str
    desc: str
    course_id: str
    course_url: str
    course_name: str
    type: str


def get_session():
    # set number of max redirects (probably can be extended)
    session = httpx.AsyncClient(follow_redirects=True, max_redirects=3, timeout=30)
    moodle_session = os.environ.get("MOODLE_SESSION")  # get cookie from env
    session.cookies = Cookies({"MoodleSession": moodle_session})
    return session


async def fetch_resource(url: str, session: httpx.AsyncClient):
    # head
    response = await session.head(url)
    response.raise_for_status()
    content_type = response.headers["Content-Type"]

    response = await session.get(url)
    response.raise_for_status()
    return response.content, content_type


async def course_task(course_id: int, session: httpx.AsyncClient):
    course_url = f"{MOODLE_ROOT}/course/view.php?id={course_id}"

    response = await session.get(course_url)
    response.raise_for_status()

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    course_name = soup.find("div", class_="page-header-headings").find("h1").text.strip()
    resources = soup.find_all("li", class_="resource")

    course_docs: list[Document] = []
    for resource in resources:
        file_id = resource["id"]
        file_url = resource.find("a")["href"]

        # fetch
        start_time = time.time()
        try:
            content, content_type = await fetch_resource(file_url, session)
        except httpx.ReadTimeout:
            print(file_url)
            continue

        if start_time - time.time() > 15:  # find out large files
            print(file_url)

        # choose file extension
        if content_type == PDF_TYPE:
            extension = ".pdf"
        elif content_type == PPTX_TYPE:
            extension = ".pptx"
        else:
            continue

        # save to file
        file_name = file_id + extension
        destination = SAVE_PATH / "files" / file_name
        with open(destination, "wb") as f:
            f.write(content)

        # get file name of hidden object
        file_desc = resource.find("span", class_="instancename")
        inner_span = file_desc.find("span", class_="accesshide")
        if inner_span:
            inner_span.decompose()
        file_desc = file_desc.text.strip()

        doc = Document(
            id=file_name,  # file_id
            url=file_url,
            name=file_name,
            desc=file_desc,
            course_id=course_id,
            course_url=course_url,
            course_name=course_name,
            type="moodle",
        )
        course_docs.append(doc)

    # don't save empty courses
    if len(course_docs) == 0:
        return

    # save meta to temporary file
    with open(SAVE_PATH / "temp" / f"{course_id}.json", "w", encoding="utf-8") as file:
        file.write(json.dumps(course_docs, ensure_ascii=False, indent=4))


async def scrap():
    """
    Algorithm:
        1. get session
        2. get all courses ids
        3. save html
        4. start async tasks of downloading each course
            - get and store resource file locally
            - store meta data of each resource
            - save meta in temp folder for each course
        5. combine temp meta files in one
        6. remove temp folder
    """
    os.environ["MOODLE_SESSION"] = "kfacnvclp7eqmjum1gra6s4f9q"

    # get session
    session = get_session()

    # save html after all courses are loaded on page
    with open("scripts/courses.html", "r", encoding="utf-8") as f:
        html = f.read()

    # get meta data of all known courses
    soup = bs4.BeautifulSoup(html, "html.parser")
    courses_ids = [li["data-course-id"] for li in soup.find_all("li") if "data-course-id" in li.attrs]

    # create files and temp folders if not exist
    if not os.path.exists(SAVE_PATH / "files"):
        os.mkdir(SAVE_PATH / "files")

    if not os.path.exists(SAVE_PATH / "temp"):
        os.mkdir(SAVE_PATH / "temp")

    async with asyncio.TaskGroup() as tg:
        tasks = []

        for course_id in courses_ids:  # [courses_ids[0], courses_ids[1]]
            task = tg.create_task(course_task(course_id, session))
            tasks.append(task)

        await tqdm_asyncio.gather(*tasks, desc=f"{course_id: <10}", unit="course")

    # combine temp files
    docs = []
    temp_path = Path(SAVE_PATH / "temp")
    for temp_file in temp_path.iterdir():
        with open(temp_file, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            docs.extend(data)

    # save meta file
    with open(SAVE_PATH / META_FILE, "w", encoding="utf-8") as file:
        file.write(json.dumps(docs, ensure_ascii=False, indent=4))

    # remove temp folder
    if os.path.exists(SAVE_PATH / "temp"):
        shutil.rmtree(SAVE_PATH / "temp")


if __name__ == "__main__":
    asyncio.run(scrap())
