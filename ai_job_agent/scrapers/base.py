"""Base classes for job scrapers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class JobListing:
    """Represents a single job listing from any portal."""
    job_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    salary: str = ""
    experience_required: str = ""
    skills: list[str] = field(default_factory=list)
    url: str = ""
    portal: str = ""
    posted_date: str = ""
    job_type: str = ""
    easy_apply: bool = False
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "salary": self.salary,
            "experience_required": self.experience_required,
            "skills": self.skills,
            "url": self.url,
            "portal": self.portal,
            "posted_date": self.posted_date,
            "job_type": self.job_type,
            "easy_apply": self.easy_apply,
            "scraped_at": self.scraped_at,
        }

    def matching_text(self) -> str:
        """Combined text for matching purposes."""
        return " ".join([
            self.title,
            self.description,
            self.company,
            " ".join(self.skills),
            self.location,
        ])


class BaseScraper(ABC):
    """Abstract base class for all job portal scrapers."""

    def __init__(self, config: dict):
        self.config = config
        self.portal_name = "unknown"

    @abstractmethod
    def search(self, keywords: list[str], location: str = "", **filters) -> list[JobListing]:
        """Search for jobs matching the given criteria."""
        pass

    @abstractmethod
    def get_job_details(self, job_url: str) -> JobListing:
        """Fetch full details for a specific job listing."""
        pass

    def _build_headers(self) -> dict:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
