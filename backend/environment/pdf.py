"""Section « Environnement du bien » du rapport PDF : synthèse IA étiquetée, faits mesurés sourcés, sources datées."""
from __future__ import annotations

import html
from datetime import datetime

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer

SOURCE_SHORT = {"bdtopo": "IGN BD TOPO", "osm": "OpenStreetMap", "cadastre": "Cadastre", "gpu": "GPU", "georisques": "Géorisques", "clc": "CLC 2018", "alti": "RGE ALTI", "ban": "BAN"}
LEVEL = {"none": "nul", "low": "faible", "medium": "moyen", "high": "fort", "info": "recensé"}
SECTIONS_PDF = ["resume", "immediat", "voisinage", "nature", "mobilite", "services", "nuisances", "terrain", "risques", "urbanisme", "evolution"]


def _d(m) -> str:
    return "—" if m is None else (f"{m / 1000:.1f} km".replace(".", ",") if m >= 1000 else f"{int(m)} m")


def _e(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _fmt_date(v) -> str:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:  # noqa: BLE001
        return str(v)[:10]


def _items_rows(items: list[dict], label_fn, limit: int) -> list[list[str]]:
    rows = []
    for it in items[:limit]:
        rows.append([_e(label_fn(it)), _d(it.get("distance_m")), _e(it.get("direction") or ""), SOURCE_SHORT.get(it.get("source"), _e(it.get("source")))])
    return rows


def environment_section(env_doc: dict, h2: ParagraphStyle, body: ParagraphStyle, small: ParagraphStyle, table_fn) -> list:
    """env_doc = document `env_analyses` ({analysis, report, created_at})."""
    a = env_doc.get("analysis") or {}
    rep = env_doc.get("report") or {}
    sections = rep.get("sections") or {}
    titles = rep.get("titles") or {}
    h3 = ParagraphStyle("env_h3", parent=body, fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=7, spaceAfter=2)
    ai = ParagraphStyle("env_ai", parent=body, leftIndent=6, borderPadding=(2, 4, 2, 4), textColor=body.textColor)
    tag = ParagraphStyle("env_tag", parent=small, fontName="Helvetica-Bold", textColor=small.textColor)
    out: list = [PageBreak(), Paragraph("Environnement du bien", h2)]
    out.append(Paragraph(
        f"Analyse générée le {_fmt_date(a.get('generated_at') or env_doc.get('created_at'))} à partir de données publiques (BAN, Cadastre, IGN BD TOPO, RGE ALTI, "
        f"Corine Land Cover, Géoportail de l'Urbanisme, Géorisques) complétées par OpenStreetMap. Distances à vol d'oiseau mesurées par l'application. "
        "Les paragraphes « Synthèse IA » sont des interprétations, jamais des mesures.", small))

    if a.get("parcel") or a.get("building"):
        p, b = a.get("parcel") or {}, a.get("building") or {}
        rows = [["Élément", "Valeur", "Source"]]
        if p:
            rows.append([f"Parcelle {p.get('section')} {p.get('numero')}", f"{p.get('contenance_m2') or '—'} m²", "Cadastre"])
        if b:
            rows.append(["Bâtiment", f"emprise {b.get('footprint_m2') or '—'} m²" + (f" · {b.get('nombre_d_etages')} niveau(x)" if b.get("nombre_d_etages") else "") + (f" · {b.get('usage_1')}" if b.get("usage_1") else ""), "IGN BD TOPO"])
        d = a.get("density") or {}
        rows.append(["Densité bâtie (250 m)", f"{d.get('built_ratio_pct', '—')} % · {d.get('buildings', '—')} bâtiments · plus proche à {_d(d.get('nearest_m'))}", "calculé"])
        t = a.get("terrain") or {}
        rows.append(["Relief", (f"altitude {t.get('altitude_m')} m" if t.get("altitude_m") is not None else "altitude non disponible") +
                     (f" · pente {str(t.get('slope_pct')).replace('.', ',')} % ({t.get('aspect')})" if t.get("slope_pct") is not None else ""), "RGE ALTI · calculé"])
        if t.get("landcover"):
            rows.append(["Occupation du sol", f"{t['landcover'].get('label')} (1/100 000, contexte paysager)", "CLC 2018"])
        out.append(table_fn([[_e(c) for c in r] for r in rows], [42 * mm, 100 * mm, 32 * mm], body))

    facts = {
        "nature": _items_rows((a.get("green_spaces") or [])[:5] + (a.get("water") or [])[:3], lambda i: i.get("nature") or i.get("name") or i.get("type") or "Élément", 8),
        "mobilite": _items_rows((a.get("roads") or [])[:5] + (a.get("railways") or [])[:1] + (a.get("transport") or [])[:4],
                                lambda i: (i.get("name") or i.get("nature") or i.get("type") or "Voie") + (f" ({i['importance_label']})" if i.get("importance_label") else ""), 10),
        "services": _items_rows(a.get("services") or [], lambda i: (i.get("name") or (i.get("type") or "").split("=")[-1] or "Service") + (f" · {i.get('category')}" if i.get("category") else ""), 10),
        "nuisances": _items_rows(a.get("nuisances") or [], lambda i: f"{i.get('label')} ({i.get('type')})", 8),
    }

    for key in SECTIONS_PDF:
        text = sections.get(key)
        rows = facts.get(key)
        if not text and not rows and key not in ("risques", "urbanisme", "evolution"):
            continue
        out.append(Paragraph(_e(titles.get(key, key.capitalize())), h3))
        if text:
            out.append(Paragraph("Synthèse IA — interprétation des données ci-dessous", tag))
            for para in str(text).split("\n"):
                if para.strip():
                    out.append(Paragraph(_e(para.strip()), ai))
        if rows:
            out.append(Spacer(1, 3))
            out.append(table_fn([["Élément", "Distance", "Direction", "Source"]] + rows, [94 * mm, 22 * mm, 26 * mm, 32 * mm], body))
        if key == "risques":
            r = a.get("risks")
            if r:
                lines = [f"À l'adresse : {i.get('label')} — {LEVEL.get(i.get('level'), i.get('level'))}" for i in r.get("at_address") or []] or ["Aucun risque recensé à l'adresse même."]
                lines += [f"Échelle communale : {i.get('label')}" for i in (r.get("commune_only") or [])[:6]]
                for ln in lines:
                    out.append(Paragraph("• " + _e(ln), body))
                out.append(Paragraph("Source : Géorisques (officiel). L'état des risques et pollutions réglementaire reste à établir par le vendeur.", small))
            else:
                out.append(Paragraph("Géorisques n'a pas pu être consulté : information indisponible.", body))
        if key == "urbanisme":
            u = a.get("urbanism")
            if u:
                for z in u.get("zones") or []:
                    out.append(Paragraph("• " + _e(f"Zone {z.get('libelle') or '?'}" + (f" (type {z.get('typezone')})" if z.get("typezone") else "") + (f" — {z.get('libelong')}" if z.get("libelong") else "") + (f" · règlement : {z.get('reglement')}" if z.get("reglement") else "")), body))
                for s in (u.get("servitudes") or [])[:5]:
                    out.append(Paragraph("• " + _e(f"Servitude : {s.get('libelle')}"), body))
                for s in (u.get("prescriptions") or [])[:5]:
                    out.append(Paragraph("• " + _e(f"Prescription : {s.get('libelle')}"), body))
                out.append(Paragraph(_e(u.get("notice") or "Source : Géoportail de l'Urbanisme. Vérification auprès de la collectivité recommandée."), small))
            else:
                out.append(Paragraph("Le Géoportail de l'Urbanisme n'a pas répondu : zonage indisponible.", body))
        if key == "evolution":
            unbuilt = [p for p in a.get("nearby_parcels") or [] if not p.get("built")]
            if unbuilt:
                for p in unbuilt[:6]:
                    out.append(Paragraph("• " + _e(f"Parcelle {p.get('section')} {p.get('numero')} non bâtie · {p.get('surface_m2')} m² · à {_d(p.get('distance_m'))}" + (" · mitoyenne" if p.get("adjacent") else "")), body))
            else:
                out.append(Paragraph("Aucune parcelle non bâtie identifiée dans l'emprise analysée (≈ 120 m).", body))
            out.append(Paragraph("Source : Cadastre × IGN BD TOPO (calculé). Le caractère constructible n'est pas évalué.", small))

    checks = sections.get("a_verifier") or []
    if checks:
        out.append(Paragraph("Points à vérifier", h3))
        for c in checks[:8]:
            out.append(Paragraph("• " + _e(c), body))

    # Sources
    out.append(Paragraph("Sources consultées", h3))
    seen: dict[str, dict] = {}
    for s in a.get("sources") or []:
        if s.get("id") not in seen or (seen[s["id"]].get("status") == "ok" and s.get("status") != "ok"):
            seen[s["id"]] = s
    rows = [["Source", "Type", "Licence", "Consultée le", "Statut"]]
    for s in seen.values():
        rows.append([_e(s.get("name")), "officielle" if s.get("kind") == "official" else "ouverte", _e(s.get("licence")), _fmt_date(s.get("fetched_at")),
                     {"ok": "OK", "partial": "partielle", "unavailable": "indisponible"}.get(s.get("status"), _e(s.get("status")))])
    out.append(table_fn(rows, [62 * mm, 18 * mm, 44 * mm, 24 * mm, 26 * mm], body))
    for lim in a.get("limits") or []:
        out.append(Paragraph("• " + _e(lim), small))
    if rep.get("disclaimer"):
        out.append(Paragraph(_e(rep["disclaimer"]), small))
    return out
