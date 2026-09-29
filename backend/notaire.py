"""Export notaire — synthèse PDF du dossier de vente + pièces validées fusionnées (reportlab + pypdf)."""
from __future__ import annotations

import logging
from datetime import date, datetime
from io import BytesIO
from typing import Optional

from PIL import Image as PILImage
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from models import PropertyDoc
from report import APP_NAME, BRAND, CONDITION_LABELS, INK, MUTED, _table, brand_header, eur

logger = logging.getLogger("notaire")

STATUS_LABELS = {"manquant": "Manquant", "a_verifier": "À vérifier", "valide": "Validé", "expire": "Expiré",
                 "non_applicable": "Non applicable", "erreur_ocr": "Lecture échouée"}
CATEGORY_LABELS = {"obligatoire": "Obligatoire", "copropriete": "Copropriété", "conditionnel": "Selon situation",
                   "recommande": "Recommandé"}


def _fr_date(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        return date.fromisoformat(iso[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return iso


def _styles():
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
    return {
        "h1": ParagraphStyle("h1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=BRAND, alignment=0, spaceAfter=2),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=INK, spaceBefore=10, spaceAfter=4),
        "body": body,
        "small": ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=MUTED),
        "big": ParagraphStyle("big", parent=body, fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=BRAND),
    }


def attached_documents(dossier: dict) -> list[dict]:
    """Validated (or validated-but-expired) documents, in checklist order, with their item label."""
    out = []
    for it in dossier["items"]:
        for d in it["documents"]:
            if d["validated"]:
                out.append({**d, "item_label": it["label"], "item_required": it["required"]})
    return out


def build_cover(prop: PropertyDoc, final: Optional[dict], dossier: dict, attachments: list[dict],
                target: Optional[dict]) -> bytes:
    st = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"{APP_NAME} — Dossier de vente — {prop.address_label}")
    story = [brand_header(f"{APP_NAME} · Dossier de vente — synthèse pour le notaire", st["h1"],
                          f"Édité le {datetime.now().strftime('%d/%m/%Y')} · document préparé par le vendeur avec {APP_NAME}", st["small"]),
             Spacer(1, 8)]

    ptype = "Maison" if prop.property_type == "maison" else "Appartement"
    desc = f"{ptype} · {prop.surface:g} m² · {prop.rooms} pièces · {prop.bedrooms} chambre(s) · {CONDITION_LABELS.get(prop.condition, prop.condition)}"
    if prop.year_built:
        desc += f" · construit en {prop.year_built}"
    if prop.property_type == "maison" and prop.land_surface:
        desc += f" · terrain {prop.land_surface:g} m²"
    story.append(Paragraph("Bien concerné", st["h2"]))
    story.append(Paragraph(f"<b>{prop.address_label}</b>", st["body"]))
    story.append(Paragraph(desc, st["body"]))
    story.append(Paragraph(f"Commune : {prop.commune} ({prop.postcode}) · code INSEE {prop.code_commune}", st["small"]))

    est = prop.estimation
    if est:
        story.append(Paragraph(f"Estimation {APP_NAME}", st["h2"]))
        rows = [["Indicateur", "Valeur"],
                ["Fourchette ventes comparables", f"{eur(est.low)} – {eur(est.high)}"],
                ["Valeur centrale comparables", eur(est.value)],
                ["Ventes comparables", f"{est.confidence.n_comparables} ventes · {est.confidence.radius_label}"]]
        if final and len([c for c in final["components"] if c["effective_weight"] > 0]) > 1:
            rows.append(["Estimation finale pondérée", f"{eur(final['value'])}  ({eur(final['low'])} – {eur(final['high'])})"])
        if target:
            rows.append(["Prix cible du vendeur", f"{eur(target['target_price'])} — {target['label']}"])
        story.append(_table(rows, [80 * mm, 94 * mm], st["body"]))
        story.append(Paragraph("Estimation indicative fondée sur les ventes réelles enregistrées ; le rapport d'estimation détaillé est disponible séparément.", st["small"]))

    prog = dossier["progress"]
    story.append(Paragraph("État du dossier de diagnostic technique et pièces", st["h2"]))
    story.append(Paragraph(f"<b>{prog['done']}/{prog['total_required']}</b> documents obligatoires validés par le vendeur.", st["body"]))
    rows = [["Pièce", "Catégorie", "Statut", "Date", "Validité"]]
    for it in dossier["items"]:
        docs = [d for d in it["documents"] if d["validated"]] or it["documents"]
        best = docs[0] if docs else None
        fields = (best or {}).get("validated_fields") or (best or {}).get("ocr") or {}
        rows.append([it["label"] + (" *" if it["required"] else ""), CATEGORY_LABELS.get(it["category"], it["category"]),
                     STATUS_LABELS.get(it["status"], it["status"]), _fr_date(fields.get("document_date")),
                     _fr_date((best or {}).get("expiry_date")) if best else "—"])
    story.append(_table(rows, [66 * mm, 28 * mm, 26 * mm, 26 * mm, 28 * mm], st["body"]))
    story.append(Paragraph("* pièce obligatoire selon la situation déclarée du bien. Les statuts « manquant » et « à vérifier » signalent les pièces restant à fournir ou à contrôler.", st["small"]))

    if dossier.get("risks"):
        from report import risks_section

        story.extend(risks_section(dossier["risks"], st["h2"], st["body"], st["small"]))

    story.append(Paragraph("Pièces jointes à ce dossier", st["h2"]))
    if not attachments:
        story.append(Paragraph("Aucun document validé pour le moment : seules les pièces validées par le vendeur sont jointes.", st["body"]))
    else:
        rows = [["N°", "Pièce", "Document", "Émetteur", "Date", "Validité"]]
        for i, a in enumerate(attachments, 1):
            f = a.get("validated_fields") or a.get("ocr") or {}
            exp = _fr_date(a.get("expiry_date"))
            if a["status"] == "expire":
                exp += " (expiré)"
            rows.append([str(i), a["item_label"], f.get("title") or a["filename"], f.get("issuer") or "—",
                         _fr_date(f.get("document_date")), exp])
        story.append(_table(rows, [10 * mm, 46 * mm, 50 * mm, 36 * mm, 16 * mm, 16 * mm], st["body"]))
        story.append(Paragraph("Les pièces suivent dans l'ordre ci-dessus. Les informations extraites ont été lues par IA puis vérifiées et validées par le vendeur ; elles n'ont pas de valeur juridique propre : seuls les documents originaux font foi.", st["small"]))
    doc.build(story)
    return buf.getvalue()


def _image_page(a: dict, index: int, data: bytes) -> bytes:
    st = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    img = PILImage.open(BytesIO(data))
    w, h = img.size
    max_w, max_h = A4[0] - 28 * mm, A4[1] - 50 * mm
    scale = min(max_w / w, max_h / h)
    f = a.get("validated_fields") or a.get("ocr") or {}
    story = [Paragraph(f"Pièce n°{index} — {a['item_label']}", st["h2"]),
             Paragraph(f"{f.get('title') or a['filename']} · {_fr_date(f.get('document_date'))}", st["small"]),
             Spacer(1, 4), Image(BytesIO(data), width=w * scale, height=h * scale)]
    doc.build(story)
    return buf.getvalue()


def _note_page(text: str) -> bytes:
    st = _styles()
    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=A4).build([Paragraph(text, st["body"])])
    return buf.getvalue()


def build_notaire_pdf(prop: PropertyDoc, final: Optional[dict], dossier: dict, attachments: list[dict],
                      files: list[Optional[tuple[bytes, str]]], target: Optional[dict]) -> bytes:
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(build_cover(prop, final, dossier, attachments, target))))
    for i, (a, blob) in enumerate(zip(attachments, files), 1):
        if blob is None:
            writer.append(PdfReader(BytesIO(_note_page(f"Pièce n°{i} — {a['item_label']} : fichier indisponible au moment de l'export."))))
            continue
        data, mime = blob
        try:
            if mime == "application/pdf" or data[:5] == b"%PDF-":
                writer.append(PdfReader(BytesIO(_note_page(f"<b>Pièce n°{i} — {a['item_label']}</b><br/>{(a.get('validated_fields') or a.get('ocr') or {}).get('title') or a['filename']}"))))
                writer.append(PdfReader(BytesIO(data)))
            else:
                writer.append(PdfReader(BytesIO(_image_page(a, i, data))))
        except Exception:  # noqa: BLE001
            logger.exception("Attachment %s could not be merged", a.get("id"))
            writer.append(PdfReader(BytesIO(_note_page(f"Pièce n°{i} — {a['item_label']} : fichier illisible, à transmettre séparément."))))
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
