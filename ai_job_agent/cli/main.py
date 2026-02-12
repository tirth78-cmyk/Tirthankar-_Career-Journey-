"""Command-line interface for the AI Job Agent."""

import sys
import logging

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..config.settings import Settings
from ..parsers.resume_parser import ResumeParser
from ..scrapers.linkedin_scraper import LinkedInScraper
from ..scrapers.naukri_scraper import NaukriScraper
from ..scrapers.iimjobs_scraper import IIMJobsScraper
from ..matching.matcher import JobMatcher
from ..applicator.manager import ApplicationManager
from ..storage.tracker import JobTracker

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, config, verbose):
    """AI Job Agent - Intelligent job search and auto-apply."""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["settings"] = Settings(config)
    ctx.obj["tracker"] = JobTracker(ctx.obj["settings"].storage.get("db_path", "data/jobs.json"))


@cli.command()
@click.option("--resume", "-r", required=True, help="Path to resume file (PDF/DOCX/TXT)")
@click.pass_context
def parse(ctx, resume):
    """Parse a resume and display extracted profile information."""
    console.print(Panel("[bold]Parsing Resume...[/bold]", style="blue"))

    parser = ResumeParser()
    try:
        profile = parser.parse(resume)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Display profile
    console.print(f"\n[bold green]Name:[/bold green] {profile.name}")
    console.print(f"[bold green]Email:[/bold green] {profile.email}")
    console.print(f"[bold green]Phone:[/bold green] {profile.phone}")
    console.print(f"[bold green]Experience:[/bold green] {profile.total_experience_years} years")

    if profile.skills:
        console.print(f"\n[bold green]Skills ({len(profile.skills)}):[/bold green]")
        console.print(", ".join(profile.skills))

    if profile.experience:
        console.print(f"\n[bold green]Experience ({len(profile.experience)} entries):[/bold green]")
        for exp in profile.experience[:5]:
            console.print(f"  - {exp.get('title', 'N/A')}")

    if profile.education:
        console.print(f"\n[bold green]Education:[/bold green]")
        for edu in profile.education[:3]:
            console.print(f"  - {edu.get('degree', 'N/A')}")

    console.print(f"\n[bold green]Search Keywords:[/bold green]")
    console.print(", ".join(profile.to_search_keywords()))

    console.print("\n[green]Resume parsed successfully![/green]")


