from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


AGENT_NAMES = [
    "manager",
    "project_analyzer",
    "tool_probe",
    "slither",
    "foundry",
    "semgrep",
    "echidna",
    "aderyn",
    "protocol",
    "business_logic",
    "transaction_logic",
    "code_analysis",
    "threat_modeling",
    "verification",
    "report",
]


def _normalize_base_url(value: Any) -> str:
    base = str(value or "").strip().rstrip("/")
    suffix = "/chat/completions"
    if base.lower().endswith(suffix):
        return base[: -len(suffix)]
    return base


@dataclass
class ApiProfile:
    id: str = "default"
    name: str = "Default OpenAI Compatible"
    provider: str = "openai-compatible"
    base_url: str = ""
    api_key: str = ""
    default_model: str = ""
    enabled: bool = False


@dataclass
class AgentAIConfig:
    ai_enabled: bool = False
    api_profile_id: str = "default"
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout_seconds: int = 120
    send_source_code: bool = False
    fallback_strategy: str = "rule"


@dataclass
class AuditConfig:
    mode: str = "hybrid-auto"
    analysis_depth: str = "standard"
    database_path: str = "data/yerbamate.sqlite"
    api_profiles: list[ApiProfile] = field(default_factory=list)
    agent_ai: dict[str, AgentAIConfig] = field(default_factory=dict)
    tools: dict[str, bool] = field(default_factory=dict)
    permissions: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "AuditConfig":
        api_key = os.getenv("YERBAMATE_API_KEY", os.getenv("CONTRACTSENTINEL_API_KEY", "")).strip()
        base_url = _normalize_base_url(
            os.getenv("YERBAMATE_BASE_URL", os.getenv("CONTRACTSENTINEL_BASE_URL", ""))
        )
        model = os.getenv("YERBAMATE_MODEL", os.getenv("CONTRACTSENTINEL_MODEL", "")).strip()
        profile = ApiProfile(
            base_url=base_url,
            api_key=api_key,
            default_model=model,
            enabled=bool(api_key and base_url and model),
        )
        agent_ai = {
            "project_analyzer": AgentAIConfig(ai_enabled=False),
            "tool_probe": AgentAIConfig(ai_enabled=False),
            "slither": AgentAIConfig(ai_enabled=False),
            "foundry": AgentAIConfig(ai_enabled=False),
            "code_analysis": AgentAIConfig(ai_enabled=False),
            "verification": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "protocol": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "business_logic": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "transaction_logic": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "threat_modeling": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "report": AgentAIConfig(
                ai_enabled=profile.enabled,
                model=model,
                max_tokens=4096,
                fallback_strategy="lead-auditor-opinion",
            ),
        }
        return cls(
            api_profiles=[profile],
            agent_ai=agent_ai,
            tools={
                "built_in_rules": True,
                "slither": True,
                "foundry": True,
                "echidna": False,
                "halmos": False,
                "semgrep": False,
                "aderyn": False,
            },
            permissions={
                "save_model_call_logs": True,
                "send_source_to_remote": False,
                "generate_foundry_tests": True,
            },
        )

    @classmethod
    def from_file(cls, path: Path | None) -> "AuditConfig":
        if path is None:
            return cls.default()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AuditConfig":
        default = cls.default()
        profiles = [
            ApiProfile(
                id=item.get("id", item.get("name", "default")),
                name=item.get("name", "Default"),
                provider=item.get("provider", "openai-compatible"),
                base_url=_normalize_base_url(item.get("base_url", item.get("baseUrl", ""))),
                api_key=str(item.get("api_key", item.get("apiKey", ""))).strip(),
                default_model=str(item.get("default_model", item.get("defaultModel", ""))).strip(),
                enabled=bool(item.get("enabled", False)),
            )
            for item in raw.get("api_profiles", raw.get("apiProfiles", []))
        ] or default.api_profiles

        agent_ai: dict[str, AgentAIConfig] = {}
        raw_agent_ai = raw.get("agent_ai", raw.get("agentAI", {}))
        for name in AGENT_NAMES:
            base = default.agent_ai.get(name, AgentAIConfig())
            item = raw_agent_ai.get(name, {})
            agent_ai[name] = AgentAIConfig(
                ai_enabled=bool(item.get("ai_enabled", item.get("aiEnabled", base.ai_enabled))),
                api_profile_id=item.get("api_profile_id", item.get("apiProfileId", base.api_profile_id)),
                model=str(item.get("model", base.model)).strip(),
                temperature=float(item.get("temperature", base.temperature)),
                max_tokens=int(item.get("max_tokens", item.get("maxTokens", base.max_tokens))),
                timeout_seconds=int(item.get("timeout_seconds", item.get("timeoutSeconds", base.timeout_seconds))),
                send_source_code=bool(item.get("send_source_code", item.get("sendSourceCode", base.send_source_code))),
                fallback_strategy=str(item.get("fallback_strategy", item.get("fallbackStrategy", base.fallback_strategy))).strip(),
            )

        raw_tools = cls._normalize_tools(raw.get("tools", {}))

        return cls(
            mode=raw.get("mode", default.mode),
            analysis_depth=raw.get("analysis_depth", raw.get("analysisDepth", default.analysis_depth)),
            database_path=raw.get("database_path", raw.get("databasePath", default.database_path)),
            api_profiles=profiles,
            agent_ai=agent_ai,
            tools={**default.tools, **raw_tools},
            permissions={**default.permissions, **raw.get("permissions", {})},
        )

    @staticmethod
    def _normalize_tools(raw_tools: dict[str, Any]) -> dict[str, bool]:
        aliases = {
            "builtInRules": "built_in_rules",
            "built-in-rules": "built_in_rules",
        }
        normalized: dict[str, bool] = {}
        for key, value in raw_tools.items():
            normalized[aliases.get(key, key)] = bool(value)
        return normalized

    def profile_for_agent(self, agent_name: str) -> ApiProfile | None:
        agent_config = self.agent_ai.get(agent_name)
        if not agent_config:
            return None
        for profile in self.api_profiles:
            if profile.id == agent_config.api_profile_id and self._profile_usable(profile, agent_config):
                return profile
        if agent_config.api_profile_id:
            return None
        return next((profile for profile in self.api_profiles if self._profile_usable(profile, agent_config)), None)

    @staticmethod
    def _profile_usable(profile: ApiProfile, agent_config: AgentAIConfig) -> bool:
        model = (agent_config.model or profile.default_model).strip()
        has_auth = bool(profile.api_key.strip()) or profile.provider == "ollama"
        return bool(profile.enabled and _normalize_base_url(profile.base_url) and model and has_auth)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "analysis_depth": self.analysis_depth,
            "database_path": self.database_path,
            "api_profiles": [
                {
                    "id": profile.id,
                    "name": profile.name,
                    "provider": profile.provider,
                    "base_url": profile.base_url,
                    "default_model": profile.default_model,
                    "enabled": profile.enabled,
                    "has_api_key": bool(profile.api_key),
                }
                for profile in self.api_profiles
            ],
            "agent_ai": {
                name: {
                    "ai_enabled": config.ai_enabled,
                    "api_profile_id": config.api_profile_id,
                    "model": config.model,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "timeout_seconds": config.timeout_seconds,
                    "send_source_code": config.send_source_code,
                    "fallback_strategy": config.fallback_strategy,
                }
                for name, config in self.agent_ai.items()
            },
            "tools": self.tools,
            "permissions": self.permissions,
        }
