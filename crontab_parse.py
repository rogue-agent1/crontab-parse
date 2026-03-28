#!/usr/bin/env python3
"""crontab_parse - Parse and explain cron expressions."""
import sys, re
from datetime import datetime, timedelta

FIELDS = ["minute","hour","day_of_month","month","day_of_week"]
MONTHS = {v:i for i,v in enumerate(["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"],1)}
DAYS = {v:i for i,v in enumerate(["sun","mon","tue","wed","thu","fri","sat"])}

def parse_field(s, mn, mx):
    values = set()
    for part in s.split(","):
        step = 1
        if "/" in part: part, step = part.split("/"); step = int(step)
        if part == "*": values.update(range(mn, mx+1, step))
        elif "-" in part:
            a, b = part.split("-"); values.update(range(int(a), int(b)+1, step))
        else: values.add(int(part))
    return sorted(values)

def parse_cron(expr):
    parts = expr.strip().split()
    if len(parts) != 5: raise ValueError("Need 5 fields")
    ranges = [(0,59),(0,23),(1,31),(1,12),(0,6)]
    return {FIELDS[i]: parse_field(parts[i], *ranges[i]) for i in range(5)}

def explain(expr):
    p = expr.strip().split()
    descs = []
    names = ["minute","hour","day of month","month","day of week"]
    for i, (field, name) in enumerate(zip(p, names)):
        if field != "*": descs.append(f"{name}: {field}")
    return "At " + ", ".join(descs) if descs else "Every minute"

def next_run(expr, after=None):
    if after is None: after = datetime.now()
    parsed = parse_cron(expr)
    dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(525960):
        if (dt.minute in parsed["minute"] and dt.hour in parsed["hour"] and
            dt.day in parsed["day_of_month"] and dt.month in parsed["month"] and
            dt.weekday() in [(d-1)%7 for d in parsed["day_of_week"]] if 0 not in parsed["day_of_week"] else True):
            return dt
        dt += timedelta(minutes=1)

if __name__ == "__main__":
    if len(sys.argv) < 3: print("Usage: crontab_parse.py <explain|next|parse> 'expr'"); sys.exit(1)
    cmd, expr = sys.argv[1], sys.argv[2]
    if cmd == "explain": print(explain(expr))
    elif cmd == "next":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        dt = datetime.now()
        for _ in range(n):
            dt = next_run(expr, dt); print(dt.strftime("%Y-%m-%d %H:%M")); dt += timedelta(minutes=1)
    elif cmd == "parse":
        import json; print(json.dumps(parse_cron(expr), indent=2))
