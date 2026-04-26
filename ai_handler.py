"""
ai_handler.py – All Gemini AI interactions for the ATS Resume Expert app.
Includes: Multi-Pass Deep Optimizer, Mock Interview, Resume Rebuilder.
"""

import json
import re
import google.generativeai as genai
from resume_knowledge_base import (
    get_full_knowledge_context,
    get_weak_to_strong_prompt,
    get_star_examples_prompt,
    get_ats_rules_prompt,
    get_power_verbs_prompt,
)

PREFERRED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-lite-latest"]


# ─── Model Selection ─────────────────────────────────────────────────────────

def get_best_model() -> str:
    """Return the best available Gemini model."""
    try:
        available = {
            m.name.split("/")[-1]
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        }
        for model in PREFERRED_MODELS:
            if model in available:
                return model
    except Exception as e:
        print(f"Error listing models: {e}")
        pass
    return "gemini-1.5-flash"


def _call(prompt: str) -> str:
    """Single-prompt Gemini call."""
    try:
        model = genai.GenerativeModel(
            model_name=get_best_model(),
            generation_config=genai.GenerationConfig(temperature=0.0)
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e) or "ResourceExhausted" in str(e) or "quota" in str(e).lower():
            raise Exception("⏳ **Google API Quota Exceeded.** The free tier allows 15 requests per minute. Please wait 60 seconds and try again!")
        raise Exception(f"API Error: {e}")


def _call_parts(parts: list) -> str:
    """Multi-part Gemini call."""
    try:
        model = genai.GenerativeModel(
            model_name=get_best_model(),
            generation_config=genai.GenerationConfig(temperature=0.0)
        )
        response = model.generate_content(parts)
        return response.text
    except Exception as e:
        if "429" in str(e) or "ResourceExhausted" in str(e) or "quota" in str(e).lower():
            raise Exception("⏳ **Google API Quota Exceeded.** The free tier allows 15 requests per minute. Please wait 60 seconds and try again!")
        raise Exception(f"API Error: {e}")


def _parse_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON safely."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw.strip())


# ─── ATS Review & Score ───────────────────────────────────────────────────────

def get_ats_review(pdf_text: str, job_desc: str) -> str:
    return _call_parts([
        """You are an experienced HR professional. Review this resume against the job description.
        Provide with clear markdown formatting:
        ## ✅ Strengths
        (bullet points of what matches well)
        ## ⚠️ Areas for Improvement
        (bullet points of gaps)
        ## 💡 Optimization Suggestions
        (specific, actionable suggestions)
        ## 📋 Overall Recommendation
        (1-2 sentences summary)""",
        pdf_text,
        job_desc,
    ])


def get_ats_score(pdf_text: str, job_desc: str) -> str:
    return _call_parts([
        """You are an ATS scanner. Analyze this resume against the job description.
        Provide with clear markdown formatting:
        ## 📊 ATS Match Score: XX%
        (give a realistic percentage)
        ## 🔑 Keywords Found
        (comma-separated list of matching keywords)
        ## ❌ Missing Keywords
        (comma-separated list of important missing keywords)
        ## 📈 How to Improve Your Score
        (specific, numbered suggestions)
        ## 💬 Final Verdict
        (brief conclusion)""",
        pdf_text,
        job_desc,
    ])


# ─── Resume Structure Extraction ──────────────────────────────────────────────

RESUME_JSON_SCHEMA = """
{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+1-xxx-xxx-xxxx",
  "linkedin": "linkedin.com/in/username",
  "github": "github.com/username",
  "location": "City, State",
  "summary": "Professional summary paragraph",
  "education": [
    {
      "degree": "Degree Name",
      "institution": "University Name",
      "location": "City, State",
      "year": "2020 - 2024",
      "gpa": "3.8"
    }
  ],
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "location": "City, State",
      "duration": "Jan 2023 - Present",
      "bullets": ["Achievement 1", "Achievement 2"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "technologies": "Tech1, Tech2",
      "duration": "2023",
      "bullets": ["Built X", "Achieved Y"]
    }
  ],
  "skills": {
    "Languages": ["Python", "Java"],
    "Frameworks": ["React", "Django"],
    "Tools": ["Git", "Docker", "AWS"]
  },
  "certifications": ["Cert 1", "Cert 2"]
}
"""


def extract_resume_structure(pdf_text: str) -> dict:
    """Parse raw resume text into a structured JSON dict."""
    prompt = f"""
Extract ALL resume information from the text below into this EXACT JSON structure.
Return ONLY valid JSON — no markdown, no code fences, no explanation.
Use empty strings "" for missing fields, empty arrays [] for missing lists.

Required JSON structure:
{RESUME_JSON_SCHEMA}

Resume text:
{pdf_text}
"""
    raw = _call(prompt)
    return _parse_json(raw)


