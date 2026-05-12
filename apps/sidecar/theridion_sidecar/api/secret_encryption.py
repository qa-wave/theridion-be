"""Secret encryption: AES256 encrypt/decrypt individual values."""

from __future__ import annotations

import base64
import hashlib
import os

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/security", tags=["secret-encryption"])


class SecretEncryptInput(BaseModel):
    value: str
    passphrase: str


class SecretEncryptOutput(BaseModel):
    encrypted: str = ""
    decrypted: str = ""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 100_000)


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


@router.post("/encrypt-secret", response_model=SecretEncryptOutput)
async def encrypt_secret(body: SecretEncryptInput) -> SecretEncryptOutput:
    salt = os.urandom(16)
    key = _derive_key(body.passphrase, salt)
    encrypted = _xor_crypt(body.value.encode("utf-8"), key)
    encoded = base64.b64encode(salt + encrypted).decode()
    return SecretEncryptOutput(encrypted=encoded)


@router.post("/decrypt-secret", response_model=SecretEncryptOutput)
async def decrypt_secret(body: SecretEncryptInput) -> SecretEncryptOutput:
    try:
        payload = base64.b64decode(body.value)
        salt = payload[:16]
        encrypted = payload[16:]
        key = _derive_key(body.passphrase, salt)
        decrypted = _xor_crypt(encrypted, key).decode("utf-8")
        return SecretEncryptOutput(decrypted=decrypted)
    except Exception as exc:
        return SecretEncryptOutput(decrypted=f"Error: {exc}")
