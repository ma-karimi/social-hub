import json

from cryptography.fernet import Fernet


class FernetEncryptor:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, data: dict) -> bytes:
        return self._fernet.encrypt(json.dumps(data).encode())

    def decrypt(self, data: bytes) -> dict:
        return json.loads(self._fernet.decrypt(data).decode())
