"""Manages the job application process across portals."""

import time
import logging
from pathlib import Path

from ..storage.tracker import JobTracker

logger = logging.getLogger(__name__)


class ApplicationManager:
    """Handles applying to approved jobs on various portals."""

    def __init__(self, config: dict, tracker: JobTracker):
        self.config = config
        self.tracker = tracker
        self.daily_limit = config.get("daily_apply_limit", 25)
        self._applied_today = 0

    def apply_to_approved(self, resume_path: str) -> dict:
        """Apply to all approved jobs up to the daily limit.

        Returns a summary of application results.
        """
        approved_jobs = self.tracker.get_approved()
        results = {"applied": 0, "failed": 0, "skipped": 0, "details": []}

        if not approved_jobs:
            logger.info("No approved jobs to apply to.")
            return results

        resume = Path(resume_path)
        if not resume.exists():
            raise FileNotFoundError(f"Resume not found: {resume_path}")

        for job in approved_jobs:
            if self._applied_today >= self.daily_limit:
                logger.warning(f"Daily application limit ({self.daily_limit}) reached.")
                results["skipped"] += len(approved_jobs) - results["applied"] - results["failed"]
                break

            portal = job.get("portal", "")
            job_id = job.get("job_id", "")
            title = job.get("title", "Unknown")
            company = job.get("company", "Unknown")

            try:
                success = self._apply_single(job, resume_path)
                if success:
                    self.tracker.record_application(job_id, success=True)
                    results["applied"] += 1
                    results["details"].append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "status": "applied",
                    })
                    logger.info(f"Applied: {title} at {company} ({portal})")
                else:
                    self.tracker.record_application(
                        job_id, success=False, details="Application submission failed"
                    )
                    results["failed"] += 1
                    results["details"].append({
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "status": "failed",
                    })

                self._applied_today += 1
                # Rate limiting between applications
                time.sleep(3)

            except Exception as e:
                logger.error(f"Error applying to {title} at {company}: {e}")
                self.tracker.record_application(job_id, success=False, details=str(e))
                results["failed"] += 1

        return results

    def _apply_single(self, job: dict, resume_path: str) -> bool:
        """Apply to a single job. Returns True on success.

        This is a framework that dispatches to portal-specific apply methods.
        Actual browser automation would use Selenium for form filling.
        """
        portal = job.get("portal", "")
        url = job.get("url", "")

        if not url:
            logger.warning(f"No URL for job {job.get('job_id')}, skipping.")
            return False

        if portal == "naukri":
            return self._apply_naukri(job, resume_path)
        elif portal == "linkedin":
            return self._apply_linkedin(job, resume_path)
        elif portal == "iimjobs":
            return self._apply_iimjobs(job, resume_path)
        else:
            logger.warning(f"Unknown portal: {portal}")
            return False

    def _apply_naukri(self, job: dict, resume_path: str) -> bool:
        """Apply on Naukri using Selenium automation.

        NOTE: This requires Selenium with Chrome WebDriver configured.
        The actual implementation would:
        1. Log in to Naukri
        2. Navigate to the job URL
        3. Click the Apply button
        4. Upload resume if needed
        5. Submit the application
        """
        logger.info(f"Naukri apply: {job.get('title')} - {job.get('url')}")
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service

            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            try:
                driver.get(job["url"])
                # Wait for page and look for apply button
                apply_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply')]"))
                )
                apply_btn.click()
                time.sleep(2)
                logger.info(f"Successfully applied on Naukri: {job.get('title')}")
                return True
            finally:
                driver.quit()

        except ImportError:
            logger.warning("Selenium not installed. Install with: pip install selenium webdriver-manager")
            return False
        except Exception as e:
            logger.error(f"Naukri auto-apply failed: {e}")
            return False

    def _apply_linkedin(self, job: dict, resume_path: str) -> bool:
        """Apply on LinkedIn (Easy Apply).

        Similar Selenium-based approach for LinkedIn Easy Apply jobs.
        """
        logger.info(f"LinkedIn apply: {job.get('title')} - {job.get('url')}")
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service

            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            try:
                driver.get(job["url"])
                apply_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'apply')]"))
                )
                apply_btn.click()
                time.sleep(2)
                logger.info(f"Successfully applied on LinkedIn: {job.get('title')}")
                return True
            finally:
                driver.quit()

        except ImportError:
            logger.warning("Selenium not installed for LinkedIn apply.")
            return False
        except Exception as e:
            logger.error(f"LinkedIn auto-apply failed: {e}")
            return False

    def _apply_iimjobs(self, job: dict, resume_path: str) -> bool:
        """Apply on IIM Jobs portal."""
        logger.info(f"IIM Jobs apply: {job.get('title')} - {job.get('url')}")
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service

            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            try:
                driver.get(job["url"])
                apply_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply')]"))
                )
                apply_btn.click()
                time.sleep(2)
                logger.info(f"Successfully applied on IIM Jobs: {job.get('title')}")
                return True
            finally:
                driver.quit()

        except ImportError:
            logger.warning("Selenium not installed for IIM Jobs apply.")
            return False
        except Exception as e:
            logger.error(f"IIM Jobs auto-apply failed: {e}")
            return False
