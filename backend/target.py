"""Prix cible — positionnement du prix souhaité par le vendeur dans la fourchette finale et le marché."""
from __future__ import annotations

from typing import Optional

from models import Estimation

NEGOTIATION_PCT = 0.05  # marge de négociation usuelle observée en France (≈ 3 à 7 %)

ZONES = {
    "sous_fourchette": ("Sous la fourchette",
                        "Ce prix est inférieur à la borne basse estimée : vous laissez probablement de la valeur. "
                        "Pertinent uniquement pour une vente très rapide."),
    "bas": ("Bas de fourchette",
            "Prix attractif : délai de vente court attendu et marge de négociation faible à prévoir."),
    "central": ("Au prix du marché",
                "Cohérent avec la valeur centrale estimée : bon équilibre entre délai de vente et prix obtenu."),
    "haut": ("Haut de fourchette",
             "Ambitieux mais défendable si le bien est très bien présenté (photos, dossier complet). "
             "Prévoyez une marge de négociation."),
    "au_dessus": ("Au-dessus de la fourchette",
                  "Risque élevé de décrochage : peu de visites, délai allongé et baisse de prix ultérieure, "
                  "souvent perçue négativement par les acquéreurs."),
}


def _eur(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", "\u202f") + "\u202f€"


def analyze_target(target: float, surface: float, est: Estimation, final: dict, signal: Optional[dict]) -> dict:
    low, high, value = final["low"], final["high"], final["value"]
    span = max(high - low, 1.0)
    position = (target - low) / span
    delta_pct = (target - value) / value
    if target < low:
        zone = "sous_fourchette"
    elif target > high:
        zone = "au_dessus"
    elif delta_pct < -0.03:
        zone = "bas"
    elif delta_pct > 0.03:
        zone = "haut"
    else:
        zone = "central"
    label, advice = ZONES[zone]

    tips: list[str] = []
    verdict = (signal or {}).get("verdict")
    if verdict == "favorable" and zone in ("haut", "au_dessus"):
        tips.append("Marché local porteur : un prix ambitieux a davantage de chances d'être absorbé.")
    elif verdict == "attentiste" and zone in ("central", "haut", "au_dessus"):
        tips.append("Marché local attentiste : les acquéreurs négocient davantage, un prix au-dessus de la valeur "
                    "centrale ralentit la vente.")
    elif verdict == "attentiste" and zone in ("bas", "sous_fourchette"):
        tips.append("Marché local attentiste : un prix attractif est un vrai atout pour vendre dans les délais.")

    level = next((m for m in est.market if m.median_pm2 and m.count >= 5), None)
    target_pm2 = target / surface
    vs_market_pm2 = (target_pm2 - level.median_pm2) / level.median_pm2 if level else None
    if vs_market_pm2 is not None:
        sign = "au-dessus" if vs_market_pm2 > 0 else "en dessous"
        tips.append(f"Soit {_eur(target_pm2)}/m², {abs(vs_market_pm2) * 100:.0f} % {sign} du prix/m² médian "
                    f"({level.label.lower()}, {level.count} ventes).".replace(" 0 % au-dessus", " au niveau"))

    net = float(int(round(target * (1 - NEGOTIATION_PCT) / 1000)) * 1000)
    tips.append(f"Après une négociation usuelle (~{NEGOTIATION_PCT * 100:.0f} %), le prix net vendeur serait "
                f"d'environ {_eur(net)}" + (" — sous la borne basse estimée." if net < low else "."))
    if zone == "au_dessus":
        tips.append(f"Pour revenir dans la fourchette, il faudrait baisser d'au moins {_eur(target - high)}.")
    elif zone == "sous_fourchette":
        tips.append(f"La borne basse estimée est {_eur(low - target)} plus haute que votre prix.")

    return {
        "target_price": target, "target_price_m2": round(target_pm2 / 10) * 10,
        "low": low, "high": high, "value": value,
        "position": round(position, 3), "delta_pct": round(delta_pct, 4),
        "zone": zone, "label": label, "advice": advice,
        "net_after_negotiation": net, "negotiation_pct": NEGOTIATION_PCT,
        "vs_market_pm2_pct": round(vs_market_pm2, 4) if vs_market_pm2 is not None else None,
        "market_verdict": verdict, "tips": tips,
    }
