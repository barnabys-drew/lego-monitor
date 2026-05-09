"""eBay Browse API — active-listing median price for LEGO sets.

Replaces the BrickEconomy + BrickLink scrapers (both Cloudflare-blocked) with
eBay's official Browse API. Returns the median price of the top N active 'Used'
listings for a given set ID + name.

Auth (OAuth2 client credentials):
    - Register a free Production app at https://developer.ebay.com/
    - Set EBAY_APP_ID (client id) and EBAY_CERT_ID (client secret) in env
    - This module fails soft (returns None) if either is missing

Token lifecycle is handled in-process: one access token cached, refreshed
when expired.

Why active listings instead of sold listings?
    The Marketplace Insights API (sold listings) requires manual approval per
    app. Browse API is free and immediate. Active-listing median is a decent
    'current ask' proxy; resale-arb users typically buy below this and sell
    at-or-above it.
"""
from __future__ import annotations

import base64
import logging
import os
import statistics
import time
from typing import List, Optional

import requests

log = logging.getLogger("ebay_price")

_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
_SCOPE = "https://api.ebay.com/oauth/api_scope"

# Process-level token cache
_token_cache: dict = {"access_token": None, "expires_at": 0.0}


def _get_credentials() -> Optional[tuple[str, str]]:
    app_id = os.environ.get("EBAY_APP_ID", "").strip()
    cert_id = os.environ.get("EBAY_CERT_ID", "").strip()
    if not app_id or not cert_id:
        return None
    return app_id, cert_id


def _get_token(force_refresh: bool = False) -> Optional[str]:
    """Return a cached or freshly-fetched eBay access token. None on auth failure."""
    now = time.time()
    if not force_refresh and _token_cache["access_token"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]
    creds = _get_credentials()
    if creds is None:
        return None
    app_id, cert_id = creds
    basic = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    try:
        resp = requests.post(
            _TOKEN_URL,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": _SCOPE},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json() or {}
    except (requests.RequestException, ValueError) as e:
        log.warning(f"eBay token fetch failed: {e}")
        return None
    token = data.get("access_token")
    expires_in = int(data.get("expires_in", 7200) or 7200)
    if not token:
        return None
    _token_cache["access_token"] = token
    # Refresh 60s early
    _token_cache["expires_at"] = now + expires_in - 60
    return token


def _search_listings(token: str, query: str, limit: int = 20) -> List[dict]:
    """Call Browse API search, return raw item list."""
    try:
        resp = requests.get(
            _SEARCH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                # Locale + currency hints — required for accurate pricing in USD
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            },
            params={"q": query, "limit": limit},
            timeout=15,
        )
        if resp.status_code == 401:
            # Token may have rotated mid-flight; bubble up so caller can retry
            return []
        resp.raise_for_status()
        return (resp.json() or {}).get("itemSummaries", []) or []
    except (requests.RequestException, ValueError) as e:
        log.warning(f"eBay search failed for '{query}': {e}")
        return []


def fetch_ebay_price(set_id: str, name: str = "", limit: int = 20) -> Optional[float]:
    """Return median 'Used' active-listing price for `set_id`, or None if unavailable.

    Searches for `lego <set_id> <first 3 words of name>` to get tighter results,
    falls back to set_id alone if no results.
    """
    if not _get_credentials():
        log.warning("EBAY_APP_ID / EBAY_CERT_ID not set — returning None")
        return None
    token = _get_token()
    if token is None:
        return None

    # Build a query that's specific enough to weed out part-out listings.
    short_name = " ".join((name or "").split()[:3])
    queries = []
    if short_name:
        queries.append(f"lego {set_id} {short_name}")
    queries.append(f"lego {set_id}")

    items: List[dict] = []
    for q in queries:
        items = _search_listings(token, q, limit=limit)
        if items:
            break

    if not items:
        return None

    prices: List[float] = []
    for item in items:
        # Skip auction-only listings (we want buy-it-now pricing)
        buying_options = set(item.get("buyingOptions") or [])
        if buying_options and "FIXED_PRICE" not in buying_options:
            continue
        price_obj = item.get("price") or {}
        try:
            value = float(price_obj.get("value", 0) or 0)
        except (TypeError, ValueError):
            continue
        # eBay returns prices in the marketplace currency (USD here)
        if 5 < value < 50000:  # sanity bounds — drop free items + obvious typos
            prices.append(value)

    if not prices:
        return None
    # Median is more robust than mean against listing-spam outliers
    return round(statistics.median(prices), 2)
