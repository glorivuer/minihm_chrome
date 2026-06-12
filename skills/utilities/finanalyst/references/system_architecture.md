# Finance News Scraper System Architecture

This document maps the actual implementation found in `/home/remora/financenews/` as of June 2026.

## ⚙️ Core Components

| Component | Path | Trigger | Description |
| :--- | :--- | :--- | :--- |
| **Scraper Script** | `run_scrape.py` | System Crontab | Uses Playwright (CDP) to scrape Reuters, FT, BBC. |
| **Scraper Wrapper** | `run_scrape.sh` | System Crontab | Shell wrapper for `run_scrape.py`. |
| **Analyzer Script** | `news_analyzer.py` | Hermes Cronjob | Summarizes news using LLM. |
| **Analyzer Wrapper**| `run_hourly_scraper.sh`| Hermes Cronjob | Shell wrapper for `news_analyzer.py`. |
| **State Storage** | `state.json` | Internal | Tracks `last_run`, `daily_seq`, and content `hashes`. |
| **URL Config** | `urls.yaml` | Internal | List of target news sites. |
| **Logs** | `run.log` | - | Combined output of the scraper. |

## 🔄 Execution Flow

1.  **System Crontab** (`0 0-15 * * *`) runs `run_scrape.sh`.
    - Navigates to `https://www.reuters.com/business/`, `https://www.ft.com/markets`, etc.
    - Compares current body text hash against `state.json`.
    - If hash differs: Saves `{site}_{YYMMDD}{HH}_{seq}.md` to `/home/remora/financenews/{YYMMDD}/`.
    - If hash same: Skips file creation.
2.  **Hermes Cronjob** (`2 0-15 * * *`) runs `run_hourly_scraper.sh`.
    - Scans for files created in the last 65 minutes.
    - Aggregates content and sends to LLM for strategy analysis.
    - Saves report to `/home/remora/financenews/analysis/{YYMMDD}/hourly_analysis_{HH}.md`.

## 🛠️ Key Files & Paths
- **Base Directory**: `/home/remora/financenews/`
- **Venv**: `/home/remora/myapp/minihm/.venv/` (contains Playwright/OpenAI)
- **Display**: `:10` (requires `XAUTHORITY=/home/remora/.Xauthority`)
