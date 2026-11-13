from __future__ import annotations

from typing import Optional


def fmt_usd(val: Optional[float], decimals: int = 2) -> str:
    if val is None:
        return "N/D"
    abs_v = abs(val)
    sign = "-" if val < 0 else ""
    if abs_v >= 1_000_000_000:
        return f"{sign}${abs_v / 1_000_000_000:,.2f}B"
    if abs_v >= 1_000_000:
        return f"{sign}${abs_v / 1_000_000:,.2f}M"
    if abs_v >= 1_000:
        return f"{sign}${abs_v:,.0f}"
    return f"{sign}${abs_v:,.{decimals}f}"


def fmt_eur(val: Optional[float], decimals: int = 2) -> str:
    if val is None:
        return "N/D"
    abs_v = abs(val)
    sign = "-" if val < 0 else ""
    if abs_v >= 1_000_000_000:
        return f"{sign}€{abs_v / 1_000_000_000:,.2f}B"
    if abs_v >= 1_000_000:
        return f"{sign}€{abs_v / 1_000_000:,.2f}M"
    if abs_v >= 1_000:
        return f"{sign}€{abs_v:,.0f}"
    return f"{sign}€{abs_v:,.{decimals}f}"


def fmt_tao(val: Optional[float], decimals: int = 2) -> str:
    if val is None:
        return "N/D"
    abs_v = abs(val)
    sign = "-" if val < 0 else ""
    if abs_v >= 1_000_000:
        return f"{sign}{abs_v / 1_000_000:,.2f}M τ"
    if abs_v >= 1_000:
        return f"{sign}{abs_v:,.1f}K τ" if abs_v >= 10_000 else f"{sign}{abs_v:,.0f} τ"
    return f"{sign}{abs_v:,.{decimals}f} τ"


def fmt_pct(val: Optional[float], decimals: int = 2, show_plus: bool = True) -> str:
    if val is None:
        return "N/D"
    prefix = "+" if (show_plus and val > 0) else ""
    return f"{prefix}{val:.{decimals}f}%"