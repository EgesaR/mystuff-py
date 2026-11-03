"""IronVeil adapter for My Stuff server-side encrypted records."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from functools import lru_cache
from typing import Protocol, cast


class IronveilUnavailableError(RuntimeError):
    """Raised when IronVeil is unavailable or no usable provider is configured."""


class KeyProvider(Protocol):
    """Interface required by My Stuff for persistent encryption providers."""

    def seal_current(
        self,
        plaintext: bytes,
        aad: bytes,
    ) -> bytes: ...

    def open(
        self,
        envelope: bytes,
        aad: bytes,
    ) -> bytes: ...


class _DevelopmentMemoryKeyring(KeyProvider, Protocol):
    """Typing contract for the development-only IronVeil MemoryKeyring."""

    def create_key(self) -> str: ...


class _IronveilModule(Protocol):
    """Typed interface for the compiled IronVeil Python module."""

    MemoryKeyring: Callable[[], _DevelopmentMemoryKeyring]


def _require_input_bytes(value: object, name: str) -> bytes:
    """Validate bytes received at the application boundary."""
    if not isinstance(value, bytes):
        raise TypeError(f"IronVeil {name} must be bytes")

    return value


def _require_provider_bytes(
    value: object,
    *,
    operation: str,
    allow_empty: bool = True,
) -> bytes:
    """Validate data returned by a dynamically configured provider."""
    if not isinstance(value, bytes) or (not allow_empty and not value):
        raise IronveilUnavailableError(f"IronVeil provider returned an invalid {operation}")

    return value


def _coerce_provider(value: object) -> KeyProvider:
    """Validate and type a dynamically loaded provider."""
    if not callable(getattr(value, "seal_current", None)):
        raise IronveilUnavailableError("IronVeil provider must implement seal_current(data, aad)")

    if not callable(getattr(value, "open", None)):
        raise IronveilUnavailableError("IronVeil provider must implement open(envelope, aad)")

    return cast(KeyProvider, value)


class IronveilService:
    """Typed application wrapper around an IronVeil key provider."""

    def __init__(self, provider: KeyProvider) -> None:
        self._provider = _coerce_provider(provider)

    def seal(
        self,
        plaintext: bytes,
        *,
        context: bytes,
    ) -> bytes:
        """Encrypt plaintext with authenticated associated data."""
        plaintext = _require_input_bytes(plaintext, "plaintext")
        context = _require_input_bytes(context, "context")

        envelope = self._provider.seal_current(
            plaintext,
            context,
        )

        return _require_provider_bytes(
            envelope,
            operation="encrypted envelope",
            allow_empty=False,
        )

    def open(
        self,
        envelope: bytes,
        *,
        context: bytes,
    ) -> bytes:
        """Decrypt and authenticate an IronVeil envelope."""
        envelope = _require_input_bytes(envelope, "envelope")
        context = _require_input_bytes(context, "context")

        plaintext = self._provider.open(
            envelope,
            context,
        )

        return _require_provider_bytes(
            plaintext,
            operation="plaintext",
        )


def _load_factory(spec: str) -> Callable[[], object]:
    """Load a provider factory using module.path:factory_name syntax."""
    module_name, separator, attribute = spec.partition(":")

    if not separator or not module_name or not attribute:
        raise IronveilUnavailableError("IRONVEIL_PROVIDER_FACTORY must use module.path:factory_name")

    try:
        module = importlib.import_module(module_name)
        factory = getattr(module, attribute)

    except (ImportError, AttributeError) as exc:
        raise IronveilUnavailableError("Configured IronVeil provider factory could not be imported") from exc

    if not callable(factory):
        raise IronveilUnavailableError("Configured IronVeil provider factory is not callable")

    return cast(Callable[[], object], factory)


def _build_provider() -> KeyProvider:
    """Initialize the configured persistent or development provider."""

    # Production and custom providers take precedence.
    factory_spec = os.getenv(
        "IRONVEIL_PROVIDER_FACTORY",
        "",
    ).strip()

    if factory_spec:
        factory = _load_factory(factory_spec)

        try:
            provider = factory()

        except Exception as exc:
            raise IronveilUnavailableError("Configured IronVeil provider could not be initialized") from exc

        return _coerce_provider(provider)

    # MemoryKeyring is permitted only for explicitly enabled local development.
    allow_ephemeral = os.getenv(
        "IRONVEIL_ALLOW_EPHEMERAL_KEYRING",
        "false",
    ).strip().lower() in {"1", "true", "yes", "on"}

    if not allow_ephemeral:
        raise IronveilUnavailableError(
            "No persistent IronVeil provider is configured. Set IRONVEIL_PROVIDER_FACTORY=module.path:factory_name. MemoryKeyring is development-only and must be explicitly enabled."
        )

    try:
        from app.core.config import settings

        if not settings.DEBUG:
            raise IronveilUnavailableError("The ephemeral IronVeil keyring is forbidden outside DEBUG mode")

        # Import dynamically because the PyO3 extension does not currently
        # provide native type information for its exported Python classes.
        ironveil = cast(
            _IronveilModule,
            importlib.import_module("ironveil"),
        )

        provider = ironveil.MemoryKeyring()
        key_id = provider.create_key()

        if not key_id:
            raise IronveilUnavailableError("IronVeil MemoryKeyring did not initialize a key")

        return _coerce_provider(provider)

    except IronveilUnavailableError:
        raise

    except Exception as exc:
        raise IronveilUnavailableError("Unable to initialize IronVeil MemoryKeyring") from exc


@lru_cache(maxsize=1)
def get_ironveil_service() -> IronveilService:
    """Return the cached process-wide IronVeil service."""
    return IronveilService(_build_provider())


def reset_ironveil_service_for_tests() -> None:
    """Clear the cached service when tests replace provider configuration."""
    get_ironveil_service.cache_clear()
