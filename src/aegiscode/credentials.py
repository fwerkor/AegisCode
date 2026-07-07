from __future__ import annotations
import base64, getpass, json, os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptedCredentialStore:
    """Password-encrypted local credential file fallback."""
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def _fernet(self, password: str, salt: bytes) -> Fernet:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
        return Fernet(base64.urlsafe_b64encode(kdf.derive(password.encode())))
    def _read_raw(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))
    def set(self, name: str, value: str, password: str) -> None:
        salt = os.urandom(16)
        token = self._fernet(password, salt).encrypt(value.encode()).decode()
        data = self._read_raw(); data[name] = {"salt": base64.b64encode(salt).decode(), "token": token}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    def get(self, name: str, password: str) -> str | None:
        data = self._read_raw()
        if name not in data:
            return None
        rec = data[name]
        try:
            return self._fernet(password, base64.b64decode(rec["salt"])).decrypt(rec["token"].encode()).decode()
        except InvalidToken as exc:
            raise ValueError("invalid master password") from exc
    def status(self) -> dict[str, bool]:
        return {name: True for name in self._read_raw()}
    def clear(self, name: str) -> bool:
        data = self._read_raw(); existed = name in data; data.pop(name, None)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return existed

def prompt_secret(prompt: str = "API key: ") -> str:
    return getpass.getpass(prompt)
