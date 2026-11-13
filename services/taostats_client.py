from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import httpx

from config.settings import (
    CACHE_TTL_HISTORY_SEC,
    CACHE_TTL_POOLS_SEC,
    CACHE_TTL_PRICE_SEC,
    DATA_DIR,
    RAO_PER_TAO,
    TAOSTATS_API_KEY,
    TAOSTATS_BASE_URL,
)
from config.watchlists import ALL_CURATED_MAP


class TaostatsAPIError(RuntimeError):
    """Errore restituito dalle API Taostats v1."""


def _to_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _rao_to_tao(val: Any) -> float:
    return _to_float(val, 0.0) / RAO_PER_TAO


class TaostatsClient:
    """Client HTTP per Taostats API v1 con cache persistente anti-429."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 20.0) -> None:
        self.api_key = (api_key or TAOSTATS_API_KEY).strip()
        self.base_url = TAOSTATS_BASE_URL.rstrip("/")
        self.timeout = timeout
        self.cache_dir = DATA_DIR / "cache_taostats"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key or "inserisci_qui" in self.api_key:
            raise TaostatsAPIError("TAOSTATS_API_KEY mancante o non configurata nel file .env.")
        return {
            "Authorization": self.api_key,
            "Accept": "application/json",
        }

    def _read_cache(self, cache_name: str, ttl_sec: int, allow_stale: bool = False) -> Optional[Any]:
        path = self.cache_dir / f"{cache_name}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - payload.get("_cached_at", 0)
            if allow_stale or age <= ttl_sec:
                return payload.get("data")
        except Exception:
            return None
        return None

    def _write_cache(self, cache_name: str, data: Any) -> None:
        path = self.cache_dir / f"{cache_name}.json"
        payload = {"_cached_at": time.time(), "data": data}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        cache_name: Optional[str] = None,
        ttl_sec: int = 0,
        force_refresh: bool = False,
    ) -> Any:
        if cache_name and ttl_sec > 0 and not force_refresh:
            cached = self._read_cache(cache_name, ttl_sec, allow_stale=False)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._headers(), params=params or {})

        # Paracadute anti-429: se superiamo il limite al minuto, restituisce l'ultima cache salvata
        if resp.status_code == 429 and cache_name:
            stale = self._read_cache(cache_name, ttl_sec, allow_stale=True)
            if stale is not None:
                return stale

        if resp.status_code >= 400:
            raise TaostatsAPIError(f"Taostats HTTP {resp.status_code} su {endpoint}: {resp.text[:300]}")

        body = resp.json()
        if cache_name and ttl_sec > 0:
            self._write_cache(cache_name, body)
        return body

    def _get_identities_map(self, force_refresh: bool = False) -> Dict[int, Dict[str, Any]]:
        """Carica nomi, link GitHub, siti e descrizioni da /v1/subnets/identities (cache 24 ore)."""
        try:
            raw = self._get(
                "/subnets/identities",
                params={"limit": 200},
                cache_name="subnets_identities",
                ttl_sec=86400,  # 24 ore: risparmia chiamate sul piano Free
                force_refresh=force_refresh,
            )
            rows = raw.get("data", []) if isinstance(raw, dict) else []
            return {int(r["netuid"]): r for r in rows if r.get("netuid") is not None}
        except Exception:
            stale = self._read_cache("subnets_identities", 86400, allow_stale=True)
            if isinstance(stale, dict):
                return {int(r["netuid"]): r for r in stale.get("data", []) if r.get("netuid") is not None}
            return {}

    # ------------------------------------------------------------------
    # ENDPOINT PRINCIPALI
    # ------------------------------------------------------------------

    def get_tao_price(self, force_refresh: bool = False) -> Dict[str, Any]:
        raw = self._get(
            "/price",
            params={"asset": "tao"},
            cache_name="tao_price",
            ttl_sec=max(CACHE_TTL_PRICE_SEC, 120),
            force_refresh=force_refresh,
        )
        rows = raw.get("data", []) if isinstance(raw, dict) else []
        if not rows:
            raise TaostatsAPIError("Nessun dato prezzo ricevuto da /v1/price?asset=tao")

        row = rows[0]
        return {
            "symbol": row.get("symbol", "TAO"),
            "price_usd": _to_float(row.get("price")),
            "market_cap_usd": _to_float(row.get("market_cap")),
            "volume_24h_usd": _to_float(row.get("volume_24h")),
            "change_1h_pct": _to_float(row.get("percent_change_1h")),
            "change_24h_pct": _to_float(row.get("percent_change_24h")),
            "change_7d_pct": _to_float(row.get("percent_change_7d")),
            "change_30d_pct": _to_float(row.get("percent_change_30d")),
            "circulating_supply": _to_float(row.get("circulating_supply")),
            "fdv_usd": _to_float(row.get("fully_diluted_market_cap")),
            "raw": row,
        }

    def get_all_subnet_pools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Carica tutte le pool dTAO + identità ufficiali. Consuma solo 2 chiamate (poi va in cache!).
        """
        raw = self._get(
            "/subnets/pools",
            params={"limit": 200},
            cache_name="subnets_pools",
            ttl_sec=max(CACHE_TTL_POOLS_SEC, 300),
            force_refresh=force_refresh,
        )
        rows = raw.get("data", []) if isinstance(raw, dict) else []
        tao_usd = self.get_tao_price(force_refresh=False).get("price_usd", 0.0)
        id_map = self._get_identities_map(force_refresh=False)

        # Somma prezzi alpha delle subnet > 0 per stimare la quota di emissione dTAO %
        total_alpha_price_sum = sum(
            _to_float(r.get("price")) for r in rows if int(r.get("netuid", -1)) > 0
        )

        normalized: List[Dict[str, Any]] = []
        for r in rows:
            netuid = int(r.get("netuid", -1))
            ident = id_map.get(netuid, {})
            curated = ALL_CURATED_MAP.get(netuid)

            alpha_price_tao = _to_float(r.get("price"))
            tao_in_pool = _rao_to_tao(r.get("tao_in_pool"))
            alpha_in_pool = _rao_to_tao(r.get("alpha_in_pool"))
            alpha_staked = _rao_to_tao(r.get("alpha_staked"))
            alpha_out = _rao_to_tao(r.get("alpha_out"))
            total_alpha = _rao_to_tao(r.get("total_alpha"))

            # Market Cap e Liquidity in Taostats v1 sono espressi in RAO-di-TAO
            mcap_tao = _rao_to_tao(r.get("market_cap"))
            if mcap_tao <= 0 and total_alpha > 0:
                mcap_tao = total_alpha * alpha_price_tao
            mcap_usd = mcap_tao * tao_usd

            liquidity_tao = _rao_to_tao(r.get("liquidity"))
            if liquidity_tao <= 0:
                liquidity_tao = tao_in_pool * 2.0
            liquidity_usd = liquidity_tao * tao_usd

            fdv_usd = (total_alpha * alpha_price_tao * tao_usd) if total_alpha > 0 else mcap_usd

            # Quota emissioni stimata dal peso relativo del prezzo Alpha nella rete dTAO
            emission_pct = (
                (alpha_price_tao / total_alpha_price_sum) * 100.0
                if (netuid > 0 and total_alpha_price_sum > 0)
                else 0.0
            )

            name = (
                ident.get("subnet_name")
                or (curated.name if curated else None)
                or r.get("name")
                or f"Subnet {netuid}"
            )

            normalized.append(
                {
                    "netuid": netuid,
                    "name": name,
                    "symbol": r.get("symbol") or f"SN{netuid}",
                    "tier": curated.tier if curated else "other",
                    "category": curated.category if curated else (ident.get("tags") or "Altro"),
                    "alpha_price_tao": alpha_price_tao,
                    "alpha_price_usd": alpha_price_tao * tao_usd,
                    "gamma_price_tao": _to_float(r.get("gamma_price")),
                    "gamma_enabled": bool(r.get("gamma_enabled", False)),
                    "tao_in_pool": tao_in_pool,
                    "liquidity_tao": liquidity_tao,
                    "liquidity_usd": liquidity_usd,
                    "alpha_in_pool": alpha_in_pool,
                    "alpha_staked": alpha_staked,
                    "alpha_out": alpha_out,
                    "total_alpha": total_alpha,
                    "mcap_tao": mcap_tao,
                    "mcap_usd": mcap_usd,
                    "fdv_usd": fdv_usd,
                    "root_prop": _to_float(r.get("root_prop")),
                    "startup_mode": bool(r.get("startup_mode", False)),
                    "emission_pct": emission_pct,
                    "github_url": ident.get("github_repo") or (curated.github_repo if curated else ""),
                    "website": ident.get("subnet_url") or "",
                    "discord": ident.get("discord") or "",
                    "twitter": ident.get("twitter") or "",
                    "description": ident.get("description") or (curated.thesis if curated else ""),
                    "timestamp": r.get("timestamp", ""),
                    "raw": r,
                }
            )

        return normalized

    def get_pool_history(
        self,
        netuid: int,
        frequency: str = "by_hour",
        limit: int = 168,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        raw = self._get(
            "/subnets/pools/history",
            params={
                "netuid": netuid,
                "frequency": frequency,
                "limit": min(limit, 200),
                "order": "timestamp_desc",
            },
            cache_name=f"pool_hist_{netuid}_{frequency}_{limit}",
            ttl_sec=CACHE_TTL_HISTORY_SEC,
            force_refresh=force_refresh,
        )
        rows = raw.get("data", []) if isinstance(raw, dict) else []
        parsed: List[Dict[str, Any]] = []
        for r in reversed(rows):
            parsed.append(
                {
                    "timestamp": r.get("timestamp"),
                    "block_number": r.get("block_number"),
                    "price_tao": _to_float(r.get("price")),
                    "tao_in_pool": _rao_to_tao(r.get("tao_in_pool")),
                    "alpha_in_pool": _rao_to_tao(r.get("alpha_in_pool")),
                    "total_alpha": _rao_to_tao(r.get("total_alpha")),
                }
            )
        return parsed

    def get_deregistration_ranking(self, force_refresh: bool = False) -> Dict[int, Dict[str, Any]]:
        try:
            raw = self._get(
                "/subnets/deregistrations",
                params={"limit": 200},
                cache_name="subnets_dereg",
                ttl_sec=900,
                force_refresh=force_refresh,
            )
            rows = raw.get("data", []) if isinstance(raw, dict) else []
            out: Dict[int, Dict[str, Any]] = {}
            for idx, r in enumerate(rows, start=1):
                nid = int(r.get("netuid", -1))
                out[nid] = {
                    "rank": r.get("rank") or idx,
                    "registered_at_block": r.get("registered_at_block"),
                    "is_immune": bool(r.get("is_immune", False)),
                    "raw": r,
                }
            return out
        except Exception:
            return {}

    def get_coldkey_distribution(self, netuid: int, force_refresh: bool = False) -> List[Dict[str, Any]]:
        try:
            raw = self._get(
                "/subnets/distribution/coldkey",
                params={"netuid": netuid, "limit": 50},
                cache_name=f"coldkey_dist_{netuid}",
                ttl_sec=CACHE_TTL_HISTORY_SEC,
                force_refresh=force_refresh,
            )
            return raw.get("data", []) if isinstance(raw, dict) else []
        except Exception:
            return []