#!/bin/bash
# Double-click this file to set up the lead scraper on a Mac.
# It installs everything and opens the file where you paste your OpenAI key.

cd "$(dirname "$0")" || exit 1

echo "============================================"
echo "  Lead Scraper - one-time setup"
echo "============================================"
echo ""

# 1. Make sure Python 3 is available.
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 isn't installed yet."
  echo "A popup should appear asking to install 'command line developer tools'."
  echo "Click Install, wait for it to finish, THEN double-click this file again."
  xcode-select --install 2>/dev/null
  echo ""
  read -n 1 -s -r -p "Press any key to close this window."
  exit 1
fi

# 2. Create an isolated environment and install the dependencies.
echo "Installing (this takes a few minutes the first time)..."
python3 -m venv .venv || { echo "Setup failed creating the environment."; read -n 1 -s -r -p "Press any key to close."; exit 1; }
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install -r requirements.txt || { echo "Setup failed installing packages."; read -n 1 -s -r -p "Press any key to close."; exit 1; }

# 3. Install the headless browser the scraper drives.
echo "Installing the browser component..."
python -m playwright install chromium || { echo "Browser install failed."; read -n 1 -s -r -p "Press any key to close."; exit 1; }

# 4. Create the key file and open it for editing.
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo ""
echo "============================================"
echo "  Almost done - add your OpenAI key"
echo "============================================"
echo "A text window is opening now."
echo "Find the line:   OPENAI_API_KEY=sk-..."
echo "Replace the sk-... part with your real key, then press Cmd+S to save and close it."
echo ""
open -e .env

echo "When you've saved your key, double-click 'run_mac.command' to scrape leads."
echo ""
read -n 1 -s -r -p "Press any key to close this window."
