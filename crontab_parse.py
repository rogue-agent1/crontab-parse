#!/usr/bin/env python3
"""crontab_parse — Parse, validate, and list crontab entries.

Usage:
    crontab_parse.py list
    crontab_parse.py list --user root
    crontab_parse.py validate "0 */2 * * 1-5 /usr/bin/backup.sh"
    crontab_parse.py explain "30 4 1,15 * * /path/to/script"
    crontab_parse.py search "backup"
    crontab_parse.py next "0 9 * * MON-FRI" --count 5
"""

import sys
import os
import re
import json
import argparse
import subprocess
from datetime import datetime, timedelta


FIELD_NAMES = ['minute', 'hour', 'day_of_month', 'month', 'day_of_week']
FIELD_RANGES = {
    'minute': (0, 59),
    'hour': (0, 23),
    'day_of_month': (1, 31),
    'month': (1, 12),
    'day_of_week': (0, 7),  # 0 and 7 = Sunday
}

MONTH_NAMES = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
               'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
DOW_NAMES = {'sun':0,'mon':1,'tue':2,'wed':3,'thu':4,'fri':5,'sat':6}

SPECIAL = {
    '@yearly': '0 0 1 1 *',
    '@annually': '0 0 1 1 *',
    '@monthly': '0 0 1 * *',
    '@weekly': '0 0 * * 0',
    '@daily': '0 0 * * *',
    '@midnight': '0 0 * * *',
    '@hourly': '0 * * * *',
    '@reboot': '@reboot',
}


def expand_field(field: str, field_name: str) -> list:
    """Expand a cron field to a list of matching values."""
    lo, hi = FIELD_RANGES[field_name]
    
    if field == '*':
        return list(range(lo, hi + 1))
    
    values = set()
    for part in field.split(','):
        # Handle step: */5 or 1-10/2
        step = 1
        if '/' in part:
            part, step_str = part.split('/', 1)
            step = int(step_str)
        
        if part == '*':
            for v in range(lo, hi + 1, step):
                values.add(v)
        elif '-' in part:
            a, b = part.split('-', 1)
            # Handle names
            a = _resolve_name(a, field_name)
            b = _resolve_name(b, field_name)
            for v in range(int(a), int(b) + 1, step):
                values.add(v)
        else:
            v = _resolve_name(part, field_name)
            values.add(int(v))
    
    return sorted(values)


def _resolve_name(val: str, field_name: str) -> int:
    val = val.strip().lower()
    if field_name == 'month' and val in MONTH_NAMES:
        return MONTH_NAMES[val]
    if field_name == 'day_of_week' and val in DOW_NAMES:
        return DOW_NAMES[val]
    return int(val)


def explain_field(field: str, field_name: str) -> str:
    if field == '*':
        return f'every {field_name.replace("_", " ")}'
    values = expand_field(field, field_name)
    if len(values) == 1:
        return f'{field_name.replace("_", " ")} {values[0]}'
    if len(values) <= 5:
        return f'{field_name.replace("_", " ")} {",".join(map(str, values))}'
    return f'{field_name.replace("_", " ")} ({len(values)} values: {values[0]}-{values[-1]})'


