import random, time, math


def human_sleep_between_pins(pin_index, total_pins=7):
    """
    Sleeps for a random, progressively longer duration to mimic human activity
    and stay within the 6-hour GitHub Actions limit (max total sleep ~5.4 hours for 10 pins).
    """
    base_windows = [
        (0, 240),  # 0-4 min
        (300, 1200),  # 5-20 min
        (600, 1800),  # 10-30 min
        (900, 2700),  # 15-45 min
        (600, 1800),  # 10-30 min
        (900, 2400),  # 15-40 min
        (1200, 3000),  # 20-50 min
    ]

    # Use the last window for any index exceeding the list length (pins > 7)
    idx = min(pin_index, len(base_windows) - 1)
    low, high = base_windows[idx]

    s = random.uniform(low, high)
    time.sleep(s)
    return s


def short_random_sleep(min_s=2, max_s=6):
    t = random.uniform(min_s, max_s)
    time.sleep(t)
    return t


def clean_site_url_for_display(url: str) -> str:
    """Removes 'http(s)://' and 'www.' and capitalizes the first letter."""
    if url.startswith("http://"):
        url = url[len("http://") :]
    elif url.startswith("https://"):
        url = url[len("https://") :]

    if url.startswith("www."):
        url = url[len("www.") :]

    if url:
        url = url[0].upper() + url[1:]

    if url.endswith("/"):
        url = url[:-1]

    return url
