import random, time
from .pinterest_api import search_pins, save_pin_to_board
from .db import get_conn

def pick_quality_pins(items, min_saves=5):
    out = []
    for it in items:
        saves = it.get('save_count') or it.get('aggregated_pin_data', {}).get('saves') or 0
        images = it.get('images') or it.get('image')
        if not images:
            continue
        try:
            saves_int = int(saves)
        except Exception:
            saves_int = 0
        if saves_int < min_saves:
            continue
        out.append(it)
    return out

def repin_for_board(board_key, board_cfg, quota, filters, sleep_fn):
    keywords = board_cfg.get('keywords', [])
    picked = []
    conn = get_conn()
    cur = conn.cursor()
    attempts = 0
    while len(picked) < quota and attempts < quota * 10:
        attempts += 1
        q = random.choice(keywords)
        try:
            items = search_pins(q, limit=30)
        except Exception as e:
            print('search_pins failed', e)
            time.sleep(2)
            continue
        candidates = pick_quality_pins(items, min_saves=filters.get('min_saves', 5))
        random.shuffle(candidates)
        for c in candidates:
            pin_id = c.get('id')
            if not pin_id:
                continue
            cur.execute('SELECT 1 FROM pinned WHERE pinterest_pin_id = ?', (pin_id,))
            if cur.fetchone():
                continue
            try:
                save_pin_to_board(board_cfg['id'], pin_id=pin_id)
                cur.execute(
                    'INSERT OR IGNORE INTO pinned (pinterest_pin_id, board_key, source_url) VALUES (?, ?, ?)',
                    (pin_id, board_key, c.get('link'))
                )
                conn.commit()
                picked.append(pin_id)
                sleep_fn()
                break
            except Exception as e:
                print('Failed saving pin', e)
                time.sleep(2)
                continue
    conn.close()
    return picked
