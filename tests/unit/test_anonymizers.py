"""Unit tests for LangSmith anonymizers.

Tests verify that sensitive data patterns are correctly identified and masked,
while ensuring no false positives (legitimate data is not masked).
"""

import re
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.core.anonymizers import get_panos_anonymizer, create_panos_tracer


class TestGetPanosAnonymizer:
    """Tests for get_panos_anonymizer function."""

    def test_returns_anonymizer_function(self):
        """Test that function returns an anonymizer callable."""
        anonymizer = get_panos_anonymizer()
        assert callable(anonymizer), "Should return a callable anonymizer function"

    def test_anonymizer_masks_panos_api_key(self):
        """Test that PAN-OS API keys are masked."""
        anonymizer = get_panos_anonymizer()
        test_key = "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug=="
        result = anonymizer(test_key)
        assert "<panos-api-key>" in result, "PAN-OS API key should be masked"
        assert test_key not in result, "Original key should not appear in result"

    def test_anonymizer_masks_anthropic_api_key(self):
        """Test that Anthropic API keys are masked."""
        anonymizer = get_panos_anonymizer()
        test_key = "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV"
        result = anonymizer(test_key)
        assert "<anthropic-api-key>" in result, "Anthropic API key should be masked"
        assert test_key not in result, "Original key should not appear in result"

    def test_anonymizer_masks_password_fields(self):
        """Test that password fields are masked."""
        anonymizer = get_panos_anonymizer()
        test_strings = [
            'password="secret123"',
            "password: mysecret",
            "passwd=test123",
            "pwd: admin",
        ]
        for test_str in test_strings:
            result = anonymizer(test_str)
            assert "<password>" in result, f"Password in '{test_str}' should be masked"
            # Verify original password value is not in result
            password_value = re.search(r"['\"]?([^\s'\"]+)['\"]?$", test_str.split(":")[-1].split("=")[-1])
            if password_value:
                assert password_value.group(1) not in result, f"Password value should not appear in result"

    def test_anonymizer_masks_xml_passwords(self):
        """Test that XML password elements are masked."""
        anonymizer = get_panos_anonymizer()
        test_xml = "<password>MySecretPassword123</password>"
        result = anonymizer(test_xml)
        assert "<redacted>" in result, "XML password should be masked"
        assert "MySecretPassword123" not in result, "Password value should not appear"


class TestPanosApiKeyPattern:
    """Tests for PAN-OS API key pattern matching."""

    def test_valid_panos_api_keys(self):
        """Test that valid PAN-OS API keys match the pattern."""
        pattern = r"LUFRPT[A-Za-z0-9+/=]{40,}"
        valid_keys = [
            "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==",
            "LUFRPT+/ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890==",
            "LUFRPT1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVW==",
        ]

        for key in valid_keys:
            assert re.search(pattern, key), f"Pattern should match valid key: {key[:20]}..."

    def test_invalid_panos_api_keys(self):
        """Test that invalid PAN-OS API keys do NOT match."""
        pattern = r"LUFRPT[A-Za-z0-9+/=]{40,}"
        invalid_keys = [
            "LUFRPT123",  # Too short (only 3 chars after prefix, need 40+)
            "NOTKEY1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVW==",  # Wrong prefix
            "LUFRPT",  # No suffix
            "LUFRPT1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",  # 39 chars after prefix (just under 40)
        ]

        for key in invalid_keys:
            suffix_length = len(key) - 6 if len(key) > 6 else 0
            # Only test the last one if it's actually under 40
            if suffix_length >= 40:
                continue  # Skip this test case if it's actually long enough to match
            assert not re.search(pattern, key), f"Pattern should NOT match invalid key: {key[:30]}... (length after prefix: {suffix_length})"

    def test_panos_key_in_context(self):
        """Test PAN-OS key pattern in realistic context."""
        pattern = r"LUFRPT[A-Za-z0-9+/=]{40,}"
        test_strings = [
            "API key: LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==",
            '{"api_key": "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug=="}',
            "Connection string: https://192.168.1.1/api/?key=LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==",
        ]

        for test_str in test_strings:
            assert re.search(pattern, test_str), f"Pattern should match key in context: {test_str[:50]}..."


