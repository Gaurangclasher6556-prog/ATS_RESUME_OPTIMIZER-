# 🔥 Career Forge — AI Resume Optimizer & Interview Coach

Career Forge is a Streamlit web app that helps you beat Applicant Tracking
Systems (ATS) and land interviews. Upload your resume, paste a job description,
and get a **real, reproducible ATS match score**, a multi-pass AI-optimized
resume, a tailored cover letter, batch resume generation, and a full mock
interview with **real code execution**.

## ✨ Features

- **📊 Deterministic ATS Scoring** — your match score comes from a transparent,
  reproducible engine (`ats_scorer.py`), not a fluctuating LLM guess. It blends
  keyword coverage (exact + fuzzy + acronym-aware), TF-IDF semantic similarity,
  hard-skills coverage, ATS formatting checks, and impact/readability — with a
  full per-component breakdown and a visual gauge.
- **🧠 Deep Multi-Pass Optimizer** — a 4-pass pipeline (keyword analysis → STAR
  bullet rewriting → summary & skills polish → ATS audit) with safe-merge
  guarantees so no experience, education, or project is ever lost. Shows a
  **before → after score delta**.
- **🛡️ Fabrication guardrail** — flags any numeric claim the AI added that wasn't
  in your original resume, so you can verify truthfulness.
- **✨ Resume Rebuilder** — turns a rough/scrappy resume into a polished one.
- **🏢 Company Personalizer** — tailors tone and emphasis to a specific company.
- **📝 Cover Letter Generator** — tailored, ATS-friendly letters (DOCX / Markdown),
  selectable tone, no fabrication.
- **🚀 Mass Apply (Batch)** — upload a CSV of jobs, get a ZIP of tailored resumes
  with automatic retry/backoff on rate limits and a per-job score summary.
- **🎤 Mock Interview** — behavioral, coding, and system-design rounds. The coding
  round runs your code **for real** in a sandbox (Piston), falling back to an
  AI-simulated judge only if offline.
- **📈 History** — every score is saved locally (SQLite) so you can track progress.
- **🔗 JD-from-URL** and **OCR fallback** for image-based/scanned PDFs.

## 🛠️ Tech Stack

| Tool | Purpose |
| --- | --- |
| Python + Streamlit | App & UI |
| Google Gemini (+ Groq / OpenRouter fallback) | LLM passes |
| PyMuPDF | PDF text extraction (+ OCR fallback via pytesseract) |
| ReportLab / python-docx | PDF & DOCX generation |
| Piston API | Real sandboxed code execution |
| Standard library only | ATS scoring engine & local history DB |

## 🚀 Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # then add your GOOGLE_API_KEY (Groq/OpenRouter optional)
streamlit run app.py
```

For OCR on scanned PDFs, also install the system `tesseract` binary
(e.g. `brew install tesseract` or `apt-get install tesseract-ocr`).

## 🧪 Tests

```bash
python tests/test_ats_scorer.py     # deterministic scoring engine
python tests/test_ai_handler.py     # JSON parsing, safe-merge, fabrication guardrail
```

## 📂 Project Structure

```
app.py                    Streamlit UI (8 tabs)
ats_scorer.py             Deterministic ATS scoring engine (no LLM, no heavy deps)
ai_handler.py             Gemini/Groq/OpenRouter LLM logic, optimizer, cover letter
resume_knowledge_base.py  Curated RAG-style resume patterns + domain detection
pdf_generator.py          ATS-friendly PDF / DOCX / cover-letter generation
mock_interview_*.py       Mock interview module + AI logic
code_executor.py          Real code execution via Piston API
jd_utils.py               JD-from-URL fetch + PDF text/OCR extraction
database.py               Local SQLite score history
ui_components.py          Reusable SVG/HTML visual components
tests/                    Unit tests
```

© 2026 Career Forge — Created by Gaurang Sharma
