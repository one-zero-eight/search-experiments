from pathlib import Path
from typing import Literal, Annotated, Any

import yaml
from pydantic import (
    ConfigDict,
    BaseModel as _BaseModel,
    Field,
    FileUrl,
    Discriminator,
    model_validator,
)


class BaseModel(_BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")


class DatasetBase(BaseModel):
    """
    Base class for dataset
    """

    title: str = ""
    "Title of dataset"
    description: str = ""
    "Description of dataset"


class DocumentStorage(BaseModel):
    class FileEntry(BaseModel):
        url: FileUrl | None = None
        "URL to file"
        path: Path | None = None
        "Path to file"

        @model_validator(mode="after")
        def validate(self):
            # xor
            if bool(self.url) == bool(self.path):
                raise ValueError("Either url or path should be provided (not both)")

    _files: dict[str, FileEntry]
    files: dict[str, FileEntry] = {}
    "Files; key - ID of file"
    files_directory: Path | None = None
    "Directory of files: Each file will be added to files registry with relative path as ID"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._files = self.files
        if self.files_directory is not None:
            for path in self.files_directory.rglob("*"):
                if path.is_file():
                    _id = path.relative_to(
                        self.files_directory, walk_up=True
                    ).as_posix()
                    self._files[_id] = self.FileEntry(path=path)

    def get(self, item: str, default: Any = Any):
        if default is Any:
            return self._files.get(item)
        return self._files.get(item, default)

    @property
    def entries(self):
        cp = self._files.copy()
        return cp


class FileDataset(DatasetBase):
    """
    Definition of dataset with files
    """

    dataset_type: Literal["files"] = "files"
    "Type of dataset: just files"
    document_storage: DocumentStorage
    "Document storage"


class FileQueryAnswerDataset(DatasetBase):
    """
    Definition of dataset with query-answers pairs for files
    """

    dataset_type: Literal["pdf_query_answer"] = "files_query_answer"
    "Type of dataset: pdf files with query to find answer"
    document_storage: DocumentStorage
    "Document storage"
    query_answers: dict[str, list[str]] = {}
    "Query - relevant answers (ids of documents)"

    @model_validator(mode="after")
    def validate(self):
        # all answers should exist and all ids should be unique
        entries = self.document_storage.entries
        for answers in self.query_answers.values():
            for answer in answers:
                if answer not in entries:
                    raise ValueError(f"Non-existing identifier: {answer}")


DatasetDiscriminator = Annotated[
    FileDataset | FileQueryAnswerDataset, Discriminator("dataset_type")
]


class Datasets(BaseModel):
    """
    Definition of datasets
    """

    model_config = ConfigDict(json_schema_extra={"title": "Datasets"})
    schema_: str = Field(None, alias="$schema")
    datasets: dict[str, DatasetDiscriminator]
    "Datasets, key - ID of dataset (alias with version)"

    @classmethod
    def from_yaml(cls, path: Path) -> "Datasets":
        with open(path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)

        return cls.model_validate(yaml_config)

    @classmethod
    def save_schema(cls, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            schema = {
                "$schema": "https://json-schema.org/draft-07/schema#",
                **cls.model_json_schema(),
            }
            yaml.dump(schema, f, sort_keys=False)

    def __getitem__(self, item: str):
        return self.datasets[item]
