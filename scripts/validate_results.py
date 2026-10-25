#!/usr/bin/env python3
"""Independently recompute every index entry and compare with Hadoop output."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")


def read_stopwords(path: Path) -> set[str]:
    words: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip().lower()
        if entry and not entry.startswith("#"):
            words.add(entry)
    return words


def expected_index(root: Path) -> dict[str, str]:
    stopwords = read_stopwords(root / "data" / "stopwords.txt")
    per_word: dict[str, Counter[str]] = defaultdict(Counter)
    for document in sorted((root / "data" / "documents").glob("document*.txt")):
        text = document.read_text(encoding="utf-8")
        for match in WORD_PATTERN.finditer(text):
            word = match.group().lower()
            if word not in stopwords:
                per_word[word][document.name] += 1

    result: dict[str, str] = {}
    for word, counts in per_word.items():
        parts = [f"{document}:{count}" for document, count in sorted(counts.items())]
        parts.append(f"total:{sum(counts.values())}")
        result[word] = ";".join(parts)
    return result


def actual_index(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        word, value = line.split("\t", 1)
        result[word] = value
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "results" / "inverted_index.txt"
    if not output.exists():
        print(f"Missing Hadoop output: {output}", file=sys.stderr)
        return 1

    expected = expected_index(root)
    actual = actual_index(output)
    if expected == actual:
        print(f"PASS: all {len(actual)} index entries match independent counts")
        return 0

    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = [key for key in expected.keys() & actual.keys() if expected[key] != actual[key]]
    print(
        f"FAIL: expected={len(expected)} actual={len(actual)} "
        f"missing={len(missing)} extra={len(extra)} changed={len(changed)}",
        file=sys.stderr,
    )
    for label, keys in (("missing", missing), ("extra", extra), ("changed", changed)):
        if keys:
            key = keys[0]
            print(f"{label} example: {key}", file=sys.stderr)
            if label == "changed":
                print(f"  expected: {expected[key]}", file=sys.stderr)
                print(f"  actual:   {actual[key]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
