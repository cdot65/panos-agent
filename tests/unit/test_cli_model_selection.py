"""Unit tests for CLI model and temperature selection."""

import pytest
from typer.testing import CliRunner
from unittest.mock import Mock, patch

from src.cli.commands import app, resolve_model_name, MODEL_ALIASES


runner = CliRunner()


class TestModelAliases:
    """Tests for MODEL_ALIASES constant."""

    def test_model_aliases_defined(self):
        """Test that MODEL_ALIASES dictionary is defined."""
        assert MODEL_ALIASES is not None
        assert isinstance(MODEL_ALIASES, dict)

    def test_model_aliases_has_sonnet(self):
        """Test that sonnet alias is defined."""
        assert "sonnet" in MODEL_ALIASES
        assert MODEL_ALIASES["sonnet"] == "claude-sonnet-4-5-20250915"

    def test_model_aliases_has_opus(self):
        """Test that opus alias is defined."""
        assert "opus" in MODEL_ALIASES
        assert MODEL_ALIASES["opus"] == "claude-opus-4-1-20250805"

    def test_model_aliases_has_haiku(self):
        """Test that haiku alias is defined."""
        assert "haiku" in MODEL_ALIASES
        assert MODEL_ALIASES["haiku"] == "claude-haiku-4-5-20251010"

    def test_all_model_aliases_are_strings(self):
        """Test that all model aliases map to strings."""
        for alias, model_name in MODEL_ALIASES.items():
            assert isinstance(alias, str)
            assert isinstance(model_name, str)


class TestResolveModelName:
    """Tests for resolve_model_name function."""

    def test_resolve_sonnet_alias(self):
        """Test resolving 'sonnet' alias."""
        result = resolve_model_name("sonnet")
        assert result == "claude-sonnet-4-5-20250915"

    def test_resolve_opus_alias(self):
        """Test resolving 'opus' alias."""
        result = resolve_model_name("opus")
        assert result == "claude-opus-4-1-20250805"

    def test_resolve_haiku_alias(self):
        """Test resolving 'haiku' alias."""
        result = resolve_model_name("haiku")
        assert result == "claude-haiku-4-5-20251010"

    def test_resolve_case_insensitive_uppercase(self):
        """Test that alias resolution is case-insensitive (uppercase)."""
        assert resolve_model_name("SONNET") == "claude-sonnet-4-5-20250915"
        assert resolve_model_name("OPUS") == "claude-opus-4-1-20250805"
        assert resolve_model_name("HAIKU") == "claude-haiku-4-5-20251010"

    def test_resolve_case_insensitive_mixed(self):
        """Test that alias resolution is case-insensitive (mixed case)."""
        assert resolve_model_name("Sonnet") == "claude-sonnet-4-5-20250915"
        assert resolve_model_name("OpUs") == "claude-opus-4-1-20250805"
        assert resolve_model_name("HaiKU") == "claude-haiku-4-5-20251010"

    def test_resolve_full_model_name_passthrough(self):
        """Test that full model names pass through unchanged."""
        full_name = "claude-sonnet-4-5-20250915"
        result = resolve_model_name(full_name)
        assert result == full_name

    def test_resolve_unknown_alias_passthrough(self):
        """Test that unknown aliases pass through unchanged."""
        unknown = "claude-future-model-xyz"
        result = resolve_model_name(unknown)
        assert result == unknown

    def test_resolve_empty_string(self):
        """Test resolving empty string returns empty string."""
        result = resolve_model_name("")
        assert result == ""


