# thanks to Hyeongjun Do (github: dorae222)
import csv
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{}.htm"
YEARS = range(1983, 2020)

PATTERNS = {
    "Greenbook": re.compile(r"gbpt[12]", re.IGNORECASE),
    "Bluebook": re.compile(r"bluebook", re.IGNORECASE),
    "Tealbook": re.compile(r"tealbook[ab]", re.IGNORECASE),
}

ZIP_PATTERNS = {
    "Greenbook": re.compile(r"gbmaterial", re.IGNORECASE),
    "Tealbook": re.compile(r"tealbookmaterial", re.IGNORECASE),
}

def get_session():
    s = requests.Session()
    s.headers.update({"User-Agent": "FOMC-Collector/1.0"})
    return s

def classify_url(url, year):
    if 2008 <= year <= 2012:
        for doc_type, pattern in ZIP_PATTERNS.items():
            if pattern.search(url):
                return doc_type
    else:
        for doc_type, pattern in PATTERNS.items():
            if pattern.search(url):
                return doc_type
    return None

def extract_links(session, year):
    url = BASE_URL.format(year)
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return []
    
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    
    ext = ".zip" if 2008 <= year <= 2012 else ".pdf"
    file_type = "zip" if 2008 <= year <= 2012 else "pdf"
    
    for a in soup.select("a[href]"):
        href = a["href"].lower()
        if not href.endswith(ext):
            continue
        
        doc_type = classify_url(href, year)
        if doc_type:
            full_url = urljoin(url, a["href"])
            text = re.sub(r"\s+", " ", a.get_text(" ")).strip()
            links.append({
                "source_url": full_url,
                "doc_type": doc_type,
                "file_type": file_type,
                "year": year,
                "link_text": text,
                "context_url": url,
            })
    
    return links

def main():
    csv_path = "fomc_books_manifest.csv"
    
    session = get_session()
    all_links = []
    
    for year in tqdm(YEARS, desc="Scraping years"):
        all_links.extend(extract_links(session, year))
    
    seen = set()
    unique = []
    for link in all_links:
        if link["source_url"] not in seen:
            seen.add(link["source_url"])
            unique.append(link)
    
    fieldnames = ["source_url", "doc_type", "file_type", "year", "link_text", "context_url"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique)
    
    print(f"\nSaved {len(unique)} links to {csv_path}")
    for doc_type in ["Greenbook", "Bluebook", "Tealbook"]:
        count = sum(1 for l in unique if l["doc_type"] == doc_type)
        print(f"  {doc_type}: {count}")

main()
