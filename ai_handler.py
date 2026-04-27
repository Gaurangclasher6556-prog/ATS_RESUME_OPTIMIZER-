"""
ai_handler.py – All Gemini AI interactions for the ATS Resume Expert app.
Includes: Multi-Pass Deep Optimizer, Mock Interview, Resume Rebuilder.
"""

import os
from dotenv import load_dotenv
load_dotenv(override=True)
import json
import re
import google.generativeai as genai
from openai import OpenAI
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


# ─── Fallback LLM Implementations ────────────────────────────────────────────

def _call_groq(prompt: str) -> str:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise Exception("GROQ_API_KEY not found.")
    client = OpenAI(api_key=groq_api_key, base_url="https://api.groq.com/openai/v1")
    # Use llama-3.1-8b-instant or llama-3.3-70b-versatile
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return response.choices[0].message.content

def _call_openrouter(prompt: str) -> str:
    or_api_key = os.getenv("OPENROUTER_API_KEY")
    if not or_api_key:
        raise Exception("OPENROUTER_API_KEY not found.")
    client = OpenAI(api_key=or_api_key, base_url="https://openrouter.ai/api/v1")
    # Using a fast reliable model on OpenRouter, like Google's Gemini 2.5 Flash
    response = client.chat.completions.create(
        model="google/gemini-2.5-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return response.choices[0].message.content

def _call_with_fallback(prompt: str, original_parts=None) -> str:
    """Try Gemini, then Groq, then OpenRouter."""
    try:
        model = genai.GenerativeModel(
            model_name=get_best_model(),
            generation_config=genai.GenerationConfig(temperature=0.0)
        )
        # Use original_parts if provided (for Gemini's native multi-part support), else use prompt
        response = model.generate_content(original_parts if original_parts else prompt)
        return response.text
    except Exception as e:
        if "429" in str(e) or "ResourceExhausted" in str(e) or "quota" in str(e).lower():
            print(f"Gemini quota exceeded. Falling back to Groq...")
            try:
                return _call_groq(prompt)
            except Exception as e2:
                print(f"Groq failed. Falling back to OpenRouter...")
                try:
                    return _call_openrouter(prompt)
                except Exception as e3:
                    raise Exception(f"⏳ **All APIs Failed.** \nGemini: {e}\nGroq: {e2}\nOpenRouter: {e3}")
        raise Exception(f"API Error: {e}")

def _call(prompt: str) -> str:
    """Single-prompt Gemini call with fallback."""
    return _call_with_fallback(prompt)

def _call_parts(parts: list) -> str:
    """Multi-part Gemini call with fallback."""
    prompt_str = "\\n\\n".join([str(p) for p in parts])
    return _call_with_fallback(prompt_str, original_parts=parts)


def _parse_json(raw: str) -> dict:
    """Strip markdown fences and conversational text and parse JSON safely."""
    if not raw or not raw.strip():
        return {}
    
    raw = raw.strip()
    
    # Extract JSON substring
    start_obj = raw.find('{')
    start_arr = raw.find('[')
    start_idx = min(start_obj, start_arr) if (start_obj != -1 and start_arr != -1) else max(start_obj, start_arr)
        
    end_obj = raw.rfind('}')
    end_arr = raw.rfind(']')
    end_idx = max(end_obj, end_arr)
        
    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        raw = raw[start_idx:end_idx+1]
        
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error. Cleaned raw string was: {raw[:200]}...")
        return {}


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
#  VALIDATION & SAFE MERGE — Ensures no data is ever lost between passes
# ═══════════════════════════════════════════════════════════════════════════

def _validate_resume(data: dict, original: dict) -> bool:
    """Check if AI output has all critical fields populated."""
    if not isinstance(data, dict):
        return False
    # Must have name
    if not data.get("name") or data["name"].strip() == "":
        return False
    # Must not have fewer experience entries than original
    if len(data.get("experience", [])) < len(original.get("experience", [])):
        return False
    # Must not have fewer education entries than original
    if len(data.get("education", [])) < len(original.get("education", [])):
        return False
    # Bullets must not be empty on any experience entry that had bullets
    for i, exp in enumerate(data.get("experience", [])):
        if i < len(original.get("experience", [])):
            orig_bullets = original["experience"][i].get("bullets", [])
            new_bullets = exp.get("bullets", [])
            if len(orig_bullets) > 0 and len(new_bullets) == 0:
                return False
    return True


def _safe_merge(ai_output: dict, original: dict) -> dict:
    """Merge AI output onto original data — original wins for any empty/missing fields."""
    merged = dict(original)  # start with all original data

    # Personal info: keep original if AI blanked it out
    for field in ("name", "email", "phone", "linkedin", "github", "location"):
        ai_val = ai_output.get(field, "")
        if ai_val and ai_val.strip():
            merged[field] = ai_val
        # else: keep original

    # Summary: use AI version only if non-empty
    if ai_output.get("summary", "").strip():
        merged["summary"] = ai_output["summary"]

    # Education: keep original structure, only update if AI has same count
    ai_edu = ai_output.get("education", [])
    orig_edu = original.get("education", [])
    if len(ai_edu) >= len(orig_edu) and len(ai_edu) > 0:
        merged["education"] = ai_edu
    # else: keep original education

    # Experience: merge bullet-by-bullet — never lose a role
    ai_exp = ai_output.get("experience", [])
    orig_exp = original.get("experience", [])
    merged_exp = []
    for i in range(max(len(orig_exp), len(ai_exp))):
        if i < len(ai_exp) and i < len(orig_exp):
            role = dict(orig_exp[i])  # start with original
            ai_role = ai_exp[i]
            # Keep original title, company, location, duration — never change facts
            role["title"] = orig_exp[i].get("title") or ai_role.get("title", "")
            role["company"] = orig_exp[i].get("company") or ai_role.get("company", "")
            role["location"] = orig_exp[i].get("location") or ai_role.get("location", "")
            role["duration"] = orig_exp[i].get("duration") or ai_role.get("duration", "")
            # Use AI bullets only if they exist and are non-empty
            ai_bullets = ai_role.get("bullets", [])
            if ai_bullets and len(ai_bullets) > 0:
                role["bullets"] = ai_bullets
            merged_exp.append(role)
        elif i < len(orig_exp):
            merged_exp.append(orig_exp[i])
        else:
            merged_exp.append(ai_exp[i])
    merged["experience"] = merged_exp

    # Projects: same logic
    ai_proj = ai_output.get("projects", [])
    orig_proj = original.get("projects", [])
    merged_proj = []
    for i in range(max(len(orig_proj), len(ai_proj))):
        if i < len(ai_proj) and i < len(orig_proj):
            proj = dict(orig_proj[i])
            ai_p = ai_proj[i]
            proj["name"] = orig_proj[i].get("name") or ai_p.get("name", "")
            proj["technologies"] = orig_proj[i].get("technologies") or ai_p.get("technologies", "")
            proj["duration"] = orig_proj[i].get("duration") or ai_p.get("duration", "")
            ai_bullets = ai_p.get("bullets", [])
            if ai_bullets and len(ai_bullets) > 0:
                proj["bullets"] = ai_bullets
            merged_proj.append(proj)
        elif i < len(orig_proj):
            merged_proj.append(orig_proj[i])
        else:
            merged_proj.append(ai_proj[i])
    merged["projects"] = merged_proj

    # Skills: use AI version if non-empty, else keep original
    ai_skills = ai_output.get("skills", {})
    if ai_skills and (isinstance(ai_skills, dict) and len(ai_skills) > 0):
        merged["skills"] = ai_skills
    elif ai_skills and isinstance(ai_skills, list) and len(ai_skills) > 0:
        merged["skills"] = ai_skills

    # Certifications: keep all — union of original and AI
    orig_certs = original.get("certifications", [])
    ai_certs = ai_output.get("certifications", [])
    if isinstance(orig_certs, list) and isinstance(ai_certs, list):
        all_certs = list(dict.fromkeys(orig_certs + ai_certs))  # dedupe preserving order
        merged["certifications"] = all_certs
    elif ai_certs:
        merged["certifications"] = ai_certs

    return merged


# ═══════════════════════════════════════════════════════════════════════════
#  MULTI-PASS DEEP OPTIMIZER (RAG-Enhanced)
# ═══════════════════════════════════════════════════════════════════════════

_PRESERVE_WARNING = """
⚠️ CRITICAL RULES — READ BEFORE RESPONDING:
1. You MUST return the COMPLETE resume JSON with ALL fields populated.
2. DO NOT delete or empty ANY field. Every field from the input MUST appear in output.
3. DO NOT remove any experience entries, education entries, or projects.
4. DO NOT change the candidate's name, email, phone, linkedin, github, location,
   job titles, company names, institution names, degree names, or dates.
5. You may ONLY modify: bullet text, summary text, and skills list.
6. The number of experience entries in output MUST equal the number in input.
7. The number of education entries in output MUST equal the number in input.
8. The number of project entries in output MUST equal the number in input.
9. Every experience entry MUST have at least as many bullets as the original.
10. DO NOT add fake/fabricated information. Only reframe existing experience.
"""


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
    prompt = f"""You are an elite FAANG resume writer. Your task is to IMPROVE every bullet point.

{_PRESERVE_WARNING}

{kb_context}

BULLET REWRITING RULES:
1. Start each bullet with a POWER VERB from the reference list above.
2. Follow the STAR method: Action → Context → Result (with metrics).
3. Weave in these MISSING KEYWORDS naturally where relevant: {json.dumps(keyword_analysis.get('missing_critical', []))}
4. If the original bullet is vague (like "Worked on X"), rewrite with specifics inferred from context.
5. If the original bullet already has metrics, KEEP them and improve the language.
6. Keep each bullet to 1-2 lines max.
7. NEVER fabricate new jobs, companies, or degrees.
8. DO NOT add unrealistic numbers. Keep quantification reasonable and believable.

Return ONLY valid JSON in the EXACT same schema as input with ALL fields preserved.

Job Description:
{job_description}

Current Resume JSON (you MUST preserve all {len(resume_data.get('experience', []))} experience entries, all {len(resume_data.get('education', []))} education entries, all {len(resume_data.get('projects', []))} projects):
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def deep_pass3_summary_skills(resume_data: dict, job_description: str, keyword_analysis: dict) -> dict:
    """Pass 3: Optimize summary and skills sections."""
    ats_rules = get_ats_rules_prompt()
    prompt = f"""You are an elite ATS optimization specialist.

{_PRESERVE_WARNING}

TASK: Optimize ONLY the "summary" and "skills" fields of this resume.
You MUST copy ALL other fields (name, email, phone, linkedin, github, location,
education, experience, projects, certifications) EXACTLY as they are — character for character.

{ats_rules}

SUMMARY RULES:
1. Write a compelling 2-3 sentence professional summary based on their ACTUAL experience.
2. Include their core domain and top 3-4 skills from the JD.
3. DO NOT invent achievements they don't have.
4. Weave in these keywords naturally: {json.dumps(keyword_analysis.get('suggested_placement', {}).get('summary', []))}

SKILLS RULES:
1. Reorganize skills into clear categories (Languages, Frameworks, Tools, etc.).
2. Add missing keywords ONLY to the skills section: {json.dumps(keyword_analysis.get('missing_critical', []))}
3. Place the most JD-relevant skills FIRST in each category.
4. Keep ALL original skills — do not remove any.

Return ONLY valid JSON in the EXACT same schema as input.

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

{_PRESERVE_WARNING}

AUDIT THIS RESUME and fix ONLY minor issues. DO NOT rewrite content that is already good.

CHECK 1 — COMPLETENESS:
  Verify EVERY field is populated. If any field is empty that shouldn't be, flag it.
  
CHECK 2 — KEYWORD COVERAGE:
  Verify critical JD keywords appear in the resume. If any are missing, add them
  to the skills section ONLY (do not rewrite bullets).

CHECK 3 — CONSISTENCY:
  Ensure consistent date formats and tense (past for previous roles, present for current).

CHECK 4 — NO FABRICATION:
  Remove any information that looks fabricated or unrealistic.

Return the FINAL resume JSON with ALL fields preserved. Only valid JSON, no explanation.

Job Description:
{job_description}

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def optimize_resume_deep(resume_data: dict, job_description: str, progress_callback=None) -> dict:
    """Full multi-pass deep optimization pipeline with validation and safe merging."""
    original = dict(resume_data)  # Preserve the original throughout

    if progress_callback:
        progress_callback("🔍 Pass 1/4 — Extracting keywords & analyzing gaps...")
    keyword_analysis = deep_pass1_keywords(resume_data, job_description)

    if progress_callback:
        progress_callback("✏️ Pass 2/4 — Rewriting every bullet with STAR method...")
    try:
        raw_v2 = deep_pass2_bullets(resume_data, job_description, keyword_analysis)
        resume_v2 = _safe_merge(raw_v2, original)
    except Exception:
        resume_v2 = original  # fallback: keep original if pass fails

    if progress_callback:
        progress_callback("📝 Pass 3/4 — Optimizing summary & skills sections...")
    try:
        raw_v3 = deep_pass3_summary_skills(resume_v2, job_description, keyword_analysis)
        resume_v3 = _safe_merge(raw_v3, resume_v2)
    except Exception:
        resume_v3 = resume_v2  # fallback

    if progress_callback:
        progress_callback("🔎 Pass 4/4 — Final ATS audit & quality check...")
    try:
        raw_v4 = deep_pass4_audit(resume_v3, job_description)
        resume_final = _safe_merge(raw_v4, resume_v3)
    except Exception:
        resume_final = resume_v3  # fallback

    # Final safety: validate the result, fallback to original if garbage
    if not _validate_resume(resume_final, original):
        resume_final = _safe_merge(resume_final, original)

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
    prompt = f"""You are a world-class resume writer hired to improve this resume.

{_PRESERVE_WARNING}

{kb_context}

YOUR MISSION:
1. REWRITE every bullet point using the STAR method (Action → Context → Result).
2. START each bullet with a power verb from the reference list.
3. ADD realistic quantification where possible — but ONLY believable numbers.
4. WRITE a compelling professional summary (2-3 sentences) based on their ACTUAL qualifications.
5. REORGANIZE skills into clean categories.
6. DO NOT invent new jobs, companies, degrees, certifications, or technologies the person doesn't have.
7. DO NOT add unrealistic metrics. If unsure, describe the impact qualitatively.
8. You MUST keep ALL {len(resume_data.get('experience', []))} experience entries,
   ALL {len(resume_data.get('education', []))} education entries,
   ALL {len(resume_data.get('projects', []))} projects.

Return ONLY valid JSON in the same schema. No explanation.

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def polish_resume(resume_data: dict) -> dict:
    """Stage 3: Final polish — consistency, grammar, professional tone."""
    prompt = f"""You are a professional editor performing a FINAL polish on this resume.

{_PRESERVE_WARNING}

TASKS:
1. Fix any grammar or spelling errors.
2. Ensure consistent formatting (date formats, capitalization, punctuation).
3. Use present tense for current roles, past tense for previous roles.
4. Make sure the summary is compelling and not generic.
5. Ensure skills are properly categorized and deduplicated.
6. Remove any filler words or unnecessary adjectives from bullets.
7. Verify every bullet starts with a strong action verb.
8. Remove any fabricated-looking information or unrealistic numbers.

Return ONLY valid JSON with ALL fields preserved. No explanation.

Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def rebuild_resume(pdf_text: str, progress_callback=None) -> dict:
    """Full 3-stage resume rebuilder pipeline with safe merge."""
    if progress_callback:
        progress_callback("🔍 Stage 1/3 — Deep extraction from your resume...")
    extracted = deep_extract_resume(pdf_text)

    if progress_callback:
        progress_callback("✏️ Stage 2/3 — Rewriting with STAR method & power verbs...")
    try:
        raw_rewritten = rewrite_resume_content(extracted)
        rewritten = _safe_merge(raw_rewritten, extracted)
    except Exception:
        rewritten = extracted  # fallback

    if progress_callback:
        progress_callback("✨ Stage 3/3 — Final polish & quality check...")
    try:
        raw_polished = polish_resume(rewritten)
        polished = _safe_merge(raw_polished, rewritten)
    except Exception:
        polished = rewritten  # fallback

    # Final safety check
    if not _validate_resume(polished, extracted):
        polished = _safe_merge(polished, extracted)

    return polished


# ═══════════════════════════════════════════════════════════════════════════
#  MOCK INTERVIEW COACH
# ═══════════════════════════════════════════════════════════════════════════

def research_company_interview_patterns(company: str, role: str, round_name: str) -> str:
    if not company:
        return "No specific company provided. Use standard top-tier tech difficulty."
    prompt = f"""You are an elite Tech Interview Researcher.
Your task is to recall the most heavily tested concepts, common questions, and actual interview patterns for {company} for the {role} position in the '{round_name}' round.
Provide a concise, highly specific 150-word profile of what {company} actually asks. (e.g., if it's Google, mention they heavily test Graphs, DP, and Union Find. If Amazon, mention OOD and LPs).
Return plain text only."""
    try:
        return _call(prompt)
    except Exception:
        return "Failed to fetch company profile. Proceed with standard FAANG difficulty."

def generate_interview_questions(pdf_text: str, job_description: str, company: str, role: str, round_name: str, research_context: str = "") -> list:
    """Generate 5 tailored interview questions based on resume + JD + target company & round."""
    prompt = f"""You are a senior technical interviewer at {company if company else 'a top tech company'} interviewing a candidate for the {role if role else 'Software Engineer'} position.
Based on their resume, the job description, and the typical interview process at {company if company else 'this company'}, generate exactly 5 interview questions for their '{round_name}'.

COMPANY INTERVIEW RESEARCH (Use this to strictly tailor the questions to what this company actually asks!):
{research_context}


GUIDELINES FOR ROUND: '{round_name}'
- If it involves Data Structures & Algorithms (DSA), provide literal Leetcode-style algorithmic problem descriptions. Include the Problem Statement, EXACTLY 3 explicit Examples/Test cases (Example 1, Example 2, Example 3) with Inputs and Outputs, and Constraints.
- If it involves System Design, provide highly scalable architecture questions (e.g., "Design a rate limiter") and specify the exact constraints (e.g., "10M DAU, 500ms latency requirement").
- If it involves Behavioral/Culture Fit, provide deep-dives into their past projects using the STAR method.
- Make the questions difficult, realistic, and highly specific to the candidate's resume and the job description.

For each question, also provide:
- "category": "dsa" | "system_design" | "behavioral" | "technical_deep_dive"
- "what_to_look_for": A brief note on what an optimal answer entails (e.g., O(N) time complexity, consistent hashing, or STAR method).

Return as a JSON array:
[
  {{
    "question": "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\\n\\n**Example 1:**\\nInput: nums = [2,7,11,15], target = 9\\nOutput: [0,1]\\n\\n**Constraints:**\\n- `2 <= nums.length <= 10^4`",
    "category": "dsa",
    "what_to_look_for": "Look for an O(N) solution using a Hash Map instead of an O(N^2) brute force."
  }}
]

Return ONLY a valid JSON array.

Resume:
{pdf_text}

Job Description:
{job_description}
"""
    raw = _call(prompt)
    return _parse_json(raw)


def evaluate_interview_answer(question: str, answer: str, job_description: str, resume_text: str) -> dict:
    """Evaluate a candidate's interview answer."""
    prompt = f"""You are a strict, senior FAANG hiring manager evaluating an interview answer.

Question asked: "{question}"

Candidate's answer (this may be code, system architecture, or text): 
"{answer}"

EVALUATION GUIDELINES:
- If the answer is Code (DSA), act as an automated code judge. Dry-run the code against edge cases. Evaluate Time Complexity and Space Complexity. If there are bugs, point them out explicitly.
- If the answer is System Design, evaluate their choice of database, caching strategy, load balancing, and handling of bottlenecks.
- If the answer is Behavioral, evaluate their use of the STAR method and communication clarity.

Evaluate the answer and return JSON:
{{
  "score": <1-10>,
  "grade": "Excellent" | "Good" | "Average" | "Needs Improvement",
  "strengths": ["what they did well (e.g. good use of hash maps, clear architecture)"],
  "improvements": ["what failed or could be better (e.g. O(N^2) instead of O(N), missed edge case)"],
  "ideal_answer": "Provide the optimal solution (e.g. the optimal code snippet, or the optimal architecture overview)",
  "tip": "One specific, actionable tip for improvement"
}}

Return ONLY valid JSON.
"""
    raw = _call(prompt)
    return _parse_json(raw)


def simulate_code_run(question: str, code: str) -> dict:
    """Simulate Python code execution and return terminal output as JSON."""
    prompt = f"""You are a Python Sandbox execution environment and Code Judge.
You are evaluating a user's code submission for the following problem:
Problem: "{question}"

User Code:
```python
{code}
```

Task: Simulate executing this code against 3 distinct, hidden test cases (including edge cases).
You must output a JSON response that mimics a realistic terminal output, showing the stdout, test case results, and compiler/runtime errors if any.

Return ONLY a valid JSON object matching this schema:
{{
    "status": "Success" | "Syntax Error" | "Runtime Error" | "Wrong Answer",
    "passed": <int from 0 to 3>,
    "total": 3,
    "terminal_output": "A raw string simulating terminal output showing the 3 test cases, actual outputs, and expected outputs. VERY IMPORTANT: Use properly escaped newlines (\\\\n) and escape double quotes so this string does not break JSON parsing."
}}
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