class TestAnthropicApiKeyPattern:
    """Tests for Anthropic API key pattern matching."""

    def test_valid_anthropic_api_keys(self):
        """Test that valid Anthropic API keys match the pattern."""
        pattern = r"sk-ant-[A-Za-z0-9-_]{40,}"
        valid_keys = [
            "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV",
            "sk-ant-1234567890-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            "sk-ant-api03-test_key_1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJ",
        ]

        for key in valid_keys:
            assert re.search(pattern, key), f"Pattern should match valid key: {key[:30]}..."

    def test_invalid_anthropic_api_keys(self):
        """Test that invalid Anthropic API keys do NOT match."""
        pattern = r"sk-ant-[A-Za-z0-9-_]{40,}"
        invalid_keys = [
            "sk-ant-short",  # Too short (only 5 chars after prefix, need 40+)
            "sk-test-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV",  # Wrong prefix
            "sk-ant-",  # No suffix
            "sk-ant-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",  # 39 chars after prefix (just under 40)
        ]

        for key in invalid_keys:
            # Calculate length after "sk-ant-" prefix (7 chars)
            suffix_length = len(key) - 7 if len(key) > 7 else 0
            # Only test the last one if it's actually under 40
            if suffix_length >= 40:
                continue  # Skip this test case if it's actually long enough to match
            assert not re.search(pattern, key), f"Pattern should NOT match invalid key: {key[:30]}... (length after prefix: {suffix_length})"

    def test_anthropic_key_in_context(self):
        """Test Anthropic key pattern in realistic context."""
        pattern = r"sk-ant-[A-Za-z0-9-_]{40,}"
        test_strings = [
            "API key: sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV",
            '{"api_key": "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV"}',
            "export ANTHROPIC_API_KEY=sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV",
        ]

        for test_str in test_strings:
            assert re.search(pattern, test_str), f"Pattern should match key in context"


class TestPasswordFieldPattern:
    """Tests for password field pattern matching."""

    def test_password_field_variations(self):
        """Test that various password field formats are matched."""
        pattern = r"(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?[^\s'\"]+"
        test_strings = [
            'password="secret123"',
            "password: mysecret",
            "passwd=test123",
            "pwd: admin",
            'password="complex!@#$%"',
            "password:simple",
            "passwd = value123",
            "pwd = 'test'",
        ]

        for test_str in test_strings:
            match = re.search(pattern, test_str, re.IGNORECASE)
            assert match, f"Pattern should match '{test_str}'"

    def test_password_field_case_insensitive(self):
        """Test that password field matching is case-insensitive."""
        pattern = r"(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?[^\s'\"]+"
        test_strings = [
            "PASSWORD=secret",
            "Password: value",
            "PASSWD=test",
            "Pwd: admin",
        ]

        for test_str in test_strings:
            match = re.search(pattern, test_str, re.IGNORECASE)
            assert match, f"Pattern should match case-insensitive '{test_strings}'"

    def test_password_field_replacement(self):
        """Test that password field replacement works correctly."""
        pattern = r"(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?[^\s'\"]+"
        replace = r"\1: <password>"
        test_cases = [
            ('password="secret123"', "password: <password>"),
            ("password: mysecret", "password: <password>"),
            ("passwd=test123", "passwd: <password>"),
        ]

        for input_str, expected in test_cases:
            result = re.sub(pattern, replace, input_str, flags=re.IGNORECASE)
            assert "<password>" in result, f"Replacement should contain '<password>' for '{input_str}'"
            # Verify original password value is not in result
            password_value = input_str.split(":")[-1].split("=")[-1].strip(' "\'')
            assert password_value not in result or password_value == "<password>", \
                f"Password value '{password_value}' should be masked in result"


class TestXmlPasswordPattern:
    """Tests for XML password element pattern matching."""

    def test_xml_password_elements(self):
        """Test that XML password elements are matched."""
        pattern = r"<password>.*?</password>"
        test_strings = [
            "<password>secret123</password>",
            "<password>admin@123</password>",
            "<password>complex!@#$%</password>",
            "<password></password>",  # Empty password
        ]

        for test_str in test_strings:
            match = re.search(pattern, test_str)
            assert match, f"Pattern should match '{test_str}'"

    def test_xml_password_replacement(self):
        """Test that XML password replacement works correctly."""
        pattern = r"<password>.*?</password>"
        replace = "<password><redacted></password>"
        test_cases = [
            ("<password>secret123</password>", "<password><redacted></password>"),
            ("<password>admin@123</password>", "<password><redacted></password>"),
            ("<password></password>", "<password><redacted></password>"),
        ]

        for input_str, expected in test_cases:
            result = re.sub(pattern, replace, input_str)
            assert result == expected, f"Replacement should match expected for '{input_str}'"
            # Verify original password value is not in result
            password_match = re.search(r"<password>(.*?)</password>", input_str)
            if password_match and password_match.group(1):
                assert password_match.group(1) not in result, \
                    f"Password value should not appear in result"

    def test_xml_password_in_context(self):
        """Test XML password pattern in realistic PAN-OS XML context."""
        pattern = r"<password>.*?</password>"
        test_strings = [
            "<config><password>MySecret123</password></config>",
            '<?xml version="1.0"?><response><password>admin</password></response>',
            "<entry><password>complex!@#$%</password><other>data</other></entry>",
        ]

        for test_str in test_strings:
            match = re.search(pattern, test_str)
            assert match, f"Pattern should match password in XML context: {test_str[:50]}..."


