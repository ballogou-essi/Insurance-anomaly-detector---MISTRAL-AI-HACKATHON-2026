import os
import json
import requests


class MistralClient:
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY", "").strip()
        self.model = os.getenv("MISTRAL_MODEL", "mistral-large-latest").strip()
        self.base_url = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").strip()

        if not self.api_key:
            raise RuntimeError("MISTRAL_API_KEY manquante dans l'environnement.")

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"Erreur Mistral {r.status_code}: {r.text}")

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            raise RuntimeError(f"Réponse Mistral inattendue: {data}")