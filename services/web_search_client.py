from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List

import httpx

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


STOPWORDS_IT = {
    "quali", "quale", "sono", "ci", "su", "e", "o", "di", "del", "della", "delle",
    "dei", "degli", "il", "lo", "la", "i", "gli", "le", "un", "una", "per", "con",
    "tra", "fra", "che", "cosa", "come", "perche", "perché", "novita", "novità",
    "recenti", "ultime", "aggiornamenti", "dammi", "dimmi", "analizza", "analisi",
    "spiegami", "confronta", "oggi", "questo", "questa", "questi", "queste",
    "hanno", "ha", "fare", "fanno", "sta", "stanno", "migliori", "piu", "più",
}


def build_clean_query(raw_text: str, prefix: str = "Bittensor") -> str:
    """Estrae fino a 5 parole chiave pulite da una frase naturale."""
    tokens = re.findall(r"[A-Za-z0-9.\-]+", raw_text or "")
    keywords = [t for t in tokens if t.lower() not in STOPWORDS_IT and len(t) > 1]
    if prefix.lower() not in [k.lower() for k in keywords]:
        keywords.insert(0, prefix)
    return " ".join(keywords[:6])


class WebSearchClient:
    """Motore di ricerca web gratuito (DuckDuckGo Web/News + Google News RSS)."""

    @staticmethod
    def search_web(query: str, max_results: int = 8) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        seen_urls = set()

        # 1. DuckDuckGo News + Text
        if DDGS is not None:
            try:
                with DDGS() as ddgs:
                    for item in ddgs.news(query, max_results=max_results):
                        url = item.get("url") or item.get("href") or ""
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append(
                                {
                                    "title": item.get("title", ""),
                                    "snippet": item.get("body", ""),
                                    "url": url,
                                    "source": item.get("source") or "News",
                                }
                            )
            except Exception:
                pass

            if len(results) < max_results:
                try:
                    with DDGS() as ddgs:
                        for item in ddgs.text(query, max_results=max_results):
                            url = item.get("href") or item.get("url") or ""
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                results.append(
                                    {
                                        "title": item.get("title", ""),
                                        "snippet": item.get("body", ""),
                                        "url": url,
                                        "source": "Web",
                                    }
                                )
                except Exception:
                    pass

        # 2. Google News RSS (zero API key)
        if len(results) < max_results:
            try:
                encoded_q = urllib.parse.quote(query)
                rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                    resp = client.get(rss_url)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    for item in root.findall(".//item")[:5]:
                        title = item.findtext("title") or ""
                        link = item.findtext("link") or ""
                        pub = item.findtext("pubDate") or ""
                        if link and link not in seen_urls:
                            seen_urls.add(link)
                            results.append(
                                {
                                    "title": title,
                                    "snippet": f"Pubblicato: {pub}",
                                    "url": link,
                                    "source": "Google News",
                                }
                            )
            except Exception:
                pass

        return results[:max_results]