import requests
from .config import GOOGLE_MAPS_API_KEY

def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()
        return response.json().get("ip")
    except Exception as e:
        print(f"Error fetching public IP: {e}")
        return None

def get_coordinates_from_ip(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        response.raise_for_status()
        data = response.json()
        loc = data.get("loc")
        if loc:
            lat, lon = loc.split(",")
            return float(lat), float(lon)
    except Exception as e:
        print(f"Error fetching coordinates: {e}")
    return None, None

def reverse_geocode(lat, lon):
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"latlng": f"{lat},{lon}", "key": GOOGLE_MAPS_API_KEY}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "OK" and data["results"]:
            return {"latitude": lat, "longitude": lon, "address": data["results"][0]["formatted_address"]}
        return {"latitude": lat, "longitude": lon, "address": "Address not found"}
    except Exception as e:
        print(f"Error reverse geocoding: {e}")
        return {"latitude": lat, "longitude": lon, "address": "Error fetching address"}