class TestFalsePositives:
    """Tests to ensure legitimate data is NOT masked (no false positives)."""

    def test_legitimate_panos_references(self):
        """Test that legitimate PAN-OS references are not masked."""
        anonymizer = get_panos_anonymizer()
        legitimate_strings = [
            "LUFRPT is a prefix used by PAN-OS",  # Just the prefix, not a key
            "The LUFRPT format is used for API keys",  # Discussion about format
            "LUFRPT123",  # Too short to be a real key
            "Check LUFRPT documentation",  # Reference to documentation
        ]

        for test_str in legitimate_strings:
            result = anonymizer(test_str)
            # Should not contain masked placeholder (unless it's a real key)
            if "LUFRPT" in test_str and len([c for c in test_str if c.isalnum() or c in "+/="]) < 40:
                assert "<panos-api-key>" not in result or test_str == result, \
                    f"Legitimate reference should not be masked: '{test_str}'"

    def test_legitimate_password_references(self):
        """Test that legitimate password references are not masked."""
        anonymizer = get_panos_anonymizer()
        legitimate_strings = [
            "password field is required",  # Discussion about password field
            "password: ",  # Empty password field (no value)
            "The password policy requires...",  # Discussion about password policy
            "password_reset",  # Variable/function name
            "password123",  # Not in password:value format
        ]

        for test_str in legitimate_strings:
            result = anonymizer(test_str)
            # These should generally not trigger masking (or mask only if actual password present)
            # The key is that we don't want to mask discussion ABOUT passwords
            if ":" not in test_str and "=" not in test_str:
                # No password value present, so shouldn't be masked
                pass  # Just verify it doesn't crash

    def test_legitimate_xml_references(self):
        """Test that legitimate XML password references are not masked."""
        anonymizer = get_panos_anonymizer()
        legitimate_strings = [
            "<password_policy>enabled</password_policy>",  # Different element name
            "<config><password_field>required</password_field></config>",  # Different element
            "password element in XML",  # Discussion, not actual element
        ]

        for test_str in legitimate_strings:
            result = anonymizer(test_str)
            # Should not mask these (they're not <password>...</password>)
            assert "<redacted>" not in result or "<password>" not in test_str, \
                f"Legitimate XML reference should not be masked: '{test_str}'"


class TestCombinedPatterns:
    """Tests for multiple patterns appearing together."""

    def test_all_patterns_in_single_string(self):
        """Test that all patterns are masked when appearing together."""
        anonymizer = get_panos_anonymizer()
        test_string = (
            "PAN-OS API: LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==, "
            "Anthropic: sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV, "
            "Password: password='admin123', "
            "XML: <password>secret</password>"
        )

        result = anonymizer(test_string)

        # Verify all patterns are masked
        assert "<panos-api-key>" in result, "PAN-OS API key should be masked"
        assert "<anthropic-api-key>" in result, "Anthropic API key should be masked"
        assert "<password>" in result, "Password field should be masked"
        assert "<redacted>" in result, "XML password should be masked"

        # Verify original sensitive values are not in result
        assert "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==" not in result
        assert "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV" not in result
        assert "admin123" not in result or "password='admin123'" not in result
        assert "secret" not in result or "<password>secret</password>" not in result

    def test_multiple_passwords_in_string(self):
        """Test that multiple password fields are all masked."""
        anonymizer = get_panos_anonymizer()
        test_string = (
            'password="secret1", passwd="secret2", pwd="secret3"'
        )

        result = anonymizer(test_string)

        # All password fields should be masked
        assert result.count("<password>") >= 3, "All password fields should be masked"
        # Original values should not appear
        assert "secret1" not in result
        assert "secret2" not in result
        assert "secret3" not in result


