"""
Scrape structured business leads from a single web page using ScrapeGraphAI.

Usage:
    python scrape_leads.py <url> [--prompt "what to extract"] [--out leads.json|leads.csv]

Examples:
    python scrape_leads.py https://example.com/directory
    python scrape_leads.py https://example.com/members \
        --prompt "Extract every business listing" \
        --out output/leads.csv

Output format follows the --out extension: .csv writes a spreadsheet, anything
else (or no --out) writes/prints JSON.

Before you run it, read the "Responsible use" section in README.md. Scraping
personal contact data has real legal limits (site Terms of Service, GDPR,
CAN-SPAM, CFAA). "Unlimited" is not realistic: every page costs an LLM call,
and sites rate-limit and block scrapers. Scrape sources you're allowed to
scrape, at a polite rate.
"""

import argparse

from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

from leads_common import LeadList, build_config, write_output


def scrape(url: str, prompt: str) -> dict:
    graph = SmartScraperGraph(
        prompt=prompt,
        source=url,
        config=build_config(),
        schema=LeadList,
    )
    return graph.run()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Scrape structured leads from a URL.")
    parser.add_argument("url", help="Page to scrape")
    parser.add_argument(
        "--prompt",
        default="Extract all business/contact leads on this page with their "
        "name, company, email, phone, website, and address.",
        help="Natural-language description of what to extract",
    )
    parser.add_argument("--out", help="Write to this file (.json or .csv)")
    args = parser.parse_args()

    result = scrape(args.url, args.prompt)
    write_output(result, args.out)


if __name__ == "__main__":
    main()
