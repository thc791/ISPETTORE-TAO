from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from config.settings import DATA_DIR
from config.watchlists import TAO_ETFS


class MarketEtfClient:
    """Recupera prezzi ETF/ETP TAO, tassi di cambio FX e serie macro (BTC, NVDA)."""

    def __init__(self, cache_ttl_sec: int = 300) -> None:
        self.cache_ttl_sec = cache_ttl_sec
        self.cache_dir = DATA_DIR / "cache_market"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _read_cache(self, name: str) -> Optional[Any]:
        path = self.cache_dir / f"{name}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - payload.get("_cached_at", 0) <= self.cache_ttl_sec:
                return payload.get("data")
        except Exception:
            return None
        return None

    def _write_cache(self, name: str, data: Any) -> None:
        path = self.cache_dir / f"{name}.json"
        path.write_text(
            json.dumps({"_cached_at": time.time(), "data": data}, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _fetch_last_price_and_change(symbol: str) -> Optional[Dict[str, Any]]:
        try:
            hist = yf.Ticker(symbol).history(period="7d", interval="1d")
            if hist is None or hist.empty or "Close" not in hist.columns:
                return None
            closes = hist["Close"].dropna()
            if closes.empty:
                return None
            last_price = float(closes.iloc[-1])
            prev_price = float(closes.iloc[-2]) if len(closes) >= 2 else last_price
            chg_pct = ((last_price - prev_price) / prev_price * 100.0) if prev_price > 0 else 0.0
            last_date = str(closes.index[-1])[:10]
            volume = float(hist["Volume"].dropna().iloc[-1]) if "Volume" in hist.columns and not hist["Volume"].dropna().empty else 0.0
            return {
                "yahoo_symbol": symbol,
                "price": last_price,
                "change_1d_pct": chg_pct,
                "volume": volume,
                "last_date": last_date,
            }
        except Exception:
            return None

    def get_fx_rates(self, force_refresh: bool = False) -> Dict[str, float]:
        """Ritorna tassi EUR->USD, USD->EUR, SEK->USD."""
        if not force_refresh:
            cached = self._read_cache("fx_rates")
            if cached is not None:
                return cached

        eur_usd = 1.08
        sek_usd = 0.095

        eur_data = self._fetch_last_price_and_change("EURUSD=X")
        if eur_data and eur_data["price"] > 0:
            eur_usd = eur_data["price"]

        sek_data = self._fetch_last_price_and_change("SEKUSD=X")
        if sek_data and sek_data["price"] > 0:
            sek_usd = sek_data["price"]

        rates = {
            "EURUSD": eur_usd,
            "USDEUR": 1.0 / eur_usd if eur_usd > 0 else 0.92,
            "SEKUSD": sek_usd,
            "USD": 1.0,
            "EUR": eur_usd,
            "SEK": sek_usd,
        }
        self._write_cache("fx_rates", rates)
        return rates

    def get_all_etfs(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Recupera quotazioni per tutti gli ETF/ETP/Trust TAO configurati."""
        if not force_refresh:
            cached = self._read_cache("etfs_snapshot")
            if cached is not None:
                return cached

        fx = self.get_fx_rates(force_refresh=force_refresh)
        results: List[Dict[str, Any]] = []

        for etf in TAO_ETFS:
            quote = None
            for cand in etf.yahoo_candidates:
                quote = self._fetch_last_price_and_change(cand)
                if quote is not None:
                    break

            price_native = quote["price"] if quote else None
            # Determina moltiplicatore FX verso USD
            fx_to_usd = fx.get(etf.currency, 1.0)
            price_usd = (price_native * fx_to_usd) if price_native is not None else None
            price_eur = (price_usd * fx["USDEUR"]) if price_usd is not None else None

            results.append(
                {
                    "ticker": etf.ticker,
                    "yahoo_symbol": quote["yahoo_symbol"] if quote else "N/D",
                    "name": etf.name,
                    "issuer": etf.issuer,
                    "region": etf.region,
                    "isin": etf.isin,
                    "currency": etf.currency,
                    "price_native": price_native,
                    "price_usd": price_usd,
                    "price_eur": price_eur,
                    "change_1d_pct": quote["change_1d_pct"] if quote else None,
                    "volume": quote["volume"] if quote else 0.0,
                    "last_date": quote["last_date"] if quote else "N/D",
                    "ter_pct": etf.ter_pct,
                    "staking_included": etf.staking_included,
                    "notes": etf.notes,
                    "status": "OK" if quote else "Non trovato su Yahoo",
                }
            )

        self._write_cache("etfs_snapshot", results)
        return results

    def get_macro_comparison(self, period: str = "90d", force_refresh: bool = False) -> pd.DataFrame:
        """
        Ritorna serie normalizzata (base 100) di TAO-USD, BTC-USD e NVDA
        per confrontare la forza relativa di Bittensor rispetto a BTC e settore AI.
        """
        cache_name = f"macro_{period}"
        if not force_refresh:
            cached = self._read_cache(cache_name)
            if cached is not None:
                df = pd.DataFrame(cached)
                if not df.empty and "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"])
                    return df.set_index("Date")

        tickers = {"TAO": "TAO22974-USD", "BTC": "BTC-USD", "NVDA": "NVDA"}
        series_map: Dict[str, pd.Series] = {}

        # Fallback su TAO-USD se il ticker CoinMarketCap su Yahoo differisce
        tao_hist = yf.Ticker("TAO22974-USD").history(period=period)
        if tao_hist is None or tao_hist.empty:
            tao_hist = yf.Ticker("TAO-USD").history(period=period)
        if tao_hist is not None and not tao_hist.empty:
            s = tao_hist["Close"].dropna()
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            series_map["TAO"] = s

        for label in ("BTC", "NVDA"):
            h = yf.Ticker(tickers[label]).history(period=period)
            if h is not None and not h.empty:
                s = h["Close"].dropna()
                s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                series_map[label] = s

        if not series_map:
            return pd.DataFrame()

        df = pd.DataFrame(series_map).ffill().dropna()
        if df.empty:
            return df

        # Normalizza tutto a base 100 al primo giorno disponibile
        norm_df = (df / df.iloc[0]) * 100.0
        to_cache = norm_df.reset_index()
        to_cache.rename(columns={to_cache.columns[0]: "Date"}, inplace=True)
        to_cache["Date"] = to_cache["Date"].astype(str)
        self._write_cache(cache_name, to_cache.to_dict(orient="records"))
        return norm_df