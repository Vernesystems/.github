#!/usr/bin/env python3
"""Refresh the "Field notes" list in profile/README.md from the blog's RSS feed.

Standard library only, so the workflow needs no installs. Writes the file only when the list
changes; exits non-zero (leaving the README alone) if the feed is unreachable or empty.
"""

from __future__ import annotations

import html
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEED = "https://blog.vernesystems.com/feed.xml"
BLOG = "https://blog.vernesystems.com/"
README = pathlib.Path(__file__).resolve().parent.parent / "profile" / "README.md"
START, END = "<!-- FIELD-NOTES:START -->", "<!-- FIELD-NOTES:END -->"
COUNT = 3


def entries() -> list[str]:
    req = urllib.request.Request(FEED, headers={"User-Agent": "Vernesystems-profile/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    lines = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        # Only our own posts: the list is rendered on the organization page.
        if not title or not link.startswith(BLOG):
            continue
        topic = (item.findtext("category") or "").strip()
        date = item.findtext("pubDate")
        when = parsedate_to_datetime(date).strftime("%b %Y") if date else ""
        meta = " · ".join(x for x in (html.escape(topic), when) if x)
        safe = html.escape(title).replace("[", "\\[").replace("]", "\\]")
        lines.append(f"- [{safe}]({link}) &nbsp;<sub>{meta}</sub>")
        if len(lines) == COUNT:
            break
    return lines


def main() -> None:
    lines = entries()
    if not lines:
        raise SystemExit("Feed had no posts; README left unchanged.")
    text = README.read_text(encoding="utf-8")
    block = "\n".join([START, *lines, END])
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit("Markers not found in profile/README.md.")
    updated = pattern.sub(lambda _: block, text)
    if updated == text:
        print("Field notes already current.")
        return
    README.write_text(updated, encoding="utf-8", newline="\n")
    print("Field notes updated:\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
