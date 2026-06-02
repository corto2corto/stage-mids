import json
import csv
from pathlib import Path

DATA_DIR = Path("data")
PROGRESS_FILE = Path("progress.json")


def _load_progress() -> dict[str, int]:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def _save_progress(progress: dict[str, int]) -> None:
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def _get_media_name(csv_path: Path) -> str:
    return csv_path.stem


def _read_url_at(csv_path: Path, line_index: int) -> str | None:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i == line_index:
                return row["url"]
    return None


def get_next_batch() -> dict[str, str]:
    progress = _load_progress()
    batch = {}

    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        media = _get_media_name(csv_path)
        current_line = progress.get(media, 0)

        url = _read_url_at(csv_path, current_line)
        if url is None:
            continue

        batch[media] = url
        progress[media] = current_line + 1

    _save_progress(progress)
    return batch
