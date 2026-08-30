"""Key material and short fingerprints for display (never send full keys to clients)."""

from __future__ import annotations

import hashlib
import hmac
import os
import struct

# Integer seed chosen so sha256(key).hexdigest() starts with "4ac2" (UI teaching fingerprint).
_TEACHING_SEED = 81048
TEACHING_KEY: bytes = _TEACHING_SEED.to_bytes(32, "big")


def key_fingerprint(key: bytes, *, length: int = 4) -> str:
    """Return a short non-secret fingerprint for UI display."""
    digest = hashlib.sha256(key).hexdigest()
    return digest[:length]


def parse_key_material(raw: str | bytes | int | None) -> bytes:
    """Normalize key input to 32 raw bytes.

    - None → teaching key
    - int → big-endian 32-byte
    - bytes of any length → SHA-256 digest (or passthrough if already 32)
    - str hex → decode; otherwise UTF-8 then SHA-256
    """
    if raw is None:
        return TEACHING_KEY
    if isinstance(raw, int):
        return raw.to_bytes(32, "big", signed=False)
    if isinstance(raw, bytes):
        if len(raw) == 32:
            return raw
        return hashlib.sha256(raw).digest()
    text = raw.strip()
    if not text:
        return TEACHING_KEY
    try:
        decoded = bytes.fromhex(text)
        if len(decoded) == 32:
            return decoded
        return hashlib.sha256(decoded).digest()
    except ValueError:
        return hashlib.sha256(text.encode("utf-8")).digest()


def derive_branch_seed(session_seed: int, branch: str) -> int:
    """Deterministic per-branch RNG seed from the session seed."""
    material = hmac.new(
        TEACHING_KEY,
        f"{session_seed}:{branch}".encode(),
        hashlib.sha256,
    ).digest()
    return int.from_bytes(material[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


def random_key() -> bytes:
    return os.urandom(32)


def pack_context(context_ids: list[int] | tuple[int, ...]) -> bytes:
    """Stable binary encoding of a token context window."""
    return b"".join(struct.pack(">I", int(t) & 0xFFFFFFFF) for t in context_ids)
