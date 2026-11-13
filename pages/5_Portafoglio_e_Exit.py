from __future__ import annotations

import pandas as pd
import streamlit as st

from config.watchlists import TAO_ETFS
from core.portfolio_engine import evaluate_portfolio, load_portfolio, save_portfolio
from core.slippage_calc import simulate_alpha_sell_to_tao
from services.market_etf_client import MarketEtfClient
from services.taostats_client import TaostatsClient
from utils.formatters import fmt_eur, fmt_pct, fmt_tao, fmt_usd

st.set_page_config(page_title="Portafoglio & Exit", page_icon="💼", layout="wide")
st.title("💼 Portafoglio Multi-Layer & Calcolatore Mark-to-Exit")
st.caption(
    "Monitora insieme TAO Spot/Root, Subnet Alpha ed ETF/ETP. "
    "Controlla sempre 'P&L in TAO (τ)': ti dice se una subnet sta battendo o sottoperformando il semplice tenere TAO."
)


@st.cache_data(ttl=120, show_spinner=False)
def load_market():
    c = TaostatsClient()
    m = MarketEtfClient()
    return c.get_tao_price(), c.get_all_subnet_pools(), m.get_fx_rates(), m.get_all_etfs()


tao, pools, fx, etfs = load_market()
active_pools = sorted([p for p in pools if p["netuid"] > 0], key=lambda x: x["mcap_usd"], reverse=True)
pools_by_id = {p["netuid"]: p for p in active_pools}
etfs_by_ticker = {e["ticker"]: e for e in etfs}

positions = load_portfolio()

# --- FORM AGGIUNTA POSIZIONE ---
with st.expander("➕ Aggiungi una Posizione al Portafoglio Locale (salvato in data/portfolio.json)", expanded=not positions):
    ptype = st.radio("Tipo Asset", ["Subnet Alpha", "TAO Spot / Root", "ETF / ETP"], horizontal=True)
    c1, c2, c3, c4 = st.columns(4)

    netuid = 0
    ticker = ""
    label = ""

    if ptype == "Subnet Alpha":
        netuid = c1.selectbox(
            "Subnet",
            [p["netuid"] for p in active_pools],
            format_func=lambda nid: f"SN{nid} — {pools_by_id[nid]['name']}",
        )
        label = f"SN{netuid} {pools_by_id[netuid]['name']}"
        qty = c2.number_input("Quantità Token Alpha", min_value=0.0, value=100.0, step=10.0)
    elif ptype == "TAO Spot / Root":
        label = c1.text_input("Etichetta", value="TAO Root (SN0)")
        qty = c2.number_input("Quantità TAO (τ)", min_value=0.0, value=10.0, step=1.0)
    else:
        ticker = c1.selectbox("Ticker ETF/ETP", [e["ticker"] for e in TAO_ETFS])
        label = f"ETF {ticker}"
        qty = c2.number_input("Numero Quote", min_value=0.0, value=50.0, step=1.0)

    cost_usd = c3.number_input("Costo Totale Pagato ($ USD)", min_value=0.0, value=1000.0, step=50.0)
    default_cost_tao = round(cost_usd / tao["price_usd"], 4) if tao["price_usd"] > 0 else 0.0
    cost_tao = c4.number_input("Equivalente in TAO al momento dell'acquisto (τ)", min_value=0.0, value=default_cost_tao, step=0.5)

    if st.button("💾 Salva Posizione", type="primary"):
        positions.append(
            {
                "type": ptype,
                "netuid": netuid,
                "ticker": ticker,
                "label": label,
                "quantity": qty,
                "cost_basis_usd": cost_usd,
                "cost_basis_tao": cost_tao,
            }
        )
        save_portfolio(positions)
        st.success(f"Posizione '{label}' salvata!")
        st.rerun()

st.divider()

