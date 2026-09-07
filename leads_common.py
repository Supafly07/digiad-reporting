"""Shared pieces for the lead-scraping scripts: schema, LLM config, output."""

import csv
import json
import os
import re
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


def _domain(website: Optional[str]) -> Optional[str]:
    """Normalize a website to a bare domain for matching (drop scheme/www/path)."""
    if not website:
        return None
    host = re.sub(r"^\w+://", "", website.strip().lower())
    host = host.split("/")[0].split("?")[0]
    return host[4:] if host.startswith("www.") else host or None


def _dedupe_key(lead: dict) -> Optional[str]:
    """Identity for a lead: email, else domain, else name+company. None = keep as-is."""
    email = (lead.get("email") or "").strip().lower()
    if email:
        return f"email:{email}"
    domain = _domain(lead.get("website"))
    if domain:
        return f"domain:{domain}"
    name = (lead.get("name") or "").strip().lower()
    company = (lead.get("company") or "").strip().lower()
    if name or company:
        return f"nc:{name}|{company}"
    return None


def dedupe_leads(leads: List[dict]) -> List[dict]:
    """Merge duplicate leads, filling blank fields from later matches.

    Records with no identifying field at all are kept as-is (never merged).
    """
    merged: dict = {}
    passthrough: List[dict] = []
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        key = _dedupe_key(lead)
        if key is None:
            passthrough.append(lead)
            continue
        if key not in merged:
            merged[key] = dict(lead)
        else:
            existing = merged[key]
            for field, value in lead.items():
                if not existing.get(field) and value:
                    existing[field] = value
    return list(merged.values()) + passthrough


def _email_domain(email: Optional[str]) -> Optional[str]:
    """Domain part of an email address, lowercased."""
    if not email or "@" not in email:
        return None
    return email.strip().lower().rsplit("@", 1)[-1] or None


def _join_unique(values: List[Optional[str]]) -> str:
    """Distinct, order-preserving, non-empty values joined for one CSV cell."""
    seen: dict = {}
    for v in values:
        v = (v or "").strip()
        if v and v.lower() not in seen:
            seen[v.lower()] = v
    return "; ".join(seen.values())


def merge_by_domain(leads: List[dict]) -> List[dict]:
    """Collapse every lead sharing a web/email domain into one company record.

    Unlike dedupe_leads (which keeps distinct contacts), this treats a domain as
    a single company: all its emails and phones are aggregated into "; "-joined
    lists. Leads with no resolvable domain fall back to dedupe_leads behavior.
    """
    groups: dict = {}
    order: List[str] = []
    no_domain: List[dict] = []
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        domain = _domain(lead.get("website")) or _email_domain(lead.get("email"))
        if not domain:
            no_domain.append(lead)
            continue
        if domain not in groups:
            groups[domain] = []
            order.append(domain)
        groups[domain].append(lead)

    merged: List[dict] = []
    for domain in order:
        members = groups[domain]
        merged.append(
            {
                "name": next((m.get("name") for m in members if m.get("name")), None),
                "company": next(
                    (m.get("company") for m in members if m.get("company")), None
                ),
                "email": _join_unique([m.get("email") for m in members]) or None,
                "phone": _join_unique([m.get("phone") for m in members]) or None,
                "website": domain,
                "address": next(
                    (m.get("address") for m in members if m.get("address")), None
                ),
            }
        )
    # Domainless records still get the normal contact-level dedupe.
    return merged + dedupe_leads(no_domain)


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


def write_output(
    result, out: Optional[str], dedupe: bool = False, company_merge: bool = False
) -> None:
    """Write results as JSON or CSV (by file extension), or print JSON.

    company_merge collapses all leads sharing a domain into one company record
    (aggregating emails/phones). Otherwise dedupe merges distinct contacts by
    email/domain/name. Either normalizes results to {"leads": [...]}.
    """
    if company_merge:
        before = _extract_leads(result)
        after = merge_by_domain(before)
        if len(after) != len(before):
            print(f"Merged {len(before)} leads -> {len(after)} companies by domain")
        result = {"leads": after}
    elif dedupe:
        before = _extract_leads(result)
        after = dedupe_leads(before)
        if len(after) != len(before):
            print(f"Deduplicated {len(before)} -> {len(after)} leads")
        result = {"leads": after}

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
