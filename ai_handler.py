"""
ai_handler.py – All Gemini AI interactions for the ATS Resume Expert app.
"""

import json
import re
import google.generativeai as genai

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
    # Remove ```json ... ``` or ``` ... ```
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


# ─── Resume Optimizer ────────────────────────────────────────────────────────

def optimize_resume_for_jd(resume_data: dict, job_description: str) -> dict:
    """Rewrite resume content to better match the job description."""
    prompt = f"""
You are an elite ATS algorithm expert and a FAANG-level executive resume writer.
Your ONLY goal is to rewrite the provided resume JSON to score an ATS Match of 90%+ against the provided Job Description, while sounding 100% human-written and organic.

YOUR STRATEGY:
1. ATS KEYWORD EXTRACTION: First, deeply analyze the Job Description to find the exact required Hard Skills, Soft Skills, Tools, and Frameworks.
2. SEMANTIC WEAVING (CRITICAL): Do NOT just dump keywords at the bottom. You must surgically inject these EXACT string keywords organically into the candidate's existing Experience bullets, Projects, and Summary. 
3. HARVARD 'STAR' METHOD: Rewrite every single bullet point using the Action-Context-Result framework. Begin with strong power verbs.
4. PRUNING: If a bullet point or project is completely irrelevant to the job description, shorten it or remove it entirely to save space for relevant skills.
5. EXACT MATCHES: If the JD asks for "Object-Oriented Programming (Java)", write "Object-Oriented Programming (Java)", do not rephrase to "Java OOP". ATS scanners are strict.
6. ⚠️ BOUNDARY: NEVER fabricate new jobs, fake dates, or imaginary degrees. You may only creatively reframe and enhance their existing experience to map to the JD.

Return ONLY valid JSON in the exact same schema structure as the input — no markdown, no explanation.

Job Description:
{job_description}

Current Resume JSON:
{json.dumps(resume_data, indent=2)}
"""
    raw = _call(prompt)
    return _parse_json(raw)


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