# --- VALUTAZIONE PORTAFOGLIO ---
if positions:
    ev = evaluate_portfolio(
        positions=positions,
        pools_by_netuid=pools_by_id,
        tao_price_usd=tao["price_usd"],
        usd_to_eur=fx["USDEUR"],
        etfs_by_ticker=etfs_by_ticker,
    )
    tot = ev["totals"]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Valore Exit Netto (USD)", fmt_usd(tot["exit_usd"]), f"Nominale: {fmt_usd(tot['nominal_usd'])}")
    m2.metric("Valore Exit Netto (EUR)", fmt_eur(tot["exit_eur"]))
    m3.metric("Valore Netto in TAO", fmt_tao(tot["exit_tao"]))
    pnl_usd_pct = (tot["pnl_usd"] / tot["cost_usd"] * 100.0) if tot["cost_usd"] > 0 else 0.0
    m4.metric("P&L Totale ($)", fmt_usd(tot["pnl_usd"]), fmt_pct(pnl_usd_pct))
    pnl_tao_pct = (tot["pnl_tao"] / tot["cost_tao"] * 100.0) if tot["cost_tao"] > 0 else 0.0
    m5.metric("P&L vs Tenere TAO (τ)", fmt_tao(tot["pnl_tao"]), fmt_pct(pnl_tao_pct))

    df_rows = [
        {
            "ID": r["id"],
            "Tipo": r["type"],
            "Asset": r["asset"],
            "Quantità": round(r["quantity"], 3),
            "Nominale (τ)": round(r["nominal_tao"], 3),
            "Exit Netto (τ)": round(r["exit_tao"], 3),
            "Slippage %": round(r["slippage_pct"], 2),
            "Valore Exit ($)": round(r["exit_usd"], 2),
            "Valore Exit (€)": round(r["exit_eur"], 2),
            "P&L ($)": round(r["pnl_usd"], 2),
            "P&L in TAO (τ)": round(r["pnl_tao"], 3),
            "vs TAO %": round(r["pnl_tao_pct"], 2),
        }
        for r in ev["rows"]
    ]
    st.dataframe(pd.DataFrame(df_rows), use_container_width=True, hide_index=True)

    col_del1, col_del2 = st.columns([3, 1])
    del_id = col_del1.selectbox(
        "Rimuovi una posizione",
        [r["id"] for r in ev["rows"]],
        format_func=lambda idx: f"#{idx} — {ev['rows'][idx]['asset']} ({ev['rows'][idx]['quantity']})",
    )
    if col_del2.button("🗑️ Elimina Selezionata"):
        positions.pop(del_id)
        save_portfolio(positions)
        st.rerun()
else:
    st.info("Il tuo portafoglio locale è vuoto. Apri il box qui sopra per aggiungere le tue prime posizioni!")

st.divider()

# --- SIMULATORE ISTANTANEO DI USCITA ---
st.subheader("🧮 Simulatore Libero di Slippage (Prima di Fare uno Swap)")
sc1, sc2 = st.columns(2)
sim_nid = sc1.selectbox(
    "Scegli Subnet da simulare",
    [p["netuid"] for p in active_pools],
    format_func=lambda nid: f"SN{nid} — {pools_by_id[nid]['name']} (Pool: {fmt_tao(pools_by_id[nid]['tao_in_pool'])})",
)
sim_alpha = sc2.number_input("Quantità di Alpha da vendere", min_value=1.0, value=500.0, step=50.0)

sim_pool = pools_by_id[sim_nid]
res = simulate_alpha_sell_to_tao(sim_alpha, sim_pool["tao_in_pool"], sim_pool["alpha_in_pool"])

r1, r2, r3, r4 = st.columns(4)
r1.metric("Valore Nominale", fmt_tao(res["nominal_value_tao"]), fmt_usd(res["nominal_value_tao"] * tao["price_usd"]))
r2.metric("TAO Reali Ricevuti", fmt_tao(res["realized_tao"]), fmt_usd(res["realized_tao"] * tao["price_usd"]))
r3.metric("Price Impact (Slippage)", f"-{res['price_impact_pct']:.3f}%")
r4.metric("Prezzo Effettivo vs Spot", f"{res['effective_price_tao']:.5f} τ", f"Spot: {res['spot_price_tao']:.5f} τ")