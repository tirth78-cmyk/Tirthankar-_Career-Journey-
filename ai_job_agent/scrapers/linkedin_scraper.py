"""LinkedIn job scraper using public search endpoints."""

import re
import time
import hashlib
import logging
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, JobListing

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Scrapes job listings from LinkedIn's public job search."""

    BASE_URL = "https://www.linkedin.com/jobs/search"

    def __init__(self, config: dict):
        super().__init__(config)
        self.portal_name = "linkedin"
        self.session = requests.Session()
        self.session.headers.update(self._build_headers())

    def search(self, keywords: list[str], location: str = "", **filters) -> list[JobListing]:
        """Search LinkedIn for jobs matching keywords and location."""
        query = " ".join(keywords)
        params = {
            "keywords": query,
            "location": location or "India",
            "f_TPR": "r604800",  # Past week
            "position": 1,
            "pageNum": 0,
        }

        job_type = filters.get("job_type", "")
        if job_type == "full-time":
            params["f_JT"] = "F"
        elif job_type == "contract":
            params["f_JT"] = "C"
        elif job_type == "internship":
            params["f_JT"] = "I"

        jobs = []
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            jobs = self._parse_search_results(response.text)
            logger.info(f"LinkedIn: Found {len(jobs)} jobs for '{query}'")
        except requests.RequestException as e:
            logger.error(f"LinkedIn search failed: {e}")

        return jobs

    def get_job_details(self, job_url: str) -> JobListing:
        """Fetch detailed information for a specific LinkedIn job."""
        try:
            response = self.session.get(job_url, timeout=30)
            response.raise_for_status()
            return self._parse_job_detail(response.text, job_url)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch job details: {e}")
            return JobListing(url=job_url, portal=self.portal_name)

    def _parse_search_results(self, html: str) -> list[JobListing]:
        """Parse LinkedIn search results HTML into JobListing objects."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        job_cards = soup.find_all("div", class_=re.compile(r"base-card|job-search-card"))
        for card in job_cards:
            try:
                title_el = card.find("h3", class_=re.compile(r"base-search-card__title"))
                company_el = card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
                location_el = card.find("span", class_=re.compile(r"job-search-card__location"))
                link_el = card.find("a", href=True)
                date_el = card.find("time")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else ""
                url = link_el["href"] if link_el else ""
                posted = date_el.get("datetime", "") if date_el else ""

                if not title:
                    continue

                job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]

                jobs.append(JobListing(
                    job_id=f"li_{job_id}",
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    portal=self.portal_name,
                    posted_date=posted,
                ))
            except Exception as e:
                logger.debug(f"Error parsing LinkedIn card: {e}")
                continue

        return jobs

    def _parse_job_detail(self, html: str, url: str) -> JobListing:
        """Parse a LinkedIn job detail page."""
        soup = BeautifulSoup(html, "html.parser")

        title = ""
        title_el = soup.find("h1")
        if title_el:
            title = title_el.get_text(strip=True)

        company = ""
        company_el = soup.find("a", class_=re.compile(r"company"))
        if company_el:
            company = company_el.get_text(strip=True)

        description = ""
        desc_el = soup.find("div", class_=re.compile(r"description|show-more"))
        if desc_el:
            description = desc_el.get_text(strip=True)

        job_id = hashlib.md5(url.encode()).hexdigest()[:12]

        return JobListing(
            job_id=f"li_{job_id}",
            title=title,
            company=company,
            description=description,
            url=url,
            portal=self.portal_name,
        )
