"""Shared pytest fixtures for all test suites."""
import pytest

try:
    from cryptography.fernet import Fernet

    @pytest.fixture
    def fernet_key() -> str:
        return Fernet.generate_key().decode()

except ImportError:
    # cryptography not installed; skip fernet fixtures gracefully
    @pytest.fixture
    def fernet_key() -> str:
        pytest.skip("cryptography package not installed")
        return ""
