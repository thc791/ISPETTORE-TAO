from __future__ import annotations

import pandas as pd
import streamlit as st

from config.watchlists import (
    ALL_CURATED_MAP,
    PROMISING_NETUIDS,
    PROVEN_NETUIDS,
)
from services.gemini_analyst import GeminiAnalyst
from services.market_etf_client import MarketEtfClient
from services.taostats_client import TaostatsClient
from utils.formatters import fmt_eur, fmt_pct, fmt_tao, fmt_usd

st.set_page_config(
    page_title="Ispettore TAO Terminal",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=120, show_spinner=False)
def load_core_market(force: bool = False):
    tao_client = TaostatsClient()
    mkt_client = MarketEtfClient()
    tao = tao_client.get_tao_price(force_refresh=force)
    pools = tao_client.get_all_subnet_pools(force_refresh=force)
    fx = mkt_client.get_fx_rates(force_refresh=force)
    etfs = mkt_client.get_all_etfs(force_refresh=force)
    return tao, pools, fx, etfs


with st.sidebar:
    st.title("🦅 Ispettore TAO")
    st.caption("Terminale Analisi Bittensor, dTAO & ETF")
    if st.button("🔄 Aggiorna Dati Live", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Stato Connessioni")
    g_ok = GeminiAnalyst().is_ready()
    st.write("🤖 Gemini 4 Hydrogen:", "🟢 Attivo" if g_ok else "🔴 Chiave mancante")

try:
    tao, pools, fx, etfs = load_core_market()
    with st.sidebar:
        st.write("⛓️ Taostats API v1:", f"🟢 {len(pools)} Subnet")
        ok_etfs = sum(1 for e in etfs if e["status"] == "OK")
        st.write("📈 ETF / ETP Feed:", f"🟢 {ok_etfs}/{len(etfs)} attivi")
except Exception as exc:
    st.error(f"Errore nel caricamento dati iniziali: {exc}")
    st.stop()

# --- HEADER BARRA STILE TERMINALE ---
st.title("🦅 Ispettore TAO — Control Room")

tao_usd = tao["price_usd"]
tao_eur = tao_usd * fx["USDEUR"]
active_subnets = [p for p in pools if p["netuid"] > 0]
total_pool_tao = sum(p["tao_in_pool"] for p in active_subnets)
total_subnet_mcap_usd = sum(p["mcap_usd"] for p in active_subnets)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("TAO / USD", fmt_usd(tao_usd), fmt_pct(tao["change_24h_pct"]))
c2.metric("TAO / EUR", fmt_eur(tao_eur), f"7d: {fmt_pct(tao.get('change_7d_pct'))}")
c3.metric("Market Cap TAO", fmt_usd(tao["market_cap_usd"]), f"30d: {fmt_pct(tao.get('change_30d_pct'))}")
c4.metric("MCap Aggregata Subnet", fmt_usd(total_subnet_mcap_usd), f"{len(active_subnets)} subnet attive")
c5.metric("TAO nelle Pool dTAO", fmt_tao(total_pool_tao), fmt_usd(total_pool_tao * tao_usd))

st.divider()

# --- MINI PANORAMICA ETF ---
st.subheader("🏦 Monitor Rapido ETF / ETP & Trust su TAO")
etf_cols = st.columns(len(etfs))
for idx, etf in enumerate(etfs):
    with etf_cols[idx]:
        val = (
            f"{etf['price_native']:.2f} {etf['currency']}"
            if etf["price_native"] is not None
            else "N/D"
        )
        delta = fmt_pct(etf["change_1d_pct"]) if etf["change_1d_pct"] is not None else "—"
        st.metric(f"{etf['ticker']} ({etf['currency']})", val, delta)
        st.caption(f"USD: {fmt_usd(etf['price_usd'])} | EUR: {fmt_eur(etf['price_eur'])}")

st.divider()

# --- AFFIANCAMENTO TOP 10 PROVEN vs TOP 10 PROMETTENTI ---
pools_by_id = {p["netuid"]: p for p in pools}


def build_summary_df(netuids):
    rows = []
    for nid in netuids:
        p = pools_by_id.get(nid)
        if not p:
            continue
        curated = ALL_CURATED_MAP.get(nid)
        rows.append(
            {
                "SN": nid,
                "Nome": p["name"],
                "Settore": curated.category if curated else p["category"],
                "Prezzo Alpha (τ)": round(p["alpha_price_tao"], 5),
                "Prezzo ($)": round(p["alpha_price_usd"], 2),
                "MCap ($M)": round(p["mcap_usd"] / 1_000_000, 2),
                "Pool (τ)": round(p["tao_in_pool"], 0),
                "Emissioni %": round(p["emission_pct"], 2),
                "Gamma": "✅" if p["gamma_enabled"] else "—",
            }
        )
    return pd.DataFrame(rows)


col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🏆 Top 10 Proven (Risultati Oggi)")
    st.dataframe(build_summary_df(PROVEN_NETUIDS), use_container_width=True, hide_index=True)

with col_right:
    st.subheader("🚀 Top 10 Promettenti (Escluse le Prime 10)")
    st.dataframe(build_summary_df(PROMISING_NETUIDS), use_container_width=True, hide_index=True)

st.info(
    "👈 Usa il menu a sinistra per aprire: **Panoramica TAO & ETF**, le viste dettagliate **Top 10 Proven / Promettenti**, "
    "l'**Analisi Singola Subnet con Gemini**, il tuo **Portafoglio con Calcolo Slippage** e la **Finestra Prompt Copilot**."
)