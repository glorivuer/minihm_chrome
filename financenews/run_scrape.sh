#!/usr/bin/env bash
# /home/remora/financenews/run_scrape.sh

VENV_PYTHON="/home/remora/myapp/minihm/.venv/bin/python"
SCRIPTPATH="/home/remora/myapp/minihm/financenews/run_scrape.py"

echo "[$(date)] Starting news scraper execution..."
cd /home/remora/financenews && ${VENV_PYTHON} ${SCRIPTPATH} >> run.log 2>&1
echo "[$(date)] Scraper execution finished."
