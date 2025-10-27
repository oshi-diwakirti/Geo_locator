import os
import requests
from cachetools import TTLCache
from jose import jwt, jwk
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from msal import ConfidentialClientApplication
from .logger import logger

# Config from env
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AUTHORITY = os.getenv("AZURE_AUTHORITY") or f"https://login.microsoftonline.com/{TENANT_ID}"
AUDIENCE = os.getenv("AZURE_EXPOSED_API_AUDIENCE") or CLIENT_ID
JWKS_URL = f"{AUTHORITY}/discovery/v2.0/keys"
JWKS_REFRESH_INTERVAL = int(os.getenv("JWKS_REFRESH_INTERVAL", 3600))

# Simple TTL cache for JWKS and MSAL token cache
_jwks_cache = TTLCache(maxsize=1, ttl=JWKS_REFRESH_INTERVAL)

http_bearer = HTTPBearer(auto_error=False)

def _fetch_jwks():
    """Fetch JWKS (and cache)."""
    if "jwks" in _jwks_cache:
        return _jwks_cache["jwks"]
    try:
        r = requests.get(JWKS_URL, timeout=5)
        r.raise_for_status()
        jwks = r.json()
        _jwks_cache["jwks"] = jwks
        logger.info("Fetched JWKS")
        return jwks
    except Exception as e:
        logger.exception("Failed to fetch JWKS")
        raise

def _get_public_key_for_kid(kid):
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None

def validate_jwt(token: str, required_scopes: list = None, required_roles: list = None):
    """
    Validates token:
      - signature using JWKS
      - expiry, issuer, audience
      - scopes or roles if provided
    Raises HTTPException(401/403) on failure.
    Returns decoded claims dict on success.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token header")

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing kid")

    key = _get_public_key_for_kid(kid)
    if not key:
        raise HTTPException(status_code=401, detail="Public key not found for token")

    # Build public key in a format python-jose accepts
    try:
        public_key = jwk.construct(key)
    except Exception as e:
        logger.exception("Failed to construct public key")
        raise HTTPException(status_code=401, detail="Invalid public key")

    # Validate signature and claims using jose
    try:
        # jose.jwt.decode will verify signature and claims. Provide audience and issuer checks.
        issuer = f"{AUTHORITY}/v2.0"
        options = {"verify_aud": True, "verify_exp": True, "verify_iss": True}
        claims = jwt.decode(token, key, algorithms=key.get("alg", "RS256"), audience=AUDIENCE, issuer=issuer, options=options)
    except Exception as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail="Token validation failed")

    # Check scopes (scp) or roles (roles or wids)
    if required_scopes:
        token_scopes = []
        if "scp" in claims:
            token_scopes = claims.get("scp", "").split()
        # for v2 tokens, 'scp' contains space-separated scopes
        if not set(required_scopes).issubset(set(token_scopes)):
            raise HTTPException(status_code=403, detail="Required scope(s) not present")

    if required_roles:
        token_roles = claims.get("roles", []) or claims.get("wids", []) or []
        if isinstance(token_roles, str):
            token_roles = [token_roles]
        if not set(required_roles).issubset(set(token_roles)):
            raise HTTPException(status_code=403, detail="Insufficient role privileges")

    return claims

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(http_bearer)):
    """
    FastAPI dependency: returns decoded claims or raises 401/403.
    Use: Depends(get_current_user)
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = credentials.credentials
    claims = validate_jwt(token)
    return claims

def require_scopes(*scopes):
    from functools import wraps
    # from fastapi import Depends

    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, credentials: HTTPAuthorizationCredentials = Security(http_bearer), **kwargs):
            if not credentials or not credentials.credentials:
                raise HTTPException(status_code=401, detail="Authorization header missing")
            token = credentials.credentials
            claims = validate_jwt(token, required_scopes=list(scopes))
            # attach claims to kwargs for endpoint if needed
            kwargs["token_claims"] = claims
            return await fn(*args, **kwargs)
        return wrapper
    return decorator

# -------------------------
# MSAL Confidential client helper for outbound calls
# here a simple in-memory cache.
_msal_app = None
_token_cache = TTLCache(maxsize=100, ttl=3600)

def get_msal_app():
    global _msal_app
    if _msal_app:
        return _msal_app
    if not CLIENT_ID or not CLIENT_SECRET:
        logger.error("MSAL client id/secret not configured")
        raise RuntimeError("MSAL configuration missing")
    _msal_app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY
    )
    return _msal_app

def acquire_token_for_scope(scope: str):
    """
    Acquire client credentials token for given scope (e.g., "https://graph.microsoft.com/.default" or "api://<id>/.default").
    Use acquire_token_silent first, then acquire_token_for_client.
    Caches token in memory (ttl).
    """
    # cache key is the scope string
    token = _token_cache.get(scope)
    if token:
        return token

    app = get_msal_app()
    # msal expects scopes as list
    scopes = [scope] if isinstance(scope, str) else scope
    result = app.acquire_token_silent(scopes, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=scopes)
    if "access_token" in result:
        _token_cache.set(scope, result["access_token"])
        return result["access_token"]
    else:
        logger.error(f"Failed to acquire token via MSAL: {result}")
        raise RuntimeError("Failed to acquire access token")
