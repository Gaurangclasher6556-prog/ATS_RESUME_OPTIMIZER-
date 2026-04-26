import os
from pathlib import Path

# ─── Load .env ───────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
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
import fitz  # PyMuPDF
import google.generativeai as genai
import pandas as pd
import zipfile
import io
import time
from ai_handler import (
    get_ats_review, get_ats_score,
    extract_resume_structure,
    optimize_resume_deep,
    personalize_for_company,
    rebuild_resume,
    generate_interview_questions,
    evaluate_interview_answer,
    generate_interview_report,
)
from pdf_generator import generate_ats_pdf, generate_ats_docx

# ─── Page Config (MUST be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="ATS Resume Expert Pro",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stTextArea textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
    border-radius: 8px;
}

/* Header */
.app-header {
    background: linear-gradient(135deg, #16a34a 0%, #15803d 50%, #166534 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(22,163,74,0.25);
    text-align: center;
}
.app-header h1 { margin: 0; color: white; font-size: 2.2rem; font-weight: 700; }
.app-header p  { margin: 0.4rem 0 0; color: rgba(255,255,255,0.85); font-size: 1rem; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #16a34a, #15803d) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 2px 8px rgba(22,163,74,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(22,163,74,0.4) !important;
}

/* Download buttons */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 2px 8px rgba(29,78,216,0.3) !important;
}
[data-testid="stDownloadButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(29,78,216,0.4) !important;
}

/* Step badges */
.step-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(22,163,74,0.12); border: 1px solid rgba(22,163,74,0.3);
    border-radius: 20px; padding: 4px 12px;
    font-size: 0.8rem; font-weight: 600; color: #16a34a;
    margin-bottom: 0.5rem;
}

/* Result card */
.result-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    border-left: 4px solid #16a34a;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    margin-top: 1rem;
}

/* Info banner */
.info-banner {
    background: linear-gradient(135deg, rgba(29,78,216,0.08), rgba(29,78,216,0.04));
    border: 1px solid rgba(29,78,216,0.2);
    border-radius: 10px; padding: 1rem 1.2rem;
    margin-bottom: 1rem; font-size: 0.9rem; color: #1e40af;
}

