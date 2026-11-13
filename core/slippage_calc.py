from __future__ import annotations

from typing import Dict, List


def simulate_alpha_sell_to_tao(
    alpha_amount: float,
    tao_in_pool: float,
    alpha_in_pool: float,
    swap_fee_pct: float = 0.05,
) -> Dict[str, float]:
    """
    Simula la vendita di `alpha_amount` token Alpha dentro la pool AMM dTAO.
    Formula constant-product: (tao_in - delta_tao) * (alpha_in + alpha_eff) = tao_in * alpha_in
    """
    if alpha_amount <= 0 or tao_in_pool <= 0 or alpha_in_pool <= 0:
        return {
            "alpha_sold": alpha_amount,
            "spot_price_tao": 0.0,
            "nominal_value_tao": 0.0,
            "realized_tao": 0.0,
            "effective_price_tao": 0.0,
            "price_impact_pct": 0.0,
            "fee_tao": 0.0,
        }

    spot_price = tao_in_pool / alpha_in_pool
    nominal_tao = alpha_amount * spot_price

    # Applica swap fee di protocollo (~0.05%)
    fee_factor = max(0.0, 1.0 - (swap_fee_pct / 100.0))
    alpha_effective = alpha_amount * fee_factor

    new_alpha_pool = alpha_in_pool + alpha_effective
    new_tao_pool = (tao_in_pool * alpha_in_pool) / new_alpha_pool
    realized_tao = max(0.0, tao_in_pool - new_tao_pool)

    effective_price = realized_tao / alpha_amount
    price_impact_pct = ((spot_price - effective_price) / spot_price) * 100.0 if spot_price > 0 else 0.0

    return {
        "alpha_sold": alpha_amount,
        "spot_price_tao": spot_price,
        "nominal_value_tao": nominal_tao,
        "realized_tao": realized_tao,
        "effective_price_tao": effective_price,
        "price_impact_pct": max(0.0, price_impact_pct),
        "fee_tao": nominal_tao * (swap_fee_pct / 100.0),
    }


def stress_test_exit_ladder(
    tao_in_pool: float,
    alpha_in_pool: float,
    tao_sizes: List[float] | None = None,
) -> List[Dict[str, float]]:
    """Genera una scaletta di stress-test per taglie da 10, 50, 100, 500, 1000 TAO."""
    sizes = tao_sizes or [10.0, 50.0, 100.0, 500.0, 1000.0]
    if tao_in_pool <= 0 or alpha_in_pool <= 0:
        return []

    spot_price = tao_in_pool / alpha_in_pool
    rows: List[Dict[str, float]] = []
    for target_tao in sizes:
        alpha_needed = target_tao / spot_price
        sim = simulate_alpha_sell_to_tao(alpha_needed, tao_in_pool, alpha_in_pool)
        sim["target_nominal_tao"] = target_tao
        rows.append(sim)
    return rows