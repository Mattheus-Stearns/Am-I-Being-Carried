# services/api_service.py
import json
import time
from datetime import datetime, timezone, timedelta

import requests

from config import Config

SCRAPER_BASE = (
    "https://api.parse.bot/scraper/d0dcf8e8-3a72-4b21-bffb-8fa735257835"
)
REQUEST_TIMEOUT = 20
RETRY_DELAY_SECONDS = 10
STALE_AFTER = timedelta(minutes=60)


def fetch_player_data(platform, username):
    """Wake Tracker via profile, then fetch sessions; retry once if empty or stale."""
    api_key = Config.API_KEY
    if not api_key:
        print("❌ API_KEY not configured")
        return None, "API_KEY not configured", 500

    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🔍 Fetching: {platform}/{username}")

    headers = {"X-API-Key": api_key}

    try:
        profile_payload = _wake_tracker_profile(headers, platform, username)
        payload, error, status_code = _fetch_sessions(headers, platform, username)
        if status_code != 200 or payload is None:
            return None, error, status_code

        items = _session_items(payload)
        if items is None:
            print("⚠️ No 'items' in response")
            return None, "Invalid response structure", 422

        freshness = _freshness_from(payload, profile_payload)
        retried = False

        if _needs_retry(items, freshness):
            reason = "empty sessions" if not items else "stale Tracker data"
            print(
                f"⏳ {reason} (last_updated={freshness.get('last_updated')}); "
                f"retrying in {RETRY_DELAY_SECONDS}s"
            )
            time.sleep(RETRY_DELAY_SECONDS)
            retried = True

            profile_payload = _wake_tracker_profile(headers, platform, username)
            retry_payload, retry_error, retry_status = _fetch_sessions(
                headers, platform, username
            )
            if retry_status == 200 and retry_payload is not None:
                retry_items = _session_items(retry_payload)
                if retry_items:
                    payload = retry_payload
                    items = retry_items
                    freshness = _freshness_from(payload, profile_payload)
            elif not items:
                return None, retry_error, retry_status

        if not items:
            print("⚠️ Items array is empty after retry")
            return None, f"No data found for {username} on {platform}", 422

        payload["freshness"] = {
            **freshness,
            "retried": retried,
        }
        print(
            f"📊 Items count: {len(items)}; "
            f"last_updated={freshness.get('last_updated')}; "
            f"stale={freshness.get('is_stale')}; retried={retried}"
        )
        return payload, None, 200

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback

        traceback.print_exc()
        return None, str(e), 500


def _wake_tracker_profile(headers, platform, username):
    """Load the Tracker profile so session history is more likely to refresh."""
    body, error, status_code = _parse_bot_get(
        headers, "get_player_profile", platform, username
    )
    if status_code != 200 or body is None:
        print(f"⚠️ Profile wake skipped: {status_code} {error}")
        return None
    return _inner_payload(body)


def _fetch_sessions(headers, platform, username):
    body, error, status_code = _parse_bot_get(
        headers, "get_player_sessions", platform, username
    )
    if status_code != 200 or body is None:
        return None, error, status_code

    payload = _inner_payload(body)
    if not isinstance(payload, dict):
        return None, "Invalid response structure", 422
    return payload, None, 200


def _parse_bot_get(headers, endpoint, platform, username):
    try:
        response = requests.get(
            f"{SCRAPER_BASE}/{endpoint}",
            headers=headers,
            params={"platform": platform, "username": username},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        return None, "Request timed out", 408
    except requests.RequestException as e:
        return None, str(e), 500

    print(f"📊 {endpoint} status: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ API error: {response.status_code} - {response.text[:200]}")
        return None, f"API error: {response.status_code}", response.status_code

    try:
        body = response.json()
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return None, "Invalid JSON response", 502

    if isinstance(body, dict):
        print(f"📊 {endpoint} keys: {list(body.keys())}")
    return body, None, 200


def _inner_payload(body):
    if isinstance(body, dict) and isinstance(body.get("data"), dict):
        return body["data"]
    return body if isinstance(body, dict) else None


def _session_items(payload):
    items = payload.get("items") if isinstance(payload, dict) else None
    return items if isinstance(items, list) else None


def _needs_retry(items, freshness):
    return len(items) == 0 or freshness.get("is_stale") is True


def _freshness_from(session_payload, profile_payload):
    last_updated = _parse_timestamp(
        _nested_last_updated(session_payload)
        or _nested_last_updated(profile_payload)
    )
    expiry_date = _parse_timestamp(
        (session_payload or {}).get("expiryDate")
        or (profile_payload or {}).get("expiryDate")
    )

    is_stale = None
    reference = last_updated or expiry_date
    if reference is not None:
        is_stale = datetime.now(timezone.utc) - reference > STALE_AFTER

    return {
        "last_updated": last_updated.isoformat() if last_updated else None,
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "is_stale": is_stale,
    }


def _nested_last_updated(payload):
    if not isinstance(payload, dict):
        return None
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("lastUpdated")
        if isinstance(value, dict):
            return value.get("value")
        if value:
            return value
    return payload.get("lastUpdated")


def _parse_timestamp(value):
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
