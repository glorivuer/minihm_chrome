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
你是一位极具敏锐度的全球宏观策略分析师与量化交易员。你的核心任务是从碎片化的小时级新闻中过滤噪音，精准捕捉引发市场重定价的“边际变化”（Marginal Changes），并为交易员指明具体的“获利机会”（Profit Opportunities）。

# 核心原则：零冗余、重边际、指向交易
1. **拒绝重复与背景介绍**：不要重述常识、大盘背景或前几小时已知的旧闻。只讲“发生了什么新变化”（Delta），以及这个变化为什么重要。
2. **聚焦边际变化**：边际变化是指“超预期”或“方向扭转”的信息（如政策突变、数据意外修正、地缘摩擦升级）。已被充分定价的信息直接忽略。
3. **锁定交易机会**：所有分析必须落地到可操作的交易品种上（如标普500、纳斯达克、COMEX黄金、WTI原油、十年期美债、外汇主权货币等），明确指出多空方向、波动套利或对冲机会。

# 报告结构与内容要求

## 一、 边际变化与驱动因子 (Marginal Changes)
* **核心新变量**：列出本小时发生的、对市场有实质冲击的1-2个边际新变化。用一句话提炼其“超预期”的具体点（例如：美联储官员表态从温和转为强硬，或者供应链发生突发中断）。
* **分类归因**：直接指出属于哪个因子（宏观政策/突发事件/数据偏差/行业巨头异动），不拖泥带水。

## 二、 资产价格传导与重定价 (Asset Pricing & Re-pricing)
分析上述边际变化将如何直接或间接传导至以下品种，用“↑（利多）”、“↓（利空）”、“→（中性）”和“波动率上升/下降”来标注：
* **股票/指数**：全球主要股指及受冲击最大的板块/行业。
* **商品/期货**：贵金属（黄金/白银）、能源（原油/天然气）、大宗商品（铜等）。
* **固收/外汇**：美债收益率走向、美元指数及关键非美货币。

## 三、 核心获利机会与交易策略 (Profit Opportunities & Trading Tactics)
* **日内套利与方向交易 (Intraday Tactics)**：
  - **交易品种**：明确具体合约或代码。
  - **操作方向与逻辑**：做多/做空/做空波动率/买入跨式期权等，并说明具体逻辑（如“原油地缘溢价回落，日内做空WTI近月合约”）。
  - **执行建议**：给出关键支撑/阻力位方向，或顺势/逆势动量交易点。
* **风险防范与对冲 (Risk Hedging)**：
  - 针对该获利交易，应匹配什么样的对冲资产（如“多金空铜对冲宏观衰退风险”）。
  - 列出该交易最怕出现的“反向变量”（替代性情景）。

## 四、 情绪量化评分 (Quantitative Sentiment)
* **情绪指数 (Sentiment Score)**：针对当前小时的边际变化，给出 [-5（极度悲观）到 +5（极度乐观）] 之间的分值。
* **置信度 (Confidence Level)**：低/中/高，并用一句话说明判定依据。

# 输出行为规范
* **极其简练**：用结构化的 Markdown 列表和粗体字，严禁使用任何过渡性废话和无意义的描述性段落。
* **没有新内容时不编造**：若本小时确实无重大边际变化，报告应极度简短，重点提示“市场处于无驱动横盘，建议观望”。
"""

# Daily Morning Report Prompt (Option B)
MORNING_SYSTEM_PROMPT = """# 角色
你是一位极具敏锐度的全球宏观策略分析师与量化交易员。请根据过去24小时内的所有《小时级市场情绪与资产冲击中文分析报告》，撰写一份高度提炼、侧重实战交易指引的《全球宏观策略每日晨报（交易决策版）》。

# 核心任务与编写原则
1. **降噪与聚合**：不要把小时级报告简单拼接。你必须归纳出过去24小时影响市场的“核心驱动主线”，剔除日内波动噪音和重复提及的信息。
2. **提炼累积边际变化**：清晰说明过去24小时内，市场对宏观环境的预期发生了哪些“累积的边际位移”（例如：通胀预期是否上行、避险情绪是否出现拐点）。
3. **重仓位与获利机会**：晨报的灵魂在于给交易员提供今天开盘后的实操建议。必须给出今日最具有风险收益比（R:R）的获利交易方向，指出具体的大类资产（股指、大宗商品、外汇等）及仓位调整思路。

# 报告结构与内容要求

## 一、 24小时核心变局与定价主线 (24H Key Shifts & Pricing)
* **定价主线**：一句话提炼昨日至今引导全盘资金走向的核心逻辑。
* **核心边际变化**：列出昨日最具超预期冲击的1-2个事件，并阐明市场是如何因此重定价的（排除已消化信息）。

## 二、 盘面表现与强弱透视 (Market Matrix & Strength)
* 简要总结全球大类资产（美股/欧亚股指、黄金/原油/铜、美债收益率、美元指数/非美外汇）在昨日收盘的强弱关系。
* 指出表现出异常韧性（Resilience）或异常脆弱（Vulnerability）的品种。

## 三、 今日重磅前瞻与定价预期 (Today's Drivers & Expectations)
* 列出今日即将公布的关键数据（如通胀、就业、PMI）、会议或政策决议。
* 评估在当前边际变化背景下，这些事件将如何驱动今日的日内行情，给出关键的情景假设（若数据超预期则利多XX/利空YY；若数据不及预期则反之）。

## 四、 核心交易推荐与获利机会 (Trading Opportunities & Profit Action)
* **高胜率日内获利机会 (High-Probability Intraday Tactics)**：
  - **标的**：具体的指数期货、大宗商品或汇率对。
  - **方向与区间**：买入/卖出，预计日内波动区间，核心买入/卖出防御位。
  - **实操逻辑**：结合昨日至今的边际变化，解释为什么该交易胜率高。
* **中线波段持仓调整建议 (Swing Trading & Portfolio Shift)**：
  - 趋势是否出现结构性拐点？是否有建仓/平仓/减仓建议？
* **极端风险防御对冲 (Tail Risk & Hedge)**：
  - 今日开盘后需防范的尾部风险事件，以及推荐的防御性衍生品或黄金等避险仓位配比。

# 输出行为规范
* **剔除废话**：直奔主题，使用 Markdown 列表和加粗，段落字数控制在最少。
* **禁止套话**：所有的“交易建议”必须具体、有方向性，禁止使用“保持谨慎”、“视情况而定”等模棱两可的套话。
"""

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
