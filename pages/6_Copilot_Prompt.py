from __future__ import annotations

import streamlit as st

from config.watchlists import ALL_CURATED_MAP, PROMISING_NETUIDS, PROVEN_NETUIDS
from core.portfolio_engine import load_portfolio
from services.gemini_analyst import GeminiAnalyst
from services.market_etf_client import MarketEtfClient
from services.taostats_client import TaostatsClient

st.set_page_config(page_title="Copilot Prompt", page_icon="💬", layout="wide")
st.title("💬 Finestra Prompt — Ispettore TAO Copilot (Gemini 4 Hydrogen)")
st.caption("Chiedi qualsiasi cosa: analisi comparative, macro, ETF, rischi di una subnet o sviluppi recenti dal web.")


@st.cache_data(ttl=120, show_spinner=False)
def build_terminal_context():
    c = TaostatsClient()
    m = MarketEtfClient()
    tao = c.get_tao_price()
    pools = c.get_all_subnet_pools()
    etfs = m.get_all_etfs()
    pools_by_id = {p["netuid"]: p for p in pools}

    def compact_list(nids):
        out = []
        for nid in nids:
            p = pools_by_id.get(nid)
            if not p:
                continue
            cur = ALL_CURATED_MAP.get(nid)
            out.append(
                {
                    "netuid": nid,
                    "name": p["name"],
                    "category": cur.category if cur else p["category"],
                    "alpha_price_tao": round(p["alpha_price_tao"], 5),
                    "alpha_price_usd": round(p["alpha_price_usd"], 2),
                    "mcap_usd_m": round(p["mcap_usd"] / 1_000_000, 2),
                    "tao_in_pool": round(p["tao_in_pool"], 0),
                    "emission_pct": round(p["emission_pct"], 2),
                    "gamma_enabled": p["gamma_enabled"],
                    "note": cur.revenue_note if cur else "",
                }
            )
        return out

    return {
        "tao_spot": {
            "price_usd": round(tao["price_usd"], 2),
            "mcap_usd_b": round(tao["market_cap_usd"] / 1e9, 3),
            "chg_24h_pct": round(tao["change_24h_pct"], 2),
            "chg_7d_pct": round(tao.get("change_7d_pct", 0.0), 2),
            "chg_30d_pct": round(tao.get("change_30d_pct", 0.0), 2),
        },
        "etfs": [
            {
                "ticker": e["ticker"],
                "price_native": e["price_native"],
                "currency": e["currency"],
                "price_usd": round(e["price_usd"], 2) if e["price_usd"] else None,
                "chg_1d_pct": round(e["change_1d_pct"], 2) if e["change_1d_pct"] is not None else None,
            }
            for e in etfs
        ],
        "top10_proven": compact_list(PROVEN_NETUIDS),
        "top10_promising": compact_list(PROMISING_NETUIDS),
    }


with st.sidebar:
    st.subheader("Impostazioni Copilot")
    enable_web = st.toggle("🌐 Ricerca Web Live (DDG + Google News)", value=True)
    include_portfolio = st.toggle("💼 Includi il mio portafoglio nel contesto", value=False)
    if st.button("🧹 Nuova Conversazione", use_container_width=True):
        st.session_state["copilot_messages"] = []
        st.rerun()

if "copilot_messages" not in st.session_state:
    st.session_state["copilot_messages"] = [
        {
            "role": "assistant",
            "content": (
                "Ciao! Sono **Ispettore TAO Copilot** su motore **Gemini 4 Hydrogen**. "
                "Ho già davanti i prezzi live di TAO, gli ETF/ETP, le **10 Subnet Proven** e le **10 Promettenti**. "
                "Cosa analizziamo oggi?"
            ),
            "sources": [],
        }
    ]

# --- PROMPT RAPIDI ---
st.write("**Spunti rapidi:**")
qcols = st.columns(4)
quick_prompts = [
    "Confronta le 3 migliori Proven per ricavi reali e solidità della pool",
    "Tra le 10 Promettenti quali hanno il miglior rapporto Emissioni / MCap?",
    "Cerca novità recenti sugli ETF Bittensor e GTAO SEC",
    "Quali rischi vedi oggi su SN58 Attune e SN90 KubeTEE?",
]
clicked_prompt = None
for i, qp in enumerate(quick_prompts):
    if qcols[i].button(qp, use_container_width=True):
        clicked_prompt = qp

st.divider()

# --- CRONOLOGIA CHAT ---
for msg in st.session_state["copilot_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"🔗 Fonti Web ({len(msg['sources'])})"):
                for s in msg["sources"]:
                    st.markdown(f"- [{s['title']}]({s['url']})")

# --- INPUT UTENTE ---
user_input = st.chat_input("Scrivi qui la tua domanda su TAO, ETF o qualsiasi subnet...")
prompt_to_run = clicked_prompt or user_input

if prompt_to_run:
    st.session_state["copilot_messages"].append({"role": "user", "content": prompt_to_run, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt_to_run)

    analyst = GeminiAnalyst()
    if not analyst.is_ready():
        st.error("GEMINI_API_KEY mancante nel file .env.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Gemini 4 Hydrogen sta elaborando dati live e ricerca web..."):
                ctx = build_terminal_context()
                if include_portfolio:
                    ctx["user_portfolio"] = load_portfolio()

                history_clean = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["copilot_messages"][:-1]
                ]
                reply, sources = analyst.ask_copilot(
                    user_message=prompt_to_run,
                    chat_history=history_clean,
                    terminal_context=ctx,
                    enable_web_search=enable_web,
                    use_deep_model=False,
                )
                st.markdown(reply)
                if sources:
                    with st.expander(f"🔗 Fonti Web ({len(sources)})"):
                        for s in sources:
                            st.markdown(f"- [{s['title']}]({s['url']})")

        st.session_state["copilot_messages"].append(
            {"role": "assistant", "content": reply, "sources": sources}
        )