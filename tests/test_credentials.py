import pytest
from aegiscode.credentials import EncryptedCredentialStore

def test_encrypted_credential_status_does_not_expose_secret(tmp_path):
    store = EncryptedCredentialStore(tmp_path / "cred.json")
    store.set("openai", "sk-secret", "pw")
    assert store.status() == {"openai": True}
    assert "sk-secret" not in (tmp_path / "cred.json").read_text()
    assert store.get("openai", "pw") == "sk-secret"
    with pytest.raises(ValueError):
        store.get("openai", "wrong")