/* Footer */
.footer { text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 3rem; }
</style>
""", unsafe_allow_html=True)

# ─── API Key ─────────────────────────────────────────────────────────────────
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ **Google API Key not found.** Add `GOOGLE_API_KEY` to your `.env` file.")
    st.stop()
genai.configure(api_key=api_key)

# ─── PDF Text Extractor (cached) ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def extract_text(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "".join(page.get_text() for page in doc)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>📄 ATS Resume Expert Pro</h1>
    <p>Analyze · Optimize · Build · Personalize — Beat every Applicant Tracking System</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📥 Your Inputs")
    st.markdown("Upload once — use across all tabs.")
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "📎 Upload Resume (PDF)",
        type=["pdf"],
        help="Your resume in PDF format",
    )
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")

    st.markdown("---")
    job_description = st.text_area(
        "💼 Job Description",
        height=220,
        placeholder="Paste the full job description here...",
        help="Required for ATS analysis, optimization, and personalization.",
    )

    st.markdown("---")
    st.markdown("### 🏢 Company Personalizer")
    company_name = st.text_input("Company Name", placeholder="e.g. Google, Microsoft...")
    target_role  = st.text_input("Target Role",  placeholder="e.g. Software Engineer...")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.78rem;color:#64748b;'>🔒 Your resume and API key never leave your machine.</div>",
        unsafe_allow_html=True,
    )

# ─── Helper: require inputs ───────────────────────────────────────────────────
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 ATS Analysis",
    "🧠 Deep Optimizer",
    "✨ Resume Rebuilder",
    "🏢 Company Personalizer",
    "🚀 Mass Apply (Batch)",
    "🎤 Mock Interview",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ATS ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 📊 ATS Score & Review")
    st.markdown(
        '<div class="info-banner">🤖 Get an instant AI-powered review and ATS match score '
        'for your resume against the job description.</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        if st.button("🔍 Get Detailed Review", use_container_width=True, key="btn_review"):
            if need_resume() and need_jd():
                try:
                    with st.spinner("Analyzing your resume..."):
                        pdf_text = extract_text(uploaded_file.read())
                        result = get_ats_review(pdf_text, job_description)
                    st.session_state["review_result"] = result
                except Exception as e:
                    st.error(str(e))

    with col2:
        if st.button("📊 Check ATS Match Score", use_container_width=True, key="btn_score"):
            if need_resume() and need_jd():
                try:
                    with st.spinner("Calculating ATS match score..."):
                        pdf_text = extract_text(uploaded_file.read())
                        result = get_ats_score(pdf_text, job_description)
                    st.session_state["score_result"] = result
                except Exception as e:
                    st.error(str(e))

    if "review_result" in st.session_state:
        with st.container(border=True):
            st.markdown("### 📝 Professional Evaluation")
            st.markdown(st.session_state["review_result"])

    if "score_result" in st.session_state:
        with st.container(border=True):
            st.markdown("### 📈 ATS Compatibility Report")
            st.markdown(st.session_state["score_result"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DEEP MULTI-PASS OPTIMIZER (RAG-ENHANCED)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🧠 Deep Multi-Pass Optimizer")
    st.markdown(
        '<div class="info-banner">🚀 <b>4-Pass AI Pipeline</b> — Unlike basic optimizers, '
        'our system runs your resume through 4 specialized AI passes: '
        'Keyword Extraction → Bullet-by-Bullet STAR Rewriting → Summary & Skills Polish '
        '→ Final ATS Audit. Every single line gets individual attention, powered by a '
        'knowledge base of proven FAANG resume patterns.</div>',
        unsafe_allow_html=True,
    )

    if st.button("⚡ Deep Optimize My Resume", use_container_width=True, key="btn_deep_optimize"):
        if need_resume() and need_jd():
            pdf_bytes = uploaded_file.read()
            try:
                status_container = st.status("🔄 Running 4-Pass Deep Optimization...", expanded=True)
                with status_container:
                    st.write("📖 Parsing your resume structure...")
                    pdf_text = extract_text(pdf_bytes)
                    resume_data = extract_resume_structure(pdf_text)

                    progress_placeholder = st.empty()

                    def update_progress(msg):
                        progress_placeholder.write(msg)

                    optimized = optimize_resume_deep(
                        resume_data, job_description,
                        progress_callback=update_progress,
                    )

                    st.write("📄 Generating PDF and DOCX files...")
                    pdf_out  = generate_ats_pdf(optimized)
                    docx_out = generate_ats_docx(optimized)
                    status_container.update(label="✅ Deep Optimization complete — 4/4 passes done!", state="complete")

                st.session_state["opt_data"]  = optimized
                st.session_state["opt_pdf"]   = pdf_out
                st.session_state["opt_docx"]  = docx_out
                st.session_state["orig_data"] = resume_data
            except Exception as e:
                st.error(str(e))

    if "opt_data" in st.session_state:
        opt  = st.session_state["opt_data"]
        orig = st.session_state.get("orig_data", {})

        st.success("🎉 Your deep-optimized resume is ready!")

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "⬇️ Download Optimized PDF",
                data=st.session_state["opt_pdf"],
                file_name=f"optimized_resume_{opt.get('name','').replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                "⬇️ Download Optimized DOCX",
                data=st.session_state["opt_docx"],
                file_name=f"optimized_resume_{opt.get('name','').replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        # Preview changes — before vs after
        with st.expander("👁️ Before vs After — Key Changes", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📋 Original Summary**")
                st.info(orig.get("summary", "—") or "—")
            with c2:
                st.markdown("**✅ Optimized Summary**")
                st.success(opt.get("summary", "—") or "—")

            st.markdown("---")

            if opt.get("experience"):
                c3, c4 = st.columns(2)
                orig_exp = orig.get("experience", [{}])
                with c3:
                    st.markdown("**📋 Original Bullets** *(first role)*")
                    if orig_exp and orig_exp[0].get("bullets"):
                        for b in orig_exp[0]["bullets"][:4]:
                            st.markdown(f"• {b}")
                    else:
                        st.markdown("*No original bullets available*")
                with c4:
                    st.markdown("**✅ Optimized Bullets** *(first role)*")
                    for b in opt["experience"][0].get("bullets", [])[:4]:
                        st.markdown(f"• {b}")

            st.markdown("---")

            # Skills comparison
            if opt.get("skills"):
                st.markdown("**✅ Optimized Skills**")
                skills = opt["skills"]
                if isinstance(skills, dict):
                    for cat, lst in skills.items():
                        sk = ", ".join(lst) if isinstance(lst, list) else str(lst)
                        st.markdown(f"**{cat}:** {sk}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESUME REBUILDER (Scrappy → Perfect)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ✨ Resume Rebuilder — Scrappy to Perfect")
    st.markdown(
        '<div class="info-banner">🔮 <b>3-Stage AI Pipeline</b> — Give us your worst, '
        'most basic, or poorly written resume. Our AI runs it through 3 specialized stages: '
        'Deep Extraction → Complete STAR Rewrite → Professional Polish. '
        'Output: a near-perfect, ATS-optimized resume ready to impress.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="step-badge">💡 No job description needed — this rebuilds your resume from scratch</div>',
        unsafe_allow_html=True,
    )

    if st.button("✨ Rebuild My Resume", use_container_width=True, key="btn_rebuild"):
        if need_resume():
            pdf_bytes = uploaded_file.read()
            try:
                status_container = st.status("🔄 Running 3-Stage Resume Rebuild...", expanded=True)
                with status_container:
                    pdf_text = extract_text(pdf_bytes)

                    progress_placeholder = st.empty()

                    def rebuild_progress(msg):
                        progress_placeholder.write(msg)

                    rebuilt = rebuild_resume(pdf_text, progress_callback=rebuild_progress)

                    st.write("📄 Generating PDF and DOCX files...")
                    pdf_out  = generate_ats_pdf(rebuilt)
                    docx_out = generate_ats_docx(rebuilt)
                    status_container.update(label="✅ Resume rebuilt — 3/3 stages done!", state="complete")

                st.session_state["build_data"] = rebuilt
                st.session_state["build_pdf"]  = pdf_out
                st.session_state["build_docx"] = docx_out
            except Exception as e:
                st.error(str(e))

    if "build_data" in st.session_state:
        data = st.session_state["build_data"]
        st.success(f"🎉 Resume rebuilt for **{data.get('name', 'you')}** — from scrappy to professional!")

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "⬇️ Download Rebuilt PDF",
                data=st.session_state["build_pdf"],
                file_name=f"rebuilt_resume_{data.get('name','').replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                "⬇️ Download Rebuilt DOCX",
                data=st.session_state["build_docx"],
                file_name=f"rebuilt_resume_{data.get('name','').replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        with st.expander("👁️ Rebuilt Resume Preview", expanded=True):
            st.markdown(f"**✍️ Professional Summary:**")
            st.success(data.get("summary", "—") or "—")

            if data.get("experience"):
                st.markdown("**💼 Experience Highlights** *(first role)*")
                exp = data["experience"][0]
                st.markdown(f"**{exp.get('title', '')}** at **{exp.get('company', '')}**")
                for b in exp.get("bullets", [])[:5]:
                    st.markdown(f"• {b}")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**👤 Name:** {data.get('name','—')}")
                st.markdown(f"**📧 Email:** {data.get('email','—')}")
                st.markdown(f"**🎓 Education:** {len(data.get('education',[]))} entry/entries")
            with col_b:
                st.markdown(f"**💼 Experience:** {len(data.get('experience',[]))} role(s)")
                st.markdown(f"**🚀 Projects:** {len(data.get('projects',[]))} project(s)")
                skills = data.get("skills", {})
                skill_count = sum(len(v) for v in skills.values()) if isinstance(skills, dict) else len(skills)
                st.markdown(f"**🛠️ Skills:** {skill_count} skill(s)")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COMPANY PERSONALIZER
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🏢 Company-Specific Personalizer")
    st.markdown(
        '<div class="info-banner">🎯 Generate a uniquely tailored resume for each company you apply to. '
        'The AI adapts your language, emphasis, and bullet points to match each company\'s '
        'culture and expectations. Perfect for Google, Microsoft, startups, and more.</div>',
        unsafe_allow_html=True,
    )

    if not company_name or not target_role:
        st.info("⬅️ Fill in **Company Name** and **Target Role** in the sidebar to get started.")
    else:
        st.markdown(f"**Target:** `{target_role}` at **{company_name}**")

    if st.button(f"🎯 Personalize for {company_name or 'Company'}", use_container_width=True, key="btn_personalize"):
        if need_resume() and need_jd():
            if not company_name.strip() or not target_role.strip():
                st.warning("⬅️ Please fill in Company Name and Target Role in the sidebar.")
            else:
                pdf_bytes = uploaded_file.read()
                try:
                    with st.status(f"🔄 Tailoring your resume for {company_name}...", expanded=True) as status:
                        st.write("📖 Step 1 / 3 — Parsing your resume...")
                        pdf_text    = extract_text(pdf_bytes)
                        resume_data = extract_resume_structure(pdf_text)
                        st.write(f"🏢 Step 2 / 3 — Personalizing for {company_name}...")
                        personalized = personalize_for_company(
                            resume_data, job_description, company_name, target_role
                        )
                        st.write("📄 Step 3 / 3 — Generating tailored PDF and DOCX...")
                        pdf_out  = generate_ats_pdf(personalized)
                        docx_out = generate_ats_docx(personalized)
                        status.update(label=f"✅ Tailored for {company_name}!", state="complete")

                    st.session_state["pers_data"] = personalized
                    st.session_state["pers_pdf"]  = pdf_out
                    st.session_state["pers_docx"] = docx_out
                    st.session_state["pers_co"]   = company_name
                    st.session_state["pers_role"] = target_role
                except Exception as e:
                    st.error(str(e))

    if "pers_data" in st.session_state:
        pers = st.session_state["pers_data"]
        co   = st.session_state.get("pers_co", company_name)
        role = st.session_state.get("pers_role", target_role)

        st.success(f"🎉 Resume personalized for **{role}** at **{co}**!")

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                f"⬇️ Download {co} Resume PDF",
                data=st.session_state["pers_pdf"],
                file_name=f"resume_{pers.get('name','').replace(' ','_')}_{co.replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                f"⬇️ Download {co} Resume DOCX",
                data=st.session_state["pers_docx"],
                file_name=f"resume_{pers.get('name','').replace(' ','_')}_{co.replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        with st.expander("👁️ Preview Personalized Summary", expanded=True):
            st.markdown(f"**✍️ Tailored Summary for {co}:**")
            st.success(pers.get("summary", "—"))
            if pers.get("experience"):
                st.markdown(f"**💼 Top Bullet Points (Role 1, tailored for {co}):**")
                for b in pers["experience"][0].get("bullets", [])[:4]:
                    st.markdown(f"• {b}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MASS APPLY (BATCH MODE)
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 🚀 Mass Apply (Batch Optimizer)")
    st.markdown(
        '<div class="info-banner">⚡ Apply to 100 jobs effortlessly. Upload a CSV of jobs, and our AI will automatically '
        'tailor your resume for EVERY single one of them. You get a single ZIP file containing all your perfected PDFs!</div>',
        unsafe_allow_html=True,
    )

    if not uploaded_file:
        st.info("⬅️ Please upload your **Base Resume (PDF)** in the sidebar first.")
    else:
        st.markdown("**1. Download the CSV Template**")
        batch_template = pd.DataFrame([{
            "Company": "Apple",
            "Role": "AI Engineer",
            "Job Description": "Paste the full Apple JD here..."
        }, {
            "Company": "Microsoft",
            "Role": "Software Engineer",
            "Job Description": "Paste the full Microsoft JD here..."
        }])
        st.download_button("⬇️ Download CSV Template", data=batch_template.to_csv(index=False), file_name="batch_jobs_template.csv", mime="text/csv")

        st.markdown("**2. Upload your filled CSV**")
        csv_file = st.file_uploader("Upload Jobs CSV", type=["csv"], help="Must contain: Company, Role, Job Description")

        if csv_file:
            df = pd.read_csv(csv_file)
            st.success(f"✅ Loaded {len(df)} jobs.")
            st.dataframe(df.head(3))

            if st.button("🚀 Start Batch Optimization", use_container_width=True, type="primary"):
                pdf_bytes = uploaded_file.read()
                
                # Check column names
                required = ["Company", "Role", "Job Description"]
                if not all(c in df.columns for c in required):
                    st.error(f"❌ Your CSV is missing required columns. It must exactly have: {', '.join(required)}")
                else:
                    zip_buffer = io.BytesIO()
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # 1. Parse base resume once
                        status_text.write("📖 Parsing your base resume...")
                        pdf_text = extract_text(pdf_bytes)
                        base_resume_data = extract_resume_structure(pdf_text)
                        
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for index, row in df.iterrows():
                                co = str(row["Company"]).strip()
                                role = str(row["Role"]).strip()
                                jd = str(row["Job Description"]).strip()
                                
                                status_text.write(f"⚙️ Optimizing {index+1}/{len(df)}: **{role}** at **{co}**...")
                                
                                # Personalize exactly like Tab 4
                                tailored_data = personalize_for_company(base_resume_data, jd, co, role)
                                
                                # Generate PDF bytes
                                pdf_out = generate_ats_pdf(tailored_data)
                                
                                # Save to zip
                                safe_co = co.replace(" ", "_")
                                safe_role = role.replace(" ", "_").replace("/", "-")
                                zip_file.writestr(f"Resume_{safe_co}_{safe_role}.pdf", pdf_out)
                                
                                progress_bar.progress((index + 1) / len(df))
                                
                                # Respect limit roughly 15 RPM = 4 seconds per req. 
                                # Personalize uses 1 req. But we want to be safe for 15 RPM.
                                if index < len(df) - 1:
                                    time.sleep(4)
                        
                        status_text.write("✅ All resumes successfully generated and zipped!")
                        
                        st.download_button(
                            label="📥 Download All Tailored Resumes (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name="Tailored_Resumes_Batch.zip",
                            mime="application/zip",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(str(e))

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — MOCK INTERVIEW COACH
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("### 🎤 AI Mock Interview Coach")
    st.markdown(
        '<div class="info-banner">🎯 Practice makes perfect! Our AI generates '
        'tailored interview questions based on the job description and your resume, '
        'then evaluates your answers with detailed feedback and scoring. '
        'Get an ideal answer example for each question.</div>',
        unsafe_allow_html=True,
    )

    # Initialize session state for interview
    if "interview_questions" not in st.session_state:
        st.session_state["interview_questions"] = None
    if "interview_current_q" not in st.session_state:
        st.session_state["interview_current_q"] = 0
    if "interview_results" not in st.session_state:
        st.session_state["interview_results"] = []
    if "interview_pdf_text" not in st.session_state:
        st.session_state["interview_pdf_text"] = ""

    # Step 1: Generate questions
    if st.session_state["interview_questions"] is None:
        if st.button("🎤 Start Mock Interview", use_container_width=True, key="btn_interview"):
            if need_resume() and need_jd():
                try:
                    with st.spinner("🤖 Preparing your interview questions..."):
                        pdf_text = extract_text(uploaded_file.read())
                        st.session_state["interview_pdf_text"] = pdf_text
                        questions = generate_interview_questions(pdf_text, job_description)
                        st.session_state["interview_questions"] = questions
                        st.session_state["interview_current_q"] = 0
                        st.session_state["interview_results"] = []
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
    else:
        questions = st.session_state["interview_questions"]
        current_q = st.session_state["interview_current_q"]
        results = st.session_state["interview_results"]

        # Progress bar
        total = len(questions)
        answered = len(results)
        st.progress(answered / total, text=f"Question {min(answered + 1, total)} of {total}")

        if current_q < total:
            q = questions[current_q]
            cat_emoji = {"behavioral": "💬", "technical": "💻", "situational": "🎭"}.get(
                q.get("category", ""), "❓"
            )

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(22,163,74,0.08), rgba(22,163,74,0.04));
                        border: 1px solid rgba(22,163,74,0.2); border-radius: 12px;
                        padding: 1.5rem; margin-bottom: 1rem;">
                <div style="font-size: 0.8rem; color: #16a34a; font-weight: 600; margin-bottom: 0.5rem;">
                    {cat_emoji} {q.get('category', 'General').upper()} QUESTION — {current_q + 1}/{total}
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: #1e293b;">
                    {q['question']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            answer = st.text_area(
                "Your Answer:",
                height=150,
                placeholder="Type your answer here... Be specific, use examples from your experience.",
                key=f"answer_{current_q}",
            )

            col_submit, col_skip = st.columns([3, 1])
            with col_submit:
                if st.button("📤 Submit Answer", use_container_width=True, key=f"submit_{current_q}"):
                    if answer.strip():
                        try:
                            with st.spinner("🤖 Evaluating your answer..."):
                                evaluation = evaluate_interview_answer(
                                    q["question"], answer,
                                    job_description,
                                    st.session_state["interview_pdf_text"],
                                )
                            results.append({
                                "question": q["question"],
                                "category": q.get("category", ""),
                                "answer": answer,
                                "evaluation": evaluation,
                            })
                            st.session_state["interview_results"] = results
                            st.session_state["interview_current_q"] = current_q + 1
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    else:
                        st.warning("Please type an answer before submitting.")
            with col_skip:
                if st.button("⏭️ Skip", use_container_width=True, key=f"skip_{current_q}"):
                    results.append({
                        "question": q["question"],
                        "category": q.get("category", ""),
                        "answer": "(Skipped)",
                        "evaluation": {"score": 0, "grade": "Skipped", "strengths": [],
                                       "improvements": ["Question was skipped"],
                                       "ideal_answer": "N/A", "tip": "Try to answer all questions."},
                    })
                    st.session_state["interview_results"] = results
                    st.session_state["interview_current_q"] = current_q + 1
                    st.rerun()

            # Show previous results
            if results:
                st.markdown("---")
                st.markdown("### 📋 Previous Answers")
                for i, r in enumerate(results):
                    ev = r["evaluation"]
                    score = ev.get("score", 0)
                    grade = ev.get("grade", "N/A")
                    score_color = "#16a34a" if score >= 7 else "#eab308" if score >= 5 else "#ef4444"

                    with st.expander(f"Q{i+1}: {r['question'][:60]}... — **{grade}** ({score}/10)", expanded=False):
                        st.markdown(f"**Your Answer:** {r['answer'][:200]}...")
                        st.markdown(f"**Score:** <span style='color:{score_color};font-weight:700;'>{score}/10 — {grade}</span>", unsafe_allow_html=True)
                        if ev.get("strengths"):
                            st.markdown("**✅ Strengths:** " + ", ".join(ev["strengths"]))
                        if ev.get("improvements"):
                            st.markdown("**📈 Improvements:** " + ", ".join(ev["improvements"]))
                        st.markdown(f"**💡 Ideal Answer:** {ev.get('ideal_answer', 'N/A')}")

        else:
            # Interview complete — show final report
            st.balloons()
            st.markdown("## 🎉 Interview Complete!")

            # Calculate overall score
            scores = [r["evaluation"].get("score", 0) for r in results if r["evaluation"].get("score", 0) > 0]
            avg_score = sum(scores) / len(scores) if scores else 0

            # Score display
            score_color = "#16a34a" if avg_score >= 7 else "#eab308" if avg_score >= 5 else "#ef4444"
            st.markdown(f"""
            <div style="text-align:center; padding:2rem; background:linear-gradient(135deg, rgba(22,163,74,0.1), rgba(22,163,74,0.05));
                        border-radius:16px; margin:1rem 0;">
                <div style="font-size:3rem; font-weight:700; color:{score_color};">{avg_score:.1f}/10</div>
                <div style="font-size:1.1rem; color:#475569;">Overall Interview Score</div>
            </div>
            """, unsafe_allow_html=True)

            # Detailed results
            for i, r in enumerate(results):
                ev = r["evaluation"]
                score = ev.get("score", 0)
                grade = ev.get("grade", "N/A")
                s_color = "#16a34a" if score >= 7 else "#eab308" if score >= 5 else "#ef4444"

                with st.expander(f"Q{i+1}: {r['question'][:60]}... — **{grade}** ({score}/10)", expanded=(score < 7)):
                    st.markdown(f"**Your Answer:** {r['answer']}")
                    st.markdown(f"**Score:** <span style='color:{s_color};font-weight:700;'>{score}/10 — {grade}</span>", unsafe_allow_html=True)
                    if ev.get("strengths"):
                        st.markdown("**✅ Strengths:** " + ", ".join(ev["strengths"]))
                    if ev.get("improvements"):
                        st.markdown("**📈 To Improve:** " + ", ".join(ev["improvements"]))
                    st.markdown(f"**💡 Ideal Answer:** {ev.get('ideal_answer', 'N/A')}")
                    if ev.get("tip"):
                        st.info(f"💡 **Tip:** {ev['tip']}")

            # Generate AI report
            if st.button("📊 Generate Full Performance Report", use_container_width=True):
                try:
                    with st.spinner("🤖 Generating your performance report..."):
                        report = generate_interview_report(results)
                    st.markdown("---")
                    st.markdown(report)
                except Exception as e:
                    st.error(str(e))

            # Reset button
            if st.button("🔄 Start New Interview", use_container_width=True):
                st.session_state["interview_questions"] = None
                st.session_state["interview_current_q"] = 0
                st.session_state["interview_results"] = []
                st.session_state["interview_pdf_text"] = ""
                st.rerun()


# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:2rem 0 1rem;">
    <p>© 2025 ATS Resume Expert Pro &nbsp;|&nbsp; Created by Gaurang Sharma</p>
</div>
""", unsafe_allow_html=True)
