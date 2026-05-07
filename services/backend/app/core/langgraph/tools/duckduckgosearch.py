
"""DuckDuckGo search tool with page text extraction for LangGraph."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser

import httpx
from ddgs import DDGS
from langchain_core.tools import tool


class _HTMLTextExtractor(HTMLParser):
    """Convert HTML into readable plain text."""

    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "dl",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
    _SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return

        if self._skip_depth == 0 and tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
            return

        if self._skip_depth == 0 and tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())
            self._chunks.append(" ")

    def get_text(self) -> str:
        text = "".join(self._chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _extract_text_from_html(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.get_text()


def _fetch_result_text(
    client: httpx.Client,
    url: str,
    max_chars_per_result: int,
) -> str:
    try:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - network failures vary
        return f"Extraction error: {exc}"

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        return f"Skipped non-HTML content: {content_type or 'unknown content type'}"

    extracted_text = _extract_text_from_html(response.text)
    if not extracted_text:
        return "No readable text extracted from page."

    return extracted_text[:max_chars_per_result]


@tool("duckduckgo_results_json")
def duckduckgo_results_json(
    query: str,
    num_results: int = 5,
    max_chars_per_result: int = 2000,
) -> str:
    """Search DuckDuckGo and extract readable text from each result page.

    Args:
        query: Search query string.
        num_results: Number of search results to fetch (1-10).
        max_chars_per_result: Maximum extracted text to include per result.

    Returns:
        JSON list of search results with titles, links, snippets, and extracted text.
    """
    query = query.strip()
    if not query:
        return "Error: query cannot be empty."

    if num_results < 1 or num_results > 10:
        return "Error: num_results must be between 1 and 10."

    if max_chars_per_result < 250:
        return "Error: max_chars_per_result must be at least 250."

    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=num_results))

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        }
        timeout = httpx.Timeout(10.0, connect=5.0)

        enriched_results = []
        with httpx.Client(headers=headers, timeout=timeout) as client:
            for result in search_results:
                url = result.get("href") or result.get("url") or ""
                enriched_results.append(
                    {
                        "title": result.get("title", ""),
                        "link": url,
                        "snippet": result.get("body", ""),
                        "extracted_text": (
                            _fetch_result_text(client, url, max_chars_per_result)
                            if url
                            else "No result URL provided."
                        ),
                    }
                )

        return json.dumps(enriched_results, indent=2)
    except Exception as exc:
        return f"DuckDuckGo search error: {exc}"


duckduckgo_search_tool = duckduckgo_results_json
