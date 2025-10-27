import time
from ..config.config import LOCATION_UPDATE_INTERVAL

# Simple TTL cache
class TTLCache:
    def __init__(self, ttl_seconds=LOCATION_UPDATE_INTERVAL):
        self.ttl = ttl_seconds
        self.store = {}

    def get(self, key):
        value = self.store.get(key)
        if not value:
            return None
        data, timestamp = value
        if time.time() - timestamp < self.ttl:
            return data
        else:
            self.store.pop(key, None)
            return None

    def set(self, key, data):
        self.store[key] = (data, time.time())

# Instantiate shared cache
geo_cache = TTLCache(ttl_seconds=LOCATION_UPDATE_INTERVAL)
