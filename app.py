import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

from src.core import analyze_text, analyze_profile
from src.files import (
    DATA_INPUTS_DIR,
    DATA_EXPORTS_DIR,
    allowed_extension,
    save_uploaded_to_tempfile,
    read_any_file_to_text,
    build_profile_from_form,
    export_result_to_pdf,
)

load_dotenv()

app = Flask(__name__)


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/analyze/file")
def api_analyze_file():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu (field: file)."}), 400

    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "Fichier vide."}), 400

    filename = f.filename
    ext = os.path.splitext(filename)[1].lower()

    if not allowed_extension(ext):
        return jsonify({"error": f"Type non supporté: {ext}. (pdf, txt, csv, json)"}), 400

    use_mistral = request.form.get("use_mistral", "true").lower() == "true"

    tmp_path = None
    try:
        tmp_path = save_uploaded_to_tempfile(f, ext)
        raw_text = read_any_file_to_text(tmp_path, ext)

        if not raw_text or not raw_text.strip():
            return jsonify({"error": "Impossible d'extraire du contenu lisible depuis ce fichier."}), 400

        result = analyze_text(raw_text, use_mistral=use_mistral)

        # Métadonnées utiles côté UI
        result["_meta"] = {
            "input_name": filename,
            "input_type": ext.lstrip("."),
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.post("/api/analyze/form")
def api_analyze_form():
    payload = request.get_json(silent=True) or {}
    use_mistral = bool(payload.get("use_mistral", True))

    profile = build_profile_from_form(payload)
    result = analyze_profile(profile, use_mistral=use_mistral)
    result["_meta"] = {
        "input_name": "manual_form",
        "input_type": "form",
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
    }
    result["_profile"] = profile
    return jsonify(result)


@app.post("/api/export/pdf")
def api_export_pdf():
    """
    Exporte le dernier résultat (envoyé par le front) en PDF.
    Le front envoie JSON { result: {...}, filename_hint?: "..." }
    """
    payload = request.get_json(silent=True) or {}
    result = payload.get("result")
    if not isinstance(result, dict):
        return jsonify({"error": "Payload invalide. Attendu: { result: {...} }"}), 400

    filename_hint = payload.get("filename_hint", "analysis")
    pdf_path = export_result_to_pdf(result, filename_hint=filename_hint)

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=os.path.basename(pdf_path),
        mimetype="application/pdf",
    )


def _assert_required_dirs():
    # IMPORTANT: on NE crée PAS les dossiers automatiquement.
    # Tu dois créer data/inputs et data/exports à la main.
    missing = []
    if not os.path.isdir(DATA_INPUTS_DIR):
        missing.append(DATA_INPUTS_DIR)
    if not os.path.isdir(DATA_EXPORTS_DIR):
        missing.append(DATA_EXPORTS_DIR)

    if missing:
        raise RuntimeError(
            "Dossiers manquants (à créer manuellement) :\n- "
            + "\n- ".join(missing)
        )


if __name__ == "__main__":
    _assert_required_dirs()
    app.run(host="127.0.0.1", port=5000, debug=True)