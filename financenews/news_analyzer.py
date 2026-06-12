#!/usr/bin/env python3
import os
import sys
import argparse
import json
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path
from openai import OpenAI

# Configurations
BASE_DIR = Path("/home/remora/financenews")
STATE_FILE = BASE_DIR / "state.json"
CST = timezone(timedelta(hours=8))

# Load environment variables manually from minihm/.env
def load_env():
    env_vars = {}
    env_path = Path("/home/remora/myapp/minihm/.env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().strip('"').strip("'")
                        env_vars[key] = val
    return env_vars

# Get current time in Shanghai
def get_shanghai_now():
    return datetime.now(timezone.utc).astimezone(CST)

# Hourly Analysis Prompt
HOURLY_SYSTEM_PROMPT = """# 角色
你是一位资深的全球宏观策略分析师与量化研究员。你擅长在海量、碎片化的新闻标题中，快速识别具有市场冲击力的“边际变化”（Marginal Changes），并评估其对全球股票、期货大宗商品、行业板块的潜在传导路径。

# 任务
请根据过去一小时内抓取的财经新闻，撰写一份客观、简明的《小时级市场情绪与资产冲击中文分析报告》。

# 分析逻辑与步骤

## 第一步：信息降噪与分类（Filtering & Classification）
1. 过滤掉常态化信息、已被市场充分定价的旧闻、或影响范围极小的噪音。
2. 将核心新闻归类为以下驱动因子之一（若无，则不列出）：
   - **宏观政策与央行动态**（如联储官员表态、利率预期）
   - **地缘政治与突发事件**（如冲突升级、关键供应链受阻）
   - **经济数据与基本面**（如通胀、就业、PMI等指标 of 突发修正或预期偏差）
   - **行业与巨巨头异动**（如重组、核心监管变化、财报超预期等）

## 第二步：大类资产多维传导分析（Transmission Impact）
基于上述核心驱动因子，评估其对以下市场的具体影响方向（正面、中性、负面）、短期波动率走势及逻辑：
1. **股票市场（Stocks）**：
   - 全球主要股指（如 S&P 500, Nasdaq, Nikkei 225 等）。
   - 受影响最显著的行业板块（例如：若高通胀言论抬头，利空科技/成长股，利好防御性板块）。
2. **期货与大宗商品市场（Commodities & Futures）**：
   - 贵金属（黄金/白银：评估避险属性或抗通胀属性变化）。
   - 能源（原油：评估供需预期及地缘溢价变化）。
   - 债券期货（如10年期美债：评估收益率曲线的变动方向）。
   - 其他关键商品（铜、农产品等，视具体新闻而定）。

## 第三步：情绪量化与置信度评估（Quantitative Score）
1. **情绪指数（Sentiment Score）**：针对当前的整体市场情绪，给出一个介于 [-5（极度悲观/恐慌）到 +5（极度乐观/贪婪）] 之间的分值，并给出1句理由。
2. **预测置信度（Confidence Level）**：给出你对上述影响判断的信心水平（低/中/高），并说明哪些关键变量可能推翻你的预测（即“替代性情景”分析）。

## 第四步：交易决策与风险对冲建议（Trading Recommendations）
1. **日内交易（Intraday Tactics）**：面向短线交易者的具体应对思路（寻找哪些阻力位/支撑位方向，或是波动率套利）。
2. **中期波段（Swing Trading Thoughts）**：当前趋势是否发生结构性扭转，是否有分批建仓或减仓的逻辑支持。
3. **风险防御（Risk Mitigation）**：列出当前最需要警惕的尾部风险（Tail Risk）。

# 输出限制与行为规范
- **禁止过度推断**：如果新闻内容缺乏足够细节支持某项结论，必须在报告中明确指出“缺乏细节，有待进一步验证”。
- **客观平衡**：必须同时考虑正面与负面情景，避免单一方向偏见。
- **简明扼要**：使用高度浓缩、结构化的段落或列表，避免冗长的背景介绍。"""

# Daily Morning Report Prompt (Option B)
MORNING_SYSTEM_PROMPT = """# 角色
你是一位资深的全球宏观策略分析师与量化研究员。请根据过去24小时的所有《小时级市场情绪与资产冲击中文分析报告》，撰写一份《全球宏观策略与市场情绪每日晨报汇总》。

# 报告结构 (Option B)

## 一、 昨日市场概述与收盘盘面 (Market Overview)
* 根据过去24小时各时间段的累积变动，总结全球主要股指、商品、债市在昨日交易时段的最终表现与情绪主线。
* 提供一小段精简的收盘盘面分析。

## 二、 核心事件与边际变化 (Key Events & Marginal Changes)
* 梳理过去24小时最关键的核心驱动事件（宏观政策、央行、经济数据、地缘政治或巨头异动）。
* 明确指出哪些是引发市场波动的“边际变化”（即超出市场先前定价的新变化），排除旧闻噪音。

## 三、 今日日内前瞻与预期驱动 (Today's Calendar & Drivers)
* 展望今日即将公布的关键经济指标（如通胀、就业、PMI）、重大会议或财报。
* 评估这些预期事件对日内各大类资产的潜在冲击方向。

## 四、 交易决策与策略推荐 (Trading Recommendations)
* **日内短线交易建议 (Intraday Tactics)**：日内交易者的主要应对方向，波幅预测。
* **中线波段持仓思路 (Swing Trading Thoughts)**：中线建仓或避险减仓的逻辑参考。
* **尾部风险防范 (Tail Risk Mitigation)**：今日需要特别警惕的极端风险点。"""

def run_hourly_analysis():
    now_cst = get_shanghai_now()
    today_str = now_cst.strftime("%y%m%d")
    hour_str = now_cst.strftime("%H")
    
    # Check heartbeat in state.json
    heartbeat_warning = ""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            last_run_str = state.get("last_run")
            if last_run_str:
                # state contains timezone offset (isoformat)
                last_run = datetime.fromisoformat(last_run_str)
                diff_hours = (now_cst - last_run).total_seconds() / 3600.0
                if diff_hours > 2.0:
                    heartbeat_warning = f"⚠️ **Warning: Scraper heartbeat lost.** Last successful run was {diff_hours:.1f} hours ago ({last_run.strftime('%Y-%m-%d %H:%M:%S')}).\n\n"
        except Exception as e:
            print(f"[WARN] Error reading state.json: {e}", file=sys.stderr)

    daily_dir = BASE_DIR / today_str
    
    # Retrieve files from the last 65 minutes
    new_files = []
    if daily_dir.exists():
        for f in daily_dir.glob("*.md"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).astimezone(CST)
            if (now_cst - mtime).total_seconds() <= 3900: # 65 minutes
                new_files.append(f)
                
    if not new_files:
        # If no new files, exit silently (empty stdout)
        # Note: If there was a heartbeat warning, we DO output it so we know it's broken!
        if heartbeat_warning:
            print(heartbeat_warning)
            sys.exit(0)
        sys.exit(0)
        
    # Read files
    raw_content = ""
    for f in sorted(new_files):
        try:
            raw_content += f"\n\n--- Source: {f.name} ---\n" + f.read_text(encoding="utf-8")
        except Exception as e:
            raw_content += f"\n\n--- Error reading {f.name}: {e} ---\n"
            
    # Call LLM
    env = load_env()
    api_key = env.get("HERMES_API_KEY") or env.get("GEMINI_API_KEY") or env.get("NVIDIA_API_KEY")
    base_url = env.get("HERMES_BASE_URL") or env.get("GEMINI_BASE_URL") or env.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    
    # Resolve default model
    default_model = "minimaxai/minimax-m2.7"
    if env.get("GEMINI_API_KEY") or (base_url and "generativelanguage" in str(base_url)):
        default_model = "gemini-2.5-flash"
        
    model_name = env.get("HERMES_MODEL") or env.get("GEMINI_MODEL") or default_model
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    user_prompt = f"以下是过去一小时内抓取的所有财经新闻内容：\n{raw_content}\n\n请对此进行宏观策略分析。"
    
    # Call LLM with retry
    report = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": HOURLY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            report = response.choices[0].message.content
            if report is not None:
                break
            else:
                print(f"[WARN] API returned empty content (attempt {attempt+1}/3). Finish reason: {response.choices[0].finish_reason}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] API call failed (attempt {attempt+1}/3): {e}", file=sys.stderr)
        import time
        time.sleep(2)

    if report is None:
        print("Error: LLM API repeatedly returned empty/None content or failed. It may have been blocked by safety filters.", file=sys.stderr)
        sys.exit(1)
        
    # Save analysis file
    analysis_dir = BASE_DIR / "analysis" / today_str
    analysis_dir.mkdir(parents=True, exist_ok=True)
    report_file = analysis_dir / f"hourly_analysis_{hour_str}.md"
    
    full_output = heartbeat_warning + report
    report_file.write_text(full_output, encoding="utf-8")
    
    # Print to stdout (gets delivered to Telegram)
    print(full_output)

def run_morning_briefing():
    now_cst = get_shanghai_now()
    today_str = now_cst.strftime("%y%m%d")
    yesterday_cst = now_cst - timedelta(days=1)
    yesterday_str = yesterday_cst.strftime("%y%m%d")
    
    analysis_dirs = [
        BASE_DIR / "analysis" / yesterday_str,
        BASE_DIR / "analysis" / today_str
    ]
    
    # Retrieve analysis reports from the last 25 hours
    reports = []
    for d in analysis_dirs:
        if d.exists():
            for f in sorted(d.glob("hourly_analysis_*.md")):
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).astimezone(CST)
                if (now_cst - mtime).total_seconds() <= 90000: # 25 hours
                    reports.append(f)
                    
    if not reports:
        print("⚠️ **Finance News Morning Briefing**\n\nError: No hourly analysis reports found from the last 24 hours. Unable to compile morning briefing.")
        sys.exit(0)
        
    # Read reports
    aggregated_reports = ""
    for f in sorted(reports):
        try:
            aggregated_reports += f"\n\n--- Report: {f.name} ---\n" + f.read_text(encoding="utf-8")
        except Exception as e:
            aggregated_reports += f"\n\n--- Error reading report {f.name}: {e} ---\n"
            
    # Call LLM
    env = load_env()
    api_key = env.get("HERMES_API_KEY") or env.get("GEMINI_API_KEY") or env.get("NVIDIA_API_KEY")
    base_url = env.get("HERMES_BASE_URL") or env.get("GEMINI_BASE_URL") or env.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    
    # Resolve default model
    default_model = "minimaxai/minimax-m2.7"
    if env.get("GEMINI_API_KEY") or (base_url and "generativelanguage" in str(base_url)):
        default_model = "gemini-2.5-flash"
        
    model_name = env.get("HERMES_MODEL") or env.get("GEMINI_MODEL") or default_model
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    user_prompt = f"以下是过去24小时的所有小时级市场分析报告：\n{aggregated_reports}\n\n请对此进行晨报汇总合成。"
    
    # Call LLM with retry
    briefing = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": MORNING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            briefing = response.choices[0].message.content
            if briefing is not None:
                break
            else:
                print(f"[WARN] API returned empty content (attempt {attempt+1}/3). Finish reason: {response.choices[0].finish_reason}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] API call failed (attempt {attempt+1}/3): {e}", file=sys.stderr)
        import time
        time.sleep(2)

    if briefing is None:
        print("Error: LLM API repeatedly returned empty/None content or failed. It may have been blocked by safety filters.", file=sys.stderr)
        sys.exit(1)
        
    # Save daily briefing file
    analysis_dir = BASE_DIR / "analysis" / today_str
    analysis_dir.mkdir(parents=True, exist_ok=True)
    briefing_file = analysis_dir / "morning_report_0830.md"
    briefing_file.write_text(briefing, encoding="utf-8")
    
    # Print to stdout (gets delivered to Telegram)
    print(briefing)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finance News Analyzer")
    parser.add_argument("--mode", choices=["hourly", "morning"], required=True, help="Analysis mode")
    args = parser.parse_args()
    
    if args.mode == "hourly":
        run_hourly_analysis()
    elif args.mode == "morning":
        run_morning_briefing()
