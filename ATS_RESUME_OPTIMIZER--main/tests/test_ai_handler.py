"""
Unit tests for the fragile, critical helpers in ai_handler:
_parse_json (LLM JSON cleanup) and _safe_merge (never-lose-data merge).

External SDKs (google.generativeai, openai, dotenv) are stubbed so these pure
functions can be tested without network access or API keys.
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Stub external dependencies before importing ai_handler ──────────────────
def _stub(name, attrs=None):
    mod = types.ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod

genai = _stub("google.generativeai")
_stub("google", {"generativeai": genai})
genai.configure = lambda *a, **k: None
genai.list_models = lambda: []
genai.GenerativeModel = lambda *a, **k: None
genai.GenerationConfig = lambda *a, **k: None
_stub("openai", {"OpenAI": lambda *a, **k: None})
_stub("dotenv", {"load_dotenv": lambda *a, **k: None})

import ai_handler as h


# ── _parse_json ──────────────────────────────────────────────────────────────

def test_parse_plain_json():
    assert h._parse_json('{"a": 1}') == {"a": 1}


def test_parse_with_code_fence():
    assert h._parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_with_leading_prose():
    assert h._parse_json('Here is your JSON: {"a": 1} hope it helps') == {"a": 1}


def test_parse_trailing_comma_repair():
    assert h._parse_json('{"a": 1, "b": [1, 2,],}') == {"a": 1, "b": [1, 2]}


def test_parse_array():
    assert h._parse_json('[{"q": "x"}]') == [{"q": "x"}]


def test_parse_garbage_returns_empty():
    assert h._parse_json("not json at all") == {}
    assert h._parse_json("") == {}


# ── _safe_merge ──────────────────────────────────────────────────────────────

ORIGINAL = {
    "name": "Jane Doe", "email": "jane@x.com", "phone": "123",
    "summary": "Original summary",
    "education": [{"degree": "BS", "institution": "MIT"}],
    "experience": [
        {"title": "Engineer", "company": "Acme", "duration": "2020",
         "bullets": ["did a", "did b"]},
        {"title": "Intern", "company": "Beta", "duration": "2019",
         "bullets": ["helped c"]},
    ],
    "projects": [{"name": "P1", "bullets": ["built x"]}],
    "skills": {"Lang": ["Python"]},
    "certifications": ["AWS"],
}


def test_merge_never_drops_experience():
    ai_out = {"name": "Jane Doe", "experience": [
        {"bullets": ["improved a", "improved b"]}]}  # AI returned only 1 role
    merged = h._safe_merge(ai_out, ORIGINAL)
    assert len(merged["experience"]) == 2          # second role preserved
    assert merged["experience"][1]["company"] == "Beta"


def test_merge_preserves_facts():
    ai_out = {"name": "", "email": "",
              "experience": [{"title": "Changed", "company": "Changed",
                              "bullets": ["new a", "new b"]}]}
    merged = h._safe_merge(ai_out, ORIGINAL)
    assert merged["name"] == "Jane Doe"            # blank name ignored
    assert merged["email"] == "jane@x.com"
    assert merged["experience"][0]["title"] == "Engineer"   # facts kept
    assert merged["experience"][0]["bullets"] == ["new a", "new b"]  # bullets updated


def test_merge_keeps_original_bullets_if_ai_empty():
    ai_out = {"name": "Jane Doe", "experience": [{"bullets": []}, {"bullets": []}]}
    merged = h._safe_merge(ai_out, ORIGINAL)
    assert merged["experience"][0]["bullets"] == ["did a", "did b"]


def test_merge_unions_certifications():
    ai_out = {"name": "Jane Doe", "certifications": ["GCP", "AWS"]}
    merged = h._safe_merge(ai_out, ORIGINAL)
    assert set(merged["certifications"]) == {"AWS", "GCP"}


def test_validate_resume_rejects_dropped_role():
    bad = {"name": "Jane", "experience": [], "education": [{"degree": "BS"}]}
    assert h._validate_resume(bad, ORIGINAL) is False


def test_validate_resume_accepts_good():
    good = dict(ORIGINAL)
    assert h._validate_resume(good, ORIGINAL) is True


# ── fabrication guardrail ──────────────────────────────────────────────────────

def test_detect_fabricated_metrics():
    original = {"experience": [{"bullets": ["Improved latency"]}]}
    optimized = {"experience": [{"bullets": ["Improved latency by 73% for 2000000 users"]}]}
    fab = h.detect_fabricated_metrics(original, optimized)
    assert "73%" in fab or "2000000" in fab


def test_no_fabrication_when_numbers_preserved():
    original = {"experience": [{"bullets": ["Cut cost by 30%"]}]}
    optimized = {"experience": [{"bullets": ["Reduced cost by 30%"]}]}
    assert h.detect_fabricated_metrics(original, optimized) == []


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); passed += 1
        except Exception:
            print(f"FAIL  {fn.__name__}"); traceback.print_exc()
    print(f"\n{passed}/{len(fns)} tests passed")
    sys.exit(0 if passed == len(fns) else 1)
