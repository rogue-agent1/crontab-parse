#!/usr/bin/env python3
"""crontab_parse - Cron expression parser and next-run calculator."""
import sys, time
from datetime import datetime, timedelta

def parse_field(field, min_val, max_val):
    values = set()
    for part in field.split(","):
        if "/" in part:
            range_part, step = part.split("/")
            step = int(step)
            if range_part == "*":
                start, end = min_val, max_val
            elif "-" in range_part:
                start, end = map(int, range_part.split("-"))
            else:
                start, end = int(range_part), max_val
            values.update(range(start, end + 1, step))
        elif "-" in part:
            start, end = map(int, part.split("-"))
            values.update(range(start, end + 1))
        elif part == "*":
            values.update(range(min_val, max_val + 1))
        else:
            values.add(int(part))
    return values

def parse_cron(expr):
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"Expected 5 fields, got {len(parts)}")
    return {
        "minute": parse_field(parts[0], 0, 59),
        "hour": parse_field(parts[1], 0, 23),
        "day": parse_field(parts[2], 1, 31),
        "month": parse_field(parts[3], 1, 12),
        "dow": parse_field(parts[4], 0, 6),
    }

def matches(cron, dt):
    return (dt.minute in cron["minute"] and dt.hour in cron["hour"] and
            dt.day in cron["day"] and dt.month in cron["month"] and
            dt.weekday() in cron["dow"])  # Python: Mon=0, cron: Sun=0... adjust below

def next_run(expr, after=None):
    cron = parse_cron(expr)
    if after is None:
        after = datetime.now()
    dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(525960):  # max 1 year of minutes
        # cron dow: 0=Sun, Python weekday: 0=Mon. Convert:
        py_dow = (dt.weekday() + 1) % 7
        if (dt.minute in cron["minute"] and dt.hour in cron["hour"] and
            dt.day in cron["day"] and dt.month in cron["month"] and
            py_dow in cron["dow"]):
            return dt
        dt += timedelta(minutes=1)
    return None

def describe(expr):
    parts = expr.split()
    descs = []
    if parts[0] != "*": descs.append(f"minute {parts[0]}")
    if parts[1] != "*": descs.append(f"hour {parts[1]}")
    if parts[2] != "*": descs.append(f"day {parts[2]}")
    if parts[3] != "*": descs.append(f"month {parts[3]}")
    if parts[4] != "*": descs.append(f"dow {parts[4]}")
    return ", ".join(descs) if descs else "every minute"

def test():
    cron = parse_cron("*/5 * * * *")
    assert 0 in cron["minute"] and 5 in cron["minute"] and 3 not in cron["minute"]
    cron2 = parse_cron("0 9 * * 1-5")
    assert cron2["hour"] == {9}
    assert cron2["dow"] == {1, 2, 3, 4, 5}
    # next run
    base = datetime(2026, 3, 29, 12, 0)
    nr = next_run("30 14 * * *", after=base)
    assert nr.hour == 14 and nr.minute == 30
    # every 5 min
    nr2 = next_run("*/5 * * * *", after=datetime(2026, 1, 1, 0, 3))
    assert nr2.minute == 5
    assert describe("0 9 * * 1-5") == "minute 0, hour 9, dow 1-5"
    print("OK: crontab_parse")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test()
    else:
        print("Usage: crontab_parse.py test")
