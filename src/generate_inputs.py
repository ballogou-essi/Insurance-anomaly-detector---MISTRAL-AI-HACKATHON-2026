import os
import json
import random
from datetime import datetime

DATA_INPUTS_DIR = os.path.join("data", "inputs")


def generate_demo_inputs(n: int = 50, seed: int = 42) -> list[str]:
    """
    Génère N cas d'entrée (JSON) différents pour la démo et les stocke dans data/inputs/.
    Retourne la liste des chemins créés.

    - Ne crée PAS data/inputs automatiquement (conforme à ta demande).
    - Cas variés : OK / REVIEW / FLAGGED en fonction d'anomalies injectées.
    """
    if not os.path.isdir(DATA_INPUTS_DIR):
        raise RuntimeError(f"Dossier manquant : {DATA_INPUTS_DIR} (crée-le à la main)")

    random.seed(seed)

    products = ["Auto", "Habitation", "Santé", "Voyage", "RC Pro"]
    occupations = ["Employé", "Indépendant", "Étudiant", "Sans emploi", "Chauffeur VTC", "BTP", "Cadre"]
    cities = ["Paris", "Lyon", "Marseille", "Toulouse", "Nantes", "Strasbourg", "Bordeaux"]

    def make_case(i: int) -> dict:
        age = random.randint(18, 85)
        income = random.choice([18000, 22000, 28000, 35000, 48000, 65000, 90000])
        product = random.choice(products)
        occupation = random.choice(occupations)
        city = random.choice(cities)

        # anomalies possibles (pour rendre les cas "pratiques")
        anomalies = []

        # 1) âge incohérent
        if random.random() < 0.10:
            age = random.choice([0, 5, 120, -3])
            anomalies.append("age_out_of_range")

        # 2) revenu incohérent
        if random.random() < 0.12:
            income = random.choice([-1000, 0, 9999999])
            anomalies.append("income_suspicious")

        # 3) produit vs profil incohérent (ex: RC Pro avec étudiant très jeune)
        if product == "RC Pro" and age < 21 and random.random() < 0.35:
            anomalies.append("product_profile_mismatch")

        # 4) notes contenant signaux à risque
        risky_phrases = [
            "documents manquants",
            "informations contradictoires",
            "changement d'adresse récent",
            "refus de fournir justificatifs",
            "historique de sinistres élevé",
        ]
        notes = "Dossier standard."
        if random.random() < 0.30:
            notes = " / ".join(random.sample(risky_phrases, k=random.randint(1, 3)))
            anomalies.append("risky_notes")

        # label attendu (utile pour tes tests, mais ton IA recalculera)
        # On force une logique simple pour varier les cas
        if "age_out_of_range" in anomalies or "income_suspicious" in anomalies:
            expected = "FLAGGED"
        elif anomalies:
            expected = "REVIEW"
        else:
            expected = "OK"

        return {
            "case_id": f"case_{i:03d}",
            "full_name": f"Client {i:03d}",
            "age": age,
            "city": city,
            "product": product,
            "occupation": occupation,
            "annual_income": income,
            "notes": notes,
            "expected_label_for_demo": expected,
            "injected_anomalies": anomalies,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    created_paths = []
    for i in range(1, n + 1):
        obj = make_case(i)
        path = os.path.join(DATA_INPUTS_DIR, f"{obj['case_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        created_paths.append(path)

    return created_paths