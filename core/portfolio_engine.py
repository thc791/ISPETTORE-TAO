from __future__ import annotations

import json
from typing import Any, Dict, List

from config.settings import DATA_DIR
from core.slippage_calc import simulate_alpha_sell_to_tao

PORTFOLIO_FILE = DATA_DIR / "portfolio.json"


def load_portfolio() -> List[Dict[str, Any]]:
    if not PORTFOLIO_FILE.exists():
        return []
    try:
        data = json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_portfolio(positions: List[Dict[str, Any]]) -> None:
    PORTFOLIO_FILE.write_text(json.dumps(positions, indent=2, ensure_ascii=False), encoding="utf-8")


def evaluate_portfolio(
    positions: List[Dict[str, Any]],
    pools_by_netuid: Dict[int, Dict[str, Any]],
    tao_price_usd: float,
    usd_to_eur: float,
    etfs_by_ticker: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Calcola valore nominale, Mark-to-Exit e P&L in USD, EUR e TAO."""
    evaluated: List[Dict[str, Any]] = []
    tot_cost_usd = 0.0
    tot_nominal_usd = 0.0
    tot_exit_usd = 0.0
    tot_cost_tao = 0.0
    tot_exit_tao = 0.0

    for idx, pos in enumerate(positions):
        ptype = pos.get("type", "Subnet Alpha")
        qty = float(pos.get("quantity", 0.0))
        cost_usd = float(pos.get("cost_basis_usd", 0.0))
        cost_tao = float(pos.get("cost_basis_tao", 0.0))

        nominal_tao = 0.0
        exit_tao = 0.0
        impact_pct = 0.0
        nominal_usd = 0.0
        exit_usd = 0.0

        if ptype == "Subnet Alpha":
            netuid = int(pos.get("netuid", 0))
            pool = pools_by_netuid.get(netuid)
            if pool:
                sim = simulate_alpha_sell_to_tao(
                    alpha_amount=qty,
                    tao_in_pool=pool["tao_in_pool"],
                    alpha_in_pool=pool["alpha_in_pool"],
                )
                nominal_tao = sim["nominal_value_tao"]
                exit_tao = sim["realized_tao"]
                impact_pct = sim["price_impact_pct"]
                nominal_usd = nominal_tao * tao_price_usd
                exit_usd = exit_tao * tao_price_usd

        elif ptype == "TAO Spot / Root":
            nominal_tao = qty
            exit_tao = qty
            nominal_usd = qty * tao_price_usd
            exit_usd = nominal_usd

        elif ptype == "ETF / ETP":
            ticker = str(pos.get("ticker", "")).upper()
            etf = etfs_by_ticker.get(ticker)
            unit_usd = float(etf["price_usd"]) if etf and etf.get("price_usd") else 0.0
            nominal_usd = qty * unit_usd
            exit_usd = nominal_usd
            nominal_tao = (nominal_usd / tao_price_usd) if tao_price_usd > 0 else 0.0
            exit_tao = nominal_tao

        pnl_usd = exit_usd - cost_usd
        pnl_tao = exit_tao - cost_tao

        tot_cost_usd += cost_usd
        tot_nominal_usd += nominal_usd
        tot_exit_usd += exit_usd
        tot_cost_tao += cost_tao
        tot_exit_tao += exit_tao

        evaluated.append(
            {
                "id": idx,
                "type": ptype,
                "asset": pos.get("label") or pos.get("ticker") or f"SN{pos.get('netuid', 0)}",
                "quantity": qty,
                "nominal_tao": nominal_tao,
                "exit_tao": exit_tao,
                "slippage_pct": impact_pct,
                "exit_usd": exit_usd,
                "exit_eur": exit_usd * usd_to_eur,
                "cost_usd": cost_usd,
                "cost_tao": cost_tao,
                "pnl_usd": pnl_usd,
                "pnl_tao": pnl_tao,
                "pnl_usd_pct": (pnl_usd / cost_usd * 100.0) if cost_usd > 0 else 0.0,
                "pnl_tao_pct": (pnl_tao / cost_tao * 100.0) if cost_tao > 0 else 0.0,
            }
        )

    return {
        "rows": evaluated,
        "totals": {
            "cost_usd": tot_cost_usd,
            "nominal_usd": tot_nominal_usd,
            "exit_usd": tot_exit_usd,
            "exit_eur": tot_exit_usd * usd_to_eur,
            "cost_tao": tot_cost_tao,
            "exit_tao": tot_exit_tao,
            "pnl_usd": tot_exit_usd - tot_cost_usd,
            "pnl_tao": tot_exit_tao - tot_cost_tao,
        },
    }