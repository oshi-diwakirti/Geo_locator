#config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Interval in seconds for updating location
LOCATION_UPDATE_INTERVAL = 300
# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
PUBLIC_IP_PATH = os.getenv("PUBLIC_IP_PATH")
REVERSE_GEOCODE = os.getenv("REVERSE_GEOCODE")
