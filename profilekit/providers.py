from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI


ProviderName = Literal["deepseek", "openai"]


@dataclass(frozen=True)
class ModelOption:
    provider: ProviderName
    model: str
    label: str
    cost_tier: Literal["lowest", "low", "medium", "high"]
    description: str
    api_key_variable: str


MODEL_CATALOG = (
    ModelOption(
        provider="deepseek",
        model="deepseek-flash",
        label="DeepSeek Flash",
        cost_tier="lowest",
        description="Default · lowest-cost general workflow",
        api_key_variable="DEEPSEEK_API_KEY",
    ),
    ModelOption(
        provider="deepseek",
        model="deepseek-v4-pro",
        label="DeepSeek V4 Pro",
        cost_tier="low",
        description="Stronger DeepSeek reasoning",
        api_key_variable="DEEPSEEK_API_KEY",
    ),
    ModelOption(
        provider="openai",
        model="gpt-6-luna",
        label="OpenAI GPT-6 Luna",
        cost_tier="low",
        description="Efficient OpenAI option",
        api_key_variable="OPENAI_API_KEY",
    ),
    ModelOption(
        provider="openai",
        model="gpt-6-sol",
        label="OpenAI GPT-6 Sol",
        cost_tier="medium",
        description="Balanced quality and cost",
        api_key_variable="OPENAI_API_KEY",
    ),
    ModelOption(
        provider="openai",
        model="gpt-6-astra",
        label="OpenAI GPT-6 Astra",
        cost_tier="high",
        description="Highest capability, highest cost",
        api_key_variable="OPENAI_API_KEY",
    ),
)


def default_selection() -> tuple[ProviderName, str]:
    provider = os.environ.get("PROFILEKIT_PROVIDER", "deepseek").strip().lower()
    model = os.environ.get("PROFILEKIT_MODEL", "deepseek-flash").strip()
    if find_model(provider, model) is None:
        return "deepseek", "deepseek-flash"
    return provider, model  # type: ignore[return-value]


def find_model(provider: str, model: str) -> ModelOption | None:
    return next(
        (option for option in MODEL_CATALOG if option.provider == provider and option.model == model),
        None,
    )


def model_is_ready(option: ModelOption) -> bool:
    return bool(os.environ.get(option.api_key_variable, "").strip())


def available_catalog() -> list[dict[str, str | bool]]:
    return [
        {
            "provider": option.provider,
            "model": option.model,
            "label": option.label,
            "cost_tier": option.cost_tier,
            "description": option.description,
            "ready": model_is_ready(option),
        }
        for option in MODEL_CATALOG
    ]


def resolve_openai_model(provider: str, model: str) -> str:
    option = find_model(provider, model)
    if option is None:
        raise ValueError(f"Unsupported model selection: {provider}/{model}")
    api_key = os.environ.get(option.api_key_variable, "").strip()
    if not api_key:
        raise ValueError(f"{option.api_key_variable} is not configured")
    if provider != "openai":
        raise ValueError("resolve_openai_model only accepts the OpenAI provider")
    return model


def deepseek_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
