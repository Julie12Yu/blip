"""
One-time script: backfill the `date` column in Supabase for all existing rows.
Supports arXiv, ACM, and general article pages.

Run from app/ with:
    python backfill_date.py
"""

import sys
sys.dont_write_bytecode = True

import os
import time
import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client
from newspaper import Article
from tqdm import tqdm

# -------------------------
# Config
# -------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AcademicDateBot/1.0)"
}

REQUEST_TIMEOUT = 10
SLEEP_SECONDS = 0.7  # be polite to ACM/arXiv


# -------------------------
# Helpers
# -------------------------

def parse_date(date_str: str):
    """
    Parse common citation date formats into YYYY-MM-DD.
    """
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# -------------------------
# arXiv
# -------------------------

def normalize_arxiv_url(url: str) -> str:
    """
    Normalize arXiv URLs:
    - remove version suffixes
    - convert /pdf/ links to /abs/
    """
    url = re.sub(r"v\d+$", "", url)
    if "/pdf/" in url:
        url = url.replace("/pdf/", "/abs/").replace(".pdf", "")
    return url


def extract_arxiv_date(url: str):
    """
    arXiv exposes reliable citation meta tags.
    Uses the first submission date.
    """
    try:
        url = normalize_arxiv_url(url)
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        meta = (
            soup.find("meta", {"name": "citation_date"})
            or soup.find("meta", {"name": "citation_publication_date"})
        )

        if meta and meta.get("content"):
            return parse_date(meta["content"])

    except Exception as e:
        logging.debug(f"arXiv date failed for {url}: {e}")

    return None


# -------------------------
# ACM
# -------------------------

def extract_acm_date(url: str):
    """
    Robust ACM DL date extraction.
    Handles citation meta tags, OpenGraph, and split year/month fields.
    """
    try:
        headers = {
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        # 1. Common ACM citation tags (most reliable)
        meta_names = [
            "citation_publication_date",
            "citation_online_date",
            "citation_cover_date",
            "citation_conference_date",
        ]

        for name in meta_names:
            meta = soup.find("meta", {"name": name})
            if meta and meta.get("content"):
                parsed = parse_date(meta["content"])
                if parsed:
                    return parsed

        # 2. OpenGraph published time
        og = soup.find("meta", {"property": "article:published_time"})
        if og and og.get("content"):
            try:
                dt = datetime.fromisoformat(og["content"].replace("Z", ""))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # 3. Split year/month fallback
        year_meta = soup.find("meta", {"name": "citation_year"})
        month_meta = soup.find("meta", {"name": "citation_month"})

        if year_meta and month_meta:
            try:
                year = int(year_meta["content"])
                month = int(month_meta["content"])
                return datetime(year, month, 1).strftime("%Y-%m-%d")
            except ValueError:
                pass

    except Exception as e:
        logging.debug(f"ACM date failed for {url}: {e}")

    return None



# -------------------------
# Generic fallback
# -------------------------

def extract_generic_date(url: str):
    """
    Fallback for non-academic pages using newspaper3k.
    """
    try:
        article = Article(url)
        article.download()
        article.parse()

        if article.publish_date:
            return article.publish_date.strftime("%Y-%m-%d")

    except Exception as e:
        logging.debug(f"Generic date failed for {url}: {e}")

    return None



def extract_crossref_date_from_doi(doi: str):
    """
    Fetch publication date from Crossref.
    Prefers published-print → published-online → issued.
    """
    try:
        r = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "AcademicDateBot/1.0 (mailto:you@example.com)"},
            timeout=10,
        )
        r.raise_for_status()

        data = r.json()["message"]

        date_fields = [
            "published-print",
            "published-online",
            "issued",
        ]

        for field in date_fields:
            if field in data and "date-parts" in data[field]:
                parts = data[field]["date-parts"][0]
                year = parts[0]
                month = parts[1] if len(parts) > 1 else 1
                day = parts[2] if len(parts) > 2 else 1
                return datetime(year, month, day).strftime("%Y-%m-%d")

    except Exception as e:
        logging.debug(f"Crossref failed for DOI {doi}: {e}")

    return None


def extract_doi_from_acm_url(url: str):
    match = re.search(r"/doi/(?:abs/)?(10\.\d{4,9}/[^?#]+)", url)
    return match.group(1) if match else None

# -------------------------
# Dispatcher
# -------------------------

def get_date_from_url(url: str):
    if not url:
        return None

    if "arxiv.org" in url:
        return extract_arxiv_date(url)

    if "dl.acm.org" in url:
        doi = extract_doi_from_acm_url(url)
        print("doi " + doi)
        if doi:
            print("OHTHTHR " + extract_crossref_date_from_doi(doi))
            return extract_crossref_date_from_doi(doi)
        return None

    return extract_generic_date(url)


# -------------------------
# Main
# -------------------------

def main():
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY")

    client = create_client(supabase_url, supabase_key)

    logging.info("Fetching rows without dates...")

    while True:
        result = (
            client
            .table("data")
            .select("title, url, date")
            .is_("date", "null")
            .limit(1000)
            .execute()
        )

        rows = result.data or []
        if not rows:
            logging.info("No rows left to backfill.")
            break

        updated = 0
        failed = 0

        for row in tqdm(rows, desc="Backfilling dates"):
            row_title = row["title"]
            url = row["url"]

            date_str = get_date_from_url(url)

            if date_str:
                try:
                    client.table("data") \
                        .update({"date": date_str}) \
                        .eq("title", row_title) \
                        .execute()
                    updated += 1
                except Exception as e:
                    logging.error(f"Supabase update failed (title={row_title}): {e}")
                    failed += 1
            else:
                failed += 1

            time.sleep(SLEEP_SECONDS)

        logging.info(f"Batch complete. Updated={updated}, Failed={failed}")

    logging.info("Backfill finished.")


if __name__ == "__main__":
    main()
