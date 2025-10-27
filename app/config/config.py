#config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Interval in seconds for updating location
LOCATION_UPDATE_INTERVAL = 300
RATE_LIMIT = "5/minute"
# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
# Get public IP
PUBLIC_IP_PATH = os.getenv("PUBLIC_IP_PATH")
# Reverse geocode
REVERSE_GEOCODE = os.getenv("REVERSE_GEOCODE")
