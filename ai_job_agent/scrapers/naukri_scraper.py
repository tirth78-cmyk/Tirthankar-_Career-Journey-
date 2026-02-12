"""Naukri.com job scraper."""

import re
import time
import hashlib
import logging
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, JobListing

logger = logging.getLogger(__name__)


class NaukriScraper(BaseScraper):
    """Scrapes job listings from Naukri.com."""

    BASE_URL = "https://www.naukri.com/jobapi/v3/search"
    SEARCH_URL = "https://www.naukri.com"

    def __init__(self, config: dict):
        super().__init__(config)
        self.portal_name = "naukri"
        self.session = requests.Session()
        self.session.headers.update(self._build_headers())
        self.session.headers["appid"] = "109"
        self.session.headers["systemid"] = "Naukri"

    def search(self, keywords: list[str], location: str = "", **filters) -> list[JobListing]:
        """Search Naukri for jobs matching keywords."""
        query = "-".join(keywords[:5])
        search_path = f"{query}-jobs"
        if location:
            search_path += f"-in-{location.lower().replace(' ', '-')}"

        params = {
            "noOfResults": 25,
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": " ".join(keywords),
            "pageNo": 1,
            "k": " ".join(keywords),
        }
        if location:
            params["l"] = location

        experience = filters.get("experience_years")
        if experience:
            params["experience"] = str(experience)

        jobs = []
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                jobs = self._parse_api_response(data)
            else:
                # Fallback to HTML scraping
                html_url = f"{self.SEARCH_URL}/{search_path}"
                response = self.session.get(html_url, timeout=30)
                response.raise_for_status()
                jobs = self._parse_html_results(response.text)

            logger.info(f"Naukri: Found {len(jobs)} jobs for '{' '.join(keywords)}'")
        except requests.RequestException as e:
            logger.error(f"Naukri search failed: {e}")

        return jobs

    def get_job_details(self, job_url: str) -> JobListing:
        """Fetch detailed information for a specific Naukri job."""
        try:
            response = self.session.get(job_url, timeout=30)
            response.raise_for_status()
            return self._parse_job_detail(response.text, job_url)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Naukri job details: {e}")
            return JobListing(url=job_url, portal=self.portal_name)

    def _parse_api_response(self, data: dict) -> list[JobListing]:
        """Parse Naukri API JSON response."""
        jobs = []
        job_details = data.get("jobDetails", [])

        for item in job_details:
            try:
                title = item.get("title", "")
                company = item.get("companyName", "")
                location = item.get("placeholders", [{}])[0].get("label", "") if item.get("placeholders") else ""
                experience = item.get("placeholders", [{}])[1].get("label", "") if len(item.get("placeholders", [])) > 1 else ""
                salary = item.get("placeholders", [{}])[2].get("label", "") if len(item.get("placeholders", [])) > 2 else ""
                description = item.get("jobDescription", "")
                url = item.get("jdURL", "")
                job_id = item.get("jobId", "")
                skills = [tag.get("value", "") for tag in item.get("tagsAndSkills", "").split(",") if tag] if isinstance(item.get("tagsAndSkills"), str) else []

                if not title:
                    continue

                jobs.append(JobListing(
                    job_id=f"nk_{job_id}",
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    salary=salary,
                    experience_required=experience,
                    skills=[s.strip() for s in skills if s.strip()],
                    url=f"https://www.naukri.com{url}" if url and not url.startswith("http") else url,
                    portal=self.portal_name,
                ))
            except Exception as e:
                logger.debug(f"Error parsing Naukri item: {e}")
                continue

        return jobs

    def _parse_html_results(self, html: str) -> list[JobListing]:
        """Fallback HTML parser for Naukri search results."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        job_cards = soup.find_all("article", class_=re.compile(r"jobTuple"))
        if not job_cards:
            job_cards = soup.find_all("div", class_=re.compile(r"srp-jobtuple|jobTuple"))

        for card in job_cards:
            try:
                title_el = card.find("a", class_=re.compile(r"title"))
                company_el = card.find("a", class_=re.compile(r"comp-name|subTitle"))
                location_el = card.find("span", class_=re.compile(r"loc|ellipsis"))
                salary_el = card.find("span", class_=re.compile(r"sal|salary"))
                exp_el = card.find("span", class_=re.compile(r"exp|expwdth"))

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else ""
                salary = salary_el.get_text(strip=True) if salary_el else ""
                experience = exp_el.get_text(strip=True) if exp_el else ""
                url = title_el["href"] if title_el and title_el.has_attr("href") else ""

                if not title:
                    continue

                job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]
                jobs.append(JobListing(
                    job_id=f"nk_{job_id}",
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    experience_required=experience,
                    url=url,
                    portal=self.portal_name,
                ))
            except Exception as e:
                logger.debug(f"Error parsing Naukri card: {e}")
                continue

        return jobs

    def _parse_job_detail(self, html: str, url: str) -> JobListing:
        """Parse a Naukri job detail page."""
        soup = BeautifulSoup(html, "html.parser")

        title = ""
        title_el = soup.find("h1")
        if title_el:
            title = title_el.get_text(strip=True)

        company = ""
        company_el = soup.find("a", class_=re.compile(r"comp-name"))
        if company_el:
            company = company_el.get_text(strip=True)

        description = ""
        desc_el = soup.find("div", class_=re.compile(r"job-desc|dang-inner"))
        if desc_el:
            description = desc_el.get_text(strip=True)

        skills = []
        skills_el = soup.find_all("span", class_=re.compile(r"chip|tag|skill"))
        for s in skills_el:
            skills.append(s.get_text(strip=True))

        job_id = hashlib.md5(url.encode()).hexdigest()[:12]
        return JobListing(
            job_id=f"nk_{job_id}",
            title=title,
            company=company,
            description=description,
            skills=skills,
            url=url,
            portal=self.portal_name,
        )
