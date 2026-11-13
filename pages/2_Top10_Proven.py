from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config.watchlists import PROVEN_SUBNETS
from services.taostats_client import TaostatsClient
from utils.formatters import fmt_pct, fmt_tao, fmt_usd

st.set_page_config(page_title="Top 10 Proven", page_icon="🏆", layout="wide")
st.title("🏆 Le 10 Migliori Subnet Proven (Risultati Reali Oggi)")
st.caption("Subnet selezionate per ricavi verificati da clienti esterni, buyback di Alpha e liquidità profonda.")


@st.cache_data(ttl=120, show_spinner=False)
def load_data():
    c = TaostatsClient()
    return c.get_tao_price(), c.get_all_subnet_pools()


tao, pools = load_data()
pools_by_id = {p["netuid"]: p for p in pools}

rows = []
for prof in PROVEN_SUBNETS:
    p = pools_by_id.get(prof.netuid)
    if not p:
        continue
    liq_mcap_ratio = (p["liquidity_usd"] / p["mcap_usd"] * 100.0) if p["mcap_usd"] > 0 else 0.0
    rows.append(
        {
            "SN": prof.netuid,
            "Nome": p["name"],
            "Settore": prof.category,
            "Alpha (τ)": round(p["alpha_price_tao"], 5),
            "Alpha ($)": round(p["alpha_price_usd"], 2),
            "Market Cap ($M)": round(p["mcap_usd"] / 1_000_000, 2),
            "Liquidità Pool ($M)": round(p["liquidity_usd"] / 1_000_000, 2),
            "TAO in Pool": round(p["tao_in_pool"], 0),
            "Liq/MCap %": round(liq_mcap_ratio, 1),
            "Emissioni %": round(p["emission_pct"], 2),
            "Gamma": "✅" if p["gamma_enabled"] else "—",
            "Note Ricavi & Tesi": prof.revenue_note,
        }
    )

df = pd.DataFrame(rows)

tot_mcap = df["Market Cap ($M)"].sum() * 1_000_000
tot_liq = df["Liquidità Pool ($M)"].sum() * 1_000_000
tot_em = df["Emissioni %"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("MCap Totale Top 10 Proven", fmt_usd(tot_mcap))
c2.metric("Liquidità Totale Pool", fmt_usd(tot_liq))
c3.metric("Quota Emissioni Catturata", fmt_pct(tot_em, show_plus=False))
c4.metric("TAO Spot Riferimento", fmt_usd(tao["price_usd"]))

st.divider()
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("📊 Confronto Market Cap vs Liquidità Reale nella Pool ($M)")
chart_df = df.melt(
    id_vars=["Nome"],
    value_vars=["Market Cap ($M)", "Liquidità Pool ($M)"],
    var_name="Metrica",
    value_name="Milioni USD",
)
fig = px.bar(
    chart_df,
    x="Nome",
    y="Milioni USD",
    color="Metrica",
    barmode="group",
    template="plotly_dark",
)
fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig, use_container_width=True)