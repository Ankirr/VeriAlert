"""
Cached Geocoder module using GeoPy Nominatim with Redis + Disk caching and polite rate-limiting.
"""
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import redis
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from app.config import settings
from app.geo.gazetteer import get_state_centroid

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent / "data"
DISK_CACHE_FILE = CACHE_DIR / "geo_cache.json"

USER_AGENT = "verialert-disaster-response-system/1.0 (contact: disaster-alert@verialert.org)"

class CachedDisasterGeocoder:
    """
    Geocodes location queries with 2-tier caching:
      1. Redis (in-memory, TTL: 14 days, protocol=2 for Windows compatibility)
      2. Persistent Disk Cache (JSON file on disk)
      3. Nominatim API with 1.0s polite rate limiting
      4. Centroid Fallback (Gazetteer state/country centroid if Nominatim fails)
    """
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = None
        self._init_redis()
        
        # Local persistent disk cache
        self.disk_cache: Dict[str, Dict[str, Any]] = {}
        self._load_disk_cache()
        
        # Geopy Nominatim client
        self.geocoder = Nominatim(user_agent=USER_AGENT, timeout=7)
        self.last_request_time = 0.0
        self.min_interval = 1.0  # 1.0 second delay between live API calls for OSM policy compliance

    def _init_redis(self):
        try:
            self.redis_client = redis.from_url(self.redis_url, protocol=2, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis cache connected successfully for GeoPy geocoder.")
        except Exception as e:
            logger.warning(f"Redis unavailable for geocoder ({e}). Falling back to local disk cache.")
            self.redis_client = None

    def _load_disk_cache(self):
        if DISK_CACHE_FILE.exists():
            try:
                with open(DISK_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.disk_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load disk cache from {DISK_CACHE_FILE}: {e}")
                self.disk_cache = {}

    def _save_disk_cache(self):
        try:
            DISK_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(DISK_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.disk_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not write disk cache to {DISK_CACHE_FILE}: {e}")

    def geocode(self, location_query: str, state_hint: Optional[str] = None, country_hint: Optional[str] = "India") -> Dict[str, Any]:
        """
        Geocodes a location query string with caching and centroid fallback.
        """
        if not location_query or not location_query.strip():
            return self._fallback_centroid(state_hint or country_hint or "India", "Empty location query")

        query_key = location_query.strip().lower()

        # Check Level 1: Redis
        cached_result = self._get_from_redis(query_key)
        if cached_result:
            cached_result["cached"] = True
            return cached_result

        # Check Level 2: Local Disk Cache
        if query_key in self.disk_cache:
            res = dict(self.disk_cache[query_key])
            res["cached"] = True
            # Populate back to Redis if available
            self._set_to_redis(query_key, res)
            return res

        # Level 3: Live Nominatim API Call with Rate Limiting
        result = self._query_nominatim(location_query, state_hint, country_hint)
        
        # Save to both caches
        self._set_to_redis(query_key, result)
        self.disk_cache[query_key] = result
        self._save_disk_cache()
        return result

    def _query_nominatim(self, query: str, state_hint: Optional[str], country_hint: Optional[str]) -> Dict[str, Any]:
        # Enforce 1.0 second delay for OpenStreetMap rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        
        logger.info(f"Nominatim API query: '{query}'")
        self.last_request_time = time.time()

        try:
            loc = self.geocoder.geocode(query, addressdetails=True)
            if loc:
                raw = loc.raw or {}
                address = raw.get("address", {})
                
                city = address.get("city") or address.get("town") or address.get("village") or address.get("county")
                state = address.get("state")
                country = address.get("country", country_hint or "India")
                country_code = address.get("country_code", "in").upper()

                return {
                    "latitude": round(loc.latitude, 6),
                    "longitude": round(loc.longitude, 6),
                    "display_name": loc.address,
                    "city": city,
                    "district": address.get("county") or address.get("state_district") or city,
                    "state": state or state_hint,
                    "country": country,
                    "country_code": country_code,
                    "confidence": 0.95,
                    "is_fallback": False,
                    "cached": False
                }
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logger.warning(f"Nominatim timeout/unavailable for query '{query}': {e}")
        except Exception as e:
            logger.warning(f"Nominatim error for query '{query}': {e}")

        # Try fallback query with state or country if query had more details
        if state_hint and query != f"{state_hint}, {country_hint}":
            fallback_q = f"{state_hint}, {country_hint}"
            logger.info(f"Retrying with fallback location: '{fallback_q}'")
            try:
                time.sleep(1.0)
                self.last_request_time = time.time()
                loc = self.geocoder.geocode(fallback_q, addressdetails=True)
                if loc:
                    return {
                        "latitude": round(loc.latitude, 6),
                        "longitude": round(loc.longitude, 6),
                        "display_name": loc.address,
                        "city": None,
                        "district": None,
                        "state": state_hint,
                        "country": country_hint or "India",
                        "country_code": "IN",
                        "confidence": 0.70,
                        "is_fallback": True,
                        "cached": False
                    }
            except Exception as e:
                logger.warning(f"Fallback query error: {e}")

        # Centroid fallback from Gazetteer
        return self._fallback_centroid(state_hint or country_hint or "India", f"Nominatim lookup failed for '{query}'")

    def _fallback_centroid(self, region_name: str, reason: str) -> Dict[str, Any]:
        centroid = get_state_centroid(region_name)
        if not centroid:
            centroid = (20.5937, 78.9629)  # India centroid
            display_name = f"India (Centroid Fallback - {reason})"
            country = "India"
            country_code = "IN"
        else:
            display_name = f"{region_name.title()} (Centroid Fallback)"
            rn_lower = region_name.lower()
            if rn_lower in ("china", "tibet", "xizang", "lhasa"):
                country = "China"
                country_code = "CN"
            elif rn_lower in ("nepal", "kathmandu", "bhotekoshi", "darchula"):
                country = "Nepal"
                country_code = "NP"
            elif rn_lower == "bangladesh":
                country = "Bangladesh"
                country_code = "BD"
            elif rn_lower == "bhutan":
                country = "Bhutan"
                country_code = "BT"
            else:
                country = "India"
                country_code = "IN"

        return {
            "latitude": centroid[0],
            "longitude": centroid[1],
            "display_name": display_name,
            "city": None,
            "district": None,
            "state": region_name.title() if region_name.lower() not in ("india", "china", "nepal", "bangladesh", "bhutan") else None,
            "country": country,
            "country_code": country_code,
            "confidence": 0.50,
            "is_fallback": True,
            "cached": False
        }

    def _get_from_redis(self, key: str) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            return None
        try:
            val = self.redis_client.get(f"geo:v1:{key}")
            if val:
                return json.loads(val)
        except Exception as e:
            logger.debug(f"Redis get failed: {e}")
        return None

    def _set_to_redis(self, key: str, val: Dict[str, Any]):
        if not self.redis_client:
            return
        try:
            # Cache for 14 days
            self.redis_client.setex(f"geo:v1:{key}", 14 * 86400, json.dumps(val))
        except Exception as e:
            logger.debug(f"Redis set failed: {e}")

_GEOCODER_INSTANCE = None

def get_geocoder() -> CachedDisasterGeocoder:
    global _GEOCODER_INSTANCE
    if _GEOCODER_INSTANCE is None:
        _GEOCODER_INSTANCE = CachedDisasterGeocoder()
    return _GEOCODER_INSTANCE
