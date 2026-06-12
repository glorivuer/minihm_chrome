#!/bin/bash
# MiniHermes - Daily morning briefing execution script
# Triggered by cron job "00b87c22026d"

/home/remora/myapp/minihm/.venv/bin/python /home/remora/myapp/minihm/financenews/news_analyzer.py --mode morning
