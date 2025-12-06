import random, time
import logging
from .pinterest_api import search_boards, list_pins_on_board, save_pin_to_board
from .db import get_conn

logger = logging.getLogger("pinterest-agent")
logger.setLevel(logging.DEBUG)


def pick_quality_pins(items, min_saves=0):
    out = []
    for it in items:
        # Pinterest API v5 uses 'aggregated_pin_data' for engagement metrics
        # TODO: Find correct way to extract saves. API does not currently return that data
        # saves = it.get("aggregated_pin_data", {}).get("save_count") or 0
        saves = 100

        # We need a source link to track the pin if not provided by the API directly
        source_link = it.get("link")

        if not source_link:
            continue

        try:
            saves_int = int(saves)
        except Exception:
            saves_int = 0

        # Check quality/engagement threshold
        if saves_int < min_saves:
            continue

        out.append(it)

    return out


def repin_for_board(board_key, board_cfg, quota, filters, sleep_fn):
    keywords = board_cfg.get("keywords", [])
    picked = []
    conn = get_conn()
    cur = conn.cursor()

    attempts = 0
    while len(picked) < quota and attempts < quota * 10:
        attempts += 1

        q = random.choice(keywords)
        logger.info("Attempt %s: Searching boards for keyword: %s", attempts, q)

        # Search for relevant SOURCE boards
        # Note: This currently only returns the authorized user's boards (API v5 limitation).
        # TODO: Refactor discovery to pull random, external pins from the explore feed.
        try:
            source_boards = search_boards(q, limit=5)
        except Exception as e:
            logger.warning("search_boards failed: %s", e)
            time.sleep(2)
            continue

        random.shuffle(source_boards)

        # Iterate through found boards to find unsearched one
        source_board_id = None
        source_board_name = None
        for sb in source_boards:
            sb_id = sb.get("id")

            # Check if this board has been searched recently
            cur.execute(
                "SELECT 1 FROM searched_boards WHERE source_board_id = ?", (sb_id,)
            )
            if cur.fetchone():
                logger.debug("Skipping already searched board: %s", sb_id)

                continue

            source_board_id = sb_id
            source_board_name = sb.get("name")
            break

        if not source_board_id:
            logger.info("No new source boards found for keyword %s after filtering.", q)
            continue

        # List pins from the selected source board
        try:
            logger.info(
                "Listing pins from new source board: %s (%s)",
                source_board_name,
                source_board_id,
            )
            items = list_pins_on_board(source_board_id, limit=50)

            cur.execute(
                "INSERT OR IGNORE INTO searched_boards (source_board_id) VALUES (?)",
                (source_board_id,),
            )
            conn.commit()

        except Exception as e:
            logger.warning("list_pins_on_board failed for %s: %s", source_board_id, e)
            time.sleep(2)
            continue

        # Filter pins by quality and shuffle for randomness
        candidates = pick_quality_pins(items, min_saves=filters.get("min_saves", 5))
        random.shuffle(candidates)

        # Attempt to repin candidates
        for c in candidates:
            pin_id = c.get("id")
            if not pin_id:
                continue

            if c.get("creative_type") == "IDEA":
                logger.debug("Skipping Pin %s: It is an Idea Pin.", pin_id)
                continue

            cur.execute("SELECT 1 FROM pinned WHERE pinterest_pin_id = ?", (pin_id,))
            if cur.fetchone():
                logger.debug("Pin %s already repinned, skipping.", pin_id)
                continue

            try:
                save_pin_to_board(board_cfg["id"], pin_id=pin_id)

                cur.execute(
                    "INSERT OR IGNORE INTO pinned (pinterest_pin_id, board_key, source_url) VALUES (?, ?, ?)",
                    (
                        pin_id,
                        board_key,
                        c.get("link") or f"https://www.pinterest.com/pin/{pin_id}",
                    ),
                )
                conn.commit()
                picked.append(pin_id)
                logger.info("Successfully repinned %s to %s.", pin_id, board_key)

                if len(picked) >= quota:
                    conn.close()
                    return picked

                sleep_fn()
                break

            except Exception as e:
                logger.warning("Failed saving pin %s: %s", pin_id, e)
                time.sleep(2)
                continue

    conn.close()
    return picked
