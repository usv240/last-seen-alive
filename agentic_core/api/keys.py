"""API-key primitives.

Keys are *stateless*: everything the server needs to authorise a request is
carried inside the key and protected by an HMAC over a server-side pepper. The
plaintext key is returned once and is never stored anywhere.

This matters operationally. Cloud Run runs several instances of this service,
and an instance can be replaced at any time. A key held in process memory would
authenticate on the instance that minted it and 401 everywhere else, which is
exactly the failure a judge would hit: mint a key on the landing page, call the
API, get "invalid or expired". A signed key verifies identically on every
instance and survives restarts without a database.

What we give up is server-side revocation of an individual key. That is an
acceptable trade for a 60-day evaluation credential with a hard expiry and a
usage ceiling; rotating `API_KEY_PEPPER` invalidates every outstanding key at
once if that is ever needed.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

KeyTier = Literal["evaluation", "judge"]

KEY_PREFIX = "lsa_"

#: Days of validity and requests-per-day ceiling for each tier.
TIER_POLICY: dict[str, tuple[int, int]] = {
    "judge": (60, 2_000),
    "evaluation": (30, 500),
}


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    key_id: str
    digest: str
    tier: KeyTier
    expires_at: datetime
    daily_limit: int


class ApiKeyStore(Protocol):
    def put(self, record: ApiKeyRecord) -> None: ...

    def get(self, digest: str) -> ApiKeyRecord | None: ...


class MemoryApiKeyStore:
    """Records minted keys for observability only; authentication does not read it.

    Authentication is stateless (see module docstring), so nothing here is on the
    request path. Keeping the store lets a single instance report how many keys
    it minted without implying that memory is the source of truth.
    """

    def __init__(self) -> None:
        self._records: dict[str, ApiKeyRecord] = {}

    def put(self, record: ApiKeyRecord) -> None:
        self._records[record.digest] = record

    def get(self, digest: str) -> ApiKeyRecord | None:
        return self._records.get(digest)

    def __len__(self) -> int:
        return len(self._records)


def key_digest(key: str, pepper: bytes) -> str:
    """Stable non-reversible identifier for a key, safe to log."""
    return hmac.new(pepper, key.encode("utf-8"), hashlib.sha256).hexdigest()


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(payload: bytes, pepper: bytes) -> str:
    return _b64encode(hmac.new(pepper, payload, hashlib.sha256).digest())


def mint_key(*, tier: KeyTier, pepper: bytes, store: ApiKeyStore | None = None) -> tuple[str, ApiKeyRecord]:
    """Return a signed key and the record it encodes. The key is shown once."""
    days, limit = TIER_POLICY.get(tier, TIER_POLICY["evaluation"])
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=days)
    key_id = "key_" + secrets.token_hex(10)
    claims = {
        "v": 1,
        "id": key_id,
        "t": tier,
        "exp": int(expires_at.timestamp()),
        "q": limit,
    }
    payload = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    raw = f"{KEY_PREFIX}{_b64encode(payload)}.{_sign(payload, pepper)}"
    record = ApiKeyRecord(
        key_id=key_id,
        digest=key_digest(raw, pepper),
        tier=tier,
        expires_at=expires_at,
        daily_limit=limit,
    )
    if store is not None:
        store.put(record)
    return raw, record


def authenticate_key(
    raw: str, *, pepper: bytes, store: ApiKeyStore | None = None
) -> ApiKeyRecord | None:
    """Verify a key's signature and expiry without consulting any store.

    Returns None for anything that is not a well-formed, correctly signed,
    unexpired key. The caller must not distinguish these cases to the client.
    """
    if not raw.startswith(KEY_PREFIX):
        return None
    body = raw[len(KEY_PREFIX) :]
    encoded_payload, separator, signature = body.partition(".")
    if not separator or not encoded_payload or not signature:
        return None
    try:
        payload = _b64decode(encoded_payload)
    except (ValueError, base64.binascii.Error):  # type: ignore[attr-defined]
        return None
    if not hmac.compare_digest(_sign(payload, pepper), signature):
        return None
    try:
        claims = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(claims, dict) or claims.get("v") != 1:
        return None
    tier = claims.get("t")
    if tier not in TIER_POLICY:
        return None
    try:
        expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=UTC)
    except (KeyError, TypeError, ValueError, OSError, OverflowError):
        return None
    if expires_at <= datetime.now(UTC):
        return None
    return ApiKeyRecord(
        key_id=str(claims.get("id", "key_unknown")),
        digest=key_digest(raw, pepper),
        tier=tier,  # type: ignore[arg-type]
        expires_at=expires_at,
        daily_limit=int(claims.get("q", TIER_POLICY[tier][1])),
    )
