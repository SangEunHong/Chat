# utils/file_utils.py
from pathlib import Path

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            yield line

def write_jsonl(path: Path, lines):
    with path.open("a", encoding="utf-8") as f:
        for row in lines:
            f.write(row + "\n")
