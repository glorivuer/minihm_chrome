#!/bin/bash
# MiniHermes - Hourly news analysis execution script
# Triggered by cron job "00a96b63015c"

/home/remora/myapp/minihm/.venv/bin/python /home/remora/myapp/minihm/financenews/news_analyzer.py --mode hourly
