from typing import Literal
from pydantic import BaseModel, Field


###########
# SOURCES #
###########
class Source(BaseModel):
    id: str
    url: str
    name: str
    desc: str
    type: Literal["moodle", "file", "web", "tg"] = Field("file")

    def __hash__(self) -> int:
        return self.id.__hash__()


class MoodleSource(Source):
    course_id: str
    course_url: str
    course_name: str
    type: Literal["moodle"] = Field("moodle")


class FileSource(Source):
    type: Literal["file"] = Field("file")


class WebSource(Source):
    type: Literal["web"] = Field("web")


class TelegramSource(Source):
    type: Literal["tg"] = Field("tg")


#########
# UTILS #
#########
class Chunk(BaseModel):
    index: int = Field(ge=0)
    source_id: str
    text: str


##########
# SEARCH #
##########
class SearchQuery(BaseModel):
    text: str


class SearchResult(BaseModel):
    source: Source
    distance: float

    def __hash__(self) -> int:
        return self.source.id.__hash__()
