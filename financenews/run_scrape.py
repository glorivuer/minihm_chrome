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
import re
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

def is_date_or_time_line(line):
    line_lower = line.lower()
    # Matches relative times like "12 mins ago", "1 hour ago", "5 hours ago", "17 hours ago", "yesterday"
    if re.search(r'\b\d+\s+(min|minute|hour|day|sec|second)s?\s+ago\b', line_lower):
        return True
    if re.search(r'\b\d+\s+(min|hr|h|m|d)\b', line_lower): # e.g. "12m", "3h"
        return True
    if "mins ago" in line_lower or "hours ago" in line_lower or "days ago" in line_lower:
        return True
    
    # Matches dates like "June 12, 2026", "· June 12, 2026 ·", "12 June 2026"
    months_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)'
    date_pattern = r'^\s*·?\s*(?:' + months_pattern + r'\s+\d{1,2}(?:\s*,\s*\d{4})?|\d{1,2}\s+' + months_pattern + r'(?:\s+\d{4})?|\d{4}-\d{2}-\d{2})\s*·?\s*$'
    if re.search(date_pattern, line_lower):
        return True
        
    return False

def process_and_deduplicate_lines(raw_text, state, now_cst):
    """
    Cleans the raw text line-by-line, filters out boilerplate, dates, relative times,
    and returns deduplicated lines based on seen hashes in state.
    """
    lines = []
    new_hashes_added = 0
    seen_stories = state.setdefault("seen_stories", {})
    
    # Common boilerplate phrases to ignore
    boilerplate_blacklist = [
        "all rights reserved",
        "terms & conditions",
        "terms of use",
        "privacy policy",
        "cookie policy",
        "manage cookies",
        "individual subscriptions",
        "professional subscriptions",
        "republish holding",
        "advertise with us",
        "all quotes delayed",
        "skip to main content",
        "skip to navigation",
        "accessibility help",
        "sign in",
        "subscribe",
        "load more",
        "follow us",
        "download the app",
        "opens new tab",
        "contact us",
        "about us"
    ]
    
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
            
        # Basic character length filter (ignore lines < 20 characters)
        if len(line) < 20:
            continue
            
        # Ignore lines matching blacklisted terms (case-insensitive)
        line_lower = line.lower()
        if any(term in line_lower for term in boilerplate_blacklist):
            continue
            
        # Ignore lines that are just dates or relative times
        if is_date_or_time_line(line):
            continue
            
        # Compute SHA256 of the line
        line_hash = hashlib.sha256(line.encode('utf-8', errors='ignore')).hexdigest()[:16]
        
        # Check against seen_stories
        if line_hash in seen_stories:
            continue
            
        # Mark as seen
        seen_stories[line_hash] = now_cst.isoformat()
        lines.append(line)
        new_hashes_added += 1
        
    return lines, new_hashes_added

def clean_old_hashes(state, now_cst):
    seen_stories = state.setdefault("seen_stories", {})
    expiration_limit = now_cst - timedelta(hours=25)
    
    to_delete = []
    for h, ts_str in seen_stories.items():
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts < expiration_limit:
                to_delete.append(h)
        except Exception:
            to_delete.append(h)
            
    for h in to_delete:
        del seen_stories[h]


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
            
            # DOM cleaning via page.evaluate
            clean_js = """
            () => {
                const selectorsToRemove = [
                    'header', 'footer', 'nav', 'aside', 'noscript', 'script', 'style', 'iframe', 'svg',
                    '[role="banner"]', '[role="navigation"]', '[role="contentinfo"]',
                    '#cookie-consent', '.ad-wrapper', '.cookie-consent', '.advertisement',
                    '.newsletter-signup', '.social-share', '.related-content', '.trending-stories',
                    '.sidebar', '#sidebar', '.widget', '#widget', '.masthead', '.nav-menu',
                    '.ft-cookie-consent', '.reuters-cookie-consent', '.privacy-policy',
                    '#privacy-banner', '.ad-banner', '.paywall-promo', '.subscribe-promo',
                    '.o-cookie-message', '.o-header', '.o-footer', '.ft-editorial-notice',
                    '.bbc-cookie-banner', '#orb-header', '#footer-content'
                ];
                
                const fuzzySelectors = [
                    '[class*="cookie"]', '[id*="cookie"]', '[class*="consent"]', '[id*="consent"]',
                    '[class*="ad-wrapper"]', '[class*="advertisement"]', '[id*="advertisement"]',
                    '[id*="google_ads"]', '[class*="paywall"]', '[class*="subscription"]',
                    '[class*="newsletter"]', '[class*="social-share"]', '[class*="share-tools"]'
                ];
                
                selectorsToRemove.forEach(sel => {
                    try { document.querySelectorAll(sel).forEach(el => el.remove()); } catch(e) {}
                });
                
                fuzzySelectors.forEach(sel => {
                    try {
                        document.querySelectorAll(sel).forEach(el => {
                            const isMain = el.tagName.toLowerCase() === 'main' || el.id === 'main' || el.id === 'content' || el.classList.contains('main-content');
                            if (!isMain) { el.remove(); }
                        });
                    } catch(e) {}
                });

                const mainSelectors = ['main', '#main-content', '#content', '.main-content', 'article'];
                for (const sel of mainSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText && el.innerText.trim().length > 200) {
                        return el.innerText;
                    }
                }
                
                return document.body ? document.body.innerText : '';
            }
            """
            content = await page.evaluate(clean_js)
            if not content or len(content.strip()) < 100:
                print(f"[WARN] Cleaned content too short, falling back to raw body inner_text")
                content = await page.inner_text("body")
                
            current_hash = compute_hash(content)
        except Exception as e:
            results.append((name, False, str(e)[:80]))
            fail_count += 1
            await page.close()
            continue
        
        # Check if content changed (overall hash)
        last_hash = state["hashes"].get(site_key)
        if last_hash and current_hash == last_hash:
            print(f"[SKIP] {name}: No new content (overall hash match)")
            skip_count += 1
            results.append((name, True, "No new content"))
            await page.close()
            continue
            
        # Line-by-line cleaning and deduplication
        cleaned_lines, new_hashes_added = process_and_deduplicate_lines(content, state, get_shanghai_now())
        
        if new_hashes_added == 0:
            print(f"[SKIP] {name}: No new headlines/stories after line-level deduplication")
            skip_count += 1
            results.append((name, True, "No new content"))
            # Update the page hash so we don't process it again if it hasn't changed
            state["hashes"][site_key] = current_hash
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
        md_content = f"# {title}\n\n## URL\n{url}\n\n## Scraped At\n{get_shanghai_now().strftime('%Y-%m-%d %H:%M:%S')}\n\n## Content\n\n" + "\n\n".join(cleaned_lines) + "\n"
        filepath.write_text(md_content, encoding="utf-8")
        
        state["hashes"][site_key] = current_hash
        state["last_run"] = get_shanghai_now().isoformat()
        
        print(f"[OK] {name}: Saved as {filename} ({new_hashes_added} new lines, {len(md_content)} chars)")
        results.append((name, True, f"Saved: {filename} ({new_hashes_added} new lines)"))
        new_count += 1
        await page.close()
    
    clean_old_hashes(state, get_shanghai_now())
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
