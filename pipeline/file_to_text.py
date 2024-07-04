import os
from time import time
from tqdm import tqdm
from pathlib import Path
from pymupdf4llm import process_document, join_chunks


def file_to_text(data_path: Path):
    # create folder for raw texts if not exist
    if not os.path.exists("./texts"):
        os.mkdir("./texts")

    texts = []
    total_files = sum(1 for _ in filter(Path.is_file, data_path.iterdir()))
    for file_path in tqdm(data_path.iterdir(), total=total_files, unit="file"):
        if file_path.suffix == ".pdf":
            t = time()
            text = join_chunks(process_document(file_path))
            texts.append(text)

            # output huge files that takes more than 10 sec
            if time() - t > 10:
                print(f"{file_path.name} takes more than 10 sec")

            try:
                with open(f"texts/{file_path.name}.txt", "w", encoding="utf-8") as file:
                    file.write(text)
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    data_path = Path("data/files")
    file_to_text(data_path)
