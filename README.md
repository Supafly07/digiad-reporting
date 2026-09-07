# Lead scraping with ScrapeGraphAI

Structured web-to-JSON lead scraping powered by
[ScrapeGraphAI](https://github.com/ScrapeGraphAI/Scrapegraph-ai) — it loads a
page in a headless browser and uses an LLM to extract the fields you ask for
into clean, structured data.

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Install the headless browser ScrapeGraphAI drives
playwright install chromium

# 4. Add your LLM API key
cp .env.example .env             # then edit .env and paste your OPENAI_API_KEY
```

> **Why the versions are pinned.** `pip install scrapegraphai` on its own
> currently resolves to langchain 1.x, which the library isn't compatible with
> yet — it fails on import. `requirements.txt` pins a verified working set
> (scrapegraphai 1.40.0 + langchain 0.3.x). Bump them together, not one at a
> time.

## Usage

```bash
# Scrape one page, print JSON to the terminal
python scrape_leads.py https://example.com/directory

# Custom extraction prompt + save to a file
python scrape_leads.py https://example.com/members \
    --prompt "Extract every business listing with contact details" \
    --out output/leads.json
```

Output is a list of records with `name`, `company`, `email`, `phone`,
`website`, and `address` (missing fields come back `null`). Edit the `Lead`
schema in `scrape_leads.py` to change what gets extracted.

## Cost & scale — the honest version

There is no "unlimited" free lead scraping. Realities to plan around:

- **Every page costs an LLM call.** Thousands of pages = a real API bill. Use
  `gpt-4o-mini` (the default) to keep it cheap; `gpt-4o` is more accurate but
  pricier. Set the model with `SCRAPE_MODEL` in `.env`.
- **Sites rate-limit and block scrapers.** High-volume scraping gets IPs
  blocked and often violates the site's Terms of Service. Scrape at a polite
  rate; add delays; don't hammer a host.
- **To go beyond a single page**, ScrapeGraphAI also offers `SearchGraph`
  (search-engine-driven, multi-source) and `SmartScraperMultiGraph`. See the
  [docs](https://scrapegraph-ai.readthedocs.io/).

## Responsible use

Scraping contact/personal data is legally constrained. Before scraping a
source, make sure you're on the right side of:

- The site's **Terms of Service** and `robots.txt`.
- **Data-protection law** — GDPR (EU), CCPA (California), and similar laws
  regulate collecting and using personal data, including business emails.
- **Anti-spam law** — CAN-SPAM (US), CASL (Canada), PECR (UK) govern how you
  may contact leads you collect.
- **Computer-misuse law** — e.g. the CFAA (US); don't scrape behind logins or
  bypass access controls without permission.

Prefer sources you own or are licensed to use, official APIs, and opt-in data.
When in doubt, get permission.
