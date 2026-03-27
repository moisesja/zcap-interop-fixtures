from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

import rfc8785


def _strip_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if item is None:
                continue
            result[key] = _strip_nulls(item)
        return result
    if isinstance(value, list):
        return [_strip_nulls(item) for item in value]
    return value


def _canonicalize_reference(obj: dict[str, Any]) -> bytes:
    return rfc8785.dumps(obj)


def _reference_capability_payload(document: dict[str, Any], proof: dict[str, Any]) -> bytes:
    payload = _strip_nulls(
        {
            "capability": document,
            "proof": {
                "type": proof["type"],
                "created": proof["created"],
                "proofPurpose": proof["proofPurpose"],
                "verificationMethod": proof["verificationMethod"],
                "capabilityChain": proof.get("capabilityChain", []),
            },
        }
    )
    return _canonicalize_reference(payload)


def _reference_invocation_payload(document: dict[str, Any], proof: dict[str, Any]) -> bytes:
    payload = _strip_nulls(
        {
            "invocation": {
                "id": document["id"],
                "capability": document["capability"],
                "capabilityAction": document["capabilityAction"],
                "invocationTarget": document["invocationTarget"],
            },
            "proof": {
                "type": proof["type"],
                "created": proof["created"],
                "proofPurpose": proof["proofPurpose"],
                "verificationMethod": proof["verificationMethod"],
                "capability": proof.get("capability"),
                "capabilityAction": proof.get("capabilityAction"),
                "invocationTarget": proof.get("invocationTarget"),
                "capabilityChain": proof.get("capabilityChain", []),
            },
        }
    )
    return _canonicalize_reference(payload)


class Adapter(Protocol):
    name: str
    runner: str

    def canonicalize_capability_payload(self, document: dict[str, Any], proof: dict[str, Any]) -> bytes:
        ...

    def canonicalize_invocation_payload(self, document: dict[str, Any], proof: dict[str, Any]) -> bytes:
        ...


@dataclass
class ReferenceJcsAdapter:
    name: str = "reference-jcs"
    runner: str = "python"

    def canonicalize_capability_payload(self, document: dict[str, Any], proof: dict[str, Any]) -> bytes:
        return _reference_capability_payload(document, proof)

    def canonicalize_invocation_payload(self, document: dict[str, Any], proof: dict[str, Any]) -> bytes:
        return _reference_invocation_payload(document, proof)


@dataclass
class IdentityAuthorizationServiceAdapter:
    module_root: Path
    name: str = "identity-authorization-service"
    runner: str = "python"

    def __post_init__(self) -> None:
        module_root = str(self.module_root)
        if module_root not in sys.path:
            sys.path.insert(0, module_root)
        self._crypto = importlib.import_module("identity_authorization_service.crypto")

    def canonicalize_capability_payload(self, document: dict[str, Any], proof: dict[str, Any]) -> bytes:
        return self._crypto.canonicalize_capability_payload(document, proof)

    def canonicalize_invocation_payload(self, document: dict[str, Any], proof: dict[str, Any]) -> bytes:
        return self._crypto.canonicalize_invocation_payload(document, proof)


PYTHON_ADAPTER_CHOICES = (
    "reference-jcs",
    "identity-authorization-service",
)


def load_python_adapter(adapter_name: str, *, module_root: str | Path | None = None) -> Adapter:
    if adapter_name == "reference-jcs":
        return ReferenceJcsAdapter()
    if adapter_name == "identity-authorization-service":
        if module_root is None:
            raise ValueError("--module-root is required for identity-authorization-service")
        return IdentityAuthorizationServiceAdapter(Path(module_root).resolve())
    raise ValueError(f"Unknown adapter: {adapter_name}")


def load_python_adapter_from_config(config: Mapping[str, Any]) -> Adapter:
    return load_python_adapter(
        str(config["adapter"]),
        module_root=config.get("module_root"),
    )

