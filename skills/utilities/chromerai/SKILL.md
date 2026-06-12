---
name: chromerai
description: "AI-assisted stealth browser automation. Control Chrome/Chromium in the foreground (headed), attach to user sessions, scrape protected pages, support manual/automatic login state retention across custom profiles, and run multi-step JSON/YAML workflows. Triggered when user includes '@chromerai' or asks to automate/open Chrome."
version: 1.0.0
author: Antigravity Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [browser, chrome, chromium, automation, stealth, scrape, workflow, cdp]
    triggers: ["@chromerai", "open chrome", "stealth browser", "chrome automation", "网页抓取", "前台打开浏览器", "浏览器自动登录"]
---

# @chromerai Stealth Browser Skill

This skill enables MiniHermes to launch and control a foreground Chrome/Chromium browser using the stealth DevTools Protocol (CDP) connector. It allows the agent to scrape protected web content to clean Markdown, run multi-step automation workflows, and isolate persistent login states across multiple user profiles.

---

## 🛠️ Supported Workflows & CLI Commands

All commands execute through the wrapper script:
`/home/remora/myapp/ref/chrom_front/start_chrom_front.sh`

### 1. Scrape Webpage to Markdown
Launches the browser, navigates to the target URL, strips layout boilerplates, and converts main content to clean Markdown.
- **Default Profile**:
  ```bash
  /home/remora/myapp/ref/chrom_front/start_chrom_front.sh scrape [URL] -o [output_file.md]
  ```
- **Custom Profile**:
  ```bash
  /home/remora/myapp/ref/chrom_front/start_chrom_front.sh --profile [profile_name] scrape [URL] -o [output_file.md]
  ```

### 2. Open Blank Browser for Manual Operations / Logins
Launches the browser window and opens a blank page (`about:blank`).
- **Command**:
  ```bash
  /home/remora/myapp/ref/chrom_front/start_chrom_front.sh --profile [profile_name] open
  ```
- **Execution Flow**:
  1. The agent launches the command. The terminal command blocks, waiting for standard input.
  2. The agent pauses and informs the user: *"Blank browser window opened under profile '[profile_name]'. Please log in to your account manually in the browser window. Press Enter in the chat when done."*
  3. Once the user performs the manual login, they reply to the agent.
  4. The agent sends an empty input (Enter key) to the blocked terminal command.
  5. The browser process detaches, and all login credentials (cookies, localStorage) are persisted inside the profile directory.

### 3. Run Saved Step-by-Step Workflows
Executes a pre-defined JSON/YAML workflow sequence (saved in `/home/remora/myapp/ref/chrom_front/workflows/`).
- **Command**:
  ```bash
  /home/remora/myapp/ref/chrom_front/start_chrom_front.sh --profile [profile_name] run [workflow_name] -v "[key1=val1,key2=val2]"
  ```
- **Example (Post a Tweet)**:
  ```bash
  /home/remora/myapp/ref/chrom_front/start_chrom_front.sh --profile twitter_profile run post_tweet -v "text=Hello from my automated AI agent!"
  ```

---

## ⚙️ Profile Directories and Ports

Profiles are isolated and persistent. They are mapped deterministically to local directories and TCP ports to prevent overlaps:
- **Profile Directory**: `~/.config/chrom_front_profile_[profile_name]` (or `~/.config/chrom_front_profile` for "default").
- **Port Mapping**:
  - `default` profile: Port `9222`
  - Other profiles: Port `9223 + offset` (calculated deterministically by sum of ASCII characters in profile name)

## ⚙️ Environment & Startup Troubleshooting

### Foreground Browser (Visible Desktop) — Linux with X11/lightdm/xrdp

**⚠️ MANDATORY: ALL @chromerai operations MUST use foreground (headed) browser. Never use headless.**

When the environment has a desktop (DISPLAY is set, e.g., `:10` from xrdp/lightdm), use this exact pattern:

```bash
rm -rf /tmp/chrom_foreground && mkdir -p /tmp/chrom_foreground

# CRITICAL: Use 'env' prefix, not inline DISPLAY=X. The env vars must come BEFORE the command.
env DISPLAY=:10 XAUTHORITY=/home/remora/.Xauthority \
  /snap/chromium/3458/usr/lib/chromium-browser/chrome \
    --no-sandbox \
    --disable-gpu \
    --remote-debugging-port=9222 \
    --user-data-dir=/tmp/chrom_foreground \
    --no-first-run \
    --no-default-browser-check
```

