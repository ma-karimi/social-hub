import pytest

cryptography = pytest.importorskip("cryptography", reason="cryptography not installed")
from cryptography.fernet import Fernet  # noqa: E402

from social_hub.infrastructure.encryption.credential_encryptor import FernetEncryptor  # noqa: E402


@pytest.fixture
def encryptor():
    key = Fernet.generate_key().decode()
    return FernetEncryptor(key)


def test_encrypt_decrypt_roundtrip(encryptor):
    credentials = {"bot_token": "123:abc", "channel_id": "@channel"}
    encrypted = encryptor.encrypt(credentials)
    assert isinstance(encrypted, bytes)
    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == credentials


def test_encrypted_value_differs_each_time(encryptor):
    credentials = {"key": "value"}
    enc1 = encryptor.encrypt(credentials)
    enc2 = encryptor.encrypt(credentials)
    assert enc1 != enc2  # Fernet uses random IV


def test_wrong_key_raises():
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()
    enc1 = FernetEncryptor(key1)
    enc2 = FernetEncryptor(key2)
    encrypted = enc1.encrypt({"a": "b"})
    with pytest.raises(Exception):
        enc2.decrypt(encrypted)
