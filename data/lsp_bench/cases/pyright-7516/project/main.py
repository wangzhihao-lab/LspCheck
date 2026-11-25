from dataclasses import dataclass
from pathlib import Path

@dataclass()
class SampleClassA:
    name: str = "ealap/sample"
    dir_a: Path = Path.home().joinpath(f"source/{name}")
    dir_b: Path = dir_a.joinpath("path/to/b")
