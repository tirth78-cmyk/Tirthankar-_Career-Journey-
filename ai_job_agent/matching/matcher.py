"""Job-resume matching engine using TF-IDF and cosine similarity."""

import re
import logging
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..parsers.resume_parser import Profile
from ..scrapers.base import JobListing

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """A job listing with its match score and breakdown."""
    job: JobListing
    overall_score: float
    skill_score: float
    title_score: float
    experience_score: float

    def to_dict(self) -> dict:
        return {
            "job": self.job.to_dict(),
            "overall_score": round(self.overall_score, 3),
            "skill_score": round(self.skill_score, 3),
            "title_score": round(self.title_score, 3),
            "experience_score": round(self.experience_score, 3),
        }


class JobMatcher:
    """Matches job listings against a candidate profile using NLP techniques."""

    def __init__(self, config: dict = None):
        config = config or {}
        self.skill_weight = config.get("skill_weight", 0.4)
        self.title_weight = config.get("title_weight", 0.3)
        self.experience_weight = config.get("experience_weight", 0.3)
        self.min_score = config.get("min_score", 0.45)
        self.top_k = config.get("top_k", 20)

    def match(self, profile: Profile, jobs: list[JobListing]) -> list[MatchResult]:
        """Score and rank jobs against the profile. Returns sorted matches above threshold."""
        if not jobs:
            return []

        results = []
        for job in jobs:
            score = self._compute_match(profile, job)
            results.append(score)

        # Filter by minimum score and sort descending
        results = [r for r in results if r.overall_score >= self.min_score]
        results.sort(key=lambda r: r.overall_score, reverse=True)

        return results[:self.top_k]

    def _compute_match(self, profile: Profile, job: JobListing) -> MatchResult:
        """Compute a composite match score between profile and job."""
        skill_score = self._skill_match(profile.skills, job)
        title_score = self._title_match(profile, job)
        experience_score = self._experience_match(profile, job)

        overall = (
            self.skill_weight * skill_score
            + self.title_weight * title_score
            + self.experience_weight * experience_score
        )

        return MatchResult(
            job=job,
            overall_score=overall,
            skill_score=skill_score,
            title_score=title_score,
            experience_score=experience_score,
        )

    def _skill_match(self, profile_skills: list[str], job: JobListing) -> float:
        """Score how well the candidate's skills match the job."""
        if not profile_skills:
            return 0.0

        job_text = (job.description + " " + " ".join(job.skills) + " " + job.title).lower()
        if not job_text.strip():
            return 0.0

        matched = 0
        for skill in profile_skills:
            skill_lower = skill.lower().strip()
            if skill_lower and skill_lower in job_text:
                matched += 1

        return matched / len(profile_skills) if profile_skills else 0.0

    def _title_match(self, profile: Profile, job: JobListing) -> float:
        """Score title/role relevance using TF-IDF cosine similarity."""
        # Build profile role text from experience titles and summary
        profile_titles = " ".join(
            exp.get("title", "") for exp in profile.experience
        )
        profile_text = f"{profile_titles} {profile.summary}"

        job_text = f"{job.title} {job.description[:300]}"

        if not profile_text.strip() or not job_text.strip():
            return 0.0

        try:
            vectorizer = TfidfVectorizer(stop_words="english", max_features=500)
            tfidf_matrix = vectorizer.fit_transform([profile_text, job_text])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(similarity[0][0])
        except Exception:
            return 0.0

    def _experience_match(self, profile: Profile, job: JobListing) -> float:
        """Score experience level fit."""
        if not job.experience_required:
            return 0.7  # Neutral if not specified

        # Extract years from job requirement
        match = re.search(r"(\d+)", job.experience_required)
        if not match:
            return 0.7

        required_years = int(match.group(1))
        candidate_years = profile.total_experience_years

        if candidate_years >= required_years:
            # Good fit, slight penalty for being very overqualified
            over = candidate_years - required_years
            return max(0.5, 1.0 - (over * 0.05))
        else:
            # Under-qualified
            gap = required_years - candidate_years
            return max(0.0, 1.0 - (gap * 0.2))
