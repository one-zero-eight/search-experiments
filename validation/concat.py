import json
from pathlib import Path
from pydantic import BaseModel


class Query(BaseModel):
    text: str
    relevant: bool
    sources: list[str]


def concatenate_queries(dir_path: Path) -> list[Query]:
    """
    Reads and concatenates content from multiple JSONL files.

    Parameters:
    - file_paths: A list of paths to JSONL files.

    Returns:
    - A list containing JSON objects from all files.
    """
    queries = []

    for file_path in dir_path.iterdir():
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    # Parse each line as JSON and append to the list
                    queries.append(json.loads(line))
        except FileNotFoundError:
            print(f"Error: File {file_path} not found.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from file {file_path}: {e}")

    return queries


def ensure_query(query: Query):
    assert isinstance(query["text"], str)
    assert isinstance(query["relevant"], bool)
    if query["relevant"]:
        assert isinstance(query["sources"], list)


# Example usage
queries_folder = Path("./validation/queries/")
queries = concatenate_queries(queries_folder)


# save all queries to one file
with open("./validation/queries.jsonl", "w", encoding="utf-8") as file:
    for query in queries:
        ensure_query(query)
        file.write(json.dumps(query, ensure_ascii=False) + "\n")