@cli.command()
@click.option("--resume", "-r", required=True, help="Path to resume file")
@click.option("--location", "-l", default="", help="Preferred job location")
@click.option("--portal", "-p", multiple=True, help="Specific portals to search (linkedin, naukri, iimjobs)")
@click.pass_context
def search(ctx, resume, location, portal):
    """Search for jobs across portals based on your resume."""
    settings = ctx.obj["settings"]
    tracker = ctx.obj["tracker"]

    console.print(Panel("[bold]Searching for Jobs...[/bold]", style="blue"))

    # Parse resume
    parser = ResumeParser()
    try:
        profile = parser.parse(resume)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    keywords = profile.to_search_keywords()
    if not keywords:
        keywords = settings.preferences.get("roles", ["software engineer"])

    search_location = location or settings.preferences.get("locations", [""])[0]
    experience = settings.preferences.get("experience_years", 0)

    console.print(f"Keywords: {', '.join(keywords[:5])}")
    console.print(f"Location: {search_location or 'Any'}")

    # Determine which portals to search
    active_portals = portal if portal else None
    all_jobs = []

    # LinkedIn
    if not active_portals or "linkedin" in active_portals:
        if settings.portals.get("linkedin", {}).get("enabled", True):
            console.print("\n[yellow]Searching LinkedIn...[/yellow]")
            scraper = LinkedInScraper(settings.portals.get("linkedin", {}))
            jobs = scraper.search(keywords, search_location, experience_years=experience)
            all_jobs.extend(jobs)
            console.print(f"  Found {len(jobs)} jobs on LinkedIn")

    # Naukri
    if not active_portals or "naukri" in active_portals:
        if settings.portals.get("naukri", {}).get("enabled", True):
            console.print("\n[yellow]Searching Naukri...[/yellow]")
            scraper = NaukriScraper(settings.portals.get("naukri", {}))
            jobs = scraper.search(keywords, search_location, experience_years=experience)
            all_jobs.extend(jobs)
            console.print(f"  Found {len(jobs)} jobs on Naukri")

    # IIM Jobs
    if not active_portals or "iimjobs" in active_portals:
        if settings.portals.get("iimjobs", {}).get("enabled", True):
            console.print("\n[yellow]Searching IIM Jobs...[/yellow]")
            scraper = IIMJobsScraper(settings.portals.get("iimjobs", {}))
            jobs = scraper.search(keywords, search_location, experience_years=experience)
            all_jobs.extend(jobs)
            console.print(f"  Found {len(jobs)} jobs on IIM Jobs")

    # Deduplicate and save
    new_jobs = 0
    for job in all_jobs:
        if not tracker.is_duplicate(job.job_id):
            tracker.save_job(job.to_dict())
            new_jobs += 1

    console.print(f"\n[green]Total: {len(all_jobs)} jobs found, {new_jobs} new jobs saved.[/green]")

    # Match against profile
    console.print("\n[yellow]Matching jobs to your profile...[/yellow]")
    matcher = JobMatcher(settings.matching)
    matches = matcher.match(profile, all_jobs)

    for match in matches:
        tracker.save_match(match.to_dict())

    # Display matches
    if matches:
        table = Table(title=f"Top {len(matches)} Job Matches")
        table.add_column("#", style="dim", width=4)
        table.add_column("Score", style="green", width=7)
        table.add_column("Title", style="bold", min_width=20)
        table.add_column("Company", min_width=15)
        table.add_column("Location", min_width=10)
        table.add_column("Portal", style="cyan", width=10)

        for i, match in enumerate(matches, 1):
            score_pct = f"{match.overall_score * 100:.0f}%"
            table.add_row(
                str(i),
                score_pct,
                match.job.title[:40],
                match.job.company[:20],
                match.job.location[:15],
                match.job.portal,
            )

        console.print(table)
        console.print(f"\nRun [bold]'python -m ai_job_agent.cli review'[/bold] to review and approve jobs.")
    else:
        console.print("[yellow]No strong matches found. Try adjusting your matching threshold in config.yaml[/yellow]")


@cli.command()
@click.pass_context
def review(ctx):
    """Review matched jobs and approve/reject for application."""
    tracker = ctx.obj["tracker"]

    pending = tracker.get_pending_review()
    if not pending:
        console.print("[yellow]No jobs pending review. Run 'search' first.[/yellow]")
        return

    console.print(Panel(f"[bold]Reviewing {len(pending)} Matched Jobs[/bold]", style="blue"))

    approved_count = 0
    rejected_count = 0
    saved_count = 0

    for i, job in enumerate(pending, 1):
        console.print(f"\n{'='*60}")
        console.print(f"[bold]Job {i}/{len(pending)}[/bold]")
        console.print(f"[bold green]Title:[/bold green]   {job.get('title', 'N/A')}")
        console.print(f"[bold green]Company:[/bold green] {job.get('company', 'N/A')}")
        console.print(f"[bold green]Location:[/bold green]{job.get('location', 'N/A')}")
        console.print(f"[bold green]Salary:[/bold green]  {job.get('salary', 'Not disclosed')}")
        console.print(f"[bold green]Exp:[/bold green]     {job.get('experience_required', 'N/A')}")
        console.print(f"[bold green]Portal:[/bold green]  {job.get('portal', 'N/A')}")
        console.print(f"[bold green]Score:[/bold green]   {job.get('match_score', 0) * 100:.0f}%")

        if job.get("url"):
            console.print(f"[bold green]URL:[/bold green]     {job['url']}")

        if job.get("skills"):
            console.print(f"[bold green]Skills:[/bold green]  {', '.join(job['skills'][:10])}")

        desc = job.get("description", "")
        if desc:
            console.print(f"\n[dim]{desc[:300]}{'...' if len(desc) > 300 else ''}[/dim]")

        # Get user decision
        choice = Prompt.ask(
            "\n[bold]Action[/bold]",
            choices=["apply", "skip", "save", "quit"],
            default="skip",
        )

        if choice == "apply":
            tracker.update_status(job["job_id"], JobTracker.STATUS_APPROVED)
            approved_count += 1
            console.print("[green]Approved for application.[/green]")
        elif choice == "save":
            tracker.update_status(job["job_id"], JobTracker.STATUS_SAVED)
            saved_count += 1
            console.print("[blue]Saved for later.[/blue]")
        elif choice == "quit":
            console.print("[yellow]Review paused. Remaining jobs stay in queue.[/yellow]")
            break
        else:
            tracker.update_status(job["job_id"], JobTracker.STATUS_REJECTED)
            rejected_count += 1
            console.print("[dim]Skipped.[/dim]")

    console.print(f"\n[bold]Review Summary:[/bold]")
    console.print(f"  Approved: {approved_count}")
    console.print(f"  Skipped:  {rejected_count}")
    console.print(f"  Saved:    {saved_count}")

    if approved_count > 0:
        console.print(f"\nRun [bold]'python -m ai_job_agent.cli apply --resume <path>'[/bold] to submit applications.")


