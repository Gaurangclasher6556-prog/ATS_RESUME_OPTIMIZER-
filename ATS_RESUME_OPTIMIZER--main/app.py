import os
from pathlib import Path

# ─── Load .env ───────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)
except ImportError:
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

import streamlit as st
import google.generativeai as genai
import pandas as pd
import zipfile
import io
import time

from ai_handler import (
    get_ats_review,
    extract_resume_structure,
    optimize_resume_deep,
    personalize_for_company,
    rebuild_resume,
    generate_cover_letter,
    detect_fabricated_metrics,
)
from pdf_generator import generate_ats_pdf, generate_ats_docx, generate_cover_letter_docx
import ats_scorer
import ui_components as ui
import jd_utils
import database

# ─── Page Config (MUST be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Career Forge",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Design System ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.5rem; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(165deg, #0b1120 0%, #1e293b 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stTextArea textarea,
[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #e2e8f0 !important;
    border-radius: 8px;
}

/* Header */
.app-header {
    background: linear-gradient(135deg, #16a34a 0%, #15803d 45%, #0f766e 100%);
    padding: 1.8rem 2.5rem;
    border-radius: 18px;
    margin-bottom: 1.4rem;
    box-shadow: 0 10px 40px rgba(22,163,74,0.28);
    text-align: center;
}
.app-header h1 { margin: 0; color: white; font-size: 2.25rem; font-weight: 800; letter-spacing:-0.5px; }
.app-header p  { margin: 0.45rem 0 0; color: rgba(255,255,255,0.9); font-size: 1.02rem; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #16a34a, #15803d) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; padding: 0.6rem 1.4rem !important;
    transition: all 0.2s ease !important; box-shadow: 0 2px 10px rgba(22,163,74,0.3) !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 20px rgba(22,163,74,0.42) !important; }

[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; padding: 0.6rem 1.4rem !important;
}

/* Cards & banners */
.info-banner {
    background: linear-gradient(135deg, rgba(29,78,216,0.07), rgba(13,148,136,0.05));
    border: 1px solid rgba(29,78,216,0.18); border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: 1rem; font-size: 0.92rem; color: #1e40af;
}
.metric-card {
    background: white; border-radius: 14px; padding: 1.2rem;
    border: 1px solid #e2e8f0; box-shadow: 0 4px 18px rgba(0,0,0,0.05);
}
.step-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(22,163,74,0.12); border: 1px solid rgba(22,163,74,0.3);
    border-radius: 20px; padding: 4px 12px; font-size: 0.8rem; font-weight: 600;
    color: #16a34a; margin-bottom: 0.5rem;
}
.stTabs [data-baseweb="tab"] { font-weight: 600; }
.footer { text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 3rem; }
</style>
""", unsafe_allow_html=True)

# ─── API Key ─────────────────────────────────────────────────────────────────
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ **Google API Key not found.** Add `GOOGLE_API_KEY` to your `.env` file.")
    st.stop()
genai.configure(api_key=api_key)
database.init_db()


# ─── File / text helpers ───────────────────────────────────────────────────────
def safe_read_bytes() -> bytes:
    if uploaded_file is None:
        return b""
    uploaded_file.seek(0)
    return uploaded_file.read()


@st.cache_data(show_spinner=False)
def extract_text(file_bytes: bytes) -> str:
    """Extract resume text, with OCR fallback for image-based PDFs."""
    return jd_utils.extract_pdf_text(file_bytes)


@st.cache_data(show_spinner=False)
def get_resume_structure(file_bytes: bytes) -> dict:
    """Parse + cache the structured resume once, reused across all tabs."""
    text = extract_text(file_bytes)
    if not text.strip():
        return {}
    return extract_resume_structure(text)


def render_score(result, key_prefix: str):
    """Render a full ATS score panel (gauge + bars + keywords + tips)."""
    c1, c2 = st.columns([1, 1.3], gap="large")
    with c1:
        st.markdown(ui.score_gauge(result.overall, result.grade), unsafe_allow_html=True)
    with c2:
        st.markdown(ui.component_bars(result.components), unsafe_allow_html=True)
    st.markdown(ui.keyword_chips(result.matched_keywords, result.missing_keywords),
                unsafe_allow_html=True)
    if result.suggestions:
        st.markdown("**🎯 How to improve:**")
        for s in result.suggestions:
            st.markdown(f"- {s}")


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>🔥 Career Forge</h1>
    <p>Analyze · Optimize · Build · Personalize — beat every Applicant Tracking System</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📥 Your Inputs")
    st.markdown("Upload once — use across all tabs.")
    st.markdown("---")

    uploaded_file = st.file_uploader("📎 Upload Resume (PDF)", type=["pdf"],
                                     help="Your resume in PDF format")
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")

    st.markdown("---")
    st.markdown("### 💼 Job Description")
    jd_url = st.text_input("Fetch from URL (optional)", placeholder="https://...job-posting")
    if st.button("🔗 Fetch JD from URL", use_container_width=True):
        if jd_url.strip():
            try:
                with st.spinner("Fetching job description..."):
                    st.session_state["fetched_jd"] = jd_utils.fetch_jd_from_url(jd_url)
                st.success("Fetched! Review below.")
            except Exception as e:
                st.warning(str(e))

    job_description = st.text_area(
        "Paste / edit job description",
        value=st.session_state.get("fetched_jd", ""),
        height=200,
        placeholder="Paste the full job description here...",
    )

    st.markdown("---")
    st.markdown("### 🏢 Target")
    company_name = st.text_input("Company Name", placeholder="e.g. Google, Microsoft...")
    target_role = st.text_input("Target Role", placeholder="e.g. Software Engineer...")

    st.markdown("---")
    st.markdown("<div style='font-size:0.78rem;color:#64748b;'>🔒 Your resume and API key "
                "never leave your machine.</div>", unsafe_allow_html=True)


def need_resume():
    if not uploaded_file:
        st.warning("⬅️ Please upload your resume in the sidebar first.")
        return False
    return True


def need_jd():
    if not job_description.strip():
        st.warning("⬅️ Please paste the job description in the sidebar first.")
        return False
    return True


# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 ATS Analysis",
    "🧠 Deep Optimizer",
    "✨ Resume Rebuilder",
    "🏢 Company Personalizer",
    "📝 Cover Letter",
    "🚀 Mass Apply (Batch)",
    "🎤 Mock Interview",
    "📈 History",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ATS ANALYSIS (real deterministic score + optional AI review)
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 📊 ATS Score & Review")
    st.markdown('<div class="info-banner">⚙️ <b>Deterministic scoring engine</b> — your match '
                'score is computed by a transparent, reproducible algorithm (keyword coverage, '
                'semantic similarity, skills, formatting, and impact), <b>not</b> a fluctuating '
                'LLM guess. Same inputs always give the same score.</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        if st.button("📊 Compute ATS Match Score", use_container_width=True, key="btn_score"):
            if need_resume() and need_jd():
                try:
                    with st.spinner("Scoring your resume..."):
                        structure = get_resume_structure(safe_read_bytes())
                        target = structure if structure else extract_text(safe_read_bytes())
                        result = ats_scorer.score_resume(target, job_description)
                        st.session_state["ats_result"] = result
                        database.log_score(
                            candidate=(structure or {}).get("name", ""),
                            company=company_name, role=target_role,
                            mode="analysis", score=result.overall,
                            detail=result.grade,
                        )
                except Exception as e:
                    st.error(str(e))
    with col2:
        if st.button("🤖 Get AI Qualitative Review", use_container_width=True, key="btn_review"):
            if need_resume() and need_jd():
                try:
                    with st.spinner("Generating AI review..."):
                        text = extract_text(safe_read_bytes())
                        if not text.strip():
                            st.error("❌ Could not extract text from this PDF.")
                        else:
                            st.session_state["review_result"] = get_ats_review(text, job_description)
                except Exception as e:
                    st.error(str(e))

    if "ats_result" in st.session_state:
        with st.container(border=True):
            st.markdown("#### 📈 ATS Compatibility Report")
            render_score(st.session_state["ats_result"], "analysis")

    if "review_result" in st.session_state:
        with st.container(border=True):
            st.markdown("#### 📝 AI Qualitative Evaluation")
            st.markdown(st.session_state["review_result"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DEEP OPTIMIZER (with before/after delta + fabrication check)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🧠 Deep Multi-Pass Optimizer")
    st.markdown('<div class="info-banner">🚀 <b>4-Pass AI Pipeline</b> — Keyword Extraction → '
                'Bullet-by-Bullet STAR Rewriting → Summary & Skills Polish → Final ATS Audit. '
                'Every line gets individual attention, then we re-score to show your real gain.</div>',
                unsafe_allow_html=True)

    if st.button("⚡ Deep Optimize My Resume", use_container_width=True, key="btn_deep_optimize"):
        if need_resume() and need_jd():
            try:
                status = st.status("🔄 Running 4-Pass Deep Optimization...", expanded=True)
                with status:
                    st.write("📖 Parsing your resume structure...")
                    resume_data = get_resume_structure(safe_read_bytes())
                    progress = st.empty()
                    optimized = optimize_resume_deep(
                        resume_data, job_description,
                        progress_callback=lambda m: progress.write(m),
                    )
                    st.write("📄 Generating PDF and DOCX files...")
                    pdf_out, docx_out = generate_ats_pdf(optimized), generate_ats_docx(optimized)
                    st.write("📊 Re-scoring before vs after...")
                    delta = ats_scorer.score_delta(resume_data, optimized, job_description)
                    status.update(label="✅ Deep Optimization complete — 4/4 passes done!",
                                  state="complete")

                st.session_state.update({
                    "opt_data": optimized, "opt_pdf": pdf_out, "opt_docx": docx_out,
                    "orig_data": resume_data, "opt_delta": delta,
                    "opt_fab": detect_fabricated_metrics(resume_data, optimized),
                })
                database.log_score(candidate=optimized.get("name", ""), company=company_name,
                                   role=target_role, mode="optimizer",
                                   score=delta["after"], delta=delta["delta"])
            except Exception as e:
                st.error(str(e))

    if "opt_data" in st.session_state:
        opt = st.session_state["opt_data"]
        st.success("🎉 Your deep-optimized resume is ready!")

        if "opt_delta" in st.session_state:
            d = st.session_state["opt_delta"]
            st.markdown(ui.delta_badge(d["before"], d["after"]), unsafe_allow_html=True)
            with st.expander("📊 Full after-optimization breakdown", expanded=False):
                render_score(d["after_result"], "opt")

        if st.session_state.get("opt_fab"):
            st.warning("🛡️ **Fabrication guardrail:** these numbers appear in the optimized "
                       "resume but not the original — please verify they're truthful before "
                       f"using: `{', '.join(st.session_state['opt_fab'])}`")

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("⬇️ Download Optimized PDF", data=st.session_state["opt_pdf"],
                               file_name=f"optimized_resume_{opt.get('name','').replace(' ','_')}.pdf",
                               mime="application/pdf", use_container_width=True)
        with dl2:
            st.download_button("⬇️ Download Optimized DOCX", data=st.session_state["opt_docx"],
                               file_name=f"optimized_resume_{opt.get('name','').replace(' ','_')}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)

        with st.expander("👁️ Before vs After — Key Changes", expanded=True):
            orig = st.session_state.get("orig_data", {})
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📋 Original Summary**")
                st.info(orig.get("summary", "—") or "—")
            with c2:
                st.markdown("**✅ Optimized Summary**")
                st.success(opt.get("summary", "—") or "—")
            if opt.get("experience"):
                st.markdown("---")
                c3, c4 = st.columns(2)
                orig_exp = orig.get("experience", [{}])
                with c3:
                    st.markdown("**📋 Original Bullets** *(first role)*")
                    if orig_exp and orig_exp[0].get("bullets"):
                        for b in orig_exp[0]["bullets"][:4]:
                            st.markdown(f"• {b}")
                with c4:
                    st.markdown("**✅ Optimized Bullets** *(first role)*")
                    for b in opt["experience"][0].get("bullets", [])[:4]:
                        st.markdown(f"• {b}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESUME REBUILDER
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ✨ Resume Rebuilder — Scrappy to Perfect")
    st.markdown('<div class="info-banner">🔮 <b>3-Stage AI Pipeline</b> — Deep Extraction → '
                'Complete STAR Rewrite → Professional Polish. Give us your roughest resume; '
                'get back a near-perfect, ATS-optimized one.</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-badge">💡 No job description needed</div>', unsafe_allow_html=True)

    if st.button("✨ Rebuild My Resume", use_container_width=True, key="btn_rebuild"):
        if need_resume():
            try:
                status = st.status("🔄 Running 3-Stage Resume Rebuild...", expanded=True)
                with status:
                    text = extract_text(safe_read_bytes())
                    progress = st.empty()
                    rebuilt = rebuild_resume(text, progress_callback=lambda m: progress.write(m))
                    st.write("📄 Generating PDF and DOCX files...")
                    pdf_out, docx_out = generate_ats_pdf(rebuilt), generate_ats_docx(rebuilt)
                    status.update(label="✅ Resume rebuilt — 3/3 stages done!", state="complete")
                st.session_state.update({"build_data": rebuilt, "build_pdf": pdf_out,
                                         "build_docx": docx_out})
            except Exception as e:
                st.error(str(e))

    if "build_data" in st.session_state:
        data = st.session_state["build_data"]
        st.success(f"🎉 Resume rebuilt for **{data.get('name', 'you')}**!")
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("⬇️ Download Rebuilt PDF", data=st.session_state["build_pdf"],
                               file_name=f"rebuilt_resume_{data.get('name','').replace(' ','_')}.pdf",
                               mime="application/pdf", use_container_width=True)
        with dl2:
            st.download_button("⬇️ Download Rebuilt DOCX", data=st.session_state["build_docx"],
                               file_name=f"rebuilt_resume_{data.get('name','').replace(' ','_')}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)
        with st.expander("👁️ Rebuilt Resume Preview", expanded=True):
            st.markdown("**✍️ Professional Summary:**")
            st.success(data.get("summary", "—") or "—")
            if data.get("experience"):
                exp = data["experience"][0]
                st.markdown(f"**💼 {exp.get('title', '')}** at **{exp.get('company', '')}**")
                for b in exp.get("bullets", [])[:5]:
                    st.markdown(f"• {b}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COMPANY PERSONALIZER
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🏢 Company-Specific Personalizer")
    st.markdown('<div class="info-banner">🎯 Generate a uniquely tailored resume for each company. '
                'The AI adapts your language, emphasis, and bullets to match the company culture, '
                'then we re-score the result.</div>', unsafe_allow_html=True)

    if not company_name or not target_role:
        st.info("⬅️ Fill in **Company Name** and **Target Role** in the sidebar to get started.")
    else:
        st.markdown(f"**Target:** `{target_role}` at **{company_name}**")

    if st.button(f"🎯 Personalize for {company_name or 'Company'}", use_container_width=True,
                 key="btn_personalize"):
        if need_resume() and need_jd():
            if not company_name.strip() or not target_role.strip():
                st.warning("⬅️ Please fill in Company Name and Target Role in the sidebar.")
            else:
                try:
                    with st.status(f"🔄 Tailoring your resume for {company_name}...",
                                   expanded=True) as status:
                        st.write("📖 Parsing your resume...")
                        resume_data = get_resume_structure(safe_read_bytes())
                        st.write(f"🏢 Personalizing for {company_name}...")
                        personalized = personalize_for_company(resume_data, job_description,
                                                               company_name, target_role)
                        st.write("📄 Generating tailored PDF and DOCX...")
                        pdf_out, docx_out = generate_ats_pdf(personalized), generate_ats_docx(personalized)
                        result = ats_scorer.score_resume(personalized, job_description)
                        status.update(label=f"✅ Tailored for {company_name}!", state="complete")
                    st.session_state.update({
                        "pers_data": personalized, "pers_pdf": pdf_out, "pers_docx": docx_out,
                        "pers_co": company_name, "pers_role": target_role, "pers_score": result,
                    })
                    database.log_score(candidate=personalized.get("name", ""),
                                       company=company_name, role=target_role,
                                       mode="personalizer", score=result.overall)
                except Exception as e:
                    st.error(str(e))

    if "pers_data" in st.session_state:
        pers = st.session_state["pers_data"]
        co, role = st.session_state.get("pers_co", company_name), st.session_state.get("pers_role", target_role)
        st.success(f"🎉 Resume personalized for **{role}** at **{co}**!")
        if "pers_score" in st.session_state:
            st.markdown(ui.score_gauge(st.session_state["pers_score"].overall,
                                       st.session_state["pers_score"].grade), unsafe_allow_html=True)
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(f"⬇️ Download {co} Resume PDF", data=st.session_state["pers_pdf"],
                               file_name=f"resume_{pers.get('name','').replace(' ','_')}_{co.replace(' ','_')}.pdf",
                               mime="application/pdf", use_container_width=True)
        with dl2:
            st.download_button(f"⬇️ Download {co} Resume DOCX", data=st.session_state["pers_docx"],
                               file_name=f"resume_{pers.get('name','').replace(' ','_')}_{co.replace(' ','_')}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)
        with st.expander("👁️ Preview Personalized Summary", expanded=True):
            st.success(pers.get("summary", "—"))

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — COVER LETTER (new)
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 📝 AI Cover Letter Generator")
    st.markdown('<div class="info-banner">✍️ Generate a tailored, ATS-friendly cover letter that '
                'mirrors the job description and pulls real, quantified achievements from your '
                'resume — no generic templates, no fabrication.</div>', unsafe_allow_html=True)

    tone = st.selectbox("Tone", ["Professional", "Enthusiastic", "Concise & Direct",
                                 "Warm & Personable", "Confident & Bold"], index=0)
    if st.button("📝 Generate Cover Letter", use_container_width=True, key="btn_cover"):
        if need_resume() and need_jd():
            try:
                with st.spinner("Writing your cover letter..."):
                    resume_data = get_resume_structure(safe_read_bytes())
                    letter = generate_cover_letter(resume_data, job_description,
                                                   company_name, target_role, tone)
                    st.session_state["cover_letter"] = letter
                    st.session_state["cover_name"] = resume_data.get("name", "")
            except Exception as e:
                st.error(str(e))

    if "cover_letter" in st.session_state:
        st.markdown("---")
        edited = st.text_area("Your cover letter (editable):",
                              value=st.session_state["cover_letter"], height=380)
        name = st.session_state.get("cover_name", "")
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("⬇️ Download as DOCX",
                               data=generate_cover_letter_docx(edited, name),
                               file_name=f"cover_letter_{name.replace(' ','_')}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)
        with dl2:
            st.download_button("⬇️ Download as Markdown", data=edited.encode("utf-8"),
                               file_name=f"cover_letter_{name.replace(' ','_')}.md",
                               mime="text/markdown", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — MASS APPLY (BATCH) with retry/backoff
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("### 🚀 Mass Apply (Batch Optimizer)")
    st.markdown('<div class="info-banner">⚡ Upload a CSV of jobs and get a ZIP of resumes tailored '
                'to every one. Now with automatic retry/backoff on rate limits and a per-job '
                'ATS score summary.</div>', unsafe_allow_html=True)

    if not uploaded_file:
        st.info("⬅️ Please upload your **Base Resume (PDF)** in the sidebar first.")
    else:
        st.markdown("**1. Download the CSV Template**")
        batch_template = pd.DataFrame([
            {"Company": "Apple", "Role": "AI Engineer", "Job Description": "Paste the full Apple JD here..."},
            {"Company": "Microsoft", "Role": "Software Engineer", "Job Description": "Paste the full Microsoft JD here..."},
        ])
        st.download_button("⬇️ Download CSV Template", data=batch_template.to_csv(index=False),
                           file_name="batch_jobs_template.csv", mime="text/csv")

        st.markdown("**2. Upload your filled CSV**")
        csv_file = st.file_uploader("Upload Jobs CSV", type=["csv"],
                                    help="Must contain: Company, Role, Job Description")

        if csv_file:
            df = pd.read_csv(csv_file)
            st.success(f"✅ Loaded {len(df)} jobs.")
            st.dataframe(df.head(3))

            if st.button("🚀 Start Batch Optimization", use_container_width=True, type="primary"):
                required = ["Company", "Role", "Job Description"]
                if not all(c in df.columns for c in required):
                    st.error(f"❌ CSV must have exactly: {', '.join(required)}")
                else:
                    zip_buffer = io.BytesIO()
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    summary_rows = []
                    try:
                        status_text.write("📖 Parsing your base resume...")
                        base_resume_data = get_resume_structure(safe_read_bytes())

                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                            for index, row in df.iterrows():
                                co, role = str(row["Company"]).strip(), str(row["Role"]).strip()
                                jd = str(row["Job Description"]).strip()
                                status_text.write(f"⚙️ Optimizing {index+1}/{len(df)}: **{role}** at **{co}**...")

                                # Retry with exponential backoff on transient/rate-limit errors.
                                tailored = None
                                for attempt in range(4):
                                    try:
                                        tailored = personalize_for_company(base_resume_data, jd, co, role)
                                        break
                                    except Exception as err:
                                        if attempt == 3:
                                            raise
                                        wait = 4 * (2 ** attempt)
                                        status_text.write(f"⏳ Rate limited, retrying in {wait}s...")
                                        time.sleep(wait)

                                pdf_out = generate_ats_pdf(tailored)
                                score = ats_scorer.score_resume(tailored, jd).overall
                                summary_rows.append({"Company": co, "Role": role, "ATS Score": score})
                                safe_co = co.replace(" ", "_")
                                safe_role = role.replace(" ", "_").replace("/", "-")
                                zf.writestr(f"Resume_{safe_co}_{safe_role}.pdf", pdf_out)
                                progress_bar.progress((index + 1) / len(df))
                                if index < len(df) - 1:
                                    time.sleep(4)

                        status_text.write("✅ All resumes generated and zipped!")
                        if summary_rows:
                            st.dataframe(pd.DataFrame(summary_rows))
                        st.download_button("📥 Download All Tailored Resumes (ZIP)",
                                           data=zip_buffer.getvalue(),
                                           file_name="Tailored_Resumes_Batch.zip",
                                           mime="application/zip", use_container_width=True)
                    except Exception as e:
                        st.error(str(e))

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — MOCK INTERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    import mock_interview_module
    mock_interview_module.render_mock_interview_tab(
        company_name=company_name, target_role=target_role,
        job_description=job_description, need_resume_fn=need_resume,
        need_jd_fn=need_jd, safe_read_bytes_fn=safe_read_bytes,
        extract_text_fn=extract_text,
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — HISTORY (new)
# ══════════════════════════════════════════════════════════════════════════════
with tab8:
    st.markdown("### 📈 Your Score History")
    st.markdown('<div class="info-banner">📊 Every analysis and optimization is saved locally so '
                'you can track your ATS progress over time.</div>', unsafe_allow_html=True)

    history = database.get_history()
    if not history:
        st.info("No history yet — run an ATS analysis or optimization to start tracking.")
    else:
        hist_df = pd.DataFrame(history)[
            ["created_at", "candidate", "company", "role", "mode", "score", "delta", "detail"]
        ]
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
        chart_df = hist_df[::-1].reset_index(drop=True)[["score"]]
        if len(chart_df) > 1:
            st.line_chart(chart_df, height=240)
        if st.button("🗑️ Clear History"):
            database.clear_history()
            st.rerun()

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:2rem 0 1rem;">
    <p>© 2026 Career Forge &nbsp;|&nbsp; Created by Gaurang Sharma</p>
</div>
""", unsafe_allow_html=True)
