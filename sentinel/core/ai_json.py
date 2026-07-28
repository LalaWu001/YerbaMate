from __future__ import annotations

import json
import re
from typing import Any

from sentinel.core.model_adapter import ModelResult


def parse_ai_json(content: str) -> tuple[dict[str, Any] | None, str]:
    text = content.strip()
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed, ""
    return None, "AI response was not valid JSON object"


def ai_status(enabled: bool, response: ModelResult | None = None, accepted: bool = False, error: str = "") -> dict[str, Any]:
    return {
        "enabled": enabled,
        "called": response is not None,
        "accepted": accepted,
        "error": error or (response.error if response and not response.ok else ""),
        "prompt_hash": response.prompt_hash if response else "",
        "input_tokens": response.input_tokens if response else 0,
        "output_tokens": response.output_tokens if response else 0,
        "request_chars": response.request_chars if response else 0,
    }
