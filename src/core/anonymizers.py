"""
LangSmith anonymizers for masking sensitive data in traces.

This module provides anonymization patterns to prevent credential leakage
when sending traces to LangSmith.

Patterns covered:
- PAN-OS API keys (LUFRPT... format)
- Anthropic API keys (sk-ant-... format)
- Password fields (various formats)
- XML password elements
"""

from langchain_core.tracers.langchain import LangChainTracer
from langsmith import Client
from langsmith.anonymizer import create_anonymizer

from src.core.config import get_settings


def get_panos_anonymizer():
    """
    Create anonymizer with PAN-OS-specific patterns.

    Returns:
        Anonymizer: Configured anonymizer function
    """
    return create_anonymizer(
        [
            # Pattern 1: PAN-OS API keys (LUFRPT format)
            {"pattern": r"LUFRPT[A-Za-z0-9+/=]{40,}", "replace": "<panos-api-key>"},
            # Pattern 2: Anthropic API keys
            {"pattern": r"sk-ant-[A-Za-z0-9-_]{40,}", "replace": "<anthropic-api-key>"},
            # Pattern 3: Password fields
            {
                "pattern": r"(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?[^\s'\"]+",
                "replace": r"\1: <password>",
            },
            # Pattern 4: XML password elements
            {"pattern": r"<password>.*?</password>", "replace": "<password><redacted></password>"},
        ]
    )


def create_panos_tracer() -> LangChainTracer:
    """
    Create LangChainTracer configured with PAN-OS anonymization patterns.

    This function creates a LangChainTracer that will automatically mask
    sensitive data (API keys, passwords) before sending traces to LangSmith.

    Returns:
        LangChainTracer: Configured tracer with anonymization enabled

    Example:
        >>> from src.core.anonymizers import create_panos_tracer
        >>> tracer = create_panos_tracer()
        >>> # Use tracer with LangGraph checkpointer or LLM calls
    """
    settings = get_settings()

    # Create anonymizer with PAN-OS patterns
    anonymizer = get_panos_anonymizer()

    # Create LangSmith client with anonymizer
    client = Client(
        api_key=settings.langsmith_api_key,
        api_url=settings.langsmith_endpoint,
        anonymizer=anonymizer,
    )

    # Create and return LangChainTracer with client
    tracer = LangChainTracer(client=client)

    return tracer