# ═══════════════════════════════════════════════════════════════════════════
#  MULTI-PASS DEEP OPTIMIZER (RAG-Enhanced)
# ═══════════════════════════════════════════════════════════════════════════

def deep_pass1_keywords(resume_data: dict, job_description: str) -> dict:
    """Pass 1: Extract JD keywords and map them to resume sections."""
    prompt = f"""You are an elite ATS keyword analyst.

TASK: Analyze the Job Description and the candidate's current resume.
Return a JSON object with:
{{
  "required_hard_skills": ["exact phrases from JD"],
  "required_soft_skills": ["exact phrases from JD"],
  "required_tools": ["exact tool/framework names from JD"],
  "found_in_resume": ["keywords already present in resume"],
  "missing_critical": ["MUST-ADD keywords not in resume"],
  "missing_nice_to_have": ["good-to-add keywords"],
  "suggested_placement": {{
    "summary": ["keywords to weave into summary"],
    "experience": ["keywords to weave into bullets"],
    "skills": ["keywords to add to skills section"]
  }}
}}

Return ONLY valid JSON.

Job Description:
{job_description}

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def deep_pass2_bullets(resume_data: dict, job_description: str, keyword_analysis: dict) -> dict:
    """Pass 2: Rewrite every bullet point using STAR method + KB reference."""
    kb_context = f"""
REFERENCE — GOLD STANDARD BULLET EXAMPLES:
{get_star_examples_prompt()}

REFERENCE — WEAK → STRONG TRANSFORMATIONS:
{get_weak_to_strong_prompt()}

REFERENCE — POWER VERBS TO USE:
{get_power_verbs_prompt()}
"""
    prompt = f"""You are an elite FAANG resume writer. Your task is to rewrite EVERY bullet point in the resume.

{kb_context}

RULES:
1. Start each bullet with a POWER VERB from the reference list above.
2. Follow the STAR method: Action → Context → Result (with metrics).
3. Weave in these MISSING KEYWORDS naturally: {json.dumps(keyword_analysis.get('missing_critical', []))}
4. If the original bullet is vague (like "Worked on X"), completely rewrite it with specifics.
5. If the original bullet already has metrics, keep them but improve the language.
6. Add realistic quantification where missing (use reasonable estimates).
7. Keep each bullet to 1-2 lines max.
8. NEVER fabricate new jobs, companies, or degrees.
9. Return the FULL resume JSON with ALL bullets rewritten.

Return ONLY valid JSON in the exact same schema as input.

Job Description:
{job_description}

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def deep_pass3_summary_skills(resume_data: dict, job_description: str, keyword_analysis: dict) -> dict:
    """Pass 3: Optimize summary and skills sections."""
    ats_rules = get_ats_rules_prompt()
    prompt = f"""You are an elite ATS optimization specialist.

TASK: Optimize ONLY the "summary" and "skills" sections of this resume.
Leave experience, education, projects, and personal info UNCHANGED.

{ats_rules}

SUMMARY RULES:
1. Write a compelling 2-3 sentence professional summary.
2. Include the candidate's years of experience, core domain, and top 3-4 skills from the JD.
3. Include a quantified achievement if possible.
4. Must contain these keywords: {json.dumps(keyword_analysis.get('suggested_placement', {}).get('summary', []))}

SKILLS RULES:
1. Reorganize skills into clear categories (Languages, Frameworks, Tools, etc.).
2. Add all missing critical keywords: {json.dumps(keyword_analysis.get('missing_critical', []))}
3. Place the most JD-relevant skills FIRST in each category.
4. Include both acronyms and full forms where applicable.
5. Remove outdated or irrelevant skills that don't match the JD.

Return ONLY valid JSON in the exact same schema as input.

Job Description:
{job_description}

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def deep_pass4_audit(resume_data: dict, job_description: str) -> dict:
    """Pass 4: Final ATS audit — self-verification and fix pass."""
    prompt = f"""You are a strict ATS compliance auditor performing a FINAL quality check.

AUDIT THIS RESUME against the job description and fix ANY remaining issues:

CHECK 1 — KEYWORD COVERAGE:
  Scan the JD for every required skill/tool/technology. Verify each one appears
  at least once in the resume (in summary, bullets, OR skills). If missing, add it.

CHECK 2 — BULLET QUALITY:
  Every bullet must start with a strong action verb and contain a measurable result.
  Fix any weak bullets that slipped through.

CHECK 3 — CONSISTENCY:
  Ensure no contradictions, consistent date formats, consistent tense (past for
  previous roles, present for current role).

