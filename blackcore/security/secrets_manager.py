"""Secure secrets management for API keys and sensitive data."""

import os
import json
import base64
from typing import Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv()


class SecretsManager:
    """Manages secure storage and retrieval of secrets."""

    def __init__(self, provider: str = "env"):
        """Initialize secrets manager.

        Args:
            provider: Type of secrets provider ('env', 'aws', 'azure', 'vault')
        """
        self.provider = provider
        self._key_cache: Dict[str, Dict[str, Any]] = {}
        self._encryption_key = self._get_or_create_encryption_key()
        self._key_rotation_interval = timedelta(days=30)

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for local secret storage."""
        key_file = Path.home() / ".blackcore" / "secret.key"
        key_file.parent.mkdir(exist_ok=True, mode=0o700, parents=True)

        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        else:
            # Generate a new key
            password = os.getenv("BLACKCORE_MASTER_KEY", "default-dev-key").encode()
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))

            # Save key securely
            with open(key_file, "wb") as f:
                f.write(key)
            os.chmod(key_file, 0o600)

            return key

    def get_secret(self, key: str, version: str = "latest") -> str:
        """Retrieve a secret value.

        Args:
            key: Secret key name
            version: Version of secret to retrieve

        Returns:
            Decrypted secret value

        Raises:
            KeyError: If secret not found
            ValueError: If decryption fails
        """
        # Check cache first
        if key in self._key_cache:
            cached = self._key_cache[key]
            if not self._should_rotate_key(cached["timestamp"]):
                return cached["value"]

        # Retrieve based on provider
        if self.provider == "env":
            value = self._get_from_env(key)
        elif self.provider == "aws":
            value = self._get_from_aws_secrets_manager(key, version)
        elif self.provider == "azure":
            value = self._get_from_azure_keyvault(key, version)
        elif self.provider == "vault":
            value = self._get_from_hashicorp_vault(key, version)
        else:
            raise ValueError(f"Unknown secrets provider: {self.provider}")

        # Cache the value
        self._key_cache[key] = {"value": value, "timestamp": datetime.utcnow(), "version": version}

        return value

    def _get_from_env(self, key: str) -> str:
        """Get secret from environment variable."""
        env_key = key.upper().replace("/", "_").replace("-", "_")
        value = os.getenv(env_key)

        if not value:
            raise KeyError(f"Secret '{key}' not found in environment")

        return value

    def _get_from_aws_secrets_manager(self, key: str, version: str) -> str:
        """Get secret from AWS Secrets Manager."""
        try:
            import boto3

            client = boto3.client("secretsmanager")

            response = client.get_secret_value(
                SecretId=key, VersionId=version if version != "latest" else None
            )

            if "SecretString" in response:
                return response["SecretString"]
            else:
                # Binary secret
                return base64.b64decode(response["SecretBinary"]).decode()

        except ImportError:
            raise ImportError("boto3 required for AWS Secrets Manager")
        except Exception as e:
            raise KeyError(f"Failed to retrieve secret '{key}' from AWS: {e}")

    def _get_from_azure_keyvault(self, key: str, version: str) -> str:
        """Get secret from Azure Key Vault."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            vault_url = os.getenv("AZURE_KEYVAULT_URL")
            if not vault_url:
                raise ValueError("AZURE_KEYVAULT_URL not set")

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)

            secret = client.get_secret(key, version=version if version != "latest" else None)
            return secret.value

        except ImportError:
            raise ImportError("azure-keyvault-secrets required for Azure Key Vault")
        except Exception as e:
            raise KeyError(f"Failed to retrieve secret '{key}' from Azure: {e}")

    def _get_from_hashicorp_vault(self, key: str, version: str) -> str:
        """Get secret from HashiCorp Vault."""
        try:
            import hvac

            vault_url = os.getenv("VAULT_ADDR", "http://localhost:8200")
            vault_token = os.getenv("VAULT_TOKEN")

            if not vault_token:
                raise ValueError("VAULT_TOKEN not set")

            client = hvac.Client(url=vault_url, token=vault_token)

            # Parse key format: secret/data/path/to/secret
            path_parts = key.split("/")
            mount_point = path_parts[0]
            secret_path = "/".join(path_parts[1:])

            response = client.secrets.kv.v2.read_secret_version(
                path=secret_path,
                mount_point=mount_point,
                version=int(version) if version != "latest" else None,
            )

            return response["data"]["data"]["value"]

        except ImportError:
            raise ImportError("hvac required for HashiCorp Vault")
        except Exception as e:
            raise KeyError(f"Failed to retrieve secret '{key}' from Vault: {e}")

    def store_secret(self, key: str, value: str) -> None:
        """Store a secret securely (local storage only)."""
        if self.provider != "env":
            raise NotImplementedError(f"Secret storage not implemented for {self.provider}")

        # Encrypt the value
        f = Fernet(self._encryption_key)
        encrypted = f.encrypt(value.encode())

        # Store in secure local file
        secrets_file = Path.home() / ".blackcore" / "secrets.enc"
        secrets_file.parent.mkdir(exist_ok=True, mode=0o700)

        # Load existing secrets
        secrets = {}
        if secrets_file.exists():
            with open(secrets_file, "rb") as file:
                try:
                    decrypted = f.decrypt(file.read())
                    secrets = json.loads(decrypted)
                except Exception:
                    pass

        # Update secret
        secrets[key] = {
            "value": base64.b64encode(encrypted).decode(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Save back
        encrypted_data = f.encrypt(json.dumps(secrets).encode())
        with open(secrets_file, "wb") as file:
            file.write(encrypted_data)
        os.chmod(secrets_file, 0o600)

    def _should_rotate_key(self, timestamp: datetime) -> bool:
        """Check if key should be rotated based on age."""
        age = datetime.utcnow() - timestamp
        return age > self._key_rotation_interval

    def rotate_secret(self, key: str, new_value: str) -> None:
        """Rotate a secret to a new value."""
        # Store new value
        self.store_secret(key, new_value)

        # Clear from cache
        if key in self._key_cache:
            del self._key_cache[key]

        # Log rotation (without exposing values)
        if hasattr(self, "audit_logger"):
            self.audit_logger.log_secret_rotation(key)
        else:
            from .audit import AuditLogger

            audit = AuditLogger()
            audit.log_secret_rotation(key)

    def __repr__(self) -> str:
        """Safe string representation without exposing secrets."""
        return f"<SecretsManager provider='{self.provider}' cached_keys={len(self._key_cache)}>"

    def __str__(self) -> str:
        """Safe string representation without exposing secrets."""
        return self.__repr__()
