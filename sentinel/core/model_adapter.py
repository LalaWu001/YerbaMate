from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from sentinel.core.config import AgentAIConfig, ApiProfile


@dataclass
class ModelResult:
    ok: bool
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    request_chars: int = 0
    error: str = ""
    prompt_hash: str = ""
    finish_reason: str = ""


class ModelAdapter:
    def __init__(self) -> None:
        self.call_logs: list[dict] = []

    def call_json(
        self,
        profile: ApiProfile | None,
        agent_config: AgentAIConfig,
        system_prompt: str,
        user_payload: dict,
    ) -> ModelResult:
        if not profile or not profile.enabled:
            return ModelResult(ok=False, content="", error="No enabled API profile configured")
        base_url = self._normalize_base_url(profile.base_url)
        api_key = profile.api_key.strip()
        if not base_url:
            return ModelResult(ok=False, content="", error="Base URL missing")
        if not api_key and profile.provider != "ollama":
            return ModelResult(ok=False, content="", error="API key or base URL missing")

        model = (agent_config.model or profile.default_model).strip()
        if not model:
            return ModelResult(ok=False, content="", error="Model name missing")

        payload_text = json.dumps(user_payload, ensure_ascii=False, indent=2)
        request_chars = len(payload_text)
        prompt_hash = hashlib.sha256((system_prompt + payload_text).encode("utf-8")).hexdigest()[:16]
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload_text},
            ],
            "temperature": agent_config.temperature,
            "max_tokens": agent_config.max_tokens,
        }
        url = base_url + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        timeout = max(30, int(getattr(agent_config, "timeout_seconds", 120) or 120))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            message = str(exc)
            if "timed out" in message.lower():
                message = (
                    f"{message} after {timeout}s with {request_chars:,} input characters; "
                    "reduce source sharing, use a faster model, or increase timeoutSeconds."
                )
            self._record_call(profile, model, prompt_hash, payload_text, message, 0, 0)
            return ModelResult(ok=False, content="", error=message, prompt_hash=prompt_hash, request_chars=request_chars)

        choice = raw.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = str(choice.get("finish_reason", "") or "")
        usage = raw.get("usage", {})
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        self._record_call(profile, model, prompt_hash, payload_text, content, input_tokens, output_tokens)
        return ModelResult(
            ok=bool(content),
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            request_chars=request_chars,
            prompt_hash=prompt_hash,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _normalize_base_url(value: str) -> str:
        base = value.strip().rstrip("/")
        suffix = "/chat/completions"
        if base.lower().endswith(suffix):
            return base[: -len(suffix)]
        return base

    def _record_call(
        self,
        profile: ApiProfile,
        model: str,
        prompt_hash: str,
        request_preview: str,
        response_preview: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.call_logs.append(
            {
                "provider": profile.provider,
                "model": model,
                "prompt_hash": prompt_hash,
                "request_preview": request_preview[:1200],
                "response_preview": response_preview[:1200],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )
