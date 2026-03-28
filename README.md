# crontab_parse

Parse, validate, explain, and inspect crontab entries. Show next execution times.

## Usage

```bash
# List current crontab
python3 crontab_parse.py list

# Explain a cron expression
python3 crontab_parse.py explain "30 4 1,15 * * /path/to/script"

# Validate entry
python3 crontab_parse.py validate "0 */2 * * 1-5 /usr/bin/backup.sh"

# Show next 5 execution times
python3 crontab_parse.py next "0 9 * * MON-FRI" --count 5

# Search crontab
python3 crontab_parse.py search "backup"
```

## Zero dependencies. Single file. Python 3.8+.
