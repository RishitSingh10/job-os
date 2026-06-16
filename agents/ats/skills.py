"""Skills taxonomy and text-analysis helpers for ATS scoring.

Deterministic, dependency-free utilities: a curated set of recognised skills (incl.
multi-word phrases), tokenisation, keyword extraction, and heuristics for required
experience and education level. Keeping these pure makes scoring reproducible and
unit-testable without a model.
"""

from __future__ import annotations

import re
from collections import Counter

# A curated (non-exhaustive) skills taxonomy. Multi-word skills are matched as
# phrases; single tokens are matched as words.
SKILLS: frozenset[str] = frozenset(
    {
        # languages
        "python",
        "java",
        "javascript",
        "typescript",
        "go",
        "golang",
        "rust",
        "c++",
        "c#",
        "ruby",
        "php",
        "scala",
        "kotlin",
        "swift",
        "r",
        "sql",
        "bash",
        # web / backend
        "fastapi",
        "django",
        "flask",
        "node.js",
        "express",
        "react",
        "next.js",
        "vue",
        "angular",
        "svelte",
        "graphql",
        "rest",
        "grpc",
        "html",
        "css",
        "tailwind",
        "redux",
        "spring",
        "rails",
        # data / ml / ai
        "machine learning",
        "deep learning",
        "nlp",
        "natural language processing",
        "computer vision",
        "pytorch",
        "tensorflow",
        "scikit-learn",
        "pandas",
        "numpy",
        "llm",
        "large language models",
        "generative ai",
        "genai",
        "rag",
        "transformers",
        "hugging face",
        "langchain",
        "embeddings",
        "mlops",
        "data science",
        "data engineering",
        "etl",
        "spark",
        "hadoop",
        "airflow",
        # cloud / infra / devops
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "terraform",
        "ansible",
        "ci/cd",
        "jenkins",
        "github actions",
        "linux",
        "microservices",
        "serverless",
        "lambda",
        "redis",
        "kafka",
        "rabbitmq",
        "nginx",
        # databases
        "postgresql",
        "postgres",
        "mysql",
        "mongodb",
        "sqlite",
        "elasticsearch",
        "dynamodb",
        "snowflake",
        "bigquery",
        "chromadb",
        # practices
        "agile",
        "scrum",
        "tdd",
        "unit testing",
        "system design",
        "distributed systems",
        "api design",
        "code review",
        "design patterns",
        "oop",
    }
)

# Phrases (contain a space or punctuation) are matched literally; the rest by word.
_PHRASE_SKILLS = frozenset(s for s in SKILLS if not s.isalnum())
_WORD_SKILLS = frozenset(s for s in SKILLS if s.isalnum())

_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]*")

STOPWORDS: frozenset[str] = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "for",
        "to",
        "of",
        "in",
        "on",
        "at",
        "by",
        "with",
        "from",
        "as",
        "is",
        "are",
        "be",
        "been",
        "being",
        "was",
        "were",
        "will",
        "would",
        "shall",
        "should",
        "can",
        "could",
        "may",
        "might",
        "must",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "we",
        "you",
        "they",
        "he",
        "she",
        "them",
        "our",
        "your",
        "their",
        "his",
        "her",
        "not",
        "no",
        "yes",
        "our",
        "will",
        "work",
        "working",
        "experience",
        "years",
        "year",
        "role",
        "team",
        "teams",
        "company",
        "strong",
        "ability",
        "able",
        "help",
        "using",
        "use",
        "used",
        "new",
        "etc",
        "into",
        "out",
        "over",
        "under",
        "more",
        "most",
        "least",
        "very",
        "across",
        "within",
        "per",
        "via",
        "looking",
        "seeking",
        "join",
        "build",
        "building",
        "help",
        "including",
        "include",
        "includes",
        "required",
        "require",
        "requirements",
        "responsibilities",
        "qualifications",
        "preferred",
        "plus",
        "nice",
        "candidate",
        "candidates",
        "you'll",
        "we're",
        "who",
        "what",
        "when",
        "where",
        "which",
        "while",
        "about",
        "your",
    ]
)

# Note: bare "degree" is intentionally excluded — it appears in phrases like
# "no degree" / "degree required" without indicating an attained/required level.
_DEGREE_LEVELS = {
    "phd": 3,
    "ph.d": 3,
    "doctorate": 3,
    "master": 2,
    "msc": 2,
    "mba": 2,
    "bachelor": 1,
    "bsc": 1,
    "b.s": 1,
    "undergraduate": 1,
}


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (keeps tech punctuation like c++, ci/cd handled via phrases)."""
    return [t.lower() for t in _TOKEN.findall(text)]


def content_tokens(text: str) -> list[str]:
    """Tokens with stopwords and very short tokens removed."""
    return [t for t in tokenize(text) if len(t) >= 3 and t not in STOPWORDS]


def extract_skills(text: str) -> set[str]:
    """Recognised skills present in the text (phrases + single words).

    Phrase skills (``c++``, ``ci/cd``, ``node.js``, ``machine learning``) match as
    substrings; single-word skills match against plain alphanumeric tokens so trailing
    sentence punctuation (``"Kubernetes."``) doesn't defeat the match.
    """
    lowered = text.lower()
    found = {s for s in _PHRASE_SKILLS if s in lowered}
    words = set(re.findall(r"[a-z0-9]+", lowered))
    found |= {s for s in _WORD_SKILLS if s in words}
    return found


def extract_keywords(text: str, *, top_n: int = 20) -> list[str]:
    """Salient keywords: recognised skills plus the most frequent content terms."""
    skills = extract_skills(text)
    counts = Counter(t for t in content_tokens(text) if t not in skills)
    frequent = [term for term, _ in counts.most_common(top_n)]
    # Skills first (most meaningful), then frequent terms, de-duplicated, capped.
    ordered = list(dict.fromkeys([*sorted(skills), *frequent]))
    return ordered[:top_n]


def extract_required_years(text: str) -> int | None:
    """Smallest 'N+ years' / 'N-M years' requirement found, if any."""
    matches = re.findall(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years|yrs)", text.lower())
    years = [int(m) for m in matches]
    return min(years) if years else None


def detect_degree_level(text: str) -> int:
    """Highest degree level mentioned: 3=PhD, 2=Master, 1=Bachelor, 0=none."""
    lowered = text.lower()
    level = 0
    for keyword, value in _DEGREE_LEVELS.items():
        if keyword in lowered:
            level = max(level, value)
    return level
