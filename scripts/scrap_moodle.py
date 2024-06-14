import asyncio
import json
from pathlib import Path

import browser_cookie3
import bs4
import httpx
from markdownify import markdownify as md
from tqdm.asyncio import tqdm_asyncio


def get_session():
    cj = browser_cookie3.load(domain_name="moodle.innopolis.university")
    session = httpx.AsyncClient(follow_redirects=True)
    session.cookies = cj
    return session


async def fetch_resource(url: str, session: httpx.AsyncClient):
    # head
    response = await session.head(url)
    response.raise_for_status()
    content_type = response.headers["Content-Type"]

    response = await session.get(url)
    response.raise_for_status()
    return response.content, content_type


async def get_structure_of_course(
    moodle_root: str, course_id: int, session: httpx.AsyncClient
):
    url = f"{moodle_root}/course/view.php?id={course_id}"

    response = await session.get(url)
    response.raise_for_status()

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    course_name = (
        soup.find("div", class_="page-header-headings").find("h1").text.strip()
    )
    course_sections = soup.find_all("li", class_="course-section")

    sections = []

    for section in course_sections:
        section_object = {}
        section_object["id"] = section["id"]
        section_object["name"] = (
            section.find("h3", class_="sectionname")
            .text.strip()
            .replace("Общее", "General")
        )
        _summarytext = section.find("div", class_="summarytext")
        if _summarytext:
            _summarytext: bs4.element.Tag
            section_object["summary"] = md(str(_summarytext)).strip()

        _resources = section.find_all("li", class_="resource")
        resources = []
        for resource in _resources:
            resource_id = resource["id"]
            _resource_name = resource.find("span", class_="instancename")
            # remove accesshide span
            _inner_span = _resource_name.find("span", class_="accesshide")
            if _inner_span:
                _inner_span.decompose()
            resource_name = _resource_name.text.strip()

            resource_url = resource.find("a")["href"]
            resources.append(
                {"id": resource_id, "name": resource_name, "url": resource_url}
            )

        section_object["resources"] = resources
        sections.append(section_object)

    return {
        "name": course_name,
        "sections": sections,
    }


PDF_TYPE = "application/pdf"
PPTX_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


async def resource_task(section, course, resource, session, output_dir):
    if not resource.get("url"):
        return

    content, content_type = await fetch_resource(resource["url"], session)
    if content_type == PDF_TYPE:
        destination = (
            output_dir / course["name"] / section["name"] / f"{resource['name']}.pdf"
        )
    elif content_type == PPTX_TYPE:
        destination = (
            output_dir / course["name"] / section["name"] / f"{resource['name']}.pptx"
        )
    else:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as f:
        f.write(content)


async def download_course(course_ids: list[int]):
    moodle_root = "https://moodle.innopolis.university"
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    async with get_session() as session:
        for course_id in course_ids:
            course = await get_structure_of_course(moodle_root, course_id, session)

            # save to file
            with open(output_dir / "meta.json", "w") as f:
                json.dump(course, f, indent=4)

            # download pdfs
            async with asyncio.TaskGroup() as tg:
                for section in course["sections"]:
                    # create meta file
                    _meta_path = (
                        output_dir / course["name"] / section["name"] / "meta.json"
                    )
                    _meta_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(_meta_path, "w") as f:
                        json.dump(section, f, indent=4)

                    tasks = []
                    for resource in section["resources"]:
                        t = tg.create_task(
                            resource_task(
                                section, course, resource, session, output_dir
                            )
                        )
                        tasks.append(t)
                    if not tasks:
                        continue
                    await tqdm_asyncio.gather(*tasks, desc=f"{section["id"]: <10}", unit="files")


if __name__ == "__main__":
    asyncio.run(download_course([1114]))