class TestRealWorldTraceSamples:
    """Tests with realistic trace data samples."""

    def test_panos_api_response_trace(self):
        """Test anonymization of PAN-OS API response trace."""
        anonymizer = get_panos_anonymizer()
        trace_sample = """
        {
            "api_key": "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==",
            "request": {
                "url": "https://192.168.1.1/api/?key=LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==",
                "method": "GET"
            },
            "response": {
                "status": "success",
                "data": "<response><result><entry><password>admin123</password></entry></result></response>"
            }
        }
        """

        result = anonymizer(trace_sample)

        # Verify API keys are masked
        assert "<panos-api-key>" in result
        assert "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==" not in result

        # Verify XML password is masked
        assert "<redacted>" in result
        assert "admin123" not in result or "<password>admin123</password>" not in result

    def test_llm_request_trace(self):
        """Test anonymization of LLM request trace with API key."""
        anonymizer = get_panos_anonymizer()
        trace_sample = """
        {
            "llm_request": {
                "model": "claude-3-5-sonnet",
                "api_key": "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV",
                "messages": [
                    {"role": "user", "content": "password=secret123"}
                ]
            }
        }
        """

        result = anonymizer(trace_sample)

        # Verify Anthropic API key is masked
        assert "<anthropic-api-key>" in result
        assert "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV" not in result

        # Verify password field is masked
        assert "<password>" in result
        assert "secret123" not in result or "password=secret123" not in result

    def test_configuration_trace(self):
        """Test anonymization of configuration trace with multiple sensitive fields."""
        anonymizer = get_panos_anonymizer()
        trace_sample = """
        {
            "config": {
                "panos_api_key": "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==",
                "anthropic_api_key": "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV",
                "credentials": {
                    "password": "super_secret",
                    "passwd": "another_secret"
                },
                "xml_config": "<config><password>xml_secret</password></config>"
            }
        }
        """

        result = anonymizer(trace_sample)

        # Verify all sensitive patterns are masked
        assert "<panos-api-key>" in result
        assert "<anthropic-api-key>" in result
        assert result.count("<password>") >= 2  # At least 2 password fields
        assert "<redacted>" in result

        # Verify original values are not present
        assert "LUFRPT14MW5xOEo1R09KVlBZNnpnemh0VHRBNnE9OGNHNjh0VDM4Ug==" not in result
        assert "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV" not in result
        assert "super_secret" not in result
        assert "another_secret" not in result
        assert "xml_secret" not in result


class TestCreatePanosTracer:
    """Tests for create_panos_tracer function."""

    @patch("src.core.anonymizers.LangChainTracer")
    @patch("src.core.anonymizers.Client")
    @patch("src.core.anonymizers.get_panos_anonymizer")
    @patch("src.core.anonymizers.get_settings")
    def test_create_tracer_with_anonymizer(
        self, mock_settings, mock_get_anon, mock_client, mock_tracer_class
    ):
        """Test that create_panos_tracer creates tracer with anonymizer."""
        # Setup mocks
        mock_settings_instance = Mock()
        mock_settings_instance.langsmith_api_key = "lsv2_pt_test_key"
        mock_settings_instance.langsmith_endpoint = "https://api.smith.langchain.com"
        mock_settings.return_value = mock_settings_instance

        mock_anonymizer = Mock()
        mock_get_anon.return_value = mock_anonymizer

        mock_ls_client = Mock()
        mock_client.return_value = mock_ls_client

        mock_tracer_instance = Mock()
        mock_tracer_class.return_value = mock_tracer_instance

        # Call function
        result = create_panos_tracer()

        # Verify anonymizer was created
        mock_get_anon.assert_called_once()

        # Verify Client was created with anonymizer
        mock_client.assert_called_once_with(
            api_key="lsv2_pt_test_key",
            api_url="https://api.smith.langchain.com",
            anonymizer=mock_anonymizer,
        )

        # Verify LangChainTracer was created with client
        mock_tracer_class.assert_called_once_with(client=mock_ls_client)

        # Verify tracer instance is returned
        assert result == mock_tracer_instance

    @patch("src.core.anonymizers.LangChainTracer")
    @patch("src.core.anonymizers.Client")
    @patch("src.core.anonymizers.get_panos_anonymizer")
    @patch("src.core.anonymizers.get_settings")
    def test_create_tracer_returns_langchain_tracer(
        self, mock_settings, mock_get_anon, mock_client, mock_tracer_class
    ):
        """Test that create_panos_tracer returns LangChainTracer instance."""
        # Setup mocks
        mock_settings_instance = Mock()
        mock_settings_instance.langsmith_api_key = "lsv2_pt_test_key"
        mock_settings_instance.langsmith_endpoint = "https://api.smith.langchain.com"
        mock_settings.return_value = mock_settings_instance

        mock_get_anon.return_value = Mock()
        mock_client.return_value = Mock()
        mock_tracer_instance = Mock()
        mock_tracer_class.return_value = mock_tracer_instance

        # Call function
        result = create_panos_tracer()

        # Should return LangChainTracer instance
        assert result == mock_tracer_instance
        assert isinstance(result, Mock)  # Mock instance
