# backend/app/marrfa_client.py
import json
import requests
from typing import Dict, Any, List, Optional

BASE_URL = "https://apiv2.marrfa.com/properties"


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
    """
    if not x:
        return None

    if isinstance(x, str):
        s = x.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    u = obj.get("url") or obj.get("image") or obj.get("src")
                    if isinstance(u, str) and u.startswith(("http://", "https://")):
                        return u
            except Exception:
                return None

        if s.startswith(("http://", "https://")):
            return s
        return None

    if isinstance(x, dict):
        u = x.get("url") or x.get("image") or x.get("src")
        if isinstance(u, str) and u.startswith(("http://", "https://")):
            return u
        return None

    if isinstance(x, list) and x:
        return _extract_url(x[0])

    return None


def search_properties(filters: Dict[str, Any]) -> List[dict]:
    """
    Returns normalized properties for Streamlit:
    id, title, location, price_from, price_to, currency,
    completion_year, cover_image, images, listing_url
    """
    params: Dict[str, Any] = {}

    def set_if_present(key: str):
        if key in filters and filters[key] is not None:
            params[key] = _maybe_csv(filters[key])

    for key in [
        "search_query",
        "areas",
        "unit_types",
        "unit_bedrooms",
        "status",
        "sale_status",
        "unit_price_from",
        "unit_price_to",
        "unit_area_from",
        "unit_area_to",
        "ids",
        "page",
        "per_page",
    ]:
        set_if_present(key)

    print(f"Making request to {BASE_URL} with params: {params}")

    try:
        resp = requests.get(BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        print(f"Response data: {data}")
    except Exception as e:
        print(f"Error fetching properties: {e}")
        raise

    items = data.get("items", []) or data.get("data", [])
    print(f"Found {len(items)} items")

    properties: List[dict] = []
    for p in items:
        property_id = p.get("id")

        # ✅ Completion year
        completion = p.get("completion_datetime") or p.get("completion_date") or ""
        completion_year = str(completion)[:4] if completion else None

        # ✅ Price
        min_price = p.get("min_price_aed") or p.get("min_price")
        max_price = p.get("max_price_aed") or p.get("max_price")
        price_from = float(min_price) if min_price not in (None, 0) else None
        price_to = float(max_price) if max_price not in (None, 0) else None

        # ✅ Images (normalized)
        cover_url = (
                _extract_url(p.get("cover_image"))
                or _extract_url(p.get("cover_image_url"))
                or _extract_url(p.get("thumbnail"))
                or _extract_url(p.get("thumbnail_url"))
                or _extract_url(p.get("images"))
        )

        images_list: List[str] = []
        images_raw = p.get("images")
        if isinstance(images_raw, list):
            for it in images_raw[:12]:
                u = _extract_url(it)
                if u:
                    images_list.append(u)

        # ✅ Marrfa website listing url format (confirmed by you)
        listing_url = (
            f"https://www.marrfa.com/propertylisting/{property_id}"
            if property_id is not None
            else None
        )

        properties.append(
            {
                "id": property_id,
                "title": p.get("name") or p.get("title") or "Untitled property",
                "location": p.get("area"),
                "price_from": price_from,
                "price_to": price_to,
                "currency": p.get("price_currency") or "AED",
                "completion_year": completion_year,
                "cover_image": cover_url,
                "images": images_list or None,
                "listing_url": listing_url,
            }
        )

    print(f"Returning {len(properties)} properties")
    return properties