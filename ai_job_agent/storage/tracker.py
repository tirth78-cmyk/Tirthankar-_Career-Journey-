"""Job tracking persistence using TinyDB."""

import os
from datetime import datetime
from pathlib import Path

from tinydb import TinyDB, Query


class JobTracker:
    """Tracks job listings, review decisions, and application status."""

    STATUS_SCRAPED = "scraped"
    STATUS_MATCHED = "matched"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_SAVED = "saved"
    STATUS_APPLIED = "applied"
    STATUS_FAILED = "failed"

    def __init__(self, db_path: str = "data/jobs.json"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(db_path)
        self.jobs = self.db.table("jobs")
        self.applications = self.db.table("applications")

    def save_job(self, job_data: dict, status: str = STATUS_SCRAPED):
        """Save or update a job listing."""
        Job = Query()
        existing = self.jobs.search(Job.job_id == job_data.get("job_id"))
        record = {
            **job_data,
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }
        if existing:
            self.jobs.update(record, Job.job_id == job_data["job_id"])
        else:
            record["created_at"] = datetime.now().isoformat()
            self.jobs.insert(record)

    def save_match(self, match_data: dict):
        """Save a matched job with its score."""
        job_data = match_data["job"]
        job_data["match_score"] = match_data["overall_score"]
        job_data["skill_score"] = match_data["skill_score"]
        job_data["title_score"] = match_data["title_score"]
        job_data["experience_score"] = match_data["experience_score"]
        self.save_job(job_data, status=self.STATUS_MATCHED)

    def update_status(self, job_id: str, status: str):
        """Update the status of a tracked job."""
        Job = Query()
        self.jobs.update(
            {"status": status, "updated_at": datetime.now().isoformat()},
            Job.job_id == job_id,
        )

    def get_jobs_by_status(self, status: str) -> list[dict]:
        """Get all jobs with a given status."""
        Job = Query()
        return self.jobs.search(Job.status == status)

    def get_pending_review(self) -> list[dict]:
        """Get all matched jobs awaiting review."""
        return self.get_jobs_by_status(self.STATUS_MATCHED)

    def get_approved(self) -> list[dict]:
        """Get all jobs approved for application."""
        return self.get_jobs_by_status(self.STATUS_APPROVED)

    def record_application(self, job_id: str, success: bool, details: str = ""):
        """Record an application attempt."""
        status = self.STATUS_APPLIED if success else self.STATUS_FAILED
        self.update_status(job_id, status)
        self.applications.insert({
            "job_id": job_id,
            "status": status,
            "details": details,
            "applied_at": datetime.now().isoformat(),
        })

    def get_stats(self) -> dict:
        """Get summary statistics."""
        all_jobs = self.jobs.all()
        stats = {
            "total": len(all_jobs),
            "scraped": 0,
            "matched": 0,
            "approved": 0,
            "rejected": 0,
            "saved": 0,
            "applied": 0,
            "failed": 0,
        }
        for job in all_jobs:
            status = job.get("status", "")
            if status in stats:
                stats[status] += 1
        return stats

    def is_duplicate(self, job_id: str) -> bool:
        """Check if a job has already been tracked."""
        Job = Query()
        return bool(self.jobs.search(Job.job_id == job_id))
