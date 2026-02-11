"""
One-time script: backfill the `date` column in Supabase for all existing rows.
Supports arXiv, ACM, and general article pages.
Run from app/ with: python backfill_date.py
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

logging.basicConfig(level=logging.INFO)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AcademicDateBot/1.0)"
}


# -------------------------
# Site-specific extractors
# -------------------------

def extract_arxiv_date(url: str):
    """
    arXiv pages expose submission history.
    Use first submission date.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        history = soup.find("div", class_="submission-history")
        if not history:
            return None

        text = history.get_text(" ", strip=True)
        match = re.search(r"\b(\d{1,2}\s+\w+\s+\d{4})\b", text)
        if match:
            dt = datetime.strptime(match.group(1), "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logging.debug(f"arXiv date failed for {url}: {e}")

    return None


def extract_acm_date(url: str):
    """
    ACM exposes citation meta tags
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        meta = soup.find("meta", {"name": "citation_publication_date"})
        if meta and meta.get("content"):
            dt = datetime.strptime(meta["content"], "%Y/%m/%d")
            return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logging.debug(f"ACM date failed for {url}: {e}")

    return None


def extract_generic_date(url: str):
    """
    Fallback: newspaper3k
    """
    try:
        a = Article(url)
        a.download()
        a.parse()
        if a.publish_date:
            return a.publish_date.strftime("%Y-%m-%d")
    except Exception as e:
        logging.debug(f"Generic date failed for {url}: {e}")

    return None


def get_date_from_url(url: str):
    if "arxiv.org" in url:
        return extract_arxiv_date(url)
    if "dl.acm.org" in url:
        return extract_acm_date(url)

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
    for i in range(5):
        result = client.table("data").select("title, url, date").is_("date", "null").execute()
        rows = result.data

        if not rows:
            logging.info("No rows need backfilling.")
            return

        updated = 0
        failed = 0

        for row in tqdm(rows, desc="Backfilling dates"):
            row_title = row["title"]
            url = row["url"]

            if not url:
                failed += 1
                continue

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

            time.sleep(0.5)  # be polite

        logging.info(f"Done. Updated={updated}, Failed={failed}")


if __name__ == "__main__":
    main()
