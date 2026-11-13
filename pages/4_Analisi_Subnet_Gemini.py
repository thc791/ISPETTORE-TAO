from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config.watchlists import ALL_CURATED_MAP, EXTRA_WATCHLIST, PROMISING_NETUIDS, PROVEN_NETUIDS
from core.health_scoring import compute_top5_concentration_pct, evaluate_subnet_health
from core.slippage_calc import stress_test_exit_ladder
from services.gemini_analyst import GeminiAnalyst
from services.github_client import GitHubClient
from services.taostats_client import TaostatsClient
from utils.formatters import fmt_tao, fmt_usd

st.set_page_config(page_title="Analisi Subnet & Gemini", page_icon="🔬", layout="wide")
st.title("🔬 Analisi Singola Subnet & Intelligence Gemini 4 Hydrogen")


@st.cache_data(ttl=120, show_spinner=False)
def load_pools():
    c = TaostatsClient()
    return c.get_tao_price(), c.get_all_subnet_pools()


tao, pools = load_pools()
active_pools = sorted([p for p in pools if p["netuid"] > 0], key=lambda x: x["mcap_usd"], reverse=True)
pools_by_id = {p["netuid"]: p for p in active_pools}

# --- FILTRO RAPIDO SUBNET ---
col_f1, col_f2 = st.columns([1, 2])
group_choice = col_f1.selectbox(
    "Gruppo rapido",
    ["Top 10 Proven", "Top 10 Promettenti", "Extra Watchlist", "Tutte le Subnet (per MCap)"],
)

if group_choice == "Top 10 Proven":
    candidate_ids = [nid for nid in PROVEN_NETUIDS if nid in pools_by_id]
elif group_choice == "Top 10 Promettenti":
    candidate_ids = [nid for nid in PROMISING_NETUIDS if nid in pools_by_id]
elif group_choice == "Extra Watchlist":
    candidate_ids = [s.netuid for s in EXTRA_WATCHLIST if s.netuid in pools_by_id]
else:
    candidate_ids = [p["netuid"] for p in active_pools]

selected_nid = col_f2.selectbox(
    "Seleziona Subnet",
    candidate_ids,
    format_func=lambda nid: (
        f"SN{nid} — {pools_by_id[nid]['name']} "
        f"(MCap: {fmt_usd(pools_by_id[nid]['mcap_usd'])} | Em: {pools_by_id[nid]['emission_pct']:.2f}%)"
    ),
)

pool = pools_by_id[selected_nid]
curated = ALL_CURATED_MAP.get(selected_nid)

# --- KPI PRINCIPALI ---
st.divider()
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Prezzo Alpha (τ)", f"{pool['alpha_price_tao']:.5f} τ", fmt_usd(pool["alpha_price_usd"]))
k2.metric("Market Cap", fmt_usd(pool["mcap_usd"]), fmt_tao(pool["mcap_tao"]))
k3.metric("TAO nella Pool", fmt_tao(pool["tao_in_pool"]), f"Liq: {fmt_usd(pool['liquidity_usd'])}")
k4.metric("Quota Emissioni", f"{pool['emission_pct']:.2f}%")
k5.metric("Gamma Credits", "✅ Attivo" if pool["gamma_enabled"] else "Non attivo")

if pool.get("description") or (curated and curated.revenue_note):
    st.info(
        f"**Tesi / Descrizione:** {pool.get('description') or curated.thesis}  \n"
        f"**Note Economiche:** {curated.revenue_note if curated else 'Usa il dossier Gemini qui sotto per ricavi/buyback aggiornati.'}"
    )

if pool.get("github_url") or pool.get("website"):
    links = []
    if pool.get("website"):
        links.append(f"🌐 [Sito Ufficiale]({pool['website']})")
    if pool.get("github_url"):
        links.append(f"💻 [GitHub]({pool['github_url']})")
    if pool.get("twitter"):
        links.append(f"𝕏 [Social]({pool['twitter']})")
    st.markdown(" | ".join(links))

st.divider()

# --- STORICO 7GG + STRESS TEST SLIPPAGE ---
col_hist, col_slip = st.columns([3, 2])

with col_hist:
    st.subheader("📈 Andamento Prezzo Alpha (ultimi 7 giorni, in τ)")
    try:
        hist = TaostatsClient().get_pool_history(selected_nid, frequency="by_hour", limit=168)
        if hist:
            hdf = pd.DataFrame(hist)
            fig = px.line(
                hdf,
                x="timestamp",
                y="price_tao",
                labels={"timestamp": "Data/Ora", "price_tao": "Prezzo Alpha (τ)"},
                template="plotly_dark",
            )
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nessuno storico orario restituito per questa subnet.")
    except Exception as exc:
        st.warning(f"Storico momentaneamente in rate-limit o non disponibile: {exc}")

