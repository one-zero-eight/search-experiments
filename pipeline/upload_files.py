import os
from tqdm import tqdm
from pathlib import Path
from minio import Minio, S3Error


def upload_files(client: Minio, data_path: Path):
    """Upload files to minio.
    The script assumes that files are stored in data_path/{dataset_name}/files folders of each dataset.
    """
    for dataset_path in data_path.iterdir():
        dataset_name = dataset_path.name
        dataset_path = dataset_path / "files"
        total_files = sum(1 for _ in filter(Path.is_file, dataset_path.iterdir()))

        # print entries
        print(f"Dataset {dataset_name:<10} has {total_files:<4} files.")

        # create bucket if not exist
        if not client.bucket_exists("data"):
            client.make_bucket("data")

        for file_path in tqdm(dataset_path.iterdir()):
            file_name = file_path.name

            try:
                with open(file_path, "rb") as file:
                    file_stat = os.stat(file_path)

                    client.put_object(
                        bucket_name="data",
                        object_name=f"{dataset_name}/{file_name}",
                        data=file,
                        length=file_stat.st_size,
                        content_type="application/pdf",
                    )
            except S3Error as e:
                print("error occurred.", e)


if __name__ == "__main__":
    client = Minio(
        endpoint="127.0.0.1:9000",
        access_key="minioadmin",
        secret_key="password",
        secure=False,
    )
    data_path = Path("data")
    upload_files(client, data_path)