@cli.command()
@click.option("--resume", "-r", required=True, help="Path to resume file for applications")
@click.pass_context
def apply(ctx, resume):
    """Apply to all approved jobs."""
    settings = ctx.obj["settings"]
    tracker = ctx.obj["tracker"]

    approved = tracker.get_approved()
    if not approved:
        console.print("[yellow]No approved jobs. Run 'review' first to approve jobs.[/yellow]")
        return

    console.print(Panel(f"[bold]Applying to {len(approved)} Approved Jobs[/bold]", style="blue"))

    if not Confirm.ask(f"Proceed with applying to {len(approved)} jobs?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    manager = ApplicationManager(settings.application, tracker)
    results = manager.apply_to_approved(resume)

    console.print(f"\n[bold]Application Results:[/bold]")
    console.print(f"  [green]Applied:[/green]  {results['applied']}")
    console.print(f"  [red]Failed:[/red]   {results['failed']}")
    console.print(f"  [yellow]Skipped:[/yellow] {results['skipped']}")

    if results["details"]:
        table = Table(title="Application Details")
        table.add_column("Title", min_width=20)
        table.add_column("Company", min_width=15)
        table.add_column("Status", min_width=10)

        for detail in results["details"]:
            style = "green" if detail["status"] == "applied" else "red"
            table.add_row(detail["title"], detail["company"], f"[{style}]{detail['status']}[/{style}]")

        console.print(table)


@cli.command()
@click.option("--resume", "-r", required=True, help="Path to resume file")
@click.option("--location", "-l", default="", help="Preferred job location")
@click.option("--auto-apply", is_flag=True, help="Skip review and auto-apply (use with caution)")
@click.pass_context
def run(ctx, resume, location, auto_apply):
    """Run the full pipeline: parse -> search -> match -> review -> apply."""
    settings = ctx.obj["settings"]
    tracker = ctx.obj["tracker"]

    console.print(Panel("[bold]AI Job Agent - Full Pipeline[/bold]", style="blue"))

    # Step 1: Parse resume
    console.print("\n[bold]Step 1: Parsing Resume[/bold]")
    parser = ResumeParser()
    try:
        profile = parser.parse(resume)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    console.print(f"  Name: {profile.name}")
    console.print(f"  Skills: {', '.join(profile.skills[:8])}")
    console.print(f"  Experience: {profile.total_experience_years} years")

    # Step 2: Search jobs
    console.print("\n[bold]Step 2: Searching Job Portals[/bold]")
    keywords = profile.to_search_keywords()
    if not keywords:
        keywords = settings.preferences.get("roles", ["software engineer"])

    search_location = location or settings.preferences.get("locations", [""])[0]
    experience = settings.preferences.get("experience_years", 0)
    all_jobs = []

    scrapers = []
    if settings.portals.get("linkedin", {}).get("enabled", True):
        scrapers.append(("LinkedIn", LinkedInScraper(settings.portals.get("linkedin", {}))))
    if settings.portals.get("naukri", {}).get("enabled", True):
        scrapers.append(("Naukri", NaukriScraper(settings.portals.get("naukri", {}))))
    if settings.portals.get("iimjobs", {}).get("enabled", True):
        scrapers.append(("IIM Jobs", IIMJobsScraper(settings.portals.get("iimjobs", {}))))

    for name, scraper in scrapers:
        console.print(f"  Searching {name}...")
        jobs = scraper.search(keywords, search_location, experience_years=experience)
        all_jobs.extend(jobs)
        console.print(f"    Found {len(jobs)} jobs")

    # Deduplicate
    for job in all_jobs:
        if not tracker.is_duplicate(job.job_id):
            tracker.save_job(job.to_dict())

    console.print(f"  Total: {len(all_jobs)} jobs found")

    # Step 3: Match
    console.print("\n[bold]Step 3: Matching Jobs to Profile[/bold]")
    matcher = JobMatcher(settings.matching)
    matches = matcher.match(profile, all_jobs)

    for match in matches:
        tracker.save_match(match.to_dict())

    console.print(f"  {len(matches)} strong matches found")

    if not matches:
        console.print("[yellow]No strong matches. Try broadening your search.[/yellow]")
        return

    # Display matches
    table = Table(title="Matched Jobs")
    table.add_column("#", width=4)
    table.add_column("Score", width=7)
    table.add_column("Title", min_width=20)
    table.add_column("Company", min_width=15)
    table.add_column("Portal", width=10)

    for i, match in enumerate(matches, 1):
        table.add_row(
            str(i),
            f"{match.overall_score * 100:.0f}%",
            match.job.title[:40],
            match.job.company[:20],
            match.job.portal,
        )
    console.print(table)

    # Step 4: Review (unless auto-apply)
    if auto_apply:
        console.print("\n[bold]Step 4: Auto-approving all matches[/bold]")
        for match in matches:
            tracker.update_status(match.job.job_id, JobTracker.STATUS_APPROVED)
    else:
        console.print("\n[bold]Step 4: Review Jobs[/bold]")
        console.print("Review each job and decide whether to apply.\n")
        ctx.invoke(review)

    # Step 5: Apply
    approved = tracker.get_approved()
    if approved:
        console.print(f"\n[bold]Step 5: Applying to {len(approved)} Jobs[/bold]")
        if auto_apply or Confirm.ask(f"Apply to {len(approved)} approved jobs?"):
            manager = ApplicationManager(settings.application, tracker)
            results = manager.apply_to_approved(resume)
            console.print(f"  Applied: {results['applied']}, Failed: {results['failed']}")
    else:
        console.print("\n[yellow]No jobs approved for application.[/yellow]")

    # Final stats
    stats = tracker.get_stats()
    console.print(f"\n[bold]Session Summary:[/bold]")
    console.print(f"  Total jobs tracked: {stats['total']}")
    console.print(f"  Applied: {stats['applied']}")
    console.print(f"  Saved: {stats['saved']}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show job tracking statistics."""
    tracker = ctx.obj["tracker"]
    stats = tracker.get_stats()

    table = Table(title="Job Agent Statistics")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    for status, count in stats.items():
        if status == "total":
            continue
        style = {
            "applied": "green",
            "approved": "blue",
            "matched": "yellow",
            "saved": "cyan",
            "failed": "red",
        }.get(status, "white")
        table.add_row(status.capitalize(), f"[{style}]{count}[/{style}]")

    table.add_row("[bold]Total[/bold]", f"[bold]{stats['total']}[/bold]")
    console.print(table)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
