"""Pick today's item at random, without repeats until the whole pool is used."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = ROOT / "data" / "sources"
HISTORY_FILE = ROOT / "data" / "history.json"


def load_pool(sources_dir: Path = SOURCES_DIR) -> list[dict]:
    pool = []
    for path in sorted(sources_dir.glob("*.json")):
        src = json.loads(path.read_text(encoding="utf-8"))
        meta = {k: src[k] for k in ("source_title", "source_url", "attribution")}
        pool.extend({**item, **meta} for item in src["items"])
    return pool


def load_history(history_file: Path = HISTORY_FILE) -> list[dict]:
    if history_file.exists():
        return json.loads(history_file.read_text(encoding="utf-8"))
    return []


def pick(date: str, *, sources_dir: Path = SOURCES_DIR, history_file: Path = HISTORY_FILE,
         rng: random.Random | None = None) -> dict:
    """Return the item for `date` (YYYY-MM-DD), recording it in history.

    Idempotent: if `date` already has a pick, the same item is returned.
    """
    rng = rng or random.Random()
    pool = load_pool(sources_dir)
    if not pool:
        raise RuntimeError("No source items. Run ingest first.")
    by_id = {i["id"]: i for i in pool}
    history = load_history(history_file)

    for h in history:
        if h["date"] == date and h["id"] in by_id:
            return by_id[h["id"]]

    # Only the current cycle counts: history entries after the last reset.
    used: set[str] = set()
    for h in history:
        if h.get("cycle_reset"):
            used = set()
        used.add(h["id"])
    candidates = [i for i in pool if i["id"] not in used]
    reset = not candidates
    if reset:
        candidates = pool

    item = rng.choice(candidates)
    entry = {"date": date, "id": item["id"]}
    if reset:
        entry["cycle_reset"] = True
    history.append(entry)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    return item