with col_slip:
    st.subheader("💧 Stress Test Liquidità d'Uscita (AMM)")
    ladder = stress_test_exit_ladder(pool["tao_in_pool"], pool["alpha_in_pool"])
    if ladder:
        ldf = pd.DataFrame(
            [
                {
                    "Taglia Uscita": f"{r['target_nominal_tao']:,.0f} τ",
                    "Alpha Venduti": round(r["alpha_sold"], 1),
                    "TAO Incassati": round(r["realized_tao"], 2),
                    "Price Impact %": f"-{r['price_impact_pct']:.2f}%",
                }
                for r in ladder
            ]
        )
        st.dataframe(ldf, use_container_width=True, hide_index=True)

st.divider()

# --- CONTROLLO SALUTE ON-CHAIN + GITHUB (ON DEMAND) ---
st.subheader("🩺 Controllo Salute On-Chain, Whale & Sviluppo GitHub")
health_key = f"health_{selected_nid}"

if st.button("🔍 Verifica Salute On-Chain, Top-5 Whale & Commit GitHub", key=f"btn_h_{selected_nid}"):
    with st.spinner("Interrogazione Taostats e GitHub in corso..."):
        client = TaostatsClient()
        dereg_map = client.get_deregistration_ranking()
        coldkey_dist = client.get_coldkey_distribution(selected_nid)
        top5 = compute_top5_concentration_pct(coldkey_dist)
        gh = GitHubClient().get_repo_health(pool.get("github_url", ""))
        health = evaluate_subnet_health(
            pool=pool,
            dereg_info=dereg_map.get(selected_nid),
            top5_pct=top5 if top5 > 0 else None,
            commits_30d=gh.get("commits_30d"),
        )
        st.session_state[health_key] = {"health": health, "top5": top5, "gh": gh}

saved_h = st.session_state.get(health_key)
if saved_h:
    h = saved_h["health"]
    gh = saved_h["gh"]
    c_a, c_b, c_c, c_d = st.columns(4)
    c_a.metric("Stato Salute", h["badge"], f"Score: {h['score']}/100")
    c_b.metric("Concentrazione Top-5", f"{saved_h['top5']:.1f}%" if saved_h["top5"] > 0 else "N/D")
    c_c.metric("Commit GitHub (30gg)", gh.get("commits_30d") if gh.get("commits_30d") is not None else "N/D")
    c_d.metric("Ultimo Push / Stelle", f"{gh.get('last_push') or 'N/D'} (⭐ {gh.get('stars') or 0})")

    col_pos, col_neg = st.columns(2)
    with col_pos:
        for p_txt in h["positives"]:
            st.success(f"✅ {p_txt}")
    with col_neg:
        for f_txt in h["flags"]:
            st.error(f"⚠️ {f_txt}")
else:
    st.caption("Premi il pulsante qui sopra quando vuoi eseguire l'ispezione approfondita di wallet whale e GitHub.")

st.divider()

# --- DOSSIER LIVE GEMINI 4 HYDROGEN + WEB SEARCH ---
st.subheader("🤖 Dossier Live Gemini 4 Hydrogen + Ricerca Web")
dossier_key = f"dossier_{selected_nid}"

if st.button("🚀 Genera / Aggiorna Dossier Web Live con Gemini", type="primary"):
    analyst = GeminiAnalyst()
    if not analyst.is_ready():
        st.error("GEMINI_API_KEY non trovata o non valida nel file .env.")
    else:
        with st.spinner(f"Gemini 4 Hydrogen sta cercando notizie recenti su SN{selected_nid} ({pool['name']})..."):
            h_data = saved_h["health"] if saved_h else evaluate_subnet_health(pool)
            gh_data = saved_h["gh"] if saved_h else {}
            report_md, sources = analyst.analyze_subnet_live(
                subnet_data=pool,
                health_info=h_data,
                github_info=gh_data,
                use_deep_model=True,
            )
            st.session_state[dossier_key] = {"report": report_md, "sources": sources}

saved_dossier = st.session_state.get(dossier_key)
if saved_dossier:
    st.markdown(saved_dossier["report"])
    if saved_dossier["sources"]:
        with st.expander(f"🔗 Fonti Web Consultate ({len(saved_dossier['sources'])})"):
            for s in saved_dossier["sources"]:
                st.markdown(f"- [{s['title']}]({s['url']})")