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
    error: str = ""
    prompt_hash: str = ""


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
        if not profile.api_key or not profile.base_url:
            return ModelResult(ok=False, content="", error="API key or base URL missing")

        model = agent_config.model or profile.default_model
        if not model:
            return ModelResult(ok=False, content="", error="Model name missing")

        payload_text = json.dumps(user_payload, ensure_ascii=False, indent=2)
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
        url = profile.base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {profile.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self._record_call(profile, model, prompt_hash, payload_text, str(exc), 0, 0)
            return ModelResult(ok=False, content="", error=str(exc), prompt_hash=prompt_hash)

        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        self._record_call(profile, model, prompt_hash, payload_text, content, input_tokens, output_tokens)
        return ModelResult(
            ok=bool(content),
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            prompt_hash=prompt_hash,
        )

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
