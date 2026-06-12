#!/usr/bin/env python3
"""
Finance News Scraper - Uses foreground browser only (no headless)
"""
import asyncio
import json
import hashlib
import sys
import socket
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import yaml
import subprocess

BASE_DIR = Path("/home/remora/financenews")
STATE_FILE = BASE_DIR / "state.json"
URLS_FILE = BASE_DIR / "urls.yaml"
BROWSER_PORT = 9222

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_run": None, "daily_seq": 0, "last_date": None, "hashes": {}}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_shanghai_now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

def get_date_str():
    return get_shanghai_now().strftime("%y%m%d")

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except:
            return False

def compute_hash(content):
    return hashlib.sha256(content.encode('utf-8', errors='ignore')).hexdigest()[:16]

async def get_browser(p):
    """Always use foreground browser on DISPLAY=:10"""
    
    # Check if browser already running on port 9222
    if is_port_open(BROWSER_PORT):
        print(f"[INFO] Connecting to existing browser on port {BROWSER_PORT}...")
        try:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{BROWSER_PORT}")
            print(f"[INFO] Connected to existing foreground browser")
            return browser, False
        except Exception as e:
            print(f"[WARN] Failed to connect: {e}")
    
    # Launch new foreground browser (keep profile persistent)
    print(f"[INFO] Launching new foreground browser on DISPLAY=:10...")
    # Do not delete profile directory to preserve login sessions
    
    env = os.environ.copy()
    env["DISPLAY"] = ":10"
    env["XAUTHORITY"] = "/home/remora/.Xauthority"
    
    cmd = [
        "/snap/chromium/3458/usr/lib/chromium-browser/chrome",
        "--no-sandbox",
        "--disable-gpu",
        f"--remote-debugging-port={BROWSER_PORT}",
        "--user-data-dir=/home/remora/financenews/.chrome_profile",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    subprocess.Popen(cmd, env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for port to be ready
    for _ in range(20):
        await asyncio.sleep(0.5)
        if is_port_open(BROWSER_PORT):
            break
    
    try:
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{BROWSER_PORT}")
        print(f"[INFO] Connected to new foreground browser")
        return browser, True
    except Exception as e:
        print(f"[ERROR] Failed to launch foreground browser: {e}")
        return None, False

async def scrape_all():
    print("=" * 60)
    print("Finance News Scraper (Foreground Browser)")
    print(f"Time: {get_shanghai_now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    state = load_state()
    today = get_date_str()
    
    if state.get("last_date") != today:
        state["daily_seq"] = 0
        state["last_date"] = today
        print(f"[INFO] New day, resetting sequence")
    
    with open(URLS_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    sites = config.get("sites", [])
    print(f"[INFO] Found {len(sites)} sites to scrape")
    
    from playwright.async_api import async_playwright
    p = await async_playwright().start()
    browser, browser_launched = await get_browser(p)
    
    if browser is None:
        print("[ERROR] No browser available")
        await p.stop()
        return 1
    
    # Get the existing context (window) to open new tabs inside the same window
    if browser.contexts:
        context = browser.contexts[0]
    else:
        context = await browser.new_context()

    results = []
    new_count = 0
    skip_count = 0
    fail_count = 0
    
    for site in sites:
        name = site["name"]
        url = site["url"]
        site_key = f"{name}_{today}"
        
        print(f"\n[INFO] Processing: {name}")
        
        # Clear cookies before each navigation to prevent session tracking/bot flags in the same window
        await context.clear_cookies()
        # Open a new tab (page) in the same window (context)
        page = await context.new_page()
        
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            status = response.status if response else 0
            if status >= 400:
                results.append((name, False, f"HTTP {status}"))
                fail_count += 1
                await page.close()
                continue
            await asyncio.sleep(3)  # Wait for JS rendering
            content = await page.inner_text("body")
            current_hash = compute_hash(content)
        except Exception as e:
            results.append((name, False, str(e)[:80]))
            fail_count += 1
            await page.close()
            continue
        
        # Check if content changed
        last_hash = state["hashes"].get(site_key)
        if last_hash and current_hash == last_hash:
            print(f"[SKIP] {name}: No new content")
            skip_count += 1
            results.append((name, True, "No new content"))
            await page.close()
            continue
        
        # Save new content
        state["daily_seq"] += 1
        seq = state["daily_seq"]
        
        daily_dir = BASE_DIR / today
        daily_dir.mkdir(exist_ok=True)
        sh_hour = get_shanghai_now().strftime("%H")
        filename = f"{name}_{today}{sh_hour}_{seq:03d}.md"
        filepath = daily_dir / filename
        
        title = await page.title()
        md_content = f"# {title}\n\n## URL\n{url}\n\n## Scraped At\n{get_shanghai_now().strftime('%Y-%m-%d %H:%M:%S')}\n\n## Content\n\n{content[:50000]}\n"
        filepath.write_text(md_content, encoding="utf-8")
        
        state["hashes"][site_key] = current_hash
        state["last_run"] = get_shanghai_now().isoformat()
        
        print(f"[OK] {name}: Saved as {filename} ({len(content)} chars)")
        results.append((name, True, f"Saved: {filename}"))
        new_count += 1
        await page.close()
    
    save_state(state)
    
    if browser_launched:
        print(f"\n[INFO] Keeping browser open for user persistence...")
        # Do not call browser.close() to keep the window open for the user to login and reuse the session
    # Note: If we connected to existing browser, we leave it open
    
    await p.stop()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Sites processed: {len(sites)}")
    print(f"New content saved: {new_count}")
    print(f"Skipped (no change): {skip_count}")
    print(f"Failed: {fail_count}")
    print("\nResults:")
    for name, success, msg in results:
        if "No new content" in msg:
            print(f"  ⚠  {name}: {msg}")
        elif success:
            print(f"  ✓  {name}: {msg}")
        else:
            print(f"  ✗  {name}: {msg}")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(scrape_all()))
