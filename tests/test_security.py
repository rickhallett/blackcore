"""Unit tests for security components."""

import pytest
from unittest.mock import Mock, patch
import json

from blackcore.security.secrets_manager import SecretsManager
from blackcore.security.validators import (
    URLValidator,
    validate_email,
    validate_url,
    InputSanitizer,
)
from blackcore.security.audit import AuditLogger


class TestSecretsManager:
    """Test secrets management functionality."""

    def test_initialization(self):
        """Test SecretsManager initialization."""
        manager = SecretsManager(provider="env")
        assert manager.provider == "env"
        assert manager._key_cache == {}

    @patch.dict("os.environ", {"NOTION_API_KEY": "test-secret-key"})
    def test_get_secret_from_env(self):
        """Test getting secret from environment."""
        manager = SecretsManager(provider="env")

        secret = manager.get_secret("notion_api_key")
        assert secret == "test-secret-key"

    def test_get_secret_not_found(self):
        """Test error when secret not found."""
        manager = SecretsManager(provider="env")

        with pytest.raises(KeyError) as exc_info:
            manager.get_secret("non_existent_key")

        assert "not found in environment" in str(exc_info.value)

    def test_secret_caching(self):
        """Test that secrets are cached after retrieval."""
        with patch.dict("os.environ", {"TEST_KEY": "cached-value"}):
            manager = SecretsManager(provider="env")

            # First retrieval
            secret1 = manager.get_secret("test_key")
            assert secret1 == "cached-value"
            assert "test_key" in manager._key_cache

            # Second retrieval should use cache
            with patch.dict("os.environ", {"TEST_KEY": "new-value"}):
                secret2 = manager.get_secret("test_key")
                assert secret2 == "cached-value"  # Still cached value

    @patch(
        "blackcore.security.secrets_manager.SecretsManager._get_or_create_encryption_key"
    )
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("os.chmod")
    def test_store_secret_local(
        self, mock_chmod, mock_exists, mock_mkdir, mock_get_key
    ):
        """Test storing secret locally with encryption."""
        # Mock the encryption key - must be a valid Fernet key
        from cryptography.fernet import Fernet

        mock_get_key.return_value = Fernet.generate_key()
        mock_exists.return_value = False  # No existing secrets file

        manager = SecretsManager(provider="env")

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            manager.store_secret("test_key", "test_value")

            # Verify file was written with encryption
            mock_open.assert_called()
            mock_mkdir.assert_called()
            mock_chmod.assert_called()

    def test_rotate_secret(self):
        """Test secret rotation."""
        manager = SecretsManager(provider="env")
        manager._key_cache["test_key"] = {"value": "old_value", "timestamp": None}

        with patch.object(manager, "store_secret") as mock_store:
            # Mock the audit logger since it's created conditionally
            from blackcore.security.audit import AuditLogger

            with patch.object(AuditLogger, "log_secret_rotation") as mock_log:
                manager.rotate_secret("test_key", "new_value")

                # Verify rotation actions
                mock_store.assert_called_once_with("test_key", "new_value")
                mock_log.assert_called_once()
                assert "test_key" not in manager._key_cache


class TestURLValidator:
    """Test URL validation and SSRF prevention."""

    def test_valid_https_url(self):
        """Test validation of valid HTTPS URL."""
        validator = URLValidator()
        assert validator.validate_url("https://api.notion.com/v1/pages")

    def test_reject_http_url(self):
        """Test rejection of non-HTTPS URLs."""
        validator = URLValidator()

        with pytest.raises(ValueError) as exc_info:
            validator.validate_url("http://example.com")

        assert "Only HTTPS URLs are allowed" in str(exc_info.value)

    def test_reject_private_ips(self):
        """Test rejection of private IP addresses."""
        validator = URLValidator()

        private_urls = [
            "https://192.168.1.1/admin",
            "https://10.0.0.1/internal",
            "https://172.16.0.1/private",
            "https://127.0.0.1/localhost",
        ]

        for url in private_urls:
            with pytest.raises(ValueError) as exc_info:
                validator.validate_url(url)
            assert "blocked network" in str(exc_info.value)

    def test_reject_cloud_metadata_endpoints(self):
        """Test rejection of cloud metadata endpoints."""
        validator = URLValidator()

        metadata_urls = [
            "https://169.254.169.254/latest/meta-data",
            "https://metadata.google.internal/",
            "https://metadata.azure.com/",
        ]

        for url in metadata_urls:
            with pytest.raises(ValueError) as exc_info:
                validator.validate_url(url)
            assert "blocked" in str(exc_info.value)

    def test_allowed_domains_whitelist(self):
        """Test domain allowlist functionality."""
        validator = URLValidator(allowed_domains=["api.notion.com", "notion.so"])

        # Should allow
        assert validator.validate_url("https://api.notion.com/v1/pages")
        assert validator.validate_url("https://notion.so/workspace")

        # Should reject
        with pytest.raises(ValueError) as exc_info:
            validator.validate_url("https://example.com/page")
        assert "not in allowed list" in str(exc_info.value)

    def test_reject_suspicious_patterns(self):
        """Test rejection of suspicious URL patterns."""
        validator = URLValidator()

        suspicious_urls = [
            "https://example.com@attacker.com",  # Username in URL
            "https://example.com/../../../etc/passwd",  # Directory traversal
            "https://example.com/page%00.html",  # Null byte
            "https://example.com/<script>alert(1)</script>",  # XSS attempt
        ]

        for url in suspicious_urls:
            with pytest.raises(ValueError) as exc_info:
                validator.validate_url(url)
            assert "Suspicious pattern" in str(exc_info.value)