def parse_cron_line(line: str) -> dict:
    """Parse a crontab line into schedule + command."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    # Handle special schedules
    for special, expansion in SPECIAL.items():
        if line.startswith(special):
            cmd = line[len(special):].strip()
            if expansion == '@reboot':
                return {'schedule': '@reboot', 'command': cmd, 'fields': None}
            return parse_cron_line(f'{expansion} {cmd}')
    
    # Handle environment variables
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', line):
        return {'type': 'env', 'line': line}
    
    parts = line.split(None, 5)
    if len(parts) < 6:
        return None
    
    fields = parts[:5]
    command = parts[5]
    
    return {
        'schedule': ' '.join(fields),
        'command': command,
        'fields': dict(zip(FIELD_NAMES, fields)),
    }


def cmd_list(args):
    try:
        cmd = ['crontab', '-l']
        if args.user:
            cmd = ['crontab', '-l', '-u', args.user]
        result = subprocess.run(cmd, capture_output=True, text=True)
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    
    entries = []
    for line in lines:
        parsed = parse_cron_line(line)
        if parsed:
            entries.append(parsed)
    
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        if not entries:
            print('No crontab entries found')
        for e in entries:
            if e.get('type') == 'env':
                print(f'  ENV: {e["line"]}')
            else:
                print(f'  {e["schedule"]:20s}  {e["command"]}')


def cmd_validate(args):
    parsed = parse_cron_line(args.entry)
    if not parsed or not parsed.get('fields'):
        print('❌ Invalid crontab entry')
        sys.exit(1)
    
    errors = []
    for name, value in parsed['fields'].items():
        try:
            expand_field(value, name)
        except (ValueError, KeyError) as e:
            errors.append(f'{name}: {e}')
    
    if errors:
        print('❌ Validation errors:')
        for e in errors:
            print(f'  {e}')
        sys.exit(1)
    else:
        print(f'✅ Valid: {parsed["schedule"]}')
        print(f'   Command: {parsed["command"]}')


def cmd_explain(args):
    # Handle bare schedule or full entry
    entry = args.entry
    parts = entry.split()
    if len(parts) == 5:
        entry += ' <command>'
    
    parsed = parse_cron_line(entry)
    if not parsed or not parsed.get('fields'):
        print('Cannot parse cron expression')
        sys.exit(1)
    
    print(f'Schedule: {parsed["schedule"]}')
    print(f'Command:  {parsed["command"]}')
    print()
    for name, value in parsed['fields'].items():
        expanded = expand_field(value, name)
        explanation = explain_field(value, name)
        print(f'  {name:15s}: {value:10s} → {explanation}')


def cmd_search(args):
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
    except Exception:
        lines = []
    
    pattern = re.compile(args.pattern, re.IGNORECASE)
    for line in lines:
        if pattern.search(line):
            print(line)


def cmd_next(args):
    """Calculate next N execution times for a cron expression."""
    parts = args.expr.split()
    if len(parts) != 5:
        print('Need exactly 5 cron fields')
        sys.exit(1)
    
    fields = dict(zip(FIELD_NAMES, parts))
    expanded = {name: expand_field(val, name) for name, val in fields.items()}
    
    now = datetime.now()
    current = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    
    found = 0
    max_iter = 525960  # ~1 year of minutes
    for _ in range(max_iter):
        # Convert Python weekday (Mon=0..Sun=6) to cron (Sun=0, Mon=1..Sat=6)
        cron_dow = (current.weekday() + 1) % 7
        dow_match = cron_dow in expanded['day_of_week'] or (7 in expanded['day_of_week'] and cron_dow == 0)
        if (current.minute in expanded['minute'] and
            current.hour in expanded['hour'] and
            current.day in expanded['day_of_month'] and
            current.month in expanded['month'] and
            dow_match):
            
            delta = current - now
            print(f'  {current.strftime("%Y-%m-%d %H:%M %a"):25s}  (in {_format_delta(delta)})')
            found += 1
            if found >= args.count:
                break
        
        current += timedelta(minutes=1)
    
    if found == 0:
        print('No matches found within 1 year')


def _format_delta(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total < 3600:
        return f'{total // 60}m'
    if total < 86400:
        return f'{total // 3600}h {(total % 3600) // 60}m'
    return f'{total // 86400}d {(total % 86400) // 3600}h'


def main():
    p = argparse.ArgumentParser(description='Crontab parser and manager')
    p.add_argument('--json', action='store_true')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('list', help='List crontab entries')
    s.add_argument('--user')
    s.set_defaults(func=cmd_list)

    s = sub.add_parser('validate', help='Validate a crontab entry')
    s.add_argument('entry')
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser('explain', help='Explain a cron expression')
    s.add_argument('entry')
    s.set_defaults(func=cmd_explain)

    s = sub.add_parser('search', help='Search crontab for pattern')
    s.add_argument('pattern')
    s.set_defaults(func=cmd_search)

    s = sub.add_parser('next', help='Show next execution times')
    s.add_argument('expr', help='Cron expression (5 fields)')
    s.add_argument('--count', type=int, default=5)
    s.set_defaults(func=cmd_next)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
