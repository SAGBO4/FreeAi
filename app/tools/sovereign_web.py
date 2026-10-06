"""Sovereign Zero-API Web Intelligence & Scraping Engine.

Provides autonomous web search and URL content extraction using Python standard
library only (urllib, html.parser), with zero external API keys and zero tracking.

Features:
- `search(query, max_results=8)`: DuckDuckGo HTML search scraper returning titles,
  clean URLs (stripping tracking redirects), and content snippets. Both awaitable
  and usable synchronously.
- `read_url(url, max_chars=6000)` / `read(...)`: Clean text extractor stripping scripts,
  styles, navigation, headers, footers and SVG elements, returning clean structured text.
- 100% local, resilient with dual sync/async interfaces.
"""

import asyncio
import html
import logging
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sovereign_web")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class AwaitableList(list):
    """List that can be awaited directly in async contexts or used synchronously."""

    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


class AwaitableDict(dict):
    """Dict that can be awaited directly in async contexts or used synchronously."""

    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


class CleanHTMLTextExtractor(HTMLParser):
    """HTML parser extracting readable text while stripping boilerplate elements."""

    IGNORED_TAGS = {
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "svg",
        "noscript",
        "iframe",
        "aside",
    }
    BLOCK_TAGS = {"p", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "tr", "div", "article"}

    def __init__(self) -> None:
        super().__init__()
        self.output: List[str] = []
        self.ignored_depth: int = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        if tag.lower() in self.IGNORED_TAGS:
            self.ignored_depth += 1
        elif tag.lower() in self.BLOCK_TAGS:
            self.output.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.IGNORED_TAGS and self.ignored_depth > 0:
            self.ignored_depth -= 1
        elif tag.lower() in self.BLOCK_TAGS:
            self.output.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self.output.append(data)

    def get_text(self) -> str:
        """Returns normalized and deduplicated whitespace text."""
        raw = "".join(self.output)
        single_spaced = re.sub(r"[ \t]+", " ", raw)
        clean_newlines = re.sub(r"\n\s*\n+", "\n\n", single_spaced)
        return clean_newlines.strip()


# Backward-compatible alias
TextContentExtractor = CleanHTMLTextExtractor


class SovereignWebEngine:
    """Zero-API web search and extraction engine for FreeAI."""

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    def _fetch_html(self, url: str) -> str:
        """Fetches raw HTML from a target URL."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")

    def _search_sync_fallback(self, query: str, max_results: int = 8) -> List[Dict[str, str]]:
        """Synchronous search logic."""
        return self._search_sync(query, max_results)

    def _search_sync(self, query: str, max_results: int = 8) -> List[Dict[str, str]]:
        """Synchronous implementation of DuckDuckGo HTML search."""
        encoded_q = urllib.parse.quote(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
        try:
            raw_html = self._fetch_html(search_url)
        except Exception as e:
            logger.warning(f"[SOVEREIGN WEB] Search query failed: {e}")
            return []

        link_matches = re.findall(
            r'class="result__a"\s+href="([^"]+)"[^>]*>(.*?)</a>',
            raw_html,
            re.DOTALL,
        )
        snippet_matches = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            raw_html,
            re.DOTALL,
        )

        def clean_markup(raw: str) -> str:
            return html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()

        results: List[Dict[str, str]] = []
        for i, (href, raw_title) in enumerate(link_matches[:max_results]):
            parsed = urllib.parse.urlparse(html.unescape(href))
            qs = urllib.parse.parse_qs(parsed.query)
            clean_url = qs.get("uddg", [href])[0]
            title = clean_markup(raw_title)
            snippet = clean_markup(snippet_matches[i]) if i < len(snippet_matches) else ""

            results.append({
                "rank": str(i + 1),
                "title": title,
                "url": clean_url,
                "snippet": snippet,
            })

        return results

    def _read_sync(self, url: str, max_chars: int = 6000) -> Dict[str, Any]:
        """Synchronous implementation of URL text reader."""
        try:
            raw_html = self._fetch_html(url)
            parser = CleanHTMLTextExtractor()
            parser.feed(raw_html)
            clean_text = parser.get_text()

            is_truncated = len(clean_text) > max_chars
            final_text = clean_text[:max_chars]

            return {
                "url": url,
                "content": final_text,
                "length": len(final_text),
                "truncated": is_truncated,
                "success": True,
            }
        except Exception as e:
            logger.warning(f"[SOVEREIGN WEB] Read URL failed ({url}): {e}")
            return {
                "url": url,
                "content": f"Erreur de lecture: {e}",
                "length": 0,
                "truncated": False,
                "success": False,
            }

    def search(self, query: str, max_results: int = 8) -> AwaitableList:
        """Searches DuckDuckGo. Returns AwaitableList usable both sync and async."""
        results = self._search_sync(query, max_results)
        return AwaitableList(results)

    def search_sync(self, query: str, max_results: int = 8) -> List[Dict[str, str]]:
        """Synchronous DuckDuckGo search."""
        return self._search_sync(query, max_results)

    def read_url(self, url: str, max_chars: int = 6000) -> AwaitableDict:
        """Reads clean text from URL. Returns AwaitableDict usable both sync and async."""
        res = self._read_sync(url, max_chars)
        return AwaitableDict(res)

    def read_sync(self, url: str, max_chars: int = 6000) -> Dict[str, Any]:
        """Synchronous URL reading."""
        return self._read_sync(url, max_chars)

    def read(self, url: str, max_chars: int = 6000) -> AwaitableDict:
        return self.read_url(url, max_chars)


# Singleton engine instance
sovereign_web = SovereignWebEngine()
