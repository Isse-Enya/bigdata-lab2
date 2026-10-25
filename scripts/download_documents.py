#!/usr/bin/env python3
"""Download ten public English documents used by the inverted-index job."""

from __future__ import annotations

import csv
import html
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


SOURCES = [
    (
        "document01.txt",
        "Apache Hadoop MapReduce Tutorial",
        "https://hadoop.apache.org/docs/r3.3.6/hadoop-mapreduce-client/hadoop-mapreduce-client-core/MapReduceTutorial.html",
        "html",
    ),
    (
        "document02.txt",
        "Apache Hadoop HDFS Architecture",
        "https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html",
        "html",
    ),
    (
        "document03.txt",
        "RFC 9110 HTTP Semantics",
        "https://www.rfc-editor.org/rfc/rfc9110.txt",
        "text",
    ),
    (
        "document04.txt",
        "RFC 8446 TLS 1.3",
        "https://www.rfc-editor.org/rfc/rfc8446.txt",
        "text",
    ),
    (
        "document05.txt",
        "RFC 1034 Domain Names Concepts and Facilities",
        "https://www.rfc-editor.org/rfc/rfc1034.txt",
        "text",
    ),
    (
        "document06.txt",
        "RFC 791 Internet Protocol",
        "https://www.rfc-editor.org/rfc/rfc791.txt",
        "text",
    ),
    (
        "document07.txt",
        "RFC 793 Transmission Control Protocol",
        "https://www.rfc-editor.org/rfc/rfc793.txt",
        "text",
    ),
    (
        "document08.txt",
        "RFC 959 File Transfer Protocol",
        "https://www.rfc-editor.org/rfc/rfc959.txt",
        "text",
    ),
    (
        "document09.txt",
        "RFC 1918 Address Allocation for Private Internets",
        "https://www.rfc-editor.org/rfc/rfc1918.txt",
        "text",
    ),
    (
        "document10.txt",
        "RFC 5322 Internet Message Format",
        "https://www.rfc-editor.org/rfc/rfc5322.txt",
        "text",
    ),
]


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "header", "footer"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "header", "footer"} and self.ignored_depth:
            self.ignored_depth -= 1
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "pre", "br"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)

    def text(self) -> str:
        value = html.unescape(" ".join(self.parts))
        lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
        return "\n".join(line for line in lines if line)


def fetch(url: str, kind: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "bigdata-lab2-course-project/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    text = raw.decode("utf-8", errors="replace")
    if kind == "html":
        parser = VisibleTextParser()
        parser.feed(text)
        return parser.text()
    return text


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "data" / "documents"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_rows: list[list[str]] = []
    for filename, title, url, kind in SOURCES:
        body = fetch(url, kind)
        header = f"Title: {title}\nSource: {url}\n\n"
        (output_dir / filename).write_text(header + body + "\n", encoding="utf-8")
        metadata_rows.append([filename, title, url])
        print(f"{filename}: {len(body):,} characters")

    with (output_dir / "sources.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["document", "title", "source_url"])
        writer.writerows(metadata_rows)

    print(f"Downloaded {len(SOURCES)} documents to {output_dir}")


if __name__ == "__main__":
    main()
