import json
import re
from typing import Any, Dict, List, Optional

from src.mistral_client import MistralClient


SYSTEM_PROMPT = """Tu es un expert en détection d’anomalies dans des dossiers de souscription d’assurance.
Tu dois analyser des informations (texte brut, extrait de PDF, JSON, CSV ou formulaire) et produire une restitution métier.

Règles strictes :
- Tu dois renvoyer un SEUL objet JSON valide, sans markdown.
- Champs obligatoires :
  - status: "OK" | "REVIEW" | "FLAGGED"
  - risk_score: entier 0..100
  - top_alerts: liste de 3 à 7 alertes courtes (strings)
  - recommended_action: string court (ex: "Approve", "Review with documents", "Reject / Escalate")
  - summary_explanation: 3 à 6 phrases claires orientées métier
- Pas de données inventées (si une info manque, le dire et augmenter la prudence).
- Si ambigu, choisir "REVIEW".
"""

USER_PROMPT_TEMPLATE = """Voici un contenu à analyser (peut provenir d'un fichier ou d'une saisie manuelle).

CONTENU:
{content}

Tâche:
1) Détecte les incohérences / anomalies possibles.
2) Évalue un score de risque (0..100).
3) Propose une action recommandée.
4) Résume clairement.

Réponds uniquement avec l'objet JSON final.
"""


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        v = int(float(x))
        return max(0, min(100, v))
    except Exception:
        return default


def _normalize_status(s: Any) -> str:
    s = str(s).strip().upper()
    if s in {"OK", "REVIEW", "FLAGGED"}:
        return s
    return "REVIEW"


def _ensure_top_alerts(alerts: Any) -> List[str]:
    if isinstance(alerts, list):
        out = []
        for a in alerts:
            t = str(a).strip()
            if t:
                out.append(t)
        return out[:7] if out else ["Informations insuffisantes pour conclure."]
    return ["Informations insuffisantes pour conclure."]


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Robust parsing: tries direct JSON, then tries to find the first {...} block.
    """
    text = text.strip()

    # direct attempt
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # search for first JSON object block
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None

    candidate = m.group(0).strip()
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None

    return None


def _postprocess(result: Dict[str, Any]) -> Dict[str, Any]:
    status = _normalize_status(result.get("status"))
    risk_score = _safe_int(result.get("risk_score"), default=50)
    top_alerts = _ensure_top_alerts(result.get("top_alerts"))
    recommended_action = str(result.get("recommended_action", "")).strip() or "Review"
    summary_explanation = str(result.get("summary_explanation", "")).strip()

    if not summary_explanation:
        summary_explanation = (
            "Analyse assistée par IA : le contenu fourni ne permet pas une conclusion ferme. "
            "Une revue manuelle est recommandée."
        )
        status = "REVIEW"

    return {
        "status": status,
        "risk_score": risk_score,
        "top_alerts": top_alerts,
        "recommended_action": recommended_action,
        "summary_explanation": summary_explanation,
    }


def analyze_text(raw_text: str, use_mistral: bool = True) -> Dict[str, Any]:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return _postprocess(
            {
                "status": "REVIEW",
                "risk_score": 50,
                "top_alerts": ["Aucun contenu exploitable."],
                "recommended_action": "Review",
                "summary_explanation": "Analyse assistée par IA : aucun contenu exploitable n'a été fourni.",
            }
        )

    if not use_mistral:
        # Mode fallback minimal (sans IA): on reste prudent
        return _postprocess(
            {
                "status": "REVIEW",
                "risk_score": 55,
                "top_alerts": ["Mode sans IA : analyse limitée."],
                "recommended_action": "Review with documents",
                "summary_explanation": (
                    "Mode sans IA : le système n'a pas interrogé Mistral. "
                    "Une vérification manuelle est nécessaire."
                ),
            }
        )

    client = MistralClient()
    user_prompt = USER_PROMPT_TEMPLATE.format(content=raw_text[:18000])  # limite raisonnable
    answer = client.chat(SYSTEM_PROMPT, user_prompt, temperature=0.2)

    parsed = _extract_json_from_text(answer)
    if not parsed:
        # Si Mistral répond mal, on retombe sur une sortie prudente
        return _postprocess(
            {
                "status": "REVIEW",
                "risk_score": 60,
                "top_alerts": ["Réponse IA non exploitable (format)."],
                "recommended_action": "Review",
                "summary_explanation": (
                    "Analyse assistée par IA : la réponse du modèle n'était pas dans un format exploitable. "
                    "Merci de relancer ou de fournir un contenu plus structuré."
                ),
            }
        )

    return _postprocess(parsed)


def analyze_profile(profile: Dict[str, Any], use_mistral: bool = True) -> Dict[str, Any]:
    """
    Formulaire -> on transforme en texte clair (centré IA).
    """
    lines = []
    for k, v in profile.items():
        lines.append(f"- {k}: {v}")
    content = "DOSSIER (FORMULAIRE)\n" + "\n".join(lines)
    return analyze_text(content, use_mistral=use_mistral)