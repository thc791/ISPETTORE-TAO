from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from services.market_etf_client import MarketEtfClient
from services.sec_edgar_client import SecEdgarClient
from services.taostats_client import TaostatsClient
from utils.formatters import fmt_eur, fmt_pct, fmt_usd

st.set_page_config(page_title="TAO & ETF", page_icon="🏦", layout="wide")
st.title("🏦 Panoramica TAO Spot, ETF / ETP & SEC Filings")


@st.cache_data(ttl=180, show_spinner=False)
def load_etf_page_data():
    tao = TaostatsClient().get_tao_price()
    mkt = MarketEtfClient()
    fx = mkt.get_fx_rates()
    etfs = mkt.get_all_etfs()
    macro = mkt.get_macro_comparison(period="90d")
    filings = SecEdgarClient().get_bittensor_filings()
    return tao, fx, etfs, macro, filings


tao, fx, etfs, macro, filings = load_etf_page_data()

c1, c2, c3, c4 = st.columns(4)
c1.metric("TAO Spot (USD)", fmt_usd(tao["price_usd"]), fmt_pct(tao["change_24h_pct"]))
c2.metric("TAO Spot (EUR)", fmt_eur(tao["price_usd"] * fx["USDEUR"]))
c3.metric("Cambio EUR/USD", f"{fx['EURUSD']:.4f}")
c4.metric("Volume 24h TAO", fmt_usd(tao["volume_24h_usd"]))

st.divider()

# --- TABELLA COMPLETA ETF / ETP ---
st.subheader("📊 Confronto Completo ETF / ETP / Trust")
rows = []
for e in etfs:
    rows.append(
        {
            "Ticker": e["ticker"],
            "Yahoo Symbol": e["yahoo_symbol"],
            "Nome": e["name"],
            "Regione / Mercato": e["region"],
            "ISIN": e["isin"],
            "Valuta": e["currency"],
            "Prezzo Nativo": round(e["price_native"], 3) if e["price_native"] else None,
            "Prezzo (USD)": round(e["price_usd"], 2) if e["price_usd"] else None,
            "Prezzo (EUR)": round(e["price_eur"], 2) if e["price_eur"] else None,
            "Var 1G %": round(e["change_1d_pct"], 2) if e["change_1d_pct"] is not None else None,
            "TER %": e["ter_pct"],
            "Staking Yield": "✅ Sì" if e["staking_included"] else "No",
            "Note": e["notes"],
        }
    )

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# --- CALCOLATORE PREMIO / SCONTO NAV ---
with st.expander("🧮 Calcolatore Rapido Premio / Sconto ETF rispetto a TAO Spot", expanded=False):
    st.caption(
        "Inserisci quanti TAO rappresenta 1 quota del tuo ETF/Trust (dal factsheet dell'emittente, es. ~0.025 TAO per quota) "
        "per calcolare immediatamente se scambia a premio o a sconto."
    )
    col_a, col_b, col_c = st.columns(3)
    sel_etf = col_a.selectbox("Strumento", [e["ticker"] for e in etfs if e["price_usd"]])
    tao_per_share = col_b.number_input("TAO per singola quota", min_value=0.0001, value=0.028, step=0.001, format="%.5f")
    etf_obj = next((e for e in etfs if e["ticker"] == sel_etf), None)
    if etf_obj and etf_obj["price_usd"]:
        implied_nav = tao_per_share * tao["price_usd"]
        prem_disc = ((etf_obj["price_usd"] - implied_nav) / implied_nav) * 100.0
        col_c.metric("Premio (+) / Sconto (-) sul NAV", fmt_pct(prem_disc), f"NAV teorico: {fmt_usd(implied_nav)}")

st.divider()

# --- GRAFICO MACRO TAO vs BTC vs NVDA ---
col_chart, col_sec = st.columns([3, 2])

with col_chart:
    st.subheader("📈 Forza Relativa 90 Giorni: TAO vs BTC vs NVDA (Base 100)")
    if not macro.empty:
        fig = px.line(
            macro,
            labels={"value": "Performance Base 100", "variable": "Asset", "Date": "Data"},
            template="plotly_dark",
        )
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Storico macro temporaneamente non disponibile.")

with col_sec:
    st.subheader("🏛️ Ultimi Filing SEC EDGAR (USA)")
    if filings:
        sec_df = pd.DataFrame(filings)
        st.dataframe(
            sec_df,
            use_container_width=True,
            hide_index=True,
            column_config={"url": st.column_config.LinkColumn("Documento SEC")},
        )
    else:
        st.info("Nessun nuovo filing trovato o limite temporaneo SEC EDGAR.")