"""Contract provider protocol and configuration-based loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol

from contracts.model import ApiContract, ContractError
from utils.project_paths import PROJECT_ROOT


class ContractProvider(Protocol):
    """Normalize one provider-specific contract source into ``ApiContract``."""

    def load(self, source: str | Path) -> ApiContract:
        """Load one contract source."""


def _provider_for_name(name: str) -> ContractProvider:
    normalized = name.strip().lower()
    if normalized == "static_manifest":
        from contracts.manifest_provider import StaticManifestProvider

        return StaticManifestProvider()
    if normalized == "openapi":
        try:
            from contracts.openapi_provider import OpenAPIProvider
        except ModuleNotFoundError as exc:  # pragma: no cover - only before Stage 5 task 3 exists
            raise ContractError("openapi contract provider is not available") from exc
        return OpenAPIProvider()
    raise ContractError(f"unsupported contract provider: {name}")


def load_contract_from_config(
    runtime_config: Mapping[str, Any],
    *,
    project_root: str | Path = PROJECT_ROOT,
) -> ApiContract:
    """Load a contract from the generic ``contract.provider/source`` config section."""
    section = runtime_config.get("contract")
    if not isinstance(section, Mapping):
        raise ContractError("contract configuration must be a mapping")

    provider_name = section.get("provider")
    source_value = section.get("source")
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ContractError("contract.provider must be non-empty text")
    if not isinstance(source_value, str) or not source_value.strip():
        raise ContractError("contract.source must be non-empty text")

    source = Path(source_value.strip()).expanduser()
    if not source.is_absolute():
        source = Path(project_root).resolve() / source
    return _provider_for_name(provider_name).load(source.resolve())
