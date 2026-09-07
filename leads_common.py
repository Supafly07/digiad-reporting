"""Shared pieces for the lead-scraping scripts: schema, LLM config, output."""

import csv
import json
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


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


def build_config(extra: Optional[dict] = None) -> dict:
    """LLM/browser config read from the environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    config = {
        "llm": {
            "api_key": api_key,
            "model": os.getenv("SCRAPE_MODEL", "openai/gpt-4o-mini"),
        },
        "headless": True,
        "verbose": True,
    }
    if extra:
        config.update(extra)
    return config


def _extract_leads(result) -> List[dict]:
    """Pull a flat list of lead dicts out of whatever the graph returned."""
    if isinstance(result, dict) and "leads" in result:
        return result["leads"]
    if isinstance(result, list):
        return result
    # Fall back to a single record so nothing is silently dropped.
    return [result] if result else []


# Column order for CSV output; matches the Lead schema.
FIELDNAMES = list(Lead.model_fields.keys())


def write_output(result, out: Optional[str]) -> None:
    """Write results as JSON or CSV (by file extension), or print JSON."""
    if not out:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.suffix.lower() == ".csv":
        rows = _extract_leads(result)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row if isinstance(row, dict) else {})
        print(f"Wrote {len(rows)} rows to {out_path}")
    else:
        out_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote results to {out_path}")
