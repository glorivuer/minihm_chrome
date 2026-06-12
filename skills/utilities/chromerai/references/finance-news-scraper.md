# Finance News Scraper — Implementation Reference

Architecture: **scraper + cron monitor** (two-job pattern).

## Files

| File | Purpose |
|------|---------|
| `/home/remora/financenews/run_scrape.py` | Scrapes sites, saves .md files, manages state.json |
| `/home/remora/financenews/state.json` | Tracks `last_run`, `daily_seq`, `hashes` |
| `/home/remora/financenews/urls.yaml` | Site list (name, url) |
| `/home/remora/financenews/260609/` | Daily subdirectory with .md files |

## State JSON shape

```json
{
  "last_run": "2026-06-10T14:00:20.556705+08:00",
  "daily_seq": 31,
  "last_date": "260610",
  "hashes": {
    "bbc_bus_260609": "d970e828c942783f",
    "reuters_bus_260609": "3d7d9bd79fc6c2aa"
  }
}
```

Key per site: `{name}_{YYMMDD}` (e.g. `reuters_bus_260610`).

## File naming convention

```
{site}_{YYMMDD}{HH}_{seq:03d}.md
# Example: reuters_bus_26061014_028.md
# HH = Shanghai hour at scrape time
# seq = daily sequence, resets at midnight Shanghai
```

## Cron job schedule

Beijing time 8am–11pm, every hour at `*:02`:

```cron
2 0-15 * * *   # UTC = Beijing 8:02–23:02
```

## ⚠️ CRITICAL PITFALL: `repeat` parameter

When creating a cron job, **do NOT use small `repeat` values**.

- `repeat: 24` → system parses as `N/24` where N is the current completed count
- This can silently limit the job to far fewer runs than expected
- `repeat: 24` with `completed: 8` shows as `8/24` and the job stops running when 8 are done

**Correct approach**: Omit `repeat` entirely for indefinite scheduling, or use a very large value like `repeat: 9999`.

```python
# WRONG — repeat limits total runs
cronjob(action="create", repeat=24, ...)  # stops at 24 total runs

# CORRECT — no repeat cap, schedule governs runs
cronjob(action="create", ...)  # runs forever per schedule
```

## Monitor job prompt pattern

The monitor job reads state.json and the daily directory, then summarizes new files:

```
Read the state file /home/remora/financenews/state.json and check the directory
/home/remora/financenews/ (specifically the daily subdirectory) for new news
markdown files (.md) created in the last 65 minutes.

1. Check 'last_run' in state.json. If current time is during scraper hours
   (8:00–23:00 Beijing) and last_run is older than 2 hours, output a warning.
2. Search for .md files in the daily subdirectory created in the last 65 minutes.
3. If new .md files found: read their content, analyze, output structured summary.
4. If no new files: respond with exactly '[SILENT]' to suppress delivery.
```

## Two-job vs single-job architecture

**Two-job (used here)**:
1. `run_scrape.py` — runs on schedule, scrapes sites, saves .md
2. Monitor job — detects new .md files, summarizes for Telegram

**Why**: Separation of concerns. Scraper is data collection; monitor handles analysis/reporting. Both run on the same schedule.

**Single-job**: Combine scrape + report into one cron job. Simpler but less flexible.

## Verified working pattern

```python
# In run_scrape.py — connect to existing foreground browser first
if is_port_open(9222):
    browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    # Reuses existing window

# Always clear cookies between sites to avoid session tracking
await context.clear_cookies()
page = await context.new_page()
```

## Troubleshooting

- **401 on Reuters/FT**: Sites blocking headless. Use foreground browser and manually clear Cloudflare challenge first.
- **No Telegram reply**: Check (1) cron job `last_run_at` is recent, (2) `repeat` has not been exhausted, (3) monitor job output shows new .md files detected.
- **Port 9222 conflict**: Use fresh `/tmp/chrom_foreground` for one-off launches; use persistent profile dir `/home/remora/financenews/.chrome_profile` for login-preserving sessions.