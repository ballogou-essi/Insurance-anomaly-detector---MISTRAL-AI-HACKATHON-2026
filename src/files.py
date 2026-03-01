import os
import io
import csv
import json
import tempfile
from datetime import datetime
from typing import Dict, Any

from werkzeug.utils import secure_filename
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


DATA_INPUTS_DIR = os.path.join("data", "inputs")
DATA_EXPORTS_DIR = os.path.join("data", "exports")


def allowed_extension(ext: str) -> bool:
    return ext in {".pdf", ".txt", ".csv", ".json"}


def save_uploaded_to_tempfile(file_storage, ext: str) -> str:
    fd, path = tempfile.mkstemp(prefix="uw_", suffix=ext)
    os.close(fd)
    file_storage.save(path)
    return path


def read_any_file_to_text(path: str, ext: str) -> str:
    ext = (ext or "").lower()

    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    if ext == ".json":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            obj = json.load(f)
        return json.dumps(obj, ensure_ascii=False, indent=2)

    if ext == ".csv":
        # On convertit CSV -> texte lisible (en limitant la taille)
        rows = []
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                rows.append(" | ".join(cell.strip() for cell in row))
                if i > 200:  # limite
                    rows.append("... (troncature)")
                    break
        return "\n".join(rows)

    if ext == ".pdf":
        return extract_pdf_text(path)

    raise ValueError(f"Unsupported extension: {ext}")


def extract_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    parts = []
    for page in reader.pages[:20]:  # limite pages
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(txt)
    return "\n\n".join(parts).strip()


def build_profile_from_form(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Form minimal : tu peux étendre plus tard
    return {
        "full_name": (payload.get("full_name") or "").strip(),
        "age": payload.get("age"),
        "product": (payload.get("product") or "").strip(),
        "occupation": (payload.get("occupation") or "").strip(),
        "annual_income": payload.get("annual_income"),
        "notes": (payload.get("notes") or "").strip(),
    }


def export_result_to_pdf(result: Dict[str, Any], filename_hint: str = "analysis") -> str:
    if not os.path.isdir(DATA_EXPORTS_DIR):
        raise RuntimeError(f"Dossier exports manquant : {DATA_EXPORTS_DIR} (crée-le à la main)")

    safe_hint = secure_filename(filename_hint) or "analysis"
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_name = f"{safe_hint}_{ts}.pdf"
    out_path = os.path.join(DATA_EXPORTS_DIR, out_name)

    status = result.get("status", "REVIEW")
    risk_score = result.get("risk_score", 50)
    top_alerts = result.get("top_alerts", [])
    action = result.get("recommended_action", "Review")
    summary = result.get("summary_explanation", "")

    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Rapport d'analyse – Détection d'anomalies")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Mention: Analyse assistée par IA (pas une validation humaine finale).")
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Statut: {status}")
    y -= 18
    c.drawString(50, y, f"Score de risque: {risk_score}/100")
    y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Alertes principales :")
    y -= 16

    c.setFont("Helvetica", 11)
    if isinstance(top_alerts, list) and top_alerts:
        for a in top_alerts[:7]:
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 11)
            c.drawString(60, y, f"- {str(a)[:140]}")
            y -= 14
    else:
        c.drawString(60, y, "- (Aucune)")
        y -= 14

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Action recommandée: {action}")
    y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Résumé :")
    y -= 16
    c.setFont("Helvetica", 11)

    # Simple wrapping
    for line in wrap_text(summary, max_len=95):
        if y < 80:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)
        c.drawString(50, y, line)
        y -= 14

    c.showPage()
    c.save()
    return out_path


def wrap_text(text: str, max_len: int = 90):
    text = (text or "").strip()
    if not text:
        return ["(vide)"]
    words = text.split()
    lines = []
    cur = []
    cur_len = 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur_len + add > max_len:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += add
    if cur:
        lines.append(" ".join(cur))
    return lines