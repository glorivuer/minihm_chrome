#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from openai import OpenAI

# Configurations
BASE_DIR = Path("/home/remora/financenews")
STATE_FILE = BASE_DIR / "state.json"
CST = timezone(timedelta(hours=8))

def get_shanghai_now():
    return datetime.now(timezone.utc).astimezone(CST)

def run_hourly_analysis():
    now_cst = get_shanghai_now()
    today_str = now_cst.strftime("%y%m%d")
    hour_str = now_cst.strftime("%H")
    
    # --- Heartbeat Pattern ---
    heartbeat_warning = ""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            last_run_str = state.get("last_run")
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str)
                diff_hours = (now_cst - last_run).total_seconds() / 3600.0
                if diff_hours > 2.0:
                    heartbeat_warning = f"⚠️ **Warning: Scraper heartbeat lost.** Last successful run was {diff_hours:.1f} hours ago ({last_run.strftime('%Y-%m-%d %H:%M:%S')}).\n\n"
        except Exception as e:
            print(f"[WARN] Error reading state.json: {e}", file=sys.stderr)

    daily_dir = BASE_DIR / today_str
    
    # --- File Retrieval Logic ---
    new_files = []
    if daily_dir.exists():
        for f in daily_dir.glob("*.md"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).astimezone(CST)
            if (now_cst - mtime).total_seconds() <= 3900: # 65 minutes
                new_files.append(f)
                
    if not new_files:
        # Exit silently UNLESS there's a heartbeat warning
        if heartbeat_warning:
            print(heartbeat_warning)
        sys.exit(0)
        
    # [Rest of LLM call and report generation logic...]
    # ...
    # Final output:
    # print(heartbeat_warning + report)
