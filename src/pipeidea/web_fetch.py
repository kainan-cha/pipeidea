"""Detect URLs in seeds, fetch their content, and extract readable text."""

from __future__ import annotations

import asyncio
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

# Maximum characters to keep from extracted page content.
_MAX_CONTENT_CHARS = 2000

# Tags whose text content we skip entirely.
_SKIP_TAGS = frozenset({
    "script", "style", "noscript", "svg",
    "iframe", "object", "embed", "applet",
})

# Tags that imply a line break when closed.
_BLOCK_TAGS = frozenset({
    "p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "tr", "blockquote", "section", "article", "header", "footer",
    "nav", "aside", "main", "figure", "figcaption", "td", "th",
})


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML→text extractor using stdlib only."""

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0
        self._title: str = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in _SKIP_TAGS:
            self._skip_depth += 1
        if lower == "title":
            self._in_title = True
        if lower in _BLOCK_TAGS:
            self._pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if lower == "title":
            self._in_title = False
        if lower in _BLOCK_TAGS:
            self._pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title and not self._title:
            self._title = data.strip()
        if self._skip_depth == 0:
            self._pieces.append(data)

    @property
    def title(self) -> str:
        return self._title

    @property
    def text(self) -> str:
        raw = "".join(self._pieces)
        # Collapse whitespace.
        lines = [line.strip() for line in raw.splitlines()]
        text = "\n".join(line for line in lines if line)
        return text


def _html_to_text(html: str) -> tuple[str, str]:
    """Extract (title, body_text) from raw HTML."""
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        pass
    return extractor.title, extractor.text


def extract_urls(seeds: list[str]) -> tuple[list[str], list[str]]:
    """Split seeds into (clean_seeds_without_urls, urls).

    Each seed is scanned for URLs.  URLs are collected into a separate list
    and removed from the seed text.  If removing URLs leaves the seed empty,
    the seed is dropped from the clean list.
    """
    urls: list[str] = []
    clean: list[str] = []
    for seed in seeds:
        found = _URL_RE.findall(seed)
        urls.extend(found)
        remainder = _URL_RE.sub("", seed).strip()
        if remainder:
            clean.append(remainder)
    return clean, urls


async def fetch_url_content(url: str, *, timeout: float = 10.0) -> str | None:
    """Fetch a URL and return extracted text, or None on failure."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            },
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/html" in content_type or "text/plain" in content_type:
            html = resp.text
        else:
            # Not a text page — skip binary content.
            return None

        title, body = _html_to_text(html)
        if not body:
            return None

        # Truncate to keep prompt budget sane.
        truncated = body[:_MAX_CONTENT_CHARS]
        if len(body) > _MAX_CONTENT_CHARS:
            # Cut at last sentence boundary within limit.
            last_period = truncated.rfind("。")  # CJK period
            if last_period < 0:
                last_period = truncated.rfind(".")
            if last_period > _MAX_CONTENT_CHARS // 2:
                truncated = truncated[: last_period + 1]

        header = f"Source: {url}"
        if title:
            header += f"\nTitle: {title}"
        return f"{header}\n\n{truncated}"

    except Exception:
        return None


async def fetch_seed_urls(
    seeds: list[str],
) -> tuple[list[str], list[str]]:
    """Process seeds: extract URLs, fetch their content.

    Returns (effective_seeds, web_stimuli).
    - effective_seeds: original seeds with URLs removed.  If a seed was
      *only* a URL, the page title is used as the seed text instead.
    - web_stimuli: list of fetched page contents (empty if no URLs).
    """
    clean_seeds, urls = extract_urls(seeds)
    if not urls:
        return seeds, []

    # Fetch all URLs concurrently.
    tasks = [fetch_url_content(u) for u in urls]
    results = await asyncio.gather(*tasks)
    web_stimuli = [r for r in results if r is not None]

    # If removing URLs left us with no seeds, derive a seed from the
    # first successfully fetched page title.
    if not clean_seeds and web_stimuli:
        # Extract the Title line from the first stimulus.
        for stim in web_stimuli:
            for line in stim.splitlines():
                if line.startswith("Title:"):
                    title_text = line[len("Title:"):].strip()
                    if title_text:
                        clean_seeds = [title_text]
                        break
            if clean_seeds:
                break
        # Fallback: use the URL domain as the seed.
        if not clean_seeds and urls:
            domain = urlparse(urls[0]).netloc
            clean_seeds = [domain]

    return clean_seeds, web_stimuli
