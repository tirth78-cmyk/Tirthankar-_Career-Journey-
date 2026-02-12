"""IIM Jobs portal scraper."""

import re
import hashlib
import logging
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, JobListing

logger = logging.getLogger(__name__)


class IIMJobsScraper(BaseScraper):
    """Scrapes job listings from IIMJobs.com."""

    BASE_URL = "https://www.iimjobs.com"

    def __init__(self, config: dict):
        super().__init__(config)
        self.portal_name = "iimjobs"
        self.session = requests.Session()
        self.session.headers.update(self._build_headers())

    def search(self, keywords: list[str], location: str = "", **filters) -> list[JobListing]:
        """Search IIM Jobs for matching positions."""
        query = " ".join(keywords)
        search_url = f"{self.BASE_URL}/search"
        params = {
            "q": query,
            "loc": location or "",
        }

        experience = filters.get("experience_years")
        if experience:
            params["exp"] = str(experience)

        jobs = []
        try:
            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            jobs = self._parse_search_results(response.text)
            logger.info(f"IIM Jobs: Found {len(jobs)} jobs for '{query}'")
        except requests.RequestException as e:
            logger.error(f"IIM Jobs search failed: {e}")

        return jobs

    def get_job_details(self, job_url: str) -> JobListing:
        """Fetch full details for a specific IIM Jobs listing."""
        try:
            response = self.session.get(job_url, timeout=30)
            response.raise_for_status()
            return self._parse_job_detail(response.text, job_url)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch IIM Jobs details: {e}")
            return JobListing(url=job_url, portal=self.portal_name)

    def _parse_search_results(self, html: str) -> list[JobListing]:
        """Parse IIM Jobs search results page."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        job_cards = soup.find_all("div", class_=re.compile(r"job-listing|job-card|listing-card"))
        if not job_cards:
            job_cards = soup.find_all("li", class_=re.compile(r"job"))

        for card in job_cards:
            try:
                title_el = card.find(["h2", "h3", "a"], class_=re.compile(r"title|job-title"))
                company_el = card.find(["span", "a", "div"], class_=re.compile(r"company|comp"))
                location_el = card.find(["span", "div"], class_=re.compile(r"location|loc"))
                exp_el = card.find(["span", "div"], class_=re.compile(r"exp|experience"))
                salary_el = card.find(["span", "div"], class_=re.compile(r"salary|ctc"))

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else ""
                experience = exp_el.get_text(strip=True) if exp_el else ""
                salary = salary_el.get_text(strip=True) if salary_el else ""

                link_el = card.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el["href"]
                    url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                if not title:
                    continue

                job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]
                jobs.append(JobListing(
                    job_id=f"iim_{job_id}",
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    experience_required=experience,
                    url=url,
                    portal=self.portal_name,
                ))
            except Exception as e:
                logger.debug(f"Error parsing IIM Jobs card: {e}")
                continue

        return jobs

    def _parse_job_detail(self, html: str, url: str) -> JobListing:
        """Parse an IIM Jobs detail page."""
        soup = BeautifulSoup(html, "html.parser")

        title = ""
        title_el = soup.find("h1")
        if title_el:
            title = title_el.get_text(strip=True)

        company = ""
        company_el = soup.find(["a", "span", "div"], class_=re.compile(r"company|comp-name"))
        if company_el:
            company = company_el.get_text(strip=True)

        description = ""
        desc_el = soup.find("div", class_=re.compile(r"job-desc|description|jd-text"))
        if desc_el:
            description = desc_el.get_text(strip=True)

        skills = []
        skills_section = soup.find("div", class_=re.compile(r"skill|key-skill"))
        if skills_section:
            for tag in skills_section.find_all(["span", "a", "li"]):
                skills.append(tag.get_text(strip=True))

        job_id = hashlib.md5(url.encode()).hexdigest()[:12]
        return JobListing(
            job_id=f"iim_{job_id}",
            title=title,
            company=company,
            description=description,
            skills=skills,
            url=url,
            portal=self.portal_name,
        )
