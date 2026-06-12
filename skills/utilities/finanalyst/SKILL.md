---
name: finanalyst
description: "Global macro strategy analysis and daily morning briefing generator. Summarizes, categorizes, and evaluates hourly financial news scrapes, assesses market impacts, computes sentiment scores, and aggregates them into structured reports."
version: 1.0.0
author: Antigravity Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [finance, macro, analysis, strategy, report, briefing, sentiment]
    triggers: ["@finanalyst", "finance news analysis", "财经新闻分析", "市场情绪分析", "晨报汇总", "宏观策略报告", "晨报"]
---

# @finanalyst Global Macro Strategy Skill

This skill enables MiniHermes to perform structured, professional macro strategy analysis on hourly finance news scrapes, save persistent markdown reports, and synthesize daily morning market briefings.

---

## 📂 Directory Structure and Archiving Rules

All raw scrapes and generated analysis files are organized under `/home/remora/financenews/` using China Shanghai Time (CST, UTC+8):
1. **Raw Scrapes**: `/home/remora/financenews/{YYMMDD}/{site}_{YYMMDD}{HH}_{seq:03d}.md`
2. **Hourly Analysis**: `/home/remora/financenews/analysis/{YYMMDD}/hourly_analysis_{HH}.md`
3. **Daily Morning Report**: `/home/remora/financenews/analysis/{YYMMDD}/morning_report_0830.md`

---

## 📝 1. Hourly Analysis Prompt

When running hourly (triggered by Cron or user request), the agent reads the newly scraped `.md` files from the last hour, processes them using the following macro analysis framework, saves the output to `/home/remora/financenews/analysis/{YYMMDD}/hourly_analysis_{HH}.md`, and replies to the user.

### Prompt Template:
```markdown
# 角色
你是一位资深的全球宏观策略分析师与量化研究员。你擅长在海量、碎片化的新闻标题中，快速识别具有市场冲击力的“边际变化”（Marginal Changes），并评估其对全球股票、期货大宗商品、行业板块的潜在传导路径。

# 任务
请根据过去一小时内抓取的财经新闻，撰写一份客观、简明的《小时级市场情绪与资产冲击中文分析报告》。

# 分析逻辑与步骤

## 第一步：信息降噪与分类（Filtering & Classification）
1. 过滤掉常态化信息、已被市场充分定价的旧闻、或影响范围极小的噪音。
2. 将核心新闻归类为以下驱动因子之一（若无，则不列出）：
   - **宏观政策与央行动态**（如联储官员表态、利率预期）
   - **地缘政治与突发事件**（如冲突升级、关键供应链受阻）
   - **经济数据与基本面**（如通胀、就业、PMI等指标的突发修正或预期偏差）
   - **行业与巨头异动**（如重组、核心监管变化、财报超预期等）

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
- **禁止过度推断**：如果新闻标题缺乏足够细节支持某项结论，必须在报告中明确指出“缺乏细节，有待进一步验证”。
- **客观平衡**：必须同时考虑正面与负面情景，避免单一方向偏见。
- **简明扼要**：使用高度浓缩、结构化的段落或列表，避免冗长的背景介绍。
```

---

## 📝 2. Daily Morning Report Synthesis Prompt (Option B)

When running at 8:30 AM Beijing Time (CST), the agent reads all the hourly analysis reports from the **previous 24 hours** (specifically looking at yesterday's folder and today's folder), synthesizes them using the layout below, saves the output to `/home/remora/financenews/analysis/{YYMMDD}/morning_report_0830.md`, and sends the final report to the Telegram user.

### Prompt Template:
```markdown
# 角色
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
* **尾部风险防范 (Tail Risk Mitigation)**：今日需要特别警惕的极端风险点。
```

---

## 🛠️ Troubleshooting & Health Checks (Lessons Learned)

