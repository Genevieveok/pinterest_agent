import os
import requests
from .globals import PINTEREST_ACCESS_TOKEN, API_CONFIG

API_BASE = "https://api.pinterest.com/v5"


def search_boards(query, limit=5):
    if not PINTEREST_ACCESS_TOKEN.access_token:
        raise RuntimeError("Pinterest Access Token not available.")

    url = f"{API_BASE}/search/boards"
    params = {"query": query, "page_size": limit}

    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN.access_token}",
        "Content-Type": "application/json",
    }

    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(data, url, headers, params)
    return data.get("items", [])


def list_pins_on_board(board_id, limit=50):
    if not PINTEREST_ACCESS_TOKEN.access_token:
        raise RuntimeError("Pinterest Access Token not available.")

    url = f"{API_BASE}/boards/{board_id}/pins"
    params = {"page_size": limit, "fields": "id,link,created_at,aggregated_pin_data"}

    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN.access_token}",
        "Content-Type": "application/json",
    }

    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("items", [])


def search_pins(query, limit=25):
    # This function is now DEFUNCT and should not be used for public search.
    # It will remain commented out or raised to force the repin_engine to fail
    # if it accidentally calls this. The /search/pins endpoint returns 404.
    raise NotImplementedError(
        "Public Pin Search is not supported in v5 API. Use search_boards + list_pins_on_board instead."
    )


def save_pin_to_board(
    board_id, pin_id=None, image_url=None, title=None, description=None, link=None
):
    if not PINTEREST_ACCESS_TOKEN.access_token:
        raise RuntimeError("PINTEREST_ACCESS_TOKEN not set")

    if pin_id:
        url = f"{API_BASE}/pins/{pin_id}/save"
        payload = {"board_id": board_id}

    else:
        url = f"{API_BASE}/pins"

        if not image_url or not board_id:
            raise ValueError("Pin creation requires image_url and board_id.")

        payload = {
            "board_id": board_id,
            "media_source": {"source_type": "image_url", "url": image_url},
            "title": title or "TE title for board",
            "alt_text": title or "TE image for board",
            "description": description or "TE description for board",
            "link": link or "",
        }

    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN.access_token}",
        "Content-Type": "application/json",
    }

    print(f"URL: {url}")
    print(f"PAYLOAD: {payload}")

    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()
