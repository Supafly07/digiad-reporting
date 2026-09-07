"""
Find leads across MULTIPLE sites using ScrapeGraphAI's SearchGraph.

Unlike scrape_leads.py (one URL you provide), SearchGraph runs a web search
for your prompt, scrapes the top results, and merges what it finds. This is
the closest thing to "find me leads about X" — but it costs one LLM pass per
result page, so more results = more time and more API spend.

Usage:
    python search_leads.py "<what to find>" [--results N] [--out leads.json|leads.csv]

Examples:
    python search_leads.py "dental clinics in Austin Texas with contact details"
    python search_leads.py "commercial real estate agencies in Chicago" \
        --results 5 --out output/agencies.csv

Read the "Responsible use" section in README.md before running. Search results
are other people's sites — respect their Terms of Service and applicable data
and anti-spam law (GDPR, CAN-SPAM, CFAA).
"""

import argparse

from dotenv import load_dotenv
from scrapegraphai.graphs import SearchGraph

from leads_common import LeadList, build_config, write_output


def search(prompt: str, max_results: int) -> dict:
    # SearchGraph takes no source URL — it searches the web itself.
    graph = SearchGraph(
        prompt=prompt,
        config=build_config({"max_results": max_results}),
        schema=LeadList,
    )
    return graph.run()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Find leads across the web.")
    parser.add_argument("query", help="What to search for and extract")
    parser.add_argument(
        "--results",
        type=int,
        default=3,
        help="How many search results to scrape (default 3). More = slower + costlier.",
    )
    parser.add_argument("--out", help="Write to this file (.json or .csv)")
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
    parser.add_argument(
        "--append",
        action="store_true",
        help="Fold existing rows in --out into the results (build a master list "
        "across runs)",
    )
    args = parser.parse_args()

    result = search(args.query, args.results)
    write_output(
        result,
        args.out,
        dedupe=not args.no_dedupe,
        company_merge=args.company_merge,
        append=args.append,
    )


if __name__ == "__main__":
    main()
