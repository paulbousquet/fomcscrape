# thanks to Hyeongjun Do (github: dorae222)
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{}.htm"
YEARS = range(1983, 2008)  # PDFs only, zip years handled separately

PATTERNS = {
    "Greenbook": re.compile(r"gbpt[12]", re.IGNORECASE),
    "Bluebook": re.compile(r"bluebook", re.IGNORECASE),
    "Tealbook": re.compile(r"tealbook[ab]", re.IGNORECASE),
}

OUTPUT_DIRS = {
    "Greenbook": "greenbooks",
    "Bluebook": "bluebooks",
    "Tealbook": "tealbooks",
}

for d in OUTPUT_DIRS.values():
    os.makedirs(d, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "FOMC-Collector/1.0"})

def classify_url(url):
    for doc_type, pattern in PATTERNS.items():
        if pattern.search(url):
            return doc_type
    return None

def extract_pdf_links(year):
    url = BASE_URL.format(year)
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return []
    
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    
    for a in soup.select("a[href]"):
        href = a["href"].lower()
        if not href.endswith(".pdf"):
            continue
        doc_type = classify_url(href)
        if doc_type:
            full_url = urljoin(url, a["href"])
            links.append({"url": full_url, "doc_type": doc_type})
    
    return links

def download_pdf(url, doc_type):
    filename = url.split("/")[-1]
    filepath = os.path.join(OUTPUT_DIRS[doc_type], filename)
    
    if os.path.exists(filepath):
        return False
    
    try:
        r = session.get(url, timeout=60)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

all_links = []
for year in tqdm(YEARS, desc="Scraping years"):
    all_links.extend(extract_pdf_links(year))

seen = set()
unique = [l for l in all_links if l["url"] not in seen and not seen.add(l["url"])]

print(f"Found {len(unique)} unique PDFs")
for doc_type in OUTPUT_DIRS:
    count = sum(1 for l in unique if l["doc_type"] == doc_type)
    print(f"  {doc_type}: {count}")

downloaded = 0
for link in tqdm(unique, desc="Downloading PDFs"):
    if download_pdf(link["url"], link["doc_type"]):
        downloaded += 1

print(f"\nDownloaded {downloaded} new PDFs")
