from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class LocalOpenAICompatibleClient:
    base_url: str
    api_key: str
    temperature: float
    timeout_seconds: int

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = requests.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def chat_json(self, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raw = self.chat(model=model, system_prompt=system_prompt, user_prompt=user_prompt)
        return _extract_json(raw)


def _extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)
