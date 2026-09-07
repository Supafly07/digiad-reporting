# Lead scraping with ScrapeGraphAI

Structured web-to-JSON lead scraping powered by
[ScrapeGraphAI](https://github.com/ScrapeGraphAI/Scrapegraph-ai) — it loads a
page in a headless browser and uses an LLM to extract the fields you ask for
into clean, structured data.

## Easiest start on a Mac (no typing)

1. Download this project: on the GitHub page click the green **`< > Code`**
   button → **Download ZIP**, then double-click the ZIP to unzip it.
2. Double-click **`setup_mac.command`**. The first time, Mac may say it's from an
   unidentified developer — **right-click the file → Open → Open** to allow it.
   It installs everything, then opens a text file. Paste your OpenAI key after
   `OPENAI_API_KEY=`, press **⌘S**, and close the window.
3. Double-click **`run_mac.command`**, type what leads you want, and press
   Return. When it finishes, `leads.csv` opens in Numbers/Excel.

That's it. Use `run_mac.command` any time after that. The rest of this README is
the manual/command-line version.

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

There are two entry points. Both share the `Lead` schema and output helpers in
`leads_common.py`, and both write **JSON or CSV** depending on the `--out`
extension (no `--out` prints JSON to the terminal).

### 1. Scrape pages you already have — `scrape_leads.py`

```bash
# Print JSON to the terminal
python scrape_leads.py https://example.com/directory

# Custom prompt, save as CSV
python scrape_leads.py https://example.com/members \
    --prompt "Extract every business listing with contact details" \
    --out output/leads.csv

# Several pages at once, from args or a file (one URL per line, # = comment)
python scrape_leads.py https://a.com https://b.com --out output/leads.csv
python scrape_leads.py --urls-file urls.txt --delay 3 --out output/leads.csv
```

- `--delay SECONDS` (default 2) waits between pages so you don't hammer a host.
- Results from all pages are merged and **de-duplicated** by email → domain →
  name/company, filling blank fields from matching records. Pass `--no-dedupe`
  to keep every raw record.
- `--company-merge` collapses every lead sharing a domain into **one company**
  (matched by website *or* email domain), aggregating all its emails and phones
  into `; `-separated lists — so `info@acme.com`, `sales@acme.com`, and
  `bob@acme.com` become a single Acme row. Use this for company-level lists;
  omit it when you want individual contacts.
- `--append` builds a **master list across runs**: it reads the existing
  `--out` file (`.csv` or `.json`), folds those rows in with the new results,
  and re-runs the same dedupe/company-merge over the union before writing back.
  Re-running is idempotent — nothing gets duplicated. Keep the dedupe/merge
  flags consistent between runs so the master list stays coherent.

```bash
# Grow output/master.csv over several scraping sessions
python scrape_leads.py --urls-file batch1.txt --out output/master.csv --append
python scrape_leads.py --urls-file batch2.txt --out output/master.csv --append
python search_leads.py "roofing companies in Miami" --out output/master.csv --append
```

### 2. Find leads across many sites — `search_leads.py`

Uses ScrapeGraphAI's `SearchGraph`: it runs a web search for your query,
scrapes the top results, and merges what it finds.

```bash
python search_leads.py "dental clinics in Austin Texas with contact details"

python search_leads.py "commercial real estate agencies in Chicago" \
    --results 5 --out output/agencies.csv
```

`--results N` sets how many search results to scrape (default 3). Each result
is a separate LLM pass, so more results = more time and more API spend. Merged
results are de-duplicated the same way; pass `--no-dedupe` to keep every record.

Output records have `name`, `company`, `email`, `phone`, `website`, and
`address` (missing fields come back `null`/blank). Edit the `Lead` schema in
`leads_common.py` to change what gets extracted — both scripts pick it up.

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
