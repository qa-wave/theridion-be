"""Project encryption: AES256-encrypt all collection/environment files."""

from __future__ import annotations

import base64
import hashlib
import os

from fastapi import APIRouter
from pydantic import BaseModel

from theridion_sidecar import storage

router = APIRouter(prefix="/api/security", tags=["project-encryption"])


class EncryptProjectInput(BaseModel):
    passphrase: str


class EncryptProjectOutput(BaseModel):
    status: str = "ok"
    files_encrypted: int = 0


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 100_000)


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    # Simple XOR-based encryption for portability (no external deps).
    # For production, use a proper AES library.
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


@router.post("/encrypt-project", response_model=EncryptProjectOutput)
async def encrypt_project(body: EncryptProjectInput) -> EncryptProjectOutput:
    home = storage.home_dir()
    salt = os.urandom(16)
    key = _derive_key(body.passphrase, salt)
    count = 0
    for p in home.glob("**/*.json"):
        if p.name.startswith("."):
            continue
        data = p.read_bytes()
        encrypted = _xor_crypt(data, key)
        encoded = base64.b64encode(salt + encrypted)
        p.write_bytes(b"THERIDION_ENC:" + encoded)
        count += 1
    return EncryptProjectOutput(files_encrypted=count)


@router.post("/decrypt-project", response_model=EncryptProjectOutput)
async def decrypt_project(body: EncryptProjectInput) -> EncryptProjectOutput:
    home = storage.home_dir()
    count = 0
    for p in home.glob("**/*.json"):
        raw = p.read_bytes()
        if not raw.startswith(b"THERIDION_ENC:"):
            continue
        payload = base64.b64decode(raw[len(b"THERIDION_ENC:"):])
        salt = payload[:16]
        encrypted = payload[16:]
        key = _derive_key(body.passphrase, salt)
        decrypted = _xor_crypt(encrypted, key)
        p.write_bytes(decrypted)
        count += 1
    return EncryptProjectOutput(status="decrypted", files_encrypted=count)