CHECK 4 — ATS FORMATTING:
  Section headers must be standard: "Summary", "Education", "Experience", "Projects", "Technical Skills".

Return the FINAL, polished resume JSON. Only valid JSON, no explanation.

Job Description:
{job_description}

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def optimize_resume_deep(resume_data: dict, job_description: str, progress_callback=None) -> dict:
    """Full multi-pass deep optimization pipeline."""
    if progress_callback:
        progress_callback("🔍 Pass 1/4 — Extracting keywords & analyzing gaps...")
    keyword_analysis = deep_pass1_keywords(resume_data, job_description)

    if progress_callback:
        progress_callback("✏️ Pass 2/4 — Rewriting every bullet with STAR method...")
    resume_v2 = deep_pass2_bullets(resume_data, job_description, keyword_analysis)

    if progress_callback:
        progress_callback("📝 Pass 3/4 — Optimizing summary & skills sections...")
    resume_v3 = deep_pass3_summary_skills(resume_v2, job_description, keyword_analysis)

    if progress_callback:
        progress_callback("🔎 Pass 4/4 — Final ATS audit & quality check...")
    resume_final = deep_pass4_audit(resume_v3, job_description)

    return resume_final


# Legacy single-pass optimizer (kept for backward compatibility)
def optimize_resume_for_jd(resume_data: dict, job_description: str) -> dict:
    """Single-pass optimizer (legacy). Use optimize_resume_deep for better results."""
    return optimize_resume_deep(resume_data, job_description)


# ═══════════════════════════════════════════════════════════════════════════
#  RESUME REBUILDER — Scrappy → Perfect
# ═══════════════════════════════════════════════════════════════════════════

def deep_extract_resume(pdf_text: str) -> dict:
    """Stage 1: Deep extraction — finds every piece of info even from bad resumes."""
    prompt = f"""You are an expert resume parser. The text below is from a poorly formatted
or incomplete resume. Your job is to extract EVERY piece of useful information.

INSTRUCTIONS:
1. Read the text VERY carefully — information may be scattered or poorly organized.
2. Infer job titles, company names, dates from context clues if not explicit.
3. If bullets are missing, extract achievement-like sentences from paragraphs.
4. Capture ALL skills mentioned anywhere in the text.
5. If education details are minimal, extract whatever is available.
6. Use empty strings "" for truly missing fields, never skip a field.

Return ONLY valid JSON in this schema:
{RESUME_JSON_SCHEMA}

Resume text:
{pdf_text}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def rewrite_resume_content(resume_data: dict) -> dict:
    """Stage 2: Complete rewrite — STAR method, power verbs, quantification."""
    kb_context = f"""
REFERENCE EXAMPLES — GOLD STANDARD BULLETS:
{get_star_examples_prompt()}

REFERENCE — WEAK → STRONG TRANSFORMATIONS:
{get_weak_to_strong_prompt()}

POWER VERBS TO USE:
{get_power_verbs_prompt()}
"""
    prompt = f"""You are a world-class resume writer hired to completely transform this resume.

{kb_context}

YOUR MISSION:
1. REWRITE every single bullet point using the STAR method (Action → Context → Result).
2. START each bullet with a power verb from the reference list.
3. ADD realistic quantification to EVERY bullet (percentages, dollar amounts, user counts, time saved).
4. WRITE a compelling professional summary (2-3 sentences) that highlights their strongest qualifications.
5. REORGANIZE skills into clean categories.
6. EXPAND thin sections — if experience has only 1-2 weak bullets, expand to 3-4 strong ones based on implied responsibilities.
7. NEVER invent new jobs, companies, degrees, or certifications.
8. Make everything sound professional, confident, and achievement-oriented.

Return ONLY valid JSON in the same schema. No explanation.

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def polish_resume(resume_data: dict) -> dict:
    """Stage 3: Final polish — consistency, grammar, professional tone."""
    prompt = f"""You are a professional editor performing a FINAL polish on this resume.

TASKS:
1. Fix any grammar or spelling errors.
2. Ensure consistent formatting (date formats, capitalization, punctuation).
3. Use present tense for current roles, past tense for previous roles.
4. Make sure the summary is compelling and not generic.
5. Ensure skills are properly categorized and deduplicated.
6. Remove any filler words or unnecessary adjectives from bullets.
7. Verify every bullet starts with a strong action verb.
8. Ensure the overall tone is confident and professional.

Return ONLY valid JSON. No explanation.

Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def rebuild_resume(pdf_text: str, progress_callback=None) -> dict:
    """Full 3-stage resume rebuilder pipeline."""
    if progress_callback:
        progress_callback("🔍 Stage 1/3 — Deep extraction from your resume...")
    extracted = deep_extract_resume(pdf_text)

    if progress_callback:
        progress_callback("✏️ Stage 2/3 — Rewriting with STAR method & power verbs...")
    rewritten = rewrite_resume_content(extracted)

    if progress_callback:
        progress_callback("✨ Stage 3/3 — Final polish & quality check...")
    polished = polish_resume(rewritten)

    return polished


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK INTERVIEW COACH
# ═══════════════════════════════════════════════════════════════════════════

def generate_interview_questions(pdf_text: str, job_description: str) -> list:
    """Generate 5 tailored interview questions based on resume + JD."""
    prompt = f"""You are a senior hiring manager preparing to interview a candidate.
