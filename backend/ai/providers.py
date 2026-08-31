import json
import os
import re
from urllib.parse import urlparse

import httpx

from models.cfo import FinancialToolResult


SYSTEM_PROMPT = """You are an explanation renderer for a financial copilot.
Use only the supplied structured JSON. Never calculate, estimate, infer, or invent a financial number.
Clearly label recorded facts and model predictions. Never present an assumption as a fact.
Explain reasoning and cite source ids included in the context. If context is insufficient, say so.
You have no write tools and must never claim to modify financial records.
Use concise prose without numbered lists. Do not introduce any numeric value absent from context."""


class OllamaProvider:
    """Optional local-only provider. Disabled unless AI_CFO_PROVIDER=ollama."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        self.timeout = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "8"))
        hostname = urlparse(self.base_url).hostname
        if hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Ollama base URL must remain loopback-only")

    async def generate(self, question: str, context: list[FinancialToolResult]) -> str:
        safe_context = [item.model_dump(mode="json") for item in context]
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": 0, "seed": 7},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"QUESTION: {question}\nSTRUCTURED_CONTEXT: {json.dumps(safe_context)}"},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            answer = response.json()["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Ollama returned no answer")
        self._validate_numbers(answer, question, safe_context)
        return answer.strip()

    @staticmethod
    def _validate_numbers(answer: str, question: str, context: list[dict]) -> None:
        number_pattern = r"-?\d[\d,]*(?:\.\d+)?%?"
        normalize = lambda value: value.replace(",", "").rstrip("%")
        allowed = {
            normalize(value)
            for value in re.findall(number_pattern, f"{question} {json.dumps(context)}")
        }
        allowed.update({"0", "1", "2"})
        unsupported = [value for value in re.findall(number_pattern, answer) if normalize(value) not in allowed]
        if unsupported:
            raise ValueError("Ollama answer introduced unsupported numeric values")