class TestInputValidation:
    """Test input validation functions."""

    def test_email_validation_valid(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.user@company.co.uk",
            "name+tag@domain.com",
            "user123@subdomain.example.com",
        ]

        for email in valid_emails:
            assert validate_email(email) is True

    def test_email_validation_invalid(self):
        """Test rejection of invalid email addresses."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user..name@example.com",
            ".user@example.com",
            "user@.example.com",
            "",
            "a" * 255 + "@example.com",  # Too long
        ]

        for email in invalid_emails:
            assert validate_email(email) is False

    def test_url_validation(self):
        """Test basic URL validation."""
        # Valid URLs
        assert validate_url("https://example.com") is True
        assert validate_url("https://api.example.com/v1/endpoint") is True
        assert validate_url("https://example.com:8080/path") is True

        # Invalid URLs
        assert validate_url("http://example.com") is False  # Not HTTPS
        assert validate_url("ftp://example.com") is False
        assert validate_url("not-a-url") is False
        assert validate_url("") is False
        assert validate_url("a" * 2049) is False  # Too long

    def test_input_sanitizer(self):
        """Test input sanitization."""
        # Test HTML escaping
        assert (
            InputSanitizer.sanitize_text("<script>alert(1)</script>")
            == "&lt;script&gt;alert(1)&lt;/script&gt;"
        )

        # Test null byte removal
        assert InputSanitizer.sanitize_text("test\x00data") == "testdata"

        # Test control character removal
        assert InputSanitizer.sanitize_text("test\x01\x02data") == "testdata"

        # Test length limiting
        long_text = "a" * 3000
        sanitized = InputSanitizer.sanitize_text(long_text, max_length=100)
        assert len(sanitized) == 100

    def test_filename_sanitizer(self):
        """Test filename sanitization."""
        # Test path traversal prevention
        assert InputSanitizer.sanitize_filename("../../../etc/passwd") == "etcpasswd"

        # Test special character removal
        assert InputSanitizer.sanitize_filename("file<name>.txt") == "filename.txt"

        # Test hidden file prevention
        assert InputSanitizer.sanitize_filename(".hidden") == "hidden"

        # Test length limiting
        long_name = "a" * 300 + ".txt"
        sanitized = InputSanitizer.sanitize_filename(long_name)
        assert len(sanitized) <= 210  # 200 + extension


class TestAuditLogger:
    """Test audit logging functionality."""

    def test_initialization(self):
        """Test AuditLogger initialization."""
        logger = AuditLogger()
        assert logger.log_file.name == "audit.log"
        assert hasattr(logger, "_context")

    def test_audit_context_manager(self):
        """Test audit context management."""
        logger = AuditLogger()

        # Test context setting
        with logger.audit_context(user_id="123", session_id="abc"):
            # Context should be set
            assert logger._context.user_id == "123"
            assert logger._context.session_id == "abc"

        # Context should be cleared after exit
        assert not hasattr(logger._context, "user_id")
        assert not hasattr(logger._context, "session_id")

    @patch("blackcore.security.audit.structlog.get_logger")
    def test_log_api_call(self, mock_get_logger):
        """Test API call logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        logger = AuditLogger()

        logger.log_api_call(
            method="GET",
            endpoint="/v1/pages/123",
            parameters={"filter": "test"},
            response_status=200,
            duration_ms=150.5,
        )

        # Verify log was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "api_call"
        assert "method" in call_args[1]
        assert call_args[1]["success"] is True

    def test_sensitive_data_sanitization(self):
        """Test that sensitive data is sanitized in logs."""
        logger = AuditLogger()

        # Test sanitization
        event_dict = {
            "user_id": "123",
            "api_key": "sk-secret-key-12345",
            "password": "mysecretpassword",
            "normal_field": "normal_value",
            "notion_api_key": "secret-notion-key",
        }

        sanitized = logger._sanitize_sensitive_data(None, None, event_dict.copy())

        # Sensitive fields should be redacted
        assert sanitized["api_key"] == "sk-s...2345"
        assert sanitized["password"] == "myse...word"
        assert sanitized["notion_api_key"] == "secr...-key"
        assert sanitized["normal_field"] == "normal_value"

    @patch("blackcore.security.audit.structlog.get_logger")
    def test_log_security_event(self, mock_get_logger):
        """Test security event logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        logger = AuditLogger()

        # Test different severity levels
        logger.log_security_event(
            event_type="unauthorized_access",
            severity="critical",
            description="Unauthorized access attempt",
            details={"ip": "192.168.1.1"},
        )

        mock_logger.critical.assert_called_once()

        logger.log_security_event(
            event_type="suspicious_activity",
            severity="warning",
            description="Suspicious activity detected",
        )

        mock_logger.warning.assert_called_once()

    def test_get_audit_trail(self):
        """Test audit trail retrieval."""
        from datetime import datetime, timedelta

        logger = AuditLogger()

        # Test with mock data - use fixed timestamps
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        start_date = base_time - timedelta(hours=1)
        end_date = base_time + timedelta(hours=1)

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", create=True) as mock_open:
                # Mock log entries
                log_entries = [
                    json.dumps(
                        {
                            "audit_timestamp": base_time.isoformat(),  # Should be included
                            "event_type": "api_call",
                            "user_id": "123",
                        }
                    ),
                    json.dumps(
                        {
                            "audit_timestamp": (
                                base_time - timedelta(hours=2)
                            ).isoformat(),  # Should be excluded
                            "event_type": "api_call",
                            "user_id": "456",
                        }
                    ),
                ]
                mock_open.return_value.__enter__.return_value.__iter__.return_value = (
                    log_entries
                )

                trail = logger.get_audit_trail(start_date, end_date)

                # Should only include entries within date range
                assert len(trail) == 1
                assert trail[0]["user_id"] == "123"
