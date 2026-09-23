"""PDF report for an estimation (reportlab)."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import PropertyDoc

APP_NAME = "Achètes ma maison"
LOGO_PATH = Path(__file__).parent / "data" / "logo.png"
BRAND = colors.HexColor("#1656C9")
BRAND_SOFT = colors.HexColor("#E8F0FD")
INK = colors.HexColor("#0F1F3D")
MUTED = colors.HexColor("#6B7C99")
LINE = colors.HexColor("#DCE5F2")

CONDITION_LABELS = {"a_renover": "À rénover", "travaux": "Travaux à prévoir", "correct": "État correct",
                    "bon": "Bon état", "neuf_renove": "Neuf / rénové"}
LEVEL_LABELS = {"eleve": "Confiance élevée", "moyen": "Confiance moyenne", "faible": "Confiance faible"}
AGREEMENT = {"convergent": "Les deux approches convergent", "ecart_modere": "Écart modéré entre les approches",
             "divergent": "Écart important entre les approches"}


def eur(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", "\u202f") + "\u202f€"


def pct(p: float, digits: int = 1) -> str:
    s = f"{p * 100:+.{digits}f}".replace(".", ",")
    return f"{s}\u202f%"


def build_report(prop: PropertyDoc, final: Optional[dict] = None, photos: Optional[list[tuple[bytes, bool]]] = None,
                 risks: Optional[dict] = None) -> bytes:
    est = prop.estimation
    assert est is not None
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"{APP_NAME} — {prop.address_label}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=BRAND,
                        alignment=TA_LEFT, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=INK,
                        spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=MUTED)
    big = ParagraphStyle("big", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=BRAND)

    story = []
    story.append(brand_header(f"{APP_NAME} · Rapport d'estimation", h1,
                              f"Édité le {datetime.now().strftime('%d/%m/%Y')} · Méthode : comparables DVF"
                              + (" + modèle hédonique" if est.hedonic else ""), small))
    story.append(Spacer(1, 8))

    ptype = "Maison" if prop.property_type == "maison" else "Appartement"
    desc = f"{ptype} · {prop.surface:g} m² · {prop.rooms} pièces · {prop.bedrooms} chambre(s) · {CONDITION_LABELS.get(prop.condition, prop.condition)}"
    if prop.year_built:
        desc += f" · construit en {prop.year_built}"
    if prop.property_type == "maison" and prop.land_surface:
        desc += f" · terrain {prop.land_surface:g} m²"
    story.append(Paragraph(f"<b>{prop.address_label}</b>", body))
    story.append(Paragraph(desc, body))
    story.append(Spacer(1, 10))

    # Headline
    head = Table([
        [Paragraph("Fourchette estimée", small), Paragraph("Valeur centrale", small), Paragraph("Prix / m²", small), Paragraph("Confiance", small)],
        [Paragraph(f"{eur(est.low)} – {eur(est.high)}", big), Paragraph(eur(est.value), ParagraphStyle("m", parent=body, fontName="Helvetica-Bold", fontSize=14, leading=18)),
         Paragraph(f"{eur(est.price_m2)}/m²", ParagraphStyle("m2", parent=body, fontName="Helvetica-Bold", fontSize=14, leading=18)),
         Paragraph(f"{LEVEL_LABELS[est.confidence.level]}<br/>{est.confidence.score}/100", ParagraphStyle("c", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=14))],
    ], colWidths=[70 * mm, 36 * mm, 34 * mm, 34 * mm])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_SOFT), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    story.append(head)
    if est.insufficient_data:
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Données insuffisantes</b> : très peu de ventes comparables, la fourchette a été élargie.", body))
    for n in est.notes:
        story.append(Paragraph(f"• {n}", small))

    # Confidence
    story.append(Paragraph("Niveau de confiance", h2))
    rows = [["Critère", "Score", "Détail"]] + [[d.label, f"{d.score:.0f}/{d.max_score:.0f}", d.hint] for d in est.confidence.details]
    story.append(_table(rows, [55 * mm, 22 * mm, 97 * mm], body))
    story.append(Paragraph(f"Périmètre retenu : {est.confidence.radius_label} · {est.confidence.n_comparables} ventes retenues · "
                           f"dispersion ±{est.confidence.dispersion_pct:g} % · âge médian {est.confidence.median_age_months} mois", small))

    # Calculation
    story.append(Paragraph("Calcul de la valeur (comparables)", h2))
    rows = [["Étape", "Montant"],
            ["Prix/m² médian pondéré des comparables", f"{eur(est.base_price_m2)}/m²"],
            [f"× surface {prop.surface:g} m²", eur(est.base_price_m2 * prop.surface)]]
    for a in est.adjustments:
        rows.append([a.label, "—" if a.amount == 0 else f"{pct(a.pct)} ({eur(a.amount)})"])
    rows.append(["Valeur centrale", eur(est.value)])
    story.append(_table(rows, [124 * mm, 50 * mm], body, bold_last=True))

    # Market
    story.append(Paragraph("Marché local (3 dernières années)", h2))
    rows = [["Périmètre", "Ventes", "Prix/m² médian"]] + [
        [m.label, str(m.count), f"{eur(m.median_pm2)}/m²" if m.median_pm2 else "—"] for m in est.market]
    story.append(_table(rows, [80 * mm, 40 * mm, 54 * mm], body))

    # Blended final value
    if final and len([c for c in final["components"] if c["effective_weight"] > 0]) > 1:
        story.append(Paragraph("Estimation finale pondérée", h2))
        rows = [["Signal", "Valeur", "Poids"]] + [
            [c["label"], eur(c["value"]) if c["value"] else "—", f"{c['effective_weight'] * 100:.0f} %" if c["effective_weight"] else "—"]
            for c in final["components"]]
        rows.append(["Valeur finale", f"{eur(final['value'])}  ({eur(final['low'])} – {eur(final['high'])})", "100 %"])
        story.append(_table(rows, [70 * mm, 74 * mm, 30 * mm], body, bold_last=True))

    # Hedonic
    if est.hedonic:
        h = est.hedonic
        story.append(Paragraph("Pourquoi cette estimation ? (modèle hédonique)", h2))
        story.append(Paragraph(
            f"Modèle log(prix) entraîné sur {h.model_n:,} ventes DVF. Valeur hédonique : <b>{eur(h.value)}</b> "
            f"(plage {eur(h.low)} – {eur(h.high)}), soit {pct(h.delta_vs_comparables_pct)} vs comparables — {AGREEMENT[h.agreement]}."
            .replace(",", "\u202f"), body))
        rows = [["Facteur", "Effet", "Détail"]] + [[f.label, pct(f.pct), f.detail + ("" if f.learned else " — déclaré")] for f in h.factors]
        rows.insert(1, [h.reference_label, eur(h.reference_value), "Point de départ"])
        story.append(_table(rows, [52 * mm, 24 * mm, 98 * mm], body))

    # Comparables
    story.append(Paragraph("Meilleures ventes comparables (DVF)", h2))
    rows = [["Date", "Distance", "Commune", "Surface", "Prix", "Prix/m²"]]
    for c in est.comparables[:10]:
        rows.append([c.date[:7], f"{c.distance_m} m", c.commune, f"{c.surface:g} m²" + (f" · {c.rooms} p." if c.rooms else ""),
                     eur(c.price), f"{eur(c.price_m2)}/m²"])
    story.append(_table(rows, [20 * mm, 20 * mm, 44 * mm, 34 * mm, 28 * mm, 28 * mm], body))

    if risks:
        story.extend(risks_section(risks, h2, body, small))

    # Photos (retouched preferred), 2 per row
    if photos:
        story.append(PageBreak())
        story.append(Paragraph("Photos du bien", h2))
        cell_w = (A4[0] - 36 * mm - 6 * mm) / 2
        cells = []
        for data, retouched in photos[:8]:
            try:
                im = PILImage.open(BytesIO(data))
            except Exception:  # noqa: BLE001
                continue
            w, h = im.size
            scale = min(cell_w / w, 70 * mm / h)
            cells.append([Image(BytesIO(data), width=w * scale, height=h * scale),
                          Paragraph("Visuel retouché par IA · non contractuel" if retouched else "Photo d'origine", small)])
        grid = [[cells[i], cells[i + 1] if i + 1 < len(cells) else ""] for i in range(0, len(cells), 2)]
        if grid:
            t = Table(grid, colWidths=[cell_w + 3 * mm, cell_w + 3 * mm])
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            story.append(t)

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Estimation indicative fondée sur les Demandes de Valeurs Foncières (DVF, data.gouv.fr) et la Base Adresse Nationale. "
        "Elle ne tient pas compte des caractéristiques non renseignées. Visuel et valeurs non contractuels.", small))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Avertissement", ParagraphStyle("legal_h", parent=small, fontName="Helvetica-Bold", textColor=INK)))
    for para in LEGAL_DISCLAIMER:
        story.append(Paragraph(para, ParagraphStyle("legal", parent=small, textColor=INK, leading=11)))
    doc.build(story)
    return buf.getvalue()


LEGAL_DISCLAIMER = (
    "La présente estimation constitue un avis de valeur établi à partir des informations et éléments communiqués à la date de sa "
    "réalisation. Elle est donnée à titre indicatif et ne constitue ni une expertise immobilière au sens juridique du terme, ni une "
    "garantie du prix de vente qui pourra être effectivement obtenu.",
    "La valeur estimée est susceptible d’évoluer en fonction de l’état du bien, de son environnement, des conditions du marché "
    "immobilier et de tout élément nouveau porté à notre connaissance. Cette estimation ne saurait engager la responsabilité de son "
    "auteur en cas d’écart entre la valeur estimée et le prix de vente finalement réalisé.",
)

LEVEL_FR = {"none": "Non concerné", "low": "Faible", "medium": "Moyen", "high": "Fort", "info": "Commune"}


def risks_section(risks: dict, h2: ParagraphStyle, body: ParagraphStyle, small: ParagraphStyle) -> list:
    """« Risques & environnement » (Géorisques) : lignes de synthèse + tableau des risques présents."""
    import georisques

    out = [Paragraph("Risques & environnement (Géorisques)", h2)]
    for line in georisques.summary_lines(risks):
        out.append(Paragraph(line, body))
    present = [it for it in risks.get("items", []) if it.get("present")]
    if present:
        rows = [["Risque", "Niveau", "Statut à l'adresse", "Statut commune"]]
        for it in present:
            rows.append([it["label"], it.get("detail") or LEVEL_FR.get(it.get("level"), "—"),
                         it.get("status_address") or "—", it.get("status_commune") or "—"])
        out.append(_table(rows, [58 * mm, 34 * mm, 42 * mm, 40 * mm], body))
    fetched = risks.get("fetched_at")
    when = fetched.strftime("%d/%m/%Y") if hasattr(fetched, "strftime") else str(fetched or "")[:10]
    out.append(Paragraph(f"Source : georisques.gouv.fr (données consultées le {when}). Information indicative : l'état des risques "
                         "et pollutions (ERP) réglementaire reste à établir par le vendeur.", small))
    return out


def brand_header(title: str, h1: ParagraphStyle, subtitle: str, small: ParagraphStyle) -> Table:
    """Logo + title block shared by every PDF (report, notaire, pack)."""
    cells = [Paragraph(title, h1), Paragraph(subtitle, small)]
    if LOGO_PATH.exists():
        row = [[Image(str(LOGO_PATH), width=14 * mm, height=14 * mm), cells]]
        widths = [18 * mm, None]
    else:
        row = [[cells]]
        widths = [None]
    t = Table(row, colWidths=widths)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _table(rows, widths, style, bold_last: bool = False) -> Table:
    data = [[Paragraph(str(c), style) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    ts = [("BACKGROUND", (0, 0), (-1, 0), BRAND_SOFT), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
          ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
          ("LEFTPADDING", (0, 0), (-1, -1), 4)]
    if bold_last:
        ts.append(("BACKGROUND", (0, -1), (-1, -1), BRAND_SOFT))
    t.setStyle(TableStyle(ts))
    return t
