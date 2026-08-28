import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """
    Abstract base class for all data extractors.
    Handles robust HTTP requests, rate limiting, and file saving.
    """
    
    def __init__(self, output_dir: str = "data/raw", rate_limit_seconds: float = 2.0):
        self.output_dir = output_dir
        self.rate_limit_seconds = rate_limit_seconds
        self.last_request_time = 0.0
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configure a robust requests session with retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ETL_OpenDataPH_MVP/1.0 (Research Project; Contact: developer@example.com)"
        })
        
        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _wait_for_rate_limit(self):
        """Enforces a delay between requests to respect server rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self.last_request_time = time.time()

    def download_file(self, url: str, filename: str) -> Optional[str]:
        """
        Downloads a file from the given URL and saves it to the output directory.
        
        Args:
            url (str): The URL of the file to download.
            filename (str): The local name to save the file as.
            
        Returns:
            Optional[str]: The absolute path to the downloaded file, or None if failed.
        """
        self._wait_for_rate_limit()
        
        filepath = os.path.join(self.output_dir, filename)
        logger.info(f"Downloading {url} to {filepath}")
        
        try:
            response = self.session.get(url, stream=True, timeout=(10, 30))
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Successfully downloaded {filename}")
            return os.path.abspath(filepath)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return None

    def fetch_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Fetches JSON data from a REST API endpoint.
        """
        self._wait_for_rate_limit()
        
        logger.info(f"Fetching JSON from {url}")
        try:
            response = self.session.get(url, params=params, timeout=(10, 30))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch JSON from {url}: {e}")
            return None
            
    @abstractmethod
    def extract(self) -> list[str]:
        """
        Main extraction method to be implemented by child classes.
        Should return a list of file paths to the downloaded raw files.
        """
        pass
