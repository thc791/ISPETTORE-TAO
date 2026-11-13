from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config.watchlists import EXTRA_WATCHLIST, PROMISING_SUBNETS
from services.taostats_client import TaostatsClient
from utils.formatters import fmt_pct, fmt_usd

st.set_page_config(page_title="Top 10 Promettenti", page_icon="🚀", layout="wide")
st.title("🚀 Le 10 Subnet più Promettenti (Escluse le Prime 10)")
st.caption(
    "Mid-cap e micro-cap ad alta convinzione. Guarda la colonna 'Em% / MCap': "
    "valori alti indicano subnet che catturano molte emissioni rispetto alla loro capitalizzazione."
)


@st.cache_data(ttl=120, show_spinner=False)
def load_data():
    c = TaostatsClient()
    return c.get_tao_price(), c.get_all_subnet_pools()


tao, pools = load_data()
pools_by_id = {p["netuid"]: p for p in pools}


def build_table(profiles):
    rows = []
    for prof in profiles:
        p = pools_by_id.get(prof.netuid)
        if not p:
            continue
        mcap_m = p["mcap_usd"] / 1_000_000
        em_mcap_ratio = (p["emission_pct"] / mcap_m) if mcap_m > 0 else 0.0
        rows.append(
            {
                "SN": prof.netuid,
                "Nome": p["name"],
                "Settore": prof.category,
                "Alpha (τ)": round(p["alpha_price_tao"], 5),
                "Alpha ($)": round(p["alpha_price_usd"], 2),
                "Market Cap ($M)": round(mcap_m, 2),
                "Liquidità ($M)": round(p["liquidity_usd"] / 1_000_000, 2),
                "TAO in Pool": round(p["tao_in_pool"], 0),
                "Emissioni %": round(p["emission_pct"], 2),
                "Em% / MCap": round(em_mcap_ratio, 3),
                "Gamma": "✅" if p["gamma_enabled"] else "—",
                "Tesi & Rischi": prof.revenue_note,
            }
        )
    return pd.DataFrame(rows)


df = build_table(PROMISING_SUBNETS)

c1, c2, c3 = st.columns(3)
c1.metric("MCap Totale Top 10 Promettenti", fmt_usd(df["Market Cap ($M)"].sum() * 1_000_000))
c2.metric("Liquidità Totale Pool", fmt_usd(df["Liquidità ($M)"].sum() * 1_000_000))
c3.metric("Quota Emissioni Catturata", fmt_pct(df["Emissioni %"].sum(), show_plus=False))

st.divider()
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🎯 Mappa Valutazione vs Emissioni (Dimensione bolla = Liquidità Pool)")
fig = px.scatter(
    df,
    x="Market Cap ($M)",
    y="Emissioni %",
    size="Liquidità ($M)",
    color="Settore",
    text="Nome",
    hover_data=["SN", "TAO in Pool", "Em% / MCap"],
    template="plotly_dark",
)
fig.update_traces(textposition="top center")
fig.update_layout(height=440, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig, use_container_width=True)

with st.expander("📌 Watchlist Extra (5 gemme aggiuntive ad alta convinzione)"):
    st.dataframe(build_table(EXTRA_WATCHLIST), use_container_width=True, hide_index=True)