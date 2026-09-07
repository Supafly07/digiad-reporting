#!/bin/bash
# Double-click this file to scrape leads. Run 'setup_mac.command' first (once).

cd "$(dirname "$0")" || exit 1

if [ ! -f .venv/bin/activate ]; then
  echo "It looks like setup hasn't been run yet."
  echo "Please double-click 'setup_mac.command' first, then come back here."
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi
source .venv/bin/activate

if [ ! -s .env ] || ! grep -q "sk-" .env 2>/dev/null; then
  echo "Your OpenAI key doesn't look set yet."
  echo "Double-click 'setup_mac.command' again to open the key file and paste it in."
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi

echo "============================================"
echo "  Lead Scraper"
echo "============================================"
echo ""
echo "What leads do you want to find?"
echo "For example:  dental clinics in Austin Texas with contact details"
echo ""
read -r -p "Type it here and press Return: " QUERY
if [ -z "$QUERY" ]; then
  echo "Nothing entered - closing."
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi

read -r -p "How many web results to scan? (press Return for 5): " N
N=${N:-5}

echo ""
echo "Searching and scraping... this can take a minute or two."
echo ""
python search_leads.py "$QUERY" --results "$N" --company-merge --out leads.csv

echo ""
if [ -f leads.csv ]; then
  echo "Done! Opening leads.csv (it opens in Numbers or Excel)."
  open leads.csv 2>/dev/null
else
  echo "Finished, but no results file was created. Try a different search."
fi
echo ""
read -n 1 -s -r -p "Press any key to close this window."
