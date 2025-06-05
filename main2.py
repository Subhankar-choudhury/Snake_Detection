import os
import requests
from time import sleep
from urllib.parse import quote
from typing import List, Optional
import logging
from pathlib import Path
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('inat_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class INaturalistScraper:
    BASE_URL = "https://api.inaturalist.org/v1/observations"
    REQUEST_DELAY = 1.5  # seconds between requests to be polite to the API
    MAX_RETRIES = 3
    TIMEOUT = 30  # seconds
    TARGET_IMAGES_PER_SPECIES = 250
    PER_PAGE = 30  # Max allowed by iNaturalist API
    
    def __init__(self, output_dir: str = "dataset"):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "iNaturalistImageScraper/1.0 (https://github.com/yourusername)",
            "Accept": "application/json"
        })
        
    def _make_request(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make an API request with retries and error handling."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.TIMEOUT
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < self.MAX_RETRIES - 1:
                    sleep(2 ** attempt)  # exponential backoff
                else:
                    logger.error(f"Failed after {self.MAX_RETRIES} attempts: {url}")
                    return None
    
    def _ensure_output_dir(self, taxon_name: str) -> Path:
        """Create output directory for the taxon if it doesn't exist."""
        taxon_dir = Path(self.output_dir) / taxon_name.replace(' ', '_')
        taxon_dir.mkdir(parents=True, exist_ok=True)
        return taxon_dir
    
    def download_image(self, url: str, save_path: Path) -> bool:
        """Download and save an image from a URL."""
        try:
            response = self.session.get(
                url,
                stream=True,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            with save_path.open('wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded: {save_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {str(e)}")
            return False
    
    def scrape_taxon(self, taxon_name: str) -> None:
        """Scrape research-grade observations for a given taxon."""
        logger.info(f"Starting scrape for {taxon_name}")
        
        taxon_dir = self._ensure_output_dir(taxon_name)
        total_downloaded = 0
        page = 1
        max_pages = math.ceil(self.TARGET_IMAGES_PER_SPECIES / self.PER_PAGE)
        
        while total_downloaded < self.TARGET_IMAGES_PER_SPECIES:
            logger.info(f"Processing page {page} (Downloaded {total_downloaded}/{self.TARGET_IMAGES_PER_SPECIES})")
            
            params = {
                'taxon_name': taxon_name,
                'quality_grade': 'research',
                'photos': 'true',
                'per_page': self.PER_PAGE,
                'page': page,
                'order': 'desc',
                'order_by': 'created_at'
            }
            
            data = self._make_request(self.BASE_URL, params)
            if not data or 'results' not in data or not data['results']:
                logger.warning(f"No more results found for {taxon_name}")
                break
            
            for result in data['results']:
                if not result.get('photos'):
                    continue
                    
                for i, photo in enumerate(result['photos'], 1):
                    if total_downloaded >= self.TARGET_IMAGES_PER_SPECIES:
                        break
                        
                    # Get the best available image URL
                    image_url = photo['url'].replace("square", "original")
                    ext = image_url.split('.')[-1].lower()
                    if ext not in ['jpg', 'jpeg', 'png']:
                        ext = 'jpg'
                        
                    filename = f"{result['id']}_{i}.{ext}"
                    save_path = taxon_dir / filename
                    
                    if save_path.exists():
                        logger.debug(f"Skipping existing file: {save_path}")
                        continue
                        
                    if self.download_image(image_url, save_path):
                        total_downloaded += 1
                        sleep(self.REQUEST_DELAY)
            
            page += 1
            
            # Safety check to prevent infinite loops
            if page > max_pages * 2:  # Allow some extra pages in case some observations don't have photos
                logger.warning(f"Reached maximum page limit for {taxon_name}")
                break
        
        logger.info(f"Finished scraping {taxon_name}. Downloaded {total_downloaded} images.")

def main():
    # Configuration
    species_list = [
        "Python molurus",      # Indian Rock Python
        "Bungarus caeruleus",  # Common Krait
        "Dendrelaphis punctulatus",  # Green Tree Snake
    ]
    
    # Initialize scraper
    scraper = INaturalistScraper(output_dir="inat_images")
    
    # Process each species
    for species in species_list:
        try:
            logger.info(f"\n{'='*50}\nProcessing species: {species}\n{'='*50}")
            scraper.scrape_taxon(species)
        except Exception as e:
            logger.error(f"Error processing {species}: {str(e)}", exc_info=True)
            continue

if __name__ == "__main__":
    main()
