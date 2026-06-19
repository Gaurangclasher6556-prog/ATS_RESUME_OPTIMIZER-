"""
ats_scorer.py — Deterministic, explainable ATS scoring engine.

This module does NOT depend on an LLM. Given a job description and a resume
(either raw text or a structured dict), it produces a fully reproducible
0–100 ATS match score with a transparent component breakdown.

Design goals:
  • Deterministic  — same inputs always produce the same score.
  • Explainable    — every sub-score is backed by concrete evidence.
  • Dependency-free — pure Python standard library only (re, math, difflib,
                      collections). No scikit-learn / numpy required, so it
                      installs and runs anywhere instantly.

The final score is a weighted blend of five signals:
  1. Keyword match        (35%) — exact + fuzzy + acronym-aware coverage of JD keywords.
  2. Semantic similarity  (20%) — TF-IDF cosine similarity between resume and JD.
  3. Skills coverage      (15%) — required hard-skills present in the resume.
  4. Formatting/structure (15%) — ATS-safe sections, contact info, length, dates.
  5. Impact & readability (15%) — quantified bullets, strong action verbs, concision.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Union

# ─────────────────────────────────────────────────────────────────────────────
#  Lexicons
# ─────────────────────────────────────────────────────────────────────────────

# Common English stopwords + resume/JD boilerplate that should never count as
# a meaningful keyword.
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "for", "to",
    "of", "in", "on", "at", "by", "with", "as", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "these", "those", "it", "its",
    "we", "you", "your", "our", "their", "they", "he", "she", "his", "her",
    "will", "would", "should", "can", "could", "may", "might", "must", "shall",
    "have", "has", "had", "do", "does", "did", "from", "into", "about", "over",
    "under", "out", "up", "down", "off", "than", "such", "via", "per", "etc",
    "who", "what", "when", "where", "which", "how", "why", "all", "any", "each",
    "more", "most", "other", "some", "no", "not", "only", "own", "same", "so",
    "too", "very", "just", "also", "able", "across", "within", "including",
    "candidate", "candidates", "applicant", "role", "roles", "job", "position",
    "responsibilities", "responsibility", "requirement", "requirements",
    "qualification", "qualifications", "experience", "experiences", "year",
    "years", "work", "working", "team", "teams", "company", "ability",
    "looking", "seeking", "join", "help", "strong", "good", "great", "excellent",
    "plus", "preferred", "required", "must", "nice", "ideal", "ideally",
    "etc.", "e.g", "i.e", "using", "use", "used", "new", "well", "us", "day",
}

# Curated technical skill lexicon. Used to recognise multi-word technologies and
# to weight genuine "hard skills" higher than generic words. Lower-cased.
TECH_LEXICON = {
    # languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "bash", "shell", "sql", "nosql", "html", "css", "dart", "objective-c",
    # frameworks / libs
    "react", "angular", "vue", "vue.js", "next.js", "node.js", "node", "express",
    "django", "flask", "fastapi", "spring", "spring boot", ".net", "rails",
    "laravel", "tensorflow", "pytorch", "keras", "scikit-learn", "pandas",
    "numpy", "spark", "hadoop", "kafka", "flink", "airflow", "redux", "svelte",
    # cloud / devops
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "github actions", "gitlab ci", "ci/cd",
    "helm", "prometheus", "grafana", "datadog", "cloudformation", "lambda",
    "ec2", "s3", "rds", "dynamodb", "serverless",
    # data / db
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "cassandra", "snowflake", "bigquery", "redshift", "kafka", "rabbitmq",
    "graphql", "rest", "restful", "grpc", "etl", "data warehouse",
    # concepts
    "machine learning", "deep learning", "nlp", "computer vision", "llm",
    "microservices", "distributed systems", "system design", "oop",
    "object-oriented", "agile", "scrum", "kanban", "tdd", "unit testing",
    "integration testing", "data structures", "algorithms", "design patterns",
    "scalability", "load balancing", "caching", "api", "apis", "oauth", "jwt",
    "linux", "git", "devops", "sre", "mlops", "feature engineering",
    "a/b testing", "statistics", "data visualization", "tableau", "power bi",
    "excel", "jira", "figma", "webpack", "babel", "sass", "tailwind",
}

# Acronym ↔ expansion map so "ML" matches "machine learning" and vice-versa.
ACRONYMS = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "oop": "object-oriented programming",
    "ci/cd": "continuous integration continuous deployment",
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "db": "database",
    "api": "application programming interface",
    "sre": "site reliability engineering",
    "qa": "quality assurance",
    "ui": "user interface",
    "ux": "user experience",
    "llm": "large language model",
    "iac": "infrastructure as code",
    "pwa": "progressive web app",
}
# Reverse map for expansion → acronym lookups.
_ACRONYM_REVERSE = {v: k for k, v in ACRONYMS.items()}

# Strong action verbs (lower-cased) used to assess bullet quality.
ACTION_VERBS = {
    "spearheaded", "orchestrated", "championed", "directed", "mentored",
    "mobilized", "pioneered", "led", "architected", "engineered", "automated",
    "optimized", "refactored", "integrated", "deployed", "migrated", "built",
    "designed", "developed", "implemented", "accelerated", "boosted", "drove",
    "elevated", "slashed", "reduced", "amplified", "transformed", "streamlined",
    "revitalized", "diagnosed", "investigated", "quantified", "evaluated",
    "benchmarked", "modeled", "forecasted", "synthesized", "validated",
    "partnered", "coordinated", "facilitated", "aligned", "unified", "launched",
    "created", "improved", "increased", "decreased", "managed", "delivered",
    "scaled", "shipped", "owned", "founded", "established", "negotiated",
    "analyzed", "researched", "produced", "generated", "achieved", "executed",
}

# Standard resume section headers an ATS expects to find.
EXPECTED_SECTIONS = ["experience", "education", "skills", "summary", "projects"]


# ─────────────────────────────────────────────────────────────────────────────
#  Result container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ComponentScore:
    name: str
    score: float          # 0–100
    weight: float         # 0–1
    detail: str = ""
    evidence: dict = field(default_factory=dict)


@dataclass
class ATSResult:
    overall: int
    grade: str
    components: List[ComponentScore]
    matched_keywords: List[str]
    missing_keywords: List[str]
    suggestions: List[str]

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "grade": self.grade,
            "components": [
                {
                    "name": c.name,
                    "score": round(c.score, 1),
                    "weight": c.weight,
                    "detail": c.detail,
                    "evidence": c.evidence,
                }
                for c in self.components
            ],
            "matched_keywords": self.matched_keywords,
            "missing_keywords": self.missing_keywords,
            "suggestions": self.suggestions,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Text utilities
# ─────────────────────────────────────────────────────────────────────────────

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+.#/_-]*")


def _normalize(text: str) -> str:
    return (text or "").lower().replace("’", "'")


def _tokens(text: str) -> List[str]:
    # Strip trailing/leading punctuation (".", ",", etc.) while preserving
    # internal symbols so "node.js", "ci/cd", "c++", "c#" survive intact.
    out = []
    for raw in _WORD_RE.findall(_normalize(text)):
        t = raw.strip(".,;:!?")
        if t:
            out.append(t)
    return out


def _content_tokens(text: str) -> List[str]:
    return [t for t in _tokens(text) if t not in STOPWORDS and len(t) > 1]


def _ngrams(tokens: List[str], n: int) -> List[str]:
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def resume_to_text(resume: Union[str, dict]) -> str:
    """Flatten a structured resume dict (or pass through a string) to plain text."""
    if isinstance(resume, str):
        return resume
    if not isinstance(resume, dict):
        return str(resume)

    parts: List[str] = []
    for key in ("name", "summary", "location"):
        if resume.get(key):
            parts.append(str(resume[key]))

    for edu in resume.get("education", []) or []:
        parts += [str(edu.get(k, "")) for k in ("degree", "institution", "year")]

    for exp in resume.get("experience", []) or []:
        parts += [str(exp.get(k, "")) for k in ("title", "company")]
        parts += [str(b) for b in exp.get("bullets", []) or []]

    for proj in resume.get("projects", []) or []:
        parts.append(str(proj.get("name", "")))
        parts.append(str(proj.get("technologies", "")))
        parts += [str(b) for b in proj.get("bullets", []) or []]

    skills = resume.get("skills", {})
    if isinstance(skills, dict):
        for v in skills.values():
            parts.append(", ".join(v) if isinstance(v, list) else str(v))
    elif isinstance(skills, list):
        parts.append(", ".join(str(s) for s in skills))

    certs = resume.get("certifications", [])
    if isinstance(certs, list):
        parts += [str(c) for c in certs]

    return "\n".join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────
#  Keyword extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_jd_keywords(job_description: str, top_n: int = 25) -> List[Tuple[str, float]]:
    """
    Extract the most important keywords/phrases from a job description.

    Candidates are:
      • content unigrams (non-stopwords),
      • "clean" bigrams/trigrams whose every word is a content word — built from
        the original token stream so phrases never cross stopword boundaries
        (this rejects junk like "react ideal built" while keeping real phrases
        like "machine learning" or "system design"),
      • known multi-word technologies from the curated lexicon.

    Each candidate is weighted by frequency, with large boosts for hard skills
    and moderate boosts for multi-word phrases. Returns (keyword, weight) pairs
    sorted by descending weight.
    """
    norm = _normalize(job_description)
    all_tokens = _tokens(norm)                 # includes stopwords (preserves order)
    if not all_tokens:
        return []

    counts: Counter = Counter()

    # Content unigrams (the backbone — ATS matching is fundamentally token-based).
    for t in all_tokens:
        if t not in STOPWORDS and len(t) > 1 and not t.isdigit():
            counts[t] += 1

    # Multi-word phrases: ONLY curated technologies actually present in the JD
    # (e.g., "machine learning", "system design"). Arbitrary bigrams are skipped
    # to avoid noise — their constituent words are already captured as unigrams,
    # and phrase-level overlap is handled by the semantic-similarity component.
    for skill in TECH_LEXICON:
        if " " in skill and skill in norm:
            counts[skill] += norm.count(skill) + 1

    weights: Dict[str, float] = {}
    for term, freq in counts.items():
        n_words = term.count(" ") + 1
        w = float(freq)
        if term in TECH_LEXICON or term in ACRONYMS:
            w *= 3.0                      # hard skills / acronyms matter most
        if n_words >= 2:
            w *= 1.3                      # curated multi-word skill
        weights[term] = w

    ranked = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))

    # Drop a unigram if a higher-ranked curated phrase already contains it
    # (e.g., keep "machine learning", drop standalone "learning").
    chosen: List[Tuple[str, float]] = []
    kept_phrases: List[str] = []
    for term, w in ranked:
        if " " in term:
            kept_phrases.append(term)
            chosen.append((term, w))
        elif any(term in p.split() for p in kept_phrases):
            continue
        else:
            chosen.append((term, w))
        if len(chosen) >= top_n:
            break
    return chosen


def _expand_variants(term: str) -> List[str]:
    """Return the term plus any acronym/expansion variants for matching."""
    variants = {term}
    if term in ACRONYMS:
        variants.add(ACRONYMS[term])
    if term in _ACRONYM_REVERSE:
        variants.add(_ACRONYM_REVERSE[term])
    return list(variants)


def _keyword_present(term: str, resume_norm: str, resume_token_set: set,
                     fuzzy_threshold: float = 0.88) -> bool:
    """Check exact, acronym, and fuzzy presence of a keyword in the resume."""
    for variant in _expand_variants(term):
        if variant in resume_norm:                       # exact / substring
            return True
    # Fuzzy match for single tokens (handles minor spelling variants).
    if " " not in term:
        for rt in resume_token_set:
            if abs(len(rt) - len(term)) <= 3 and \
               SequenceMatcher(None, term, rt).ratio() >= fuzzy_threshold:
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  Component scorers
# ─────────────────────────────────────────────────────────────────────────────

def _score_keywords(resume_text: str, job_description: str) -> Tuple[ComponentScore, List[str], List[str]]:
    keywords = extract_jd_keywords(job_description)
    if not keywords:
        return (ComponentScore("Keyword Match", 50.0, 0.35,
                               "No job description keywords detected."), [], [])

    resume_norm = _normalize(resume_text)
    resume_tokens = set(_tokens(resume_text))

    total_w = sum(w for _, w in keywords)
    matched_w = 0.0
    matched, missing = [], []
    for term, w in keywords:
        if _keyword_present(term, resume_norm, resume_tokens):
            matched_w += w
            matched.append(term)
        else:
            missing.append(term)

    score = 100.0 * matched_w / total_w if total_w else 0.0
    detail = f"{len(matched)}/{len(keywords)} weighted JD keywords present."
    return (ComponentScore("Keyword Match", score, 0.35, detail,
                           {"matched": len(matched), "total": len(keywords)}),
            matched, missing)


def _tfidf_cosine(text_a: str, text_b: str) -> float:
    """Pure-Python TF-IDF cosine similarity between two documents."""
    docs = [_content_tokens(text_a), _content_tokens(text_b)]
    if not docs[0] or not docs[1]:
        return 0.0

    df: Counter = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1
    n_docs = len(docs)

    def vec(doc: List[str]) -> Dict[str, float]:
        tf = Counter(doc)
        length = len(doc)
        return {
            term: (count / length) * math.log((1 + n_docs) / (1 + df[term]) + 1)
            for term, count in tf.items()
        }

    va, vb = vec(docs[0]), vec(docs[1])
    common = set(va) & set(vb)
    dot = sum(va[t] * vb[t] for t in common)
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def _score_semantic(resume_text: str, job_description: str) -> ComponentScore:
    cos = _tfidf_cosine(resume_text, job_description)
    # Cosine for resume/JD pairs realistically lands ~0.1–0.5; rescale so a
    # genuinely strong overlap (~0.45) maps near 100.
    score = max(0.0, min(100.0, (cos / 0.45) * 100.0))
    return ComponentScore("Semantic Similarity", score, 0.20,
                          f"TF-IDF cosine similarity = {cos:.3f}.",
                          {"cosine": round(cos, 3)})


def _score_skills(resume_text: str, job_description: str) -> ComponentScore:
    jd_norm = _normalize(job_description)
    resume_norm = _normalize(resume_text)
    resume_tokens = set(_tokens(resume_text))

    jd_skills = sorted({s for s in TECH_LEXICON if s in jd_norm})
    if not jd_skills:
        return ComponentScore("Skills Coverage", 70.0, 0.15,
                              "No specific hard skills detected in JD.")
    present = [s for s in jd_skills
               if _keyword_present(s, resume_norm, resume_tokens)]
    score = 100.0 * len(present) / len(jd_skills)
    return ComponentScore("Skills Coverage", score, 0.15,
                          f"{len(present)}/{len(jd_skills)} JD hard-skills present.",
                          {"present": present,
                           "missing": [s for s in jd_skills if s not in present]})


def _score_formatting(resume: Union[str, dict], resume_text: str) -> ComponentScore:
    checks: List[Tuple[str, bool]] = []
    norm = _normalize(resume_text)

    # Structured resume → check fields directly; raw text → keyword heuristic.
    if isinstance(resume, dict):
        checks.append(("Contact email present", bool(resume.get("email"))))
        checks.append(("Phone present", bool(resume.get("phone"))))
        checks.append(("Summary section", bool(resume.get("summary"))))
        checks.append(("Experience section", bool(resume.get("experience"))))
        checks.append(("Education section", bool(resume.get("education"))))
        checks.append(("Skills section", bool(resume.get("skills"))))
        has_dates = any(
            re.search(r"\b(19|20)\d{2}\b", str(e.get("duration", "")))
            for e in resume.get("experience", []) or []
        )
        checks.append(("Dated experience", has_dates))
    else:
        checks.append(("Contact email present",
                       bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", resume_text))))
        checks.append(("Phone present",
                       bool(re.search(r"(\+?\d[\d\s().-]{7,}\d)", resume_text))))
        for sec in EXPECTED_SECTIONS:
            checks.append((f"{sec.title()} section", sec in norm))
        checks.append(("Dated experience",
                       bool(re.search(r"\b(19|20)\d{2}\b", resume_text))))

    # Length sanity (an ATS resume is typically 400–1200 words).
    n_words = len(_tokens(resume_text))
    checks.append(("Reasonable length (250–1500 words)", 250 <= n_words <= 1500))

    passed = sum(1 for _, ok in checks if ok)
    score = 100.0 * passed / len(checks)
    return ComponentScore("Formatting & Structure", score, 0.15,
                          f"{passed}/{len(checks)} ATS structure checks passed.",
                          {"checks": {n: ok for n, ok in checks},
                           "word_count": n_words})


def _iter_bullets(resume: Union[str, dict], resume_text: str) -> List[str]:
    bullets: List[str] = []
    if isinstance(resume, dict):
        for exp in resume.get("experience", []) or []:
            bullets += [str(b) for b in exp.get("bullets", []) or []]
        for proj in resume.get("projects", []) or []:
            bullets += [str(b) for b in proj.get("bullets", []) or []]
    if not bullets:
        # Fall back to lines that look like bullets.
        for line in resume_text.splitlines():
            s = line.strip(" •-*\t")
            if len(s.split()) >= 4:
                bullets.append(s)
    return bullets


def _score_impact(resume: Union[str, dict], resume_text: str) -> ComponentScore:
    bullets = _iter_bullets(resume, resume_text)
    if not bullets:
        return ComponentScore("Impact & Readability", 40.0, 0.15,
                              "No achievement bullets detected.")

    quantified = sum(1 for b in bullets if re.search(r"\d", b))
    strong_start = 0
    for b in bullets:
        first = _tokens(b)[0] if _tokens(b) else ""
        if first in ACTION_VERBS:
            strong_start += 1
    avg_len = sum(len(b.split()) for b in bullets) / len(bullets)

    pct_quant = quantified / len(bullets)
    pct_verb = strong_start / len(bullets)
    # Ideal bullet length ~12–28 words.
    len_score = 1.0 if 10 <= avg_len <= 30 else max(0.0, 1 - abs(avg_len - 20) / 25)

    score = 100.0 * (0.45 * pct_quant + 0.35 * pct_verb + 0.20 * len_score)
    return ComponentScore("Impact & Readability", score, 0.15,
                          f"{quantified}/{len(bullets)} bullets quantified, "
                          f"{strong_start}/{len(bullets)} start with action verbs.",
                          {"quantified_pct": round(pct_quant, 2),
                           "action_verb_pct": round(pct_verb, 2),
                           "avg_bullet_words": round(avg_len, 1)})


# ─────────────────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────────────────

def _grade(score: int) -> str:
    if score >= 85:
        return "Excellent — highly ATS-competitive"
    if score >= 70:
        return "Strong — minor gaps to close"
    if score >= 55:
        return "Moderate — needs targeted optimization"
    if score >= 40:
        return "Weak — significant gaps"
    return "Poor — major rework recommended"


def _build_suggestions(components: List[ComponentScore],
                       missing_keywords: List[str]) -> List[str]:
    tips: List[str] = []
    by_name = {c.name: c for c in components}

    if by_name["Keyword Match"].score < 75 and missing_keywords:
        top = ", ".join(missing_keywords[:8])
        tips.append(f"Add these missing JD keywords where truthful: {top}.")
    if by_name["Skills Coverage"].score < 80:
        miss = by_name["Skills Coverage"].evidence.get("missing", [])
        if miss:
            tips.append(f"List these required hard skills if you have them: "
                        f"{', '.join(miss[:8])}.")
    if by_name["Impact & Readability"].score < 75:
        ev = by_name["Impact & Readability"].evidence
        if ev.get("quantified_pct", 1) < 0.5:
            tips.append("Quantify more bullets with metrics (%, $, time saved, scale).")
        if ev.get("action_verb_pct", 1) < 0.6:
            tips.append("Start more bullets with strong action verbs "
                        "(e.g., Architected, Optimized, Led).")
    if by_name["Formatting & Structure"].score < 90:
        failed = [n for n, ok in
                  by_name["Formatting & Structure"].evidence.get("checks", {}).items()
                  if not ok]
        if failed:
            tips.append("Fix structure gaps: " + ", ".join(failed[:5]) + ".")
    if by_name["Semantic Similarity"].score < 60:
        tips.append("Mirror the JD's language and framing more closely in your "
                    "summary and bullets to improve overall relevance.")
    if not tips:
        tips.append("Strong match across all signals — fine-tune wording and apply.")
    return tips


def score_resume(resume: Union[str, dict], job_description: str) -> ATSResult:
    """
    Compute a deterministic ATS match score.

    Args:
        resume: structured resume dict (preferred) or raw resume text.
        job_description: the target job description text.

    Returns:
        ATSResult with overall score, grade, component breakdown,
        matched/missing keywords, and actionable suggestions.
    """
    resume_text = resume_to_text(resume)

    kw_comp, matched, missing = _score_keywords(resume_text, job_description)
    components = [
        kw_comp,
        _score_semantic(resume_text, job_description),
        _score_skills(resume_text, job_description),
        _score_formatting(resume, resume_text),
        _score_impact(resume, resume_text),
    ]

    overall = sum(c.score * c.weight for c in components)
    overall_int = int(round(max(0.0, min(100.0, overall))))

    return ATSResult(
        overall=overall_int,
        grade=_grade(overall_int),
        components=components,
        matched_keywords=matched,
        missing_keywords=missing,
        suggestions=_build_suggestions(components, missing),
    )


def score_delta(before: Union[str, dict], after: Union[str, dict],
                job_description: str) -> dict:
    """Score two resume versions against the same JD and return the improvement."""
    b = score_resume(before, job_description)
    a = score_resume(after, job_description)
    return {
        "before": b.overall,
        "after": a.overall,
        "delta": a.overall - b.overall,
        "before_result": b,
        "after_result": a,
    }
