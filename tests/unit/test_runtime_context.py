"""Unit tests for runtime context (AgentContext)."""

import pytest
from src.core.config import AgentContext


class TestAgentContextDefaults:
    """Tests for AgentContext default values."""

    def test_default_model_name(self):
        """Test that default model is Claude Sonnet 4.5."""
        ctx = AgentContext()
        assert ctx.model_name == "claude-sonnet-4-5-20250915"

    def test_default_temperature(self):
        """Test that default temperature is 0.0 (deterministic)."""
        ctx = AgentContext()
        assert ctx.temperature == 0.0

    def test_default_max_tokens(self):
        """Test that default max_tokens is 4096."""
        ctx = AgentContext()
        assert ctx.max_tokens == 4096

    def test_default_firewall_client_none(self):
        """Test that default firewall_client is None."""
        ctx = AgentContext()
        assert ctx.firewall_client is None


class TestAgentContextCustomValues:
    """Tests for AgentContext with custom values."""

    def test_custom_model_name(self):
        """Test creating context with custom model name."""
        ctx = AgentContext(model_name="claude-3-opus-20240229")
        assert ctx.model_name == "claude-3-opus-20240229"

    def test_custom_temperature(self):
        """Test creating context with custom temperature."""
        ctx = AgentContext(temperature=0.7)
        assert ctx.temperature == 0.7

    def test_custom_max_tokens(self):
        """Test creating context with custom max_tokens."""
        ctx = AgentContext(max_tokens=8192)
        assert ctx.max_tokens == 8192

    def test_custom_firewall_client(self):
        """Test creating context with custom firewall client."""
        from unittest.mock import Mock

        mock_fw = Mock()
        ctx = AgentContext(firewall_client=mock_fw)
        assert ctx.firewall_client is mock_fw

    def test_all_custom_values(self):
        """Test creating context with all custom values."""
        from unittest.mock import Mock

        mock_fw = Mock()
        ctx = AgentContext(
            model_name="claude-haiku-4-5",
            temperature=0.5,
            max_tokens=2048,
            firewall_client=mock_fw,
        )
        assert ctx.model_name == "claude-haiku-4-5"
        assert ctx.temperature == 0.5
        assert ctx.max_tokens == 2048
        assert ctx.firewall_client is mock_fw


class TestAgentContextModelNames:
    """Tests for different valid model names."""

    def test_sonnet_model(self):
        """Test Sonnet model name."""
        ctx = AgentContext(model_name="claude-3-5-sonnet-20241022")
        assert "sonnet" in ctx.model_name.lower()

    def test_opus_model(self):
        """Test Opus model name."""
        ctx = AgentContext(model_name="claude-3-opus-20240229")
        assert "opus" in ctx.model_name.lower()

    def test_haiku_model(self):
        """Test Haiku model name."""
        ctx = AgentContext(model_name="claude-haiku-4-5")
        assert "haiku" in ctx.model_name.lower()


class TestAgentContextTemperatureRange:
    """Tests for temperature value ranges."""

    def test_temperature_zero(self):
        """Test temperature of 0.0 (deterministic)."""
        ctx = AgentContext(temperature=0.0)
        assert ctx.temperature == 0.0

    def test_temperature_one(self):
        """Test temperature of 1.0 (creative)."""
        ctx = AgentContext(temperature=1.0)
        assert ctx.temperature == 1.0

    def test_temperature_mid_range(self):
        """Test mid-range temperature values."""
        for temp in [0.3, 0.5, 0.7]:
            ctx = AgentContext(temperature=temp)
            assert ctx.temperature == temp

    def test_temperature_precision(self):
        """Test temperature with high precision."""
        ctx = AgentContext(temperature=0.123456789)
        assert ctx.temperature == 0.123456789


class TestAgentContextMaxTokens:
    """Tests for max_tokens values."""

    def test_small_max_tokens(self):
        """Test small max_tokens value."""
        ctx = AgentContext(max_tokens=1024)
        assert ctx.max_tokens == 1024

    def test_large_max_tokens(self):
        """Test large max_tokens value."""
        ctx = AgentContext(max_tokens=16384)
        assert ctx.max_tokens == 16384

    def test_default_max_tokens_reasonable(self):
        """Test that default max_tokens is reasonable for most tasks."""
        ctx = AgentContext()
        assert ctx.max_tokens >= 4096  # Should be at least 4k for complex tasks
        assert ctx.max_tokens <= 16384  # Should not be excessive


class TestAgentContextDataclass:
    """Tests for AgentContext as a dataclass."""

    def test_is_dataclass(self):
        """Test that AgentContext is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(AgentContext)

    def test_dataclass_fields(self):
        """Test that AgentContext has expected fields."""
        from dataclasses import fields

        field_names = {f.name for f in fields(AgentContext)}
        assert "model_name" in field_names
        assert "temperature" in field_names
        assert "max_tokens" in field_names
        assert "firewall_client" in field_names

    def test_dataclass_field_types(self):
        """Test that AgentContext fields have correct types."""
        from dataclasses import fields

        field_types = {f.name: f.type for f in fields(AgentContext)}
        assert field_types["model_name"] == str
        assert field_types["temperature"] == float
        assert field_types["max_tokens"] == int

    def test_dataclass_immutability_not_frozen(self):
        """Test that AgentContext is mutable (not frozen)."""
        ctx = AgentContext()
        # Should be able to modify fields
        ctx.temperature = 0.5
        assert ctx.temperature == 0.5


class TestAgentContextUseCases:
    """Tests for common use cases of AgentContext."""

    def test_haiku_for_speed(self):
        """Test configuration for fast operations with Haiku."""
        ctx = AgentContext(model_name="claude-haiku-4-5", temperature=0.0)
        assert "haiku" in ctx.model_name.lower()
        assert ctx.temperature == 0.0

    def test_opus_for_complexity(self):
        """Test configuration for complex tasks with Opus."""
        ctx = AgentContext(
            model_name="claude-3-opus-20240229", temperature=0.0, max_tokens=8192
        )
        assert "opus" in ctx.model_name.lower()
        assert ctx.max_tokens == 8192

    def test_creative_configuration(self):
        """Test configuration for creative tasks."""
        ctx = AgentContext(temperature=0.7)
        assert ctx.temperature == 0.7

    def test_testing_configuration(self):
        """Test configuration for testing with mock client."""
        from unittest.mock import Mock

        mock_fw = Mock()
        ctx = AgentContext(
            model_name="claude-haiku-4-5",
            temperature=0.0,
            firewall_client=mock_fw,
        )
        assert ctx.firewall_client is not None
        assert ctx.firewall_client is mock_fw

