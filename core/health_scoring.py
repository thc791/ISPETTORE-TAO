from __future__ import annotations

from typing import Any, Dict, List


def compute_top5_concentration_pct(coldkey_dist: List[Dict[str, Any]]) -> float:
    """Calcola la percentuale detenuta dai Top 5 wallet dalla distribuzione coldkey."""
    if not coldkey_dist:
        return 0.0
    balances: List[float] = []
    for item in coldkey_dist:
        val = item.get("balance") or item.get("alpha") or item.get("stake") or 0
        try:
            balances.append(float(val))
        except (TypeError, ValueError):
            continue
    total = sum(balances)
    if total <= 0:
        return 0.0
    balances.sort(reverse=True)
    return (sum(balances[:5]) / total) * 100.0


def evaluate_subnet_health(
    pool: Dict[str, Any],
    dereg_info: Dict[str, Any] | None = None,
    top5_pct: float | None = None,
    commits_30d: int | None = None,
) -> Dict[str, Any]:
    """Valuta la salute strutturale della subnet su scala 0-100 con badge e red flags."""
    score = 50
    flags: List[str] = []
    positives: List[str] = []

    tao_in_pool = float(pool.get("tao_in_pool", 0.0))
    emission_pct = float(pool.get("emission_pct", 0.0))
    gamma_enabled = bool(pool.get("gamma_enabled", False))
    startup_mode = bool(pool.get("startup_mode", False))

    # 1. Profondità della Pool (Liquidità reale d'uscita)
    if tao_in_pool >= 50_000:
        score += 20
        positives.append("Pool molto profonda (>= 50K τ)")
    elif tao_in_pool >= 10_000:
        score += 12
        positives.append("Buona liquidità pool (>= 10K τ)")
    elif tao_in_pool >= 3_000:
        score += 4
    else:
        score -= 18
        flags.append(f"Pool sottile ({tao_in_pool:,.0f} τ): alto rischio slippage")

    # 2. Quota Emissioni
    if emission_pct >= 2.0:
        score += 10
        positives.append(f"Forte supporto emissioni ({emission_pct:.2f}%)")
    elif emission_pct < 0.3 and pool.get("netuid", 0) > 0:
        score -= 8
        flags.append(f"Emissioni basse ({emission_pct:.2f}%)")

    # 3. Gamma attivo
    if gamma_enabled:
        score += 5
        positives.append("Gamma / Service Credits attivi")

    if startup_mode:
        score -= 5
        flags.append("Subnet in Startup Mode")

    # 4. Rischio Deregistrazione
    if dereg_info:
        rank = int(dereg_info.get("rank", 999))
        immune = bool(dereg_info.get("is_immune", False))
        if immune:
            positives.append("Immunità attiva")
        elif rank <= 10:
            score -= 25
            flags.append(f"ALLERTA DEREGISTRAZIONE: Rank #{rank} più basso!")
        elif rank <= 25:
            score -= 10
            flags.append(f"Zona gialla pruning: Rank #{rank}")

    # 5. Concentrazione Top-5 Wallet
    if top5_pct is not None and top5_pct > 0:
        if top5_pct >= 55.0:
            score -= 15
            flags.append(f"Alta concentrazione whale: Top-5 = {top5_pct:.1f}%")
        elif top5_pct <= 35.0:
            score += 10
            positives.append(f"Distribuzione sana: Top-5 = {top5_pct:.1f}%")

    # 6. Attività GitHub
    if commits_30d is not None:
        if commits_30d >= 20:
            score += 10
            positives.append(f"Sviluppo molto attivo ({commits_30d} commit/30gg)")
        elif commits_30d == 0:
            score -= 15
            flags.append("0 commit su GitHub negli ultimi 30 giorni")

    score = max(0, min(100, score))
    if score >= 70:
        badge = "🟢 SOLIDA"
    elif score >= 45:
        badge = "🟡 MEDIA"
    else:
        badge = "🔴 RISCHIO ALTO"

    return {
        "score": score,
        "badge": badge,
        "flags": flags,
        "positives": positives,
    }