from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path


def load_universe_codes(path: str | Path) -> list[str]:
    universe_path = Path(path)
    if not universe_path.exists():
        raise FileNotFoundError(f"universe file not found: {universe_path}")

    with universe_path.open(newline="", encoding="utf-8") as file:
        rows = csv.DictReader(file)
        if not rows.fieldnames or "ts_code" not in rows.fieldnames:
            raise ValueError("universe file must contain a ts_code column")
        return _dedupe(
            row["ts_code"].strip()
            for row in rows
            if row.get("ts_code", "").strip() and _enabled(row.get("enabled", "1"))
        )


def merge_universe_codes(*groups: list[str]) -> list[str]:
    return _dedupe(code for group in groups for code in group)


def _enabled(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "n", "disabled"}


def _dedupe(codes: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for code in codes:
        normalized = code.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
