"""Job portal scraper modules."""

from .base import JobListing, BaseScraper
from .linkedin_scraper import LinkedInScraper
from .naukri_scraper import NaukriScraper
from .iimjobs_scraper import IIMJobsScraper

__all__ = ["JobListing", "BaseScraper", "LinkedInScraper", "NaukriScraper", "IIMJobsScraper"]
