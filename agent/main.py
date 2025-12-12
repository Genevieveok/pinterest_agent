#!/usr/bin/env python3
import os, random, time, logging
import threading
from .config_loader import load_yaml_with_env
from .db import init_db, get_conn
from .repin_engine import repin_for_board
from .blog_scraper import fetch_sitemap_posts, extract_post_meta
from .generator import build_aesthetic_image, upload_image_to_github
from .pinterest_api import save_pin_to_board
from .utils import (
    human_sleep_between_pins,
    short_random_sleep,
    clean_site_url_for_display,
)

from .globals import CONFIG, PINTEREST_ACCESS_TOKEN, REQUIRED_SCOPES

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pinterest-agent")
logger.setLevel(logging.DEBUG)

BASE = os.path.dirname(__file__)
BOARDS = load_yaml_with_env(os.path.join(BASE, "boards.yml"))["boards"]
REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
IMAGE_HOST_BRANCH = (
    os.getenv("IMAGE_HOST_BRANCH") or CONFIG.get("image_host_branch") or "gh-pages"
)
SITE_URL = os.getenv("SITE_URL") or CONFIG.get("site")
CLEAN_SITE_URL = clean_site_url_for_display(SITE_URL)
repinned_results = []
created_results = []


def safe_run_with_retries(func, attempts=3, delay=5, *args, **kwargs):
    for i in range(attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning("Attempt %s failed: %s", i + 1, e)
            time.sleep(delay * (i + 1))
    logger.error(
        "All %s attempts failed for %s", attempts, getattr(func, "__name__", str(func))
    )
    return None


def run_repins():
    repins_needed = CONFIG["daily_pins"]["repins"]
    board_keys = list(BOARDS.keys())
    selected_boards = [random.choice(board_keys) for _ in range(repins_needed)]
    filters = CONFIG.get("filters", {})
    all_picked = []
    for idx, bk in enumerate(selected_boards):
        cfg = BOARDS[bk]
        picked = safe_run_with_retries(
            repin_for_board,
            attempts=3,
            delay=3,
            board_key=bk,
            board_cfg=cfg,
            quota=1,
            filters=filters,
            sleep_fn=lambda: short_random_sleep(2, 6),
        )
        if picked:
            all_picked.extend(picked)
        human_sleep_between_pins(
            idx, total_pins=repins_needed + CONFIG["daily_pins"]["new_pins"]
        )
    return all_picked


def run_new_pins():
    new_needed = CONFIG["daily_pins"]["new_pins"]
    posts = fetch_sitemap_posts(SITE_URL, limit=200)
    random.shuffle(posts)

    created_new = []

    for idx, p in enumerate(posts):
        if len(created_new) >= new_needed:
            break

        # Database Check for Existing Pin
        # Open connection only for this quick read
        conn_check = get_conn()
        cur_check = conn_check.cursor()
        cur_check.execute("SELECT 1 FROM blog_pins WHERE post_url = ?", (p,))
        pin_exists = cur_check.fetchone()
        conn_check.close()

        if pin_exists:
            continue

        meta = safe_run_with_retries(extract_post_meta, attempts=2, delay=2, post_url=p)
        if not meta:
            continue

        matched_board_key = None
        for bk, bcfg in BOARDS.items():
            for k in bcfg.get("keywords", []):
                # Ensure checking against a sequence (keywords is list/tuple)
                if k.lower() in [kw.lower() for kw in meta.get("keywords", [])]:
                    matched_board_key = bk
                    break
            if matched_board_key:
                break
        if not matched_board_key:
            matched_board_key = random.choice(list(BOARDS.keys()))
        matched_board = BOARDS[matched_board_key]

        title_for_image = meta.get("title")
        if not title_for_image:
            title_for_image = f"More on {CLEAN_SITE_URL}"

        # Image Generation and Upload
        use_ai = CONFIG.get("use_ai_generation", True) and bool(REPLICATE_TOKEN)
        local_img = None
        if use_ai:
            local_img = safe_run_with_retries(
                build_aesthetic_image,
                attempts=2,
                delay=5,
                background_url=meta.get("url"),
                title_text=title_for_image,
            )
        if not local_img:
            local_img = safe_run_with_retries(
                build_aesthetic_image,
                attempts=1,
                delay=1,
                background_url=meta.get("image"),
                title_text=title_for_image,
            )
        if not local_img:
            continue

        public_url = None
        try:
            public_url = upload_image_to_github(
                local_img,
                repo=GITHUB_REPO,
                branch=IMAGE_HOST_BRANCH,
                token=os.getenv("GITHUB_TOKEN"),
            )
        except Exception as e:
            logger.warning(
                "upload_image_to_github failed, falling back to meta image: %s", e
            )
            public_url = meta.get("image")
        if not public_url:
            logger.info("No public image available for %s, skipping", p)
            continue

        res = safe_run_with_retries(
            save_pin_to_board,
            attempts=2,
            delay=3,
            board_id=matched_board["id"],
            image_url=public_url,
            title=meta.get("title"),
            description=meta.get("description"),
            link=SITE_URL,
        )
        if not res:
            continue

        pin_id = res.get("id")
        if pin_id:
            # Database Write
            # Open new connection only for the write/commit
            conn_write = get_conn()
            cur_write = conn_write.cursor()
            cur_write.execute(
                "INSERT OR IGNORE INTO blog_pins (post_url, pinterest_pin_id) VALUES (?, ?)",
                (p, pin_id),
            )
            conn_write.commit()
            conn_write.close()

            created_new.append(pin_id)

        human_sleep_between_pins(
            idx + CONFIG["daily_pins"]["repins"],
            total_pins=CONFIG["daily_pins"]["repins"]
            + CONFIG["daily_pins"]["new_pins"],
        )

    return created_new


def run_repins_threaded():
    global repinned_results
    repinned_results = run_repins()


def run_new_pins_threaded():
    global created_results
    created_results = run_new_pins()


def main():
    logger.info("Starting Pinterest Agent")
    init_db()

    logger.info("Fetching Pinterest Access Token...")
    try:
        PINTEREST_ACCESS_TOKEN.fetch(scopes=REQUIRED_SCOPES)
        logger.info("Token fetched successfully.")
    except Exception as e:
        logger.error("Failed to fetch/refresh Pinterest token: %s. Exiting.", e)
        return

    logger.info("Starting repinning and new pin creation in parallel threads.")

    # Create thread objects
    repin_thread = threading.Thread(target=run_repins_threaded)
    new_pin_thread = threading.Thread(target=run_new_pins_threaded)

    # Start threads
    repin_thread.start()
    new_pin_thread.start()

    # Wait for both threads to complete
    # This ensures main() doesn't exit until both repinning and new pin creation are done.
    repin_thread.join()
    new_pin_thread.join()

    # Use the results captured globally
    logger.info(
        "Done. Repinned: %s New pins: %s", len(repinned_results), len(created_results)
    )


if __name__ == "__main__":
    main()
