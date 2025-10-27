import os
import time
import threading
import requests
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from dotenv import load_dotenv

from .utils.logger import logger
from .utils.cache import geo_cache
from .services import get_public_ip, get_coordinates_from_ip, reverse_geocode

# Load .env
load_dotenv()

# ---------------------------- Azure AD Config ---------------------------- #
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_EXPOSED_API_AUDIENCE = os.getenv("AZURE_EXPOSED_API_AUDIENCE")

JWKS_URI = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys"
ISSUER = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/v2.0"

# Fetch Azure AD public keys once
jwks_data = requests.get(JWKS_URI).json()

# ---------------------------- App Setup ---------------------------- #
app = FastAPI(title="Geo Locator API", version="2.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

latest_location = {"latitude": None, "longitude": None, "address": "Fetching..."}

# ---------------------------- Token Validation ---------------------------- #
def get_signing_key(kid):
    """Return the correct signing key from JWKS"""
    for key in jwks_data["keys"]:
        if key["kid"] == kid:
            return key
    return None


def verify_jwt_token(token: str):
    """Validate Azure AD Access Token"""
    try:
        header = jwt.get_unverified_header(token)
        key = get_signing_key(header["kid"])
        if not key:
            raise HTTPException(status_code=401, detail="Invalid token header")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=AZURE_EXPOSED_API_AUDIENCE,
            issuer=ISSUER,
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Token validation failed")


async def azure_auth_dependency(request: Request):
    """Extract & verify bearer token from Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = auth_header.split(" ")[1]
    payload = verify_jwt_token(token)
    return payload

# ---------------------------- Background Updater ---------------------------- #
def update_location(interval=600):
    """Background job to periodically update location"""
    global latest_location
    while True:
        try:
            ip = get_public_ip()
            if not ip:
                logger.warning("Could not fetch public IP")
                time.sleep(interval)
                continue

            cached = geo_cache.get(ip)
            if cached:
                latest_location.update(cached)
                logger.info("Using cached location data")
            else:
                lat, lon = get_coordinates_from_ip(ip)
                if lat and lon:
                    location_data = reverse_geocode(lat, lon)
                    latest_location.update(location_data)
                    geo_cache.set(ip, location_data)
                    logger.info(f"Updated location: {latest_location}")
                else:
                    logger.warning("Could not determine coordinates")
        except Exception as e:
            logger.exception(f"Error updating location: {e}")
        time.sleep(interval)

threading.Thread(target=update_location, daemon=True).start()

# ---------------------------- Routes ---------------------------- #
@app.get("/")
async def root():
    return RedirectResponse(url="/my-location/")


@app.get("/my-location/")
@limiter.limit("10/minute")
async def my_location(request: Request, user=Depends(azure_auth_dependency)):
    """Return current geolocation — requires Azure AD Bearer Token"""
    return JSONResponse(content=latest_location)


@app.get("/health")
async def health_check():
    """Simple health probe for Azure"""
    return {"status": "healthy", "service": "geo-locator-api"}
