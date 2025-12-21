# backend/app/marrfa_client.py
import json
import requests
import time
from typing import Dict, Any, List, Optional, Tuple
from functools import lru_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://apiv2.marrfa.com/properties"

# --- Global session for connection reuse ---
_http_session = None


def get_http_session():
    """Get or create a requests session with retry strategy."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        # Configure retry strategy
        retry_strategy = Retry(
            total=2,  # Reduced from 3 to 2 for speed
            backoff_factor=0.5,  # Reduced backoff
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
            pool_block=False
        )
        _http_session.mount("http://", adapter)
        _http_session.mount("https://", adapter)
    return _http_session


# --- Simple caching for identical requests ---
_property_cache = {}
_CACHE_TIMEOUT = 60  # 1 minute cache


def clear_old_cache():
    """Clear old cache entries."""
    current_time = time.time()
    keys_to_delete = []
    for key, (timestamp, _) in _property_cache.items():
        if current_time - timestamp > _CACHE_TIMEOUT:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del _property_cache[key]


def get_cache_key(filters: Dict[str, Any]) -> str:
    """Create a hash key for caching."""
    import hashlib
    # Sort filters for consistent keys
    sorted_filters = json.dumps(
        {k: filters[k] for k in sorted(filters.keys()) if filters[k] is not None},
        sort_keys=True
    )
    return hashlib.md5(sorted_filters.encode()).hexdigest()


def _maybe_csv(value: Any) -> Any:
    if isinstance(value, (list, tuple, set)):
        return ",".join(str(v) for v in value)
    return value


def _extract_url(x: Any) -> Optional[str]:
    """
    Marrfa image fields can be:
    - plain string URL
    - JSON string like '{"url":"https://..."}'
    - dict like {"url":"https://..."}
    - list of strings
    - list of dicts [{"url":"https://..."}]

    Optimized version for speed.
    """
    if not x:
        return None

    if isinstance(x, str):
        s = x.strip()
        # Fast check for http(s)
        if s.startswith(("http://", "https://")):
            return s

        # Only try JSON parsing if it looks like JSON
        if s.startswith("{") and s.endswith("}"):
            try:
                # Fast JSON parsing with minimal validation
                if '"url"' in s or '"image"' in s or '"src"' in s:
                    # Extract URL with simple string search (faster than full JSON parse)
                    for prefix in ['"url":', '"image":', '"src":']:
                        if prefix in s:
                            start_idx = s.find(prefix) + len(prefix)
                            # Find the value (skip whitespace and quotes)
                            value_start = s.find('"', start_idx)
                            if value_start != -1:
                                value_end = s.find('"', value_start + 1)
                                if value_end != -1:
                                    url = s[value_start + 1:value_end]
                                    if url.startswith(("http://", "https://")):
                                        return url
            except Exception:
                pass
        return None

    if isinstance(x, dict):
        # Direct dictionary lookup
        for key in ["url", "image", "src"]:
            if key in x and isinstance(x[key], str) and x[key].startswith(("http://", "https://")):
                return x[key]
        return None

    if isinstance(x, list) and x:
        # Just take first element
        return _extract_url(x[0])

    return None


def search_properties(filters: Dict[str, Any]) -> List[dict]:
    """
    Returns normalized properties for Streamlit:
    id, title, location, price_from, price_to, currency,
    completion_year, cover_image, images, listing_url

    Optimized for speed with caching and connection reuse.
    """
    # Clear old cache entries if cache is getting large
    if len(_property_cache) > 200:
        clear_old_cache()

    # Check cache first
    cache_key = get_cache_key(filters)
    if cache_key in _property_cache:
        timestamp, cached_data = _property_cache[cache_key]
        if time.time() - timestamp < _CACHE_TIMEOUT:
            print(f"Cache hit for property search: {filters.get('search_query', 'unknown')}")
            return cached_data

    params: Dict[str, Any] = {}

    # Only extract essential parameters for speed
    def set_if_present(key: str):
        if key in filters and filters[key] is not None:
            params[key] = _maybe_csv(filters[key])

    # Essential parameters only (reduced list for speed)
    essential_keys = [
        "search_query",
        "unit_types",
        "unit_bedrooms",
        "unit_price_from",
        "unit_price_to",
        "page",
        "per_page",
    ]

    for key in essential_keys:
        set_if_present(key)

    print(f"Making request to {BASE_URL} with params: {params}")

    start_time = time.time()

    try:
        # Use shared session with connection reuse
        session = get_http_session()
        resp = session.get(BASE_URL, params=params, timeout=8)  # Reduced from 20 to 8 seconds
        resp.raise_for_status()
        data = resp.json()
        print(f"API response time: {time.time() - start_time:.2f}s")
    except requests.exceptions.Timeout:
        print(f"Request timeout for filters: {filters}")
        # Return empty list instead of raising exception
        return []
    except requests.exceptions.ConnectionError:
        print(f"Connection error for filters: {filters}")
        return []
    except Exception as e:
        print(f"Error fetching properties: {e}")
        # Return empty list instead of raising exception
        return []

    items = data.get("items", []) or data.get("data", [])
    print(f"Found {len(items)} items")

    properties: List[dict] = []

    # Optimized property processing
    for p in items:
        try:
            property_id = p.get("id")

            # ✅ Completion year (optimized)
            completion = None
            for key in ["completion_datetime", "completion_date"]:
                if key in p and p[key]:
                    completion = p[key]
                    break

            completion_year = str(completion)[:4] if completion else None

            # ✅ Price (optimized)
            price_from = None
            price_to = None

            # Try min_price_aed first, then min_price
            min_price = p.get("min_price_aed") or p.get("min_price")
            if min_price and min_price != 0:
                try:
                    price_from = float(min_price)
                except (ValueError, TypeError):
                    pass

            # Try max_price_aed first, then max_price
            max_price = p.get("max_price_aed") or p.get("max_price")
            if max_price and max_price != 0:
                try:
                    price_to = float(max_price)
                except (ValueError, TypeError):
                    pass

            # ✅ Images (optimized - only extract cover image)
            cover_url = None
            # Check common image fields in order of likelihood
            for key in ["cover_image", "cover_image_url", "thumbnail", "thumbnail_url"]:
                if key in p and p[key]:
                    url = _extract_url(p[key])
                    if url:
                        cover_url = url
                        break

            # ✅ Marrfa website listing url format (confirmed by you)
            listing_url = None
            if property_id is not None:
                listing_url = f"https://www.marrfa.com/propertylisting/{property_id}"

            # ✅ Location
            location = p.get("area") or p.get("location") or "Dubai"

            properties.append(
                {
                    "id": property_id,
                    "title": p.get("name") or p.get("title") or "Untitled property",
                    "location": location,
                    "price_from": price_from,
                    "price_to": price_to,
                    "currency": p.get("price_currency") or "AED",
                    "completion_year": completion_year,
                    "cover_image": cover_url,
                    "images": None,  # Skip detailed images list for speed
                    "listing_url": listing_url,
                }
            )
        except Exception as e:
            print(f"Error processing property: {e}")
            # Skip this property and continue with others

    print(f"Returning {len(properties)} properties (processing time: {time.time() - start_time:.2f}s)")

    # Cache the result
    _property_cache[cache_key] = (time.time(), properties)

    return properties


# --- Helper function to clear cache (optional) ---
def clear_property_cache():
    """Clear all cached property data."""
    global _property_cache
    old_size = len(_property_cache)
    _property_cache = {}
    return f"Cleared {old_size} cached property entries"


# --- Fast search for common queries ---
@lru_cache(maxsize=50)
def search_properties_cached(filters_json: str) -> List[dict]:
    """
    LRU cached version of search_properties for identical queries.
    Use for repeated identical queries.
    """
    filters = json.loads(filters_json)
    return search_properties(filters)


# --- Simple property search for common cases ---
def quick_property_search(location: str = "dubai",
                          property_type: str = None,
                          bedrooms: str = None,
                          max_price: float = None) -> List[dict]:
    """
    Quick property search with minimal parameters.
    Useful for common simple queries.
    """
    filters = {"search_query": location}

    if property_type:
        filters["unit_types"] = [property_type]
    if bedrooms:
        filters["unit_bedrooms"] = bedrooms
    if max_price:
        filters["unit_price_to"] = max_price

    filters["page"] = 1
    filters["per_page"] = 10

    return search_properties(filters)