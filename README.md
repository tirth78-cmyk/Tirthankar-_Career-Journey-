# AI Job Agent - Career Journey

An intelligent AI-powered job search agent that automatically matches your resume to relevant job listings across multiple portals (LinkedIn, Naukri, IIM Jobs) and applies on your behalf after your review.

## Features

- **Resume Parsing**: Extracts skills, experience, education, and preferences from PDF/DOCX resumes
- **Multi-Portal Job Search**: Scrapes jobs from LinkedIn, Naukri, and IIM Jobs
- **AI-Powered Matching**: Uses TF-IDF + cosine similarity to rank jobs by relevance to your profile
- **Review Workflow**: Presents matched jobs for your approval before applying
- **Auto-Apply**: Submits applications on approved portals with your resume
- **Job Tracking Dashboard**: Track applied, reviewed, and pending jobs

## Architecture

```
ai_job_agent/
├── config/           # Configuration and settings
├── parsers/          # Resume parsing (PDF, DOCX)
├── scrapers/         # Job portal scrapers (LinkedIn, Naukri, IIM Jobs)
├── matching/         # Job-resume matching engine
├── applicator/       # Auto-application manager
├── storage/          # Job tracking and persistence
└── cli/              # Command-line interface
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your API keys and preferences
```

### 3. Run the Agent

```bash
# Parse your resume
python -m ai_job_agent.cli parse --resume path/to/resume.pdf

# Search for jobs
python -m ai_job_agent.cli search

# Review matched jobs
python -m ai_job_agent.cli review

# Apply to approved jobs
python -m ai_job_agent.cli apply

# Full automated pipeline
python -m ai_job_agent.cli run --resume path/to/resume.pdf
```

## Configuration

Edit `config.yaml` to set:
- Job preferences (role, location, salary range, experience level)
- Portal credentials (LinkedIn, Naukri, IIM Jobs)
- Matching thresholds
- Application templates

## How It Works

1. **Parse Resume** → Extracts structured data (skills, experience, education)
2. **Search Jobs** → Queries multiple job portals with relevant keywords
3. **Match & Rank** → Scores each job against your profile using NLP
4. **Review** → Presents top matches for your approval (apply / skip / save)
5. **Apply** → Submits applications to approved jobs automatically

## Supported Portals

| Portal | Search | Auto-Apply | Status |
|--------|--------|------------|--------|
| LinkedIn | Yes | Via Easy Apply | Supported |
| Naukri | Yes | Yes | Supported |
| IIM Jobs | Yes | Yes | Supported |

## License

MIT
