"""Unit tests for the deterministic ATS scoring engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ats_scorer as s


JD = """
We are looking for a Senior Software Engineer with strong experience in Python,
Django, and React. The ideal candidate has built scalable microservices on AWS,
worked with Docker and Kubernetes, and has a solid grasp of system design,
REST APIs, and CI/CD pipelines. Machine learning experience is a plus.
"""

GOOD_RESUME = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1-555-123-4567",
    "summary": "Senior Software Engineer with 6 years building scalable "
               "microservices in Python and Django on AWS.",
    "education": [{"degree": "BS Computer Science", "institution": "MIT",
                   "year": "2016"}],
    "experience": [{
        "title": "Senior Software Engineer", "company": "Acme",
        "duration": "Jan 2019 - Present",
        "bullets": [
            "Architected microservices on AWS using Docker and Kubernetes, "
            "reducing latency by 40% for 2M daily users.",
            "Built REST APIs in Django serving 5M requests/day with 99.9% uptime.",
            "Optimized CI/CD pipelines, cutting deploy time from 2h to 10m.",
            "Developed a React dashboard adopted by 12 internal teams.",
        ],
    }],
    "skills": {"Languages": ["Python", "JavaScript"],
               "Frameworks": ["Django", "React"],
               "Cloud": ["AWS", "Docker", "Kubernetes"]},
}

WEAK_RESUME = {
    "name": "John Smith",
    "email": "",
    "phone": "",
    "summary": "",
    "education": [],
    "experience": [{
        "title": "Helper", "company": "Shop", "duration": "",
        "bullets": ["Helped with stuff", "Did some work on things"],
    }],
    "skills": {},
}


def test_good_beats_weak():
    good = s.score_resume(GOOD_RESUME, JD)
    weak = s.score_resume(WEAK_RESUME, JD)
    assert good.overall > weak.overall
    assert good.overall >= 60
    assert weak.overall < 50


def test_deterministic():
    a = s.score_resume(GOOD_RESUME, JD)
    b = s.score_resume(GOOD_RESUME, JD)
    assert a.overall == b.overall
    assert a.to_dict() == b.to_dict()


def test_keyword_extraction_finds_tech():
    kws = [k for k, _ in s.extract_jd_keywords(JD)]
    joined = " ".join(kws)
    assert "python" in joined
    assert "django" in joined
    assert any("kubernetes" in k or "docker" in k for k in kws)


def test_acronym_matching():
    jd = "Seeking an ML engineer with NLP expertise."
    resume = {"summary": "Built machine learning and natural language processing models.",
              "experience": [], "skills": {}}
    res = s.score_resume(resume, jd)
    # ML→machine learning and NLP→natural language processing should match.
    assert "ml" in res.matched_keywords or "machine learning" in res.matched_keywords


def test_components_present_and_weighted():
    res = s.score_resume(GOOD_RESUME, JD)
    names = {c.name for c in res.components}
    assert names == {"Keyword Match", "Semantic Similarity", "Skills Coverage",
                     "Formatting & Structure", "Impact & Readability"}
    assert abs(sum(c.weight for c in res.components) - 1.0) < 1e-9


def test_score_in_range():
    for r in (GOOD_RESUME, WEAK_RESUME):
        res = s.score_resume(r, JD)
        assert 0 <= res.overall <= 100


def test_delta_detects_improvement():
    d = s.score_delta(WEAK_RESUME, GOOD_RESUME, JD)
    assert d["delta"] > 0
    assert d["after"] > d["before"]


def test_raw_text_resume_supported():
    txt = ("Jane Doe jane@example.com +1-555-123-4567\n"
           "Summary: Python Django engineer.\n"
           "Experience: Built REST APIs on AWS with Docker in 2020.\n"
           "Skills: Python, Django, React, Kubernetes\n"
           "Education: BS CS 2016")
    res = s.score_resume(txt, JD)
    assert res.overall > 0


def test_quantification_detected():
    res = s.score_resume(GOOD_RESUME, JD)
    impact = next(c for c in res.components if c.name == "Impact & Readability")
    assert impact.evidence["quantified_pct"] >= 0.5


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} tests passed")
    sys.exit(0 if passed == len(fns) else 1)
