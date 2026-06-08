#!/usr/bin/env bash
# MiniHermes - Telegram Bot One-Click Startup Script
# This script starts the Telegram gateway for MiniHermes.

# Ensure we exit on error
set -e

# Path configurations
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Force configuration, skills, and logs to be self-contained in the project folder
export HERMES_HOME="$PROJECT_DIR"


echo "===================================================="
echo "         Starting MiniHermes Telegram Bot           "
echo "===================================================="

# 1. Check Python and dependencies
if ! command -v python3 &>/dev/null; then
    echo "❌ Error: python3 is not installed."
    exit 1
fi

# Try to find virtual environment, default to local environment if none
if [ -d ".venv" ]; then
    echo "💡 Activating virtual environment (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "💡 Activating virtual environment (venv)..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Running with global python."
    echo "👉 Tip: You can install requirements using: pip install -r requirements.txt"
fi

# Verify python-telegram-bot is installed
if ! python3 -c "import telegram" &>/dev/null; then
    echo "❌ Error: 'python-telegram-bot' is not installed."
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

# 2. Load environment variables
if [ -f ".env" ]; then
    echo "📝 Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# 3. Check Required Keys
if [ -z "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_TOKEN" ]; then
    export TELEGRAM_BOT_TOKEN="$TELEGRAM_TOKEN"
elif [ -z "$TELEGRAM_TOKEN" ] && [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    export TELEGRAM_TOKEN="$TELEGRAM_BOT_TOKEN"
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN (or TELEGRAM_TOKEN) is not set."
    echo "Please set it in your environment or in a .env file:"
    echo "  export TELEGRAM_BOT_TOKEN=\"your-telegram-bot-token\""
    exit 1
fi
export TELEGRAM_BOT_TOKEN
export TELEGRAM_TOKEN

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GEMINI_API_KEY" ] && [ -z "$NVIDIA_API_KEY" ]; then
    echo "⚠️  Warning: No LLM API keys (OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY / NVIDIA_API_KEY) detected."
    echo "Please make sure your API keys are configured, otherwise model calls will fail."
fi

# Ensure user access is gated (Hermes defaults to restricting access for security)
if [ -z "$TELEGRAM_ALLOWED_USERS" ] && [ -z "$TELEGRAM_ALLOW_ALL_USERS" ]; then
    echo "⚠️  Access Gating Warning: Neither TELEGRAM_ALLOWED_USERS nor TELEGRAM_ALLOW_ALL_USERS is configured."
    echo "By default, only users specified in TELEGRAM_ALLOWED_USERS can converse with the bot."
    echo "Setting TELEGRAM_ALLOW_ALL_USERS=1 for public demo (caution: anyone can run commands!)."
    export TELEGRAM_ALLOW_ALL_USERS="1"
fi

# 4. Start the Gateway
echo "🚀 Starting Hermes Telegram Gateway..."
echo "Press Ctrl+C to stop the bot."
echo "----------------------------------------------------"

export _HERMES_GATEWAY="1"
python3 cli.py --gateway
