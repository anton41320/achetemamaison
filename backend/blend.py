"""Blended final estimate + market timing signal."""
from __future__ import annotations

from datetime import timedelta, timezone
from typing import Optional

from models import Estimation, MarketEstimate, Weights


def market_estimate(est: Estimation, surface: float) -> Optional[MarketEstimate]:
    """Market signal: best available median price/m² (500 m → quartier → commune) × surface, with declared adjustments."""
    level = next((m for m in est.market if m.median_pm2 and m.count >= 5), None)
    if not level:
        return None
    pct_total = sum(a.pct for a in est.adjustments if a.key != "land")
    land = next((a.amount for a in est.adjustments if a.key == "land"), 0.0)
    value = level.median_pm2 * surface * (1 + pct_total) + land
    return MarketEstimate(
        value=float(int(round(value / 1000)) * 1000), low=float(int(round(value * 0.85 / 1000)) * 1000),
        high=float(int(round(value * 1.15 / 1000)) * 1000), price_m2=float(int(round(value / surface / 10)) * 10),
        label=f"Prix/m² médian {level.label.lower()}", count=level.count,
    )


def blend(est: Estimation, weights: Weights) -> dict:
    comps = [
        {"key": "comparables", "label": "Comparables DVF", "value": est.value, "low": est.low, "high": est.high,
         "weight": weights.comparables, "available": True},
        {"key": "hedonic", "label": "Modèle hédonique", "value": est.hedonic.value if est.hedonic else None,
         "low": est.hedonic.low if est.hedonic else None, "high": est.hedonic.high if est.hedonic else None,
         "weight": weights.hedonic, "available": est.hedonic is not None},
        {"key": "market", "label": est.market_estimate.label if est.market_estimate else "Marché local",
         "value": est.market_estimate.value if est.market_estimate else None,
         "low": est.market_estimate.low if est.market_estimate else None,
         "high": est.market_estimate.high if est.market_estimate else None,
         "weight": weights.market, "available": est.market_estimate is not None},
        {"key": "ml", "label": "Machine learning (LightGBM)", "value": est.ml.value if est.ml else None,
         "low": est.ml.low if est.ml else None, "high": est.ml.high if est.ml else None,
         "weight": weights.ml, "available": bool(est.ml and est.ml.promoted)},
    ]
    active = [c for c in comps if c["available"] and c["weight"] > 0]
    total = sum(c["weight"] for c in active) or 1.0
    if not active:
        active = [comps[0]]
        total = 1.0
    value = sum(c["value"] * c["weight"] for c in active) / total
    low = sum(c["low"] * c["weight"] for c in active) / total
    high = sum(c["high"] * c["weight"] for c in active) / total
    for c in comps:
        c["effective_weight"] = round(c["weight"] / total, 3) if c in active else 0.0
    return {
        "value": float(int(round(value / 1000)) * 1000), "low": float(int(round(low / 1000)) * 1000),
        "high": float(int(round(high / 1000)) * 1000), "components": comps, "weights": weights.model_dump(),
    }


async def market_signal(db, *, lat: float, lon: float, code_commune: str, commune: str, ptype: str) -> dict:
    """"Bon moment pour vendre ?" — trend, volume and liquidity, measured at the last available DVF date."""
    last = await db.dvf_sales.find_one({}, {"date": 1}, sort=[("date", -1)])
    if not last:
        return {"available": False}
    asof = last["date"] if last["date"].tzinfo else last["date"].replace(tzinfo=timezone.utc)
    proj = {"date": 1, "price_m2": 1}
    since = asof - timedelta(days=365 * 3)
    scope_label = f"Rayon 1,5 km"
    rows = await db.dvf_sales.find({"type": ptype, "date": {"$gte": since}, "location": {
        "$geoWithin": {"$centerSphere": [[lon, lat], 1500 / 6371000.0]}}}, proj).to_list(20000)
    if len(rows) < 30:
        rows = await db.dvf_sales.find({"type": ptype, "code_commune": code_commune, "date": {"$gte": since}}, proj).to_list(20000)
        scope_label = f"Commune de {commune}"

    def window(start_days_ago: int, end_days_ago: int) -> list[dict]:
        a, b = asof - timedelta(days=start_days_ago), asof - timedelta(days=end_days_ago)
        return [r for r in rows if a < (r["date"] if r["date"].tzinfo else r["date"].replace(tzinfo=timezone.utc)) <= b]

    def median(vals: list[float]) -> Optional[float]:
        if not vals:
            return None
        s = sorted(vals)
        return s[len(s) // 2]

    recent, previous = window(365, 0), window(730, 365)
    older = window(1095, 730)
    med_recent, med_prev = median([r["price_m2"] for r in recent]), median([r["price_m2"] for r in previous])
    trend = (med_recent - med_prev) / med_prev if med_recent and med_prev else None
    prev_avg = (len(previous) + len(older)) / 2 if (previous or older) else None
    volume_ratio = len(recent) / prev_avg if prev_avg else None
    dates = sorted((r["date"] if r["date"].tzinfo else r["date"].replace(tzinfo=timezone.utc)) for r in rows)
    days_since_last = (asof - dates[-1]).days if dates else None

    def clamp(x, lo, hi):
        return max(lo, min(hi, x))

    trend_score = clamp(0.5 + (trend / 0.10) * 0.5, 0, 1) * 40 if trend is not None else 20
    volume_score = clamp(volume_ratio / 1.5, 0, 1) * 30 if volume_ratio is not None else 15
    liq_score = 30 if days_since_last is not None and days_since_last <= 30 else 20 if days_since_last is not None and days_since_last <= 90 else 10 if days_since_last is not None and days_since_last <= 180 else 0
    score = int(round(trend_score + volume_score + liq_score))
    verdict = "favorable" if score >= 60 else "neutre" if score >= 40 else "attentiste"

    def fmt_pct(p: float) -> str:
        return f"{p * 100:+.0f}\u202f%"

    reasons = []
    if trend is not None:
        reasons.append({"key": "trend", "label": "Tendance des prix",
                        "text": f"Prix/m² médian {fmt_pct(trend)} sur 12 mois ({len(recent)} ventes vs {len(previous)})",
                        "score": round(trend_score), "max_score": 40})
    else:
        reasons.append({"key": "trend", "label": "Tendance des prix", "text": "Trop peu de ventes pour mesurer une tendance",
                        "score": 20, "max_score": 40})
    if volume_ratio is not None:
        reasons.append({"key": "volume", "label": "Volume de ventes",
                        "text": f"{len(recent)} ventes sur 12 mois, soit {volume_ratio:.1f}× la moyenne des deux années précédentes".replace(".", ","),
                        "score": round(volume_score), "max_score": 30})
    else:
        reasons.append({"key": "volume", "label": "Volume de ventes", "text": "Historique insuffisant", "score": 15, "max_score": 30})
    reasons.append({"key": "liquidity", "label": "Liquidité",
                    "text": f"Dernière vente comparable il y a {days_since_last} jours" if days_since_last is not None else "Aucune vente comparable récente",
                    "score": liq_score, "max_score": 30})
    return {
        "available": True, "score": score, "verdict": verdict, "scope": scope_label,
        "as_of": asof.date().isoformat(), "trend_pct": round(trend, 4) if trend is not None else None,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "days_since_last": days_since_last, "recent_count": len(recent), "reasons": reasons,
    }
