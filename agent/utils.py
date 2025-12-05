import random, time, math

def human_sleep_between_pins(pin_index, total_pins=7):
    base_windows = [
        (0, 300),    # 0-5 min
        (600, 1800), # 10-30 min
        (900, 2700), # 15-45 min
        (1800, 3600),# 30-60 min
        (900, 2400), # 15-40 min
        (1200, 3000),# 20-50 min
        (1500, 3600) # 25-60 min
    ]
    idx = min(pin_index, len(base_windows)-1)
    low, high = base_windows[idx]
    s = random.uniform(low, high)
    time.sleep(s)
    return s

def short_random_sleep(min_s=2, max_s=6):
    t = random.uniform(min_s, max_s)
    time.sleep(t)
    return t