### 0. Source Verification & Audit Trail (New)
When a user asks for the origin of a specific summary point (e.g., \"Where did the Cobalt news come from?\"):
1. **Identify the Session**: Use `session_search(query=\"keyword\")` to find the briefing where the item was first mentioned.
2. **Locate the Raw Files**:
   - Hourly briefings (e.g., 11:00) typically correspond to the same hour's raw folder: `/home/remora/financenews/{YYMMDD}/`.
   - Use `terminal(command=\"grep -ri 'keyword' /path/to/daily/folder/\")` to find the exact raw `.md` file.
   - Note: FT and Reuters often use specific sub-headers (e.g., `ft_mkt_...`, `reuters_bus_...`).
3. **Verify Timestamp**: Match the `Scraped At` field in the raw file with the briefing time.

### 1. Hybrid Scheduling Blindness
If the **Scraper** is on the system `crontab` and the **Analyzer** is on the Hermes `cronjob`, errors in the scraper (e.g., bot detection, network failure) will be silent.
- **Symptom**: Analyzer runs but says "No new files found" or stays silent.
- **Fix**: Migrate the Scraper to Hermes `cronjob` (with `deliver: origin`) so failures are reported to Telegram, or ensure the Scraper logs to a central file (`run.log`) and have the Analyzer check it.

### 2. Heartbeat Monitoring Pattern
Always implement a heartbeat check in the analyzer by reading a `state.json` file.
- If the difference between `now` and `last_run` in `state.json` exceeds 2 hours, output a warning (e.g., `⚠️ Scraper heartbeat lost`) even if no new news is available. This prevents "silent failures" where the user assumes everything is fine just because they see no news.

### 3. Gateway Interruptions & Delivery Loss
Hermes `cronjob` output is delivered via the gateway. If the gateway shuts down or the session is interrupted exactly when a job finishes, the Telegram notification might be lost even if `last_status` is `ok`.
- **Verification**: If you suspect a missed report, check the local storage: `ls -R /home/remora/financenews/analysis/`.
- **Mitigation**: Design the analyzer to always write to disk *before* printing to stdout.

### 4. Silent Exit vs. Active Reporting
- **Good for noise**: Exiting silently when no new content is found.
- **Good for confidence**: Printing a "No new content found" summary if the user asks manually, but keeping it silent in automated cron runs unless a heartbeat is missed.

### 5. Browser Connection Issues (Foreground Mode)
When using foreground Chromium on `DISPLAY=:10` (standard for this user), the scraper may fail with `BrowserType.connect_over_cdp: connect ECONNREFUSED 127.0.0.1:9222`.
- **Cause**: The browser instance crashed or hasn't finished opening the remote debugging port.
- **Fix**: Check `ps aux | grep chromium` and kill zombie processes, or ensure the `subprocess.Popen` in `run_scrape.py` has enough wait time (currently 10s via 20x0.5s loops) for the port to open.

### 6. Content Hashing & Missing Files
The scraper uses SHA-256 hashing (`hashes` in `state.json`) to detect changes.
- **Behavior**: If a site is skipped with `No new content`, no `.md` file is generated for that hour.
- **Verification**: Check `run.log` for `[SKIP] ...: No new content` before assuming the scraper failed.

---

## 📂 Linked Files
- [Implementation Details](references/system_architecture.md) — Map of scripts, paths, and cron triggers.

To automate retrieval of the correct files based on Shanghai timezone, use the following code snippets.

### Get Last Hour's Scrapes:
```python
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
now_cst = datetime.now(timezone.utc).astimezone(CST)
today_str = now_cst.strftime("%y%m%d")
hour_str = now_cst.strftime("%H")

daily_dir = Path(f"/home/remora/financenews/{today_str}")
# Search for files created in the last 65 minutes matching today
new_files = []
if daily_dir.exists():
    for f in daily_dir.glob("*.md"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).astimezone(CST)
        if (now_cst - mtime).total_seconds() <= 3900: # 65 minutes
            new_files.append(f)
```

### Get 24-Hour Hourly Analysis Reports for Morning Briefing:
```python
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
now_cst = datetime.now(timezone.utc).astimezone(CST)
today_str = now_cst.strftime("%y%m%d")

# Get yesterday's date string
yesterday_cst = now_cst - timedelta(days=1)
yesterday_str = yesterday_cst.strftime("%y%m%d")

analysis_dirs = [
    Path(f"/home/remora/financenews/analysis/{yesterday_str}"),
    Path(f"/home/remora/financenews/analysis/{today_str}")
]

reports = []
for d in analysis_dirs:
    if d.exists():
        for f in sorted(d.glob("hourly_analysis_*.md")):
            # Only include reports from the last 24 hours
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).astimezone(CST)
            if (now_cst - mtime).total_seconds() <= 90000: # 25 hours buffer
                reports.append(f)
```
