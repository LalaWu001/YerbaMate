from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


AGENT_NAMES = [
    "project_analyzer",
    "tool_probe",
    "slither",
    "foundry",
    "protocol",
    "business_logic",
    "transaction_logic",
    "code_analysis",
    "threat_modeling",
    "verification",
    "report",
]


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
    send_source_code: bool = False
    fallback_strategy: str = "rule"


@dataclass
class AuditConfig:
    mode: str = "hybrid-auto"
    analysis_depth: str = "standard"
    database_path: str = "data/contractsentinel.sqlite"
    api_profiles: list[ApiProfile] = field(default_factory=list)
    agent_ai: dict[str, AgentAIConfig] = field(default_factory=dict)
    tools: dict[str, bool] = field(default_factory=dict)
    permissions: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "AuditConfig":
        api_key = os.getenv("CONTRACTSENTINEL_API_KEY", "")
        base_url = os.getenv("CONTRACTSENTINEL_BASE_URL", "")
        model = os.getenv("CONTRACTSENTINEL_MODEL", "")
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
            "verification": AgentAIConfig(ai_enabled=False),
            "protocol": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "business_logic": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "transaction_logic": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "threat_modeling": AgentAIConfig(ai_enabled=profile.enabled, model=model),
            "report": AgentAIConfig(ai_enabled=profile.enabled, model=model, max_tokens=4096),
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
                base_url=item.get("base_url", item.get("baseUrl", "")),
                api_key=item.get("api_key", item.get("apiKey", "")),
                default_model=item.get("default_model", item.get("defaultModel", "")),
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
                model=item.get("model", base.model),
                temperature=float(item.get("temperature", base.temperature)),
                max_tokens=int(item.get("max_tokens", item.get("maxTokens", base.max_tokens))),
                send_source_code=bool(item.get("send_source_code", item.get("sendSourceCode", base.send_source_code))),
                fallback_strategy=item.get("fallback_strategy", item.get("fallbackStrategy", base.fallback_strategy)),
            )

        return cls(
            mode=raw.get("mode", default.mode),
            analysis_depth=raw.get("analysis_depth", raw.get("analysisDepth", default.analysis_depth)),
            database_path=raw.get("database_path", raw.get("databasePath", default.database_path)),
            api_profiles=profiles,
            agent_ai=agent_ai,
            tools={**default.tools, **raw.get("tools", {})},
            permissions={**default.permissions, **raw.get("permissions", {})},
        )

    def profile_for_agent(self, agent_name: str) -> ApiProfile | None:
        agent_config = self.agent_ai.get(agent_name)
        if not agent_config:
            return None
        for profile in self.api_profiles:
            if profile.id == agent_config.api_profile_id and profile.enabled:
                return profile
        return next((profile for profile in self.api_profiles if profile.enabled), None)

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
                    "send_source_code": config.send_source_code,
                    "fallback_strategy": config.fallback_strategy,
                }
                for name, config in self.agent_ai.items()
            },
            "tools": self.tools,
            "permissions": self.permissions,
        }
