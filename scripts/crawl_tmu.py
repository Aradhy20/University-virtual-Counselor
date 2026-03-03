import os
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

TARGET_URLS = [
    "https://www.tmu.ac.in/",
    "https://www.tmu.ac.in/about-us",
    "https://www.tmu.ac.in/tmu/why-tmu",
    "https://www.tmu.ac.in/admission/procedure",
    "https://www.tmu.ac.in/contact-us",
    "https://www.tmu.ac.in/tmu/placement-overview"
]

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "website_content"

def ensure_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True)

def clean_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.extract()    

    # Get text
    text = soup.get_text(separator='\n')
    
    # Break into lines and remove leading/trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def crawl():
    ensure_dir(OUTPUT_DIR)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for url in TARGET_URLS:
        try:
            logger.info(f"Fetching {url}...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            content = clean_text(response.text)
            
            # Create filename from URL
            filename = url.replace("https://www.tmu.ac.in/", "").replace("/", "_").strip("_")
            if not filename:
                filename = "home"
            filename += ".txt"
            
            file_path = OUTPUT_DIR / filename
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Source: {url}\n\n")
                f.write(content)
                
            logger.info(f"Saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")

if __name__ == "__main__":
    crawl()
