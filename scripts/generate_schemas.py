__all__ = []

import sys
from pathlib import Path

# add parent dir to sys.path
sys.path.append(str(Path(__file__).parents[1]))
from data.datasets_schema import Datasets  # noqa: E402

Datasets.save_schema(Path(__file__).parents[1] / "data" / "datasets.schema.yaml")
