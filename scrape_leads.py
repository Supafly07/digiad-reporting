"""
Scrape structured business leads from a web page using ScrapeGraphAI.

Usage:
    python scrape_leads.py <url> [--prompt "what to extract"] [--out leads.json]

Example:
    python scrape_leads.py https://example.com/directory \
        --prompt "Extract every business listing" \
        --out output/leads.json

What it does:
    ScrapeGraphAI loads the page (headless browser), then uses an LLM to pull
    the fields defined in the `Lead` schema below into clean, structured JSON.

Before you run it, read the "Responsible use" section in README.md. Scraping
personal contact data has real legal limits (site Terms of Service, GDPR,
CAN-SPAM, CFAA). "Unlimited" is not realistic: every page costs an LLM call,
and sites rate-limit and block scrapers. Scrape sources you're allowed to
scrape, at a polite rate.
"""

import argparse
import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from scrapegraphai.graphs import SmartScraperGraph


class Lead(BaseModel):
    """One business/contact record. Missing fields are left null."""

    name: Optional[str] = Field(None, description="Person or business name")
    company: Optional[str] = Field(None, description="Company or organization")
    email: Optional[str] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Contact phone number")
    website: Optional[str] = Field(None, description="Website URL")
    address: Optional[str] = Field(None, description="Physical address")


class LeadList(BaseModel):
    leads: List[Lead]


def build_config() -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return {
        "llm": {
            "api_key": api_key,
            "model": os.getenv("SCRAPE_MODEL", "openai/gpt-4o-mini"),
        },
        "headless": True,
        "verbose": True,
    }


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
    parser.add_argument("--out", help="Write results to this JSON file")
    args = parser.parse_args()

    result = scrape(args.url, args.prompt)

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"Wrote results to {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    main()
