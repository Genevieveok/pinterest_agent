import os
import requests

TOKEN = os.getenv('PINTEREST_TOKEN')
API_BASE = 'https://api.pinterest.com/v5'
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

def search_pins(query, limit=25):
    if not TOKEN:
        raise RuntimeError('PINTEREST_TOKEN not set')
    url = f"{API_BASE}/search/pins"
    params = {'query': query, 'page_size': limit}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get('items', [])

def save_pin_to_board(board_id, pin_id=None, image_url=None, title=None, description=None, link=None):
    if not TOKEN:
        raise RuntimeError('PINTEREST_TOKEN not set')
    url = f"{API_BASE}/pins"
    payload = {'board_id': board_id}
    if pin_id:
        payload['existing_pin_id'] = pin_id
    else:
        payload['title'] = title or ''
        payload['alt_text'] = title or ''
        payload['description'] = description or ''
        payload['link'] = link or ''
        payload['media_source'] = {'source_type': 'image_url', 'url': image_url}
    r = requests.post(url, json=payload, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()
