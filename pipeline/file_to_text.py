from pymupdf4llm import process_document, join_chunks
import os
from tqdm import tqdm
from pathlib import Path


def file_to_text(data_path: Path):
    # create folder for raw texts if not exist
    if not os.path.exists("./texts"):
        os.mkdir("./texts")

    for dataset_path in data_path.iterdir():
        dataset_name = dataset_path.name
        dataset_path = dataset_path / "files"
        total_files = sum(1 for _ in filter(Path.is_file, dataset_path.iterdir()))

        # print entries
        print(f"Dataset {dataset_name:<10} has {total_files:<4} files.")

        texts = []
        for file_path in tqdm(dataset_path.iterdir(), total=total_files):
            if file_path.suffix == ".pdf":
                text = join_chunks(process_document(file_path))
                texts.append(text)

                try:
                    with open(f"texts/{file_path.name}.txt", "w", encoding="utf-8") as file:
                        file.write(text)
                except Exception as e:
                    print(f"Error: {e}")


if __name__ == "__main__":
    data_path = Path("data")
    file_to_text(data_path)
