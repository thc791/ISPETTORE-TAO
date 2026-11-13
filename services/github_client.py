from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from config.settings import CACHE_TTL_GITHUB_SEC, DATA_DIR, GITHUB_TOKEN


class GitHubClient:
    """Monitora i repository GitHub delle subnet per verificare sviluppo attivo."""

    def __init__(self, token: Optional[str] = None, timeout: float = 12.0) -> None:
        self.token = (token or GITHUB_TOKEN).strip()
        self.timeout = timeout
        self.cache_dir = DATA_DIR / "cache_github"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "IspettoreTAO/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def parse_repo_slug(url_or_slug: str) -> str:
        """Converte 'https://github.com/owner/repo' o 'owner/repo' in 'owner/repo'."""
        s = (url_or_slug or "").strip().rstrip("/")
        if not s:
            return ""
        if "github.com/" in s:
            s = s.split("github.com/", 1)[1]
        parts = [p for p in s.split("/") if p]
        if len(parts) >= 2:
            repo = parts[1].replace(".git", "")
            return f"{parts[0]}/{repo}"
        return ""

    def get_repo_health(self, url_or_slug: str, force_refresh: bool = False) -> Dict[str, Any]:
        slug = self.parse_repo_slug(url_or_slug)
        if not slug:
            return {"slug": "", "status": "no_repo", "commits_30d": None, "stars": None, "last_push": None}

        safe_name = slug.replace("/", "__")
        cache_path = self.cache_dir / f"{safe_name}.json"
        if not force_refresh and cache_path.exists():
            try:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                if time.time() - payload.get("_cached_at", 0) <= CACHE_TTL_GITHUB_SEC:
                    return payload["data"]
            except Exception:
                pass

        since_iso = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            with httpx.Client(timeout=self.timeout, headers=self._headers()) as client:
                repo_resp = client.get(f"https://api.github.com/repos/{slug}")
                if repo_resp.status_code != 200:
                    return {
                        "slug": slug,
                        "status": f"http_{repo_resp.status_code}",
                        "commits_30d": None,
                        "stars": None,
                        "last_push": None,
                    }
                repo_data = repo_resp.json()

                commits_resp = client.get(
                    f"https://api.github.com/repos/{slug}/commits",
                    params={"since": since_iso, "per_page": 100},
                )
                commits_30d = len(commits_resp.json()) if commits_resp.status_code == 200 else 0

            data = {
                "slug": slug,
                "url": f"https://github.com/{slug}",
                "status": "ok",
                "stars": repo_data.get("stargazers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "last_push": (repo_data.get("pushed_at") or "")[:10],
                "commits_30d": commits_30d,
                "archived": bool(repo_data.get("archived", False)),
            }
            cache_path.write_text(
                json.dumps({"_cached_at": time.time(), "data": data}, ensure_ascii=False),
                encoding="utf-8",
            )
            return data
        except Exception as exc:
            return {
                "slug": slug,
                "status": f"error: {exc}",
                "commits_30d": None,
                "stars": None,
                "last_push": None,
            }