| Parameter | Purpose |
|-----------|---------|
| `env DISPLAY=:10` | Target the active X11 session (check with `echo $DISPLAY`) |
| `XAUTHORITY=...` | Point to the X authentication cookie path |
| `--no-sandbox` | Required in containerized/remote desktop environments |
| `--disable-gpu` | Disable GPU hardware acceleration |
| `--user-data-dir=/tmp/chrom_foreground` | **Always use a fresh temp directory** to avoid SingletonLock conflicts |
| Chromium binary | Use `/snap/chromium/3458/usr/lib/chromium-browser/chrome` (not `/usr/bin/chromium-browser`) |

**Why `env` prefix?** Without it, DISPLAY/XAUTHORITY are interpreted as arguments to chromium-browser, not environment variables. The shell expands `env VARIABLE=value command` correctly inside `terminal()` background mode.

**Background process pattern:**
```bash
terminal(background=true, command="rm -rf /tmp/chrom_foreground && mkdir -p /tmp/chrom_foreground && env DISPLAY=:10 XAUTHORITY=/home/remora/.Xauthority /snap/chromium/3458/usr/lib/chromium-browser/chrome --no-sandbox --disable-gpu --remote-debugging-port=9222 --user-data-dir=/tmp/chrom_foreground --no-first-run --no-default-browser-check")
```

### asyncio.run() conflict
The `chrom_front` wrapper script uses `asyncio.run()` internally. When called via `terminal()` (which runs inside an existing asyncio event loop), it fails with:
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```
**Workaround**: Invoke Chromium directly instead of through the wrapper:
```bash
/usr/bin/chromium-browser --headless=new --no-sandbox --disable-gpu \
  --remote-debugging-port=9223 \
  --user-data-dir=/tmp/chrom_session \
  --disable-dev-shm-usage
```

### SingletonLock / Permission denied
Chromium refuses to start if `~/.config/chrom_front_profile/SingletonLock` exists or has wrong ownership:
```
Failed to create /home/remora/.config/chrom_front_profile/SingletonLock: Permission denied (13))
```
**Workaround**: Always use a fresh temp directory for user-data-dir:
```bash
rm -rf /tmp/chrom_fresh && mkdir -p /tmp/chrom_fresh
/usr/bin/chromium-browser --headless=new --no-sandbox ... --user-data-dir=/tmp/chrom_fresh
```

### Headless / Containerized Environments

**FOR @chromerai: Headless mode is NOT supported.** All chromerai operations require foreground (headed) browser to avoid anti-bot detection.

If headless is needed for other purposes (non-chromerai), typical flags:
| Flag | Purpose |
|------|---------|
| `--headless=new` | Run without visible window |
| `--no-sandbox` | Required in containerized environments |
| `--disable-gpu` | Disable GPU hardware acceleration |
| `--disable-dev-shm-usage` | Avoid shared memory issues in containers |

### Python venv Bootstrapping (when ensurepip/pip unavailable)

Some environments (minimal Debian installs, containers) lack both `pip` and `ensurepip`. The standard `python3 -m venv` fails with:

```
The virtual environment was not created successfully because ensurepip is not
available. On Debian/Ubuntu systems, you need to install the python3-venv
package using: apt install python3.12-venv
```

**Workaround — two-step venv bootstrap:**

```bash
# Step 1: Create venv without pip
python3 -m venv --without-pip /path/to/.venv

# Step 2: Bootstrap pip via get-pip.py
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
/path/to/.venv/bin/python3 /tmp/get-pip.py
```

**Then install packages normally:**
```bash
/path/to/.venv/bin/pip install playwright pyyaml
/path/to/.venv/bin/playwright install chromium
```

**Key insight**: `--without-pip` bypasses the ensurepip check entirely. The venv is fully functional; you just need to install pip manually afterward.

This pattern is required when:
- `pip3` / `pip` commands not found in PATH
- `python3 -m pip` fails with "externally-managed-environment" and pipx not available
- `apt-get install python3-venv` requires root and fails

### Cloudflare / Bot Protection Bypass
Cloudflare-protected sites (e.g., Reuters) can detect CDP-based automation and block with `ERR_BLOCKED_BY_RESPONSE`.

**Workaround**: User must manually navigate to the target site in the browser first and complete any Cloudflare CAPTCHA/challenge. Once the session has valid Cloudflare clearance cookies, CDP automation can access the page content.

**Verification**:
```python
# Check if page is blocked
page_title = await page.title()
page_content = await page.inner_text("body")
if "blocked" in page_content.lower() or "err_blocked" in page_content.lower():
    # Cloudflare is blocking - user needs to complete challenge manually
