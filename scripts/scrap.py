import os
import bs4
import json
import httpx
import asyncio
from pathlib import Path
from httpx import Cookies
from tqdm.asyncio import tqdm_asyncio

MOODLE_ROOT = "https://moodle.innopolis.university"
PDF_TYPE = "application/pdf"
PPTX_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DATASET_PATH = Path("data/moodle")


def get_session():
    # set number of max redirects (probably can be extended)
    session = httpx.AsyncClient(follow_redirects=True, max_redirects=2, timeout=20)
    moodle_session = os.environ.get("MOODLE_SESSION")  # get cookie from env
    session.cookies = Cookies({"MoodleSession": moodle_session})
    return session


async def get_course_info(course_id: int, session: httpx.AsyncClient):
    course_url = f"{MOODLE_ROOT}/course/view.php?id={course_id}"

    response = await session.get(course_url)
    response.raise_for_status()

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    course_name = soup.find("div", class_="page-header-headings").find("h1").text.strip()
    resources = soup.find_all("li", class_="resource")

    course_files = []
    for resource in resources:
        file_id = resource["id"]
        file_url = resource.find("a")["href"]

        # get file name of hidden object
        file_name = resource.find("span", class_="instancename")
        inner_span = file_name.find("span", class_="accesshide")
        if inner_span:
            inner_span.decompose()
        file_name = file_name.text.strip()

        course_files.append(
            {
                "file_id": file_id,
                "file_name": file_name,
                "file_url": file_url,
            }
        )

    return {"name": course_name, "url": course_url, "files": course_files}


async def fetch_resource(url: str, session: httpx.AsyncClient):
    # head
    response = await session.head(url)
    response.raise_for_status()
    content_type = response.headers["Content-Type"]

    response = await session.get(url)
    response.raise_for_status()
    return response.content, content_type


async def file_task(url: str, file_id: str, session: httpx.AsyncClient):
    content, content_type = await fetch_resource(url, session)

    if content_type == PDF_TYPE:
        destination = "data/moodle/files/" + file_id + ".pdf"
    elif content_type == PPTX_TYPE:
        destination = "data/moodle/files/" + file_id + ".pptx"
    else:
        # TODO: .txt
        return

    with open(destination, "wb") as f:
        f.write(content)


async def scrap():
    # os.environ["MOODLE_SESSION"] = "..."

    # get session
    session = get_session()

    # save html after all courses are loaded on page
    with open("scripts/courses.html", "r", encoding="utf-8") as f:
        html = f.read()

    # get meta data of all known courses
    soup = bs4.BeautifulSoup(html, "html.parser")
    courses_ids = [li["data-course-id"] for li in soup.find_all("li") if "data-course-id" in li.attrs]

    json_data = []
    for course_id in tqdm_asyncio(courses_ids):
        course_info = await get_course_info(course_id, session)

        # ignore courses with no attached files
        if len(course_info["files"]) == 0:
            continue

        json_data.append(
            {
                "course_id": course_id,
                "course_name": course_info["name"],
                "course_url": course_info["url"],
                "files": course_info["files"],
            }
        )

    # write meta to the json file
    with open("data/moodle/meta.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(json_data, indent=4))

    # the heaviest part is downloading files themselves
    os.mkdir(DATASET_PATH / "files")

    for course_info in json_data:
        async with asyncio.TaskGroup() as tg:
            tasks = []

            for course_file in course_info["files"]:
                task = tg.create_task(file_task(course_file["file_url"], course_file["file_id"], session))
                tasks.append(task)

            await tqdm_asyncio.gather(*tasks, desc=f"{course_info['course_name']: <10}", unit="files")


if __name__ == "__main__":
    """Schema:
    1. meta.json - all moodle files meta
        [
            {
                course_id: int
                course_name: str
                course_url: str
                files: [
                    file_id: int
                    file_name: str
                    file_url: str
                ]
            }
        ]
    2. /files - pdfs and pptx
    """
    asyncio.run(scrap())