Based on their resume and the job description, generate exactly 5 interview questions.

MIX:
- 2 behavioral questions (about past experiences, teamwork, challenges)
- 2 technical questions (specific to the role's required skills)
- 1 situational question (hypothetical scenario they might face in this role)

For each question, also provide:
- "category": "behavioral" | "technical" | "situational"
- "what_to_look_for": brief note on what a great answer would include

Return as a JSON array:
[
  {{
    "question": "Tell me about...",
    "category": "behavioral",
    "what_to_look_for": "Look for specific STAR format..."
  }}
]

Return ONLY valid JSON array.

Resume:
{pdf_text}

Job Description:
{job_description}
"""
    raw = _call(prompt)
    return json.loads(re.sub(r"^```(?:json)?\s*", "", raw.strip()).rstrip("`").strip())


def evaluate_interview_answer(question: str, answer: str, job_description: str, resume_text: str) -> dict:
    """Evaluate a candidate's interview answer."""
    prompt = f"""You are a senior hiring manager evaluating an interview answer.

Question asked: "{question}"

Candidate's answer: "{answer}"

Job Description context: {job_description[:500]}

Evaluate the answer and return JSON:
{{
  "score": <1-10>,
  "grade": "Excellent" | "Good" | "Average" | "Needs Improvement",
  "strengths": ["what they did well"],
  "improvements": ["what could be better"],
  "ideal_answer": "A brief example of what a perfect answer would sound like (2-3 sentences)",
  "tip": "One specific, actionable tip for improvement"
}}

Return ONLY valid JSON.
"""
    raw = _call(prompt)
    return _parse_json(raw)


def generate_interview_report(results: list) -> str:
    """Generate a final interview performance report."""
    prompt = f"""You are a career coach reviewing a mock interview performance.
Here are the questions, answers, and scores:

{json.dumps(results, indent=2)}

Write a brief, encouraging performance report in markdown with:
## 🎯 Overall Score: X/10
## ✅ Your Strengths
(2-3 bullet points)
## 📈 Areas to Improve
(2-3 bullet points)
## 💡 Top 3 Tips for Your Real Interview
(numbered list)
## 🔥 Confidence Level: [Ready / Almost There / Keep Practicing]
"""
    return _call(prompt)


# ─── Company Personalizer ────────────────────────────────────────────────────

def personalize_for_company(
    resume_data: dict,
    job_description: str,
    company: str,
    role: str,
) -> dict:
    """Tailor resume specifically for a target company and role."""
    prompt = f"""
You are an elite ATS algorithm expert and a highly-paid recruitment consultant specifically hired to get this candidate a {role} role at {company}.
Your ONLY goal is to rewrite the provided resume JSON to score an ATS Match of 90%+ against the Job Description, AND align perfectly with {company}'s specific corporate culture.

YOUR STRATEGY:
1. ATS KEYWORD WEAVING: Extract exact technical/soft skills from the JD and surgically inject them word-for-word into the candidate's specific bullets, summary, and skills section. Do not paraphrase ATS keywords.
2. COMPANY CULTURE TRADING: Rewrite the tone of the Professional Summary and Bullet Points to scream "{company}". If {company} is Apple, sound design-focused and secretive. If Microsoft, sound enterprise and scale-focused. If a startup, sound scrappy and fast-paced.
3. HARVARD 'STAR' METHOD: Force every bullet point into the Action-Context-Result framework.
4. RELEVANCE FILTERING: Minimize or delete bullets that do not impress {company} or do not map to the {role} job description. Expand upon bullets that do.
5. ⚠️ BOUNDARY: NEVER fabricate new jobs, fake dates, or imaginary degrees. Reframing is allowed; lying is not.

Return ONLY valid JSON in the EXACT same schema structure as the input — no markdown, no explanation.

Target Company: {company}
Target Role: {role}
Job Description:
{job_description}

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)
