"""
Scrape structured business leads from one or more web pages using ScrapeGraphAI.

Usage:
    python scrape_leads.py <url> [<url> ...] [--urls-file urls.txt]
        [--prompt "what to extract"] [--out leads.json|leads.csv]
        [--delay SECONDS] [--no-dedupe]

Examples:
    python scrape_leads.py https://example.com/directory
    python scrape_leads.py https://a.com https://b.com --out output/leads.csv
    python scrape_leads.py --urls-file urls.txt --delay 3 --out output/leads.csv

Politeness: when scraping several pages, --delay (default 2s) waits between
requests so you don't hammer a host. Results from all pages are merged and
de-duplicated by email/domain/name unless you pass --no-dedupe.

Output format follows the --out extension: .csv writes a spreadsheet, anything
else (or no --out) writes/prints JSON.

Before you run it, read the "Responsible use" section in README.md. Scraping
personal contact data has real legal limits (site Terms of Service, GDPR,
CAN-SPAM, CFAA). "Unlimited" is not realistic: every page costs an LLM call,
and sites rate-limit and block scrapers. Scrape sources you're allowed to
scrape, at a polite rate.
"""

import argparse
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

from leads_common import LeadList, build_config, write_output


def scrape_one(url: str, prompt: str) -> dict:
    graph = SmartScraperGraph(
        prompt=prompt,
        source=url,
        config=build_config(),
        schema=LeadList,
    )
    return graph.run()


def scrape_many(urls: List[str], prompt: str, delay: float) -> dict:
    all_leads: List[dict] = []
    for i, url in enumerate(urls):
        if i > 0 and delay > 0:
            time.sleep(delay)  # politeness delay between hosts
        print(f"[{i + 1}/{len(urls)}] {url}")
        result = scrape_one(url, prompt)
        leads = result.get("leads", []) if isinstance(result, dict) else []
        all_leads.extend(leads)
    return {"leads": all_leads}


def collect_urls(args) -> List[str]:
    urls = list(args.url)
    if args.urls_file:
        lines = Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        urls += [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    if not urls:
        raise SystemExit("Provide at least one URL, or --urls-file with URLs.")
    return urls


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Scrape structured leads from URLs.")
    parser.add_argument("url", nargs="*", help="One or more pages to scrape")
    parser.add_argument("--urls-file", help="Text file with one URL per line (# = comment)")
    parser.add_argument(
        "--prompt",
        default="Extract all business/contact leads on this page with their "
        "name, company, email, phone, website, and address.",
        help="Natural-language description of what to extract",
    )
    parser.add_argument("--out", help="Write to this file (.json or .csv)")
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds to wait between pages when scraping several (default 2)",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Keep duplicate leads instead of merging them",
    )
    parser.add_argument(
        "--company-merge",
        action="store_true",
        help="Collapse all leads at the same domain into one company "
        "(aggregates emails/phones)",
    )
    args = parser.parse_args()

    urls = collect_urls(args)
    result = scrape_many(urls, args.prompt, args.delay)
    write_output(
        result,
        args.out,
        dedupe=not args.no_dedupe,
        company_merge=args.company_merge,
    )


if __name__ == "__main__":
    main()