class TestCLIModelFlag:
    """Tests for --model CLI flag."""

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_model_flag_default_is_sonnet(self, mock_get_settings, mock_create_graph):
        """Test that default model is sonnet when --model not provided."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run without --model flag
        result = runner.invoke(app, ["run", "-p", "test", "-m", "autonomous", "--no-stream"])

        # Verify default model was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["model_name"] == "claude-sonnet-4-5-20250915"

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_model_flag_haiku(self, mock_get_settings, mock_create_graph):
        """Test --model haiku sets Haiku model."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --model haiku
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--model", "haiku", "--no-stream"
        ])

        # Verify Haiku model was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["model_name"] == "claude-haiku-4-5-20251010"

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_model_flag_opus(self, mock_get_settings, mock_create_graph):
        """Test --model opus sets Opus model."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --model opus
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--model", "opus", "--no-stream"
        ])

        # Verify Opus model was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["model_name"] == "claude-opus-4-1-20250805"

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_model_flag_full_model_name(self, mock_get_settings, mock_create_graph):
        """Test --model with full model name."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with full model name
        full_model = "claude-3-5-sonnet-20241022"
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--model", full_model, "--no-stream"
        ])

        # Verify full model name was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["model_name"] == full_model

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_model_displayed_in_output(self, mock_get_settings, mock_create_graph):
        """Test that selected model is displayed in CLI output."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --model haiku
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--model", "haiku", "--no-stream"
        ])

        # Verify model is shown in output
        assert result.exit_code == 0
        assert "claude-haiku-4-5" in result.stdout or "haiku" in result.stdout.lower()


class TestCLITemperatureFlag:
    """Tests for --temperature CLI flag."""

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_temperature_default_is_zero(self, mock_get_settings, mock_create_graph):
        """Test that default temperature is 0.0 when --temperature not provided."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run without --temperature flag
        result = runner.invoke(app, ["run", "-p", "test", "-m", "autonomous", "--no-stream"])

        # Verify default temperature was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["temperature"] == 0.0

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_temperature_custom_value(self, mock_get_settings, mock_create_graph):
        """Test --temperature with custom value."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --temperature 0.7
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--temperature", "0.7", "--no-stream"
        ])

        # Verify custom temperature was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["temperature"] == 0.7

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_temperature_zero(self, mock_get_settings, mock_create_graph):
        """Test --temperature 0.0 (deterministic)."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --temperature 0.0
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--temperature", "0.0", "--no-stream"
        ])

        # Verify temperature 0.0 was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["temperature"] == 0.0

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_temperature_one(self, mock_get_settings, mock_create_graph):
        """Test --temperature 1.0 (creative)."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --temperature 1.0
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--temperature", "1.0", "--no-stream"
        ])

        # Verify temperature 1.0 was used
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["temperature"] == 1.0

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_temperature_displayed_in_output(self, mock_get_settings, mock_create_graph):
        """Test that temperature is displayed in CLI output."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --temperature 0.5
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--temperature", "0.5", "--no-stream"
        ])

        # Verify temperature is shown in output
        assert result.exit_code == 0
        assert "0.5" in result.stdout or "temp" in result.stdout.lower()


class TestCLIModelAndTemperatureCombined:
    """Tests for combined --model and --temperature flags."""

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_haiku_with_zero_temperature(self, mock_get_settings, mock_create_graph):
        """Test Haiku model with temperature 0.0 for fast deterministic operations."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with both flags
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--model", "haiku", "--temperature", "0.0", "--no-stream"
        ])

        # Verify both settings were applied
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["model_name"] == "claude-haiku-4-5-20251010"
        assert call_kwargs["context"]["temperature"] == 0.0

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_opus_with_creative_temperature(self, mock_get_settings, mock_create_graph):
        """Test Opus model with higher temperature for creative tasks."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with both flags
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--model", "opus", "--temperature", "0.7", "--no-stream"
        ])

        # Verify both settings were applied
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert call_kwargs["context"]["model_name"] == "claude-opus-4-1-20250805"
        assert call_kwargs["context"]["temperature"] == 0.7


class TestCLIMetadataTracking:
    """Tests for model/temperature in metadata."""

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_model_name_in_metadata(self, mock_get_settings, mock_create_graph):
        """Test that model_name is included in metadata for observability."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --model haiku
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--model", "haiku", "--no-stream"
        ])

        # Verify model_name in metadata
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert "metadata" in call_kwargs["config"]
        assert "model_name" in call_kwargs["config"]["metadata"]
        assert call_kwargs["config"]["metadata"]["model_name"] == "claude-haiku-4-5-20251010"

    @patch("src.autonomous_graph.create_autonomous_graph")
    @patch("src.core.config.get_settings")
    def test_temperature_in_metadata(self, mock_get_settings, mock_create_graph):
        """Test that temperature is included in metadata for observability."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.panos_hostname = "192.168.1.1"
        mock_get_settings.return_value = mock_settings

        mock_graph = Mock()
        mock_response = Mock()
        mock_response.content = "Done"
        mock_graph.invoke.return_value = {"messages": [mock_response]}
        mock_create_graph.return_value = mock_graph

        # Run with --temperature 0.7
        result = runner.invoke(app, [
            "run", "-p", "test", "-m", "autonomous",
            "--temperature", "0.7", "--no-stream"
        ])

        # Verify temperature in metadata
        assert result.exit_code == 0
        call_kwargs = mock_graph.invoke.call_args[1]
        assert "metadata" in call_kwargs["config"]
        assert "temperature" in call_kwargs["config"]["metadata"]
        assert call_kwargs["config"]["metadata"]["temperature"] == 0.7

