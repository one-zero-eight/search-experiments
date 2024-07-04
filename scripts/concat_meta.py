import json
from pathlib import Path
import os


def concat_meta(save_path: Path):
    if os.path.exists(save_path / "meta.json"):  # remove old meta file
        os.remove(save_path / "meta.json")

    docs = []
    for entry in save_path.iterdir():
        if entry.is_file() and entry.suffix == ".json":
            with open(entry, "r", encoding="utf-8") as file:
                json_docs = json.loads(file.read())
                docs.extend(json_docs)

    with open(save_path / "meta.json", "w", encoding="utf-8") as file:
        file.write(json.dumps(docs, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    save_path = Path("data")
    concat_meta(save_path)