```

### 5. Persistent Login Windows (Headed Mode)
When scraping sites that require manual login or CAPTCHA clearance (like Reuters/Cloudflare), do NOT call `browser.close()` at the end of the script.
- **Technique**: Launch the browser in a background Popen process with a fixed `--user-data-dir`. In the Playwright script, connect via `connect_over_cdp`. After scraping, stop the Playwright connection but leave the Chromium process running.
- **Benefit**: The user can see the window on their remote desktop (DISPLAY=:10), perform a manual login once, and subsequent automated runs will reuse the persistent session cookies/state.

---

## 🐍 Direct Python CDP Scraping (Recommended)

The `start_chrom_front.sh` wrapper has a bug in `connector.py` — `connect_over_cdp()` returns a `Browser` object, NOT a `BrowserContext`. Calling `.pages` directly on the browser fails. Use this pattern instead:

```python
#!/usr/bin/env python3
import asyncio
from pathlib import Path

async def scrape():
    from playwright.async_api import async_playwright

    endpoint = "http://127.0.0.1:9222"
    p = await async_playwright().start()

    try:
        browser = await p.chromium.connect_over_cdp(endpoint)
        # Get existing pages from browser.contexts, NOT browser.pages
        contexts = browser.contexts
        page = contexts[0].pages[-1] if contexts and contexts[0].pages else await browser.new_page()

        # Navigate (reuses existing page, doesn't create new tab)
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)  # Wait for JS rendering

        title = await page.title()
        text = await page.inner_text("body")

        Path("/home/remora/output.md").write_text(f"# {title}\n\n{text}", encoding="utf-8")
        await browser.close()
        await p.stop()
    except Exception as e:
        print(f"Error: {e}")
        await p.stop()

asyncio.run(scrape())
```

**Run with:** `python3 /path/to/script.py`
**Or with project venv:** `/home/remora/financenews/.venv/bin/python /path/to/script.py`

### Full Example: Hourly Finance News Scraper

See `references/finance-news-scraper.md` for a complete implementation including:
- Foreground browser only (no headless for @chromerai)
- Hash-based content deduplication
- Daily sequence resetting
- Cron-schedulable structure

### ⚠️ Critical: `repeat` parameter with cron jobs

When scheduling cron jobs via `cronjob(action="create")`, **omit `repeat` or use a very large value**. Small values like `repeat: 24` can be parsed as `N/max` and cause the job to stop prematurely.

```python
# WRONG — repeat exhausts early
cronjob(action="create", repeat=24, schedule="0 8-23 * * *", ...)

# CORRECT — no repeat cap, schedule governs
cronjob(action="create", schedule="0 8-23 * * *", ...)
```

See `references/finance-news-scraper.md` for the full incident case study.

### Key CDP Patterns

| Need | Correct Approach |
|------|-----------------|
| List pages | `browser.contexts[0].pages` (not `browser.pages`) |
| Navigate existing page | `page.goto(url)` — reuses the page, doesn't open new tab |
| Create new tab | `browser.new_page()` — opens in same browser window |
| Check port | `curl -s http://localhost:9222/json/version` |

### Workflow: Scrape with Existing Browser Created by chromerai

1. **Check port priority** — determine if a foreground browser is available first:
   ```bash
   # Check 9223 first (foreground browser on :10)
   curl -s -m 1 http://localhost:9223/json/version && echo "Port 9223 active" || \
   # Fall back to 9222 (headless browser)
   curl -s -m 1 http://localhost:9222/json/version && echo "Port 9222 active" || \
   echo "No existing browser"
   ```
   | Port | Typical use |
   |------|-------------|
   | 9222 | Primary debug port — used by BOTH foreground and headless browsers |

1. **Check 9222 first** — determine if a browser is already running:
   ```bash
   curl -s -m 1 http://localhost:9222/json/version && echo "Browser active" || echo "No browser"
   ```
   If active, connect via CDP and navigate (reuses existing page/tab):
   ```python
   browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
   page = browser.contexts[0].pages[-1] if browser.contexts[0].pages else await browser.new_page()
   await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
   ```

4. **Wait for dynamic content**: Add `await asyncio.sleep(3)` after goto for JS-heavy pages

5. **Extract content**: Use `page.inner_text("body")` for readable text

### Quick verification
After starting, verify the debugging port is responding:
```bash
curl -s http://localhost:9223/json/version
```

## ⚠️ Safety & Confirmation Guidelines

## ⚠️ Safety & Confirmation Guidelines

1. **Gating Check**: Sensitive workflows (submitting forms, sending messages, importing/copying cookie files) require the agent to describe the action to the user and obtain explicit confirmation before running.
2. **Foreground Window**: Because the browser runs in headed mode, the user will see the window pop up. Warn the user before launching.
