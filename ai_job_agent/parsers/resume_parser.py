"""Parse resumes from PDF and DOCX formats into structured profile data."""

import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Profile:
    """Structured representation of a candidate's resume."""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    total_experience_years: float = 0.0
    raw_text: str = ""

    def to_search_keywords(self) -> list[str]:
        """Generate search keywords from the profile for job portal queries."""
        keywords = list(self.skills[:10])
        for exp in self.experience[:3]:
            if exp.get("title"):
                keywords.append(exp["title"])
        return keywords

    def to_matching_text(self) -> str:
        """Generate a combined text block for matching against job descriptions."""
        parts = [self.summary]
        parts.extend(self.skills)
        for exp in self.experience:
            parts.append(exp.get("title", ""))
            parts.append(exp.get("description", ""))
        for edu in self.education:
            parts.append(edu.get("degree", ""))
            parts.append(edu.get("field", ""))
        return " ".join(parts)


class ResumeParser:
    """Extracts structured profile data from resume files."""

    # Common technical skills to detect
    SKILL_PATTERNS = [
        "python", "java", "javascript", "typescript", "c\\+\\+", "c#", "ruby", "go",
        "rust", "scala", "kotlin", "swift", "r\\b", "sql", "nosql", "mongodb",
        "postgresql", "mysql", "redis", "elasticsearch", "kafka",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "react", "angular", "vue", "node\\.?js", "django", "flask", "fastapi",
        "spring", "express", "next\\.?js",
        "machine learning", "deep learning", "nlp", "computer vision",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "data science", "data engineering", "data analytics",
        "agile", "scrum", "ci/cd", "devops", "microservices",
        "rest api", "graphql", "grpc",
        "git", "linux", "jenkins", "ansible",
        "tableau", "power bi", "excel",
        "project management", "product management",
        "financial modeling", "business analysis", "consulting",
        "marketing", "digital marketing", "seo", "sem",
        "sales", "account management", "crm", "salesforce",
    ]

    EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    PHONE_PATTERN = re.compile(r"[\+]?[\d\s\-\(\)]{10,15}")

    def parse(self, file_path: str) -> Profile:
        """Parse a resume file and return a structured Profile."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume not found: {file_path}")

        text = self._extract_text(path)
        return self._parse_text(text)

    def _extract_text(self, path: Path) -> str:
        """Extract raw text from PDF or DOCX."""
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(path)
        elif suffix in (".docx", ".doc"):
            return self._extract_docx(path)
        elif suffix == ".txt":
            return path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported resume format: {suffix}. Use PDF, DOCX, or TXT.")

    def _extract_pdf(self, path: Path) -> str:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError("Install PyPDF2: pip install PyPDF2")

        reader = PdfReader(str(path))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_docx(self, path: Path) -> str:
        try:
            import docx
        except ImportError:
            raise ImportError("Install python-docx: pip install python-docx")

        doc = docx.Document(str(path))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

    def _parse_text(self, text: str) -> Profile:
        """Parse raw text into a structured Profile."""
        profile = Profile(raw_text=text)

        # Extract contact info
        emails = self.EMAIL_PATTERN.findall(text)
        if emails:
            profile.email = emails[0]

        phones = self.PHONE_PATTERN.findall(text)
        if phones:
            profile.phone = phones[0].strip()

        # Extract name (heuristic: first non-empty line that looks like a name)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line.split()) <= 5 and not self.EMAIL_PATTERN.search(first_line):
                profile.name = first_line

        # Extract skills
        text_lower = text.lower()
        detected_skills = []
        for skill_pattern in self.SKILL_PATTERNS:
            if re.search(r"\b" + skill_pattern + r"\b", text_lower):
                clean_skill = skill_pattern.replace("\\.", ".").replace("\\+", "+").replace("\\b", "")
                detected_skills.append(clean_skill)
        profile.skills = detected_skills

        # Extract experience sections
        profile.experience = self._extract_experience(text)

        # Extract education
        profile.education = self._extract_education(text)

        # Estimate total experience
        profile.total_experience_years = self._estimate_experience_years(text)

        # Extract summary (text between name and first section header)
        profile.summary = self._extract_summary(text)

        return profile

    def _extract_experience(self, text: str) -> list[dict]:
        """Extract work experience entries."""
        experiences = []
        exp_section = self._extract_section(text, ["experience", "work history", "employment"])
        if not exp_section:
            return experiences

        # Split by common date patterns or bullet-like structures
        entries = re.split(r"\n(?=\w.*(?:20\d{2}|19\d{2}|present|current))", exp_section, flags=re.IGNORECASE)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            lines = entry.split("\n")
            exp = {
                "title": lines[0].strip() if lines else "",
                "description": " ".join(l.strip() for l in lines[1:] if l.strip()),
            }
            experiences.append(exp)
        return experiences[:10]

    def _extract_education(self, text: str) -> list[dict]:
        """Extract education entries."""
        education = []
        edu_section = self._extract_section(text, ["education", "academic", "qualifications"])
        if not edu_section:
            return education

        entries = re.split(r"\n(?=\w)", edu_section)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            education.append({
                "degree": entry.split("\n")[0].strip(),
                "field": "",
            })
        return education[:5]

    def _extract_section(self, text: str, headers: list[str]) -> str:
        """Extract text under a section header."""
        for header in headers:
            pattern = re.compile(
                rf"(?:^|\n)\s*{header}\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:education|experience|skills|projects|certifications|summary|objective)\s*[:\-]?\s*\n|\Z)",
                re.IGNORECASE | re.DOTALL,
            )
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_summary(self, text: str) -> str:
        """Extract professional summary / objective."""
        section = self._extract_section(text, ["summary", "objective", "about", "profile"])
        if section:
            return section[:500]
        # Fallback: first paragraph-like block
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        paragraph = []
        for line in lines[1:]:  # skip name
            if len(line) > 30:
                paragraph.append(line)
            elif paragraph:
                break
        return " ".join(paragraph)[:500]

    def _estimate_experience_years(self, text: str) -> float:
        """Estimate total years of experience from dates in resume."""
        year_pattern = re.compile(r"(20\d{2}|19\d{2})\s*[-–to]+\s*(20\d{2}|19\d{2}|present|current)", re.IGNORECASE)
        matches = year_pattern.findall(text)
        total = 0.0
        for start, end in matches:
            start_year = int(start)
            end_year = 2025 if end.lower() in ("present", "current") else int(end)
            total += max(0, end_year - start_year)
        return total if total > 0 else 0.0
