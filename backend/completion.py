"""Profile completion of a property: share of the questionnaire actually filled in (used as a nudge)."""
from __future__ import annotations

from models import PropertyDoc

COMMON = [("year_built", "année de construction"), ("bathrooms", "salles de bain"), ("heating", "chauffage"), ("dpe", "DPE"),
          ("double_glazing", "double vitrage"), ("terrace", "terrasse"), ("garage", "garage"), ("orientation", "exposition"),
          ("air_conditioning", "climatisation"), ("fireplace", "cheminée / poêle"), ("solar_panels", "panneaux solaires")]
MAISON = [("land_surface", "surface du terrain"), ("pool", "piscine"), ("fenced", "terrain clos"), ("motorized_gate", "portail motorisé"),
          ("outbuilding", "dépendance"), ("single_storey", "plain-pied"), ("basement", "sous-sol"), ("convertible_attic", "combles"),
          ("pantry", "cellier"), ("dressing", "dressing"), ("master_suite", "suite parentale"), ("sanitation", "assainissement")]
APPARTEMENT = [("floor", "étage"), ("elevator", "ascenseur"), ("balcony", "balcon"), ("parking", "parking"), ("cellar", "cave"),
               ("caretaker", "gardien"), ("condo_fees", "charges de copropriété"), ("heating_mode", "mode de chauffage"),
               ("underfloor_heating", "chauffage au sol")]


def profile_completion(prop: PropertyDoc) -> dict:
    fields = COMMON + (MAISON if prop.property_type == "maison" else APPARTEMENT)
    feats = prop.features.model_dump()
    missing = [label for key, label in fields if (getattr(prop, key, None) if key in ("year_built", "land_surface") else feats.get(key)) is None]
    total = len(fields)
    filled = total - len(missing)
    return {"pct": int(round(100 * filled / total)), "filled": filled, "total": total, "missing": missing}
