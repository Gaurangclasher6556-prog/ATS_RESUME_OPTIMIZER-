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
    optimize_resume_for_jd,
    personalize_for_company,
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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 ATS Analysis",
    "✏️ AI Optimizer",
    "📄 Resume Builder",
    "🏢 Company Personalizer",
    "🚀 Mass Apply (Batch)",
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
# TAB 2 — AI OPTIMIZER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### ✏️ AI Resume Optimizer")
    st.markdown(
        '<div class="info-banner">🚀 Our AI rewrites your resume bullets, summary, and keywords '
        'to maximally match the job description — then generates a download-ready PDF & DOCX.</div>',
        unsafe_allow_html=True,
    )

    if st.button("⚡ Optimize My Resume", use_container_width=True, key="btn_optimize"):
        if need_resume() and need_jd():
            pdf_bytes = uploaded_file.read()
            try:
                with st.status("🔄 Working on your resume...", expanded=True) as status:
                    st.write("📖 Step 1 / 3 — Reading and parsing your resume...")
                    pdf_text = extract_text(pdf_bytes)
                    resume_data = extract_resume_structure(pdf_text)
                    st.write("✏️ Step 2 / 3 — Optimizing content for the job description...")
                    optimized = optimize_resume_for_jd(resume_data, job_description)
                    st.write("📄 Step 3 / 3 — Generating PDF and DOCX files...")
                    pdf_out  = generate_ats_pdf(optimized)
                    docx_out = generate_ats_docx(optimized)
                    status.update(label="✅ Optimization complete!", state="complete")

                st.session_state["opt_data"]  = optimized
                st.session_state["opt_pdf"]   = pdf_out
                st.session_state["opt_docx"]  = docx_out
                st.session_state["orig_data"] = resume_data
            except Exception as e:
                st.error(str(e))

    if "opt_data" in st.session_state:
        opt  = st.session_state["opt_data"]
        orig = st.session_state.get("orig_data", {})

        st.success("🎉 Your optimized resume is ready!")

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

        # Preview changes
        with st.expander("👁️ Preview Key Changes", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Original Summary**")
                st.info(orig.get("summary", "—") or "—")
            with c2:
                st.markdown("**Optimized Summary**")
                st.success(opt.get("summary", "—") or "—")

            if opt.get("experience"):
                st.markdown("**Optimized Experience Bullets** *(first role)*")
                for b in opt["experience"][0].get("bullets", [])[:4]:
                    st.markdown(f"• {b}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ATS RESUME BUILDER
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📄 ATS-Friendly Resume Builder")
    st.markdown(
        '<div class="info-banner">🎨 Converts your existing resume into a clean, '
        'ATS-optimized format (Jake\'s Resume style — used by top candidates at FAANG). '
        'Download as PDF or editable DOCX.</div>',
        unsafe_allow_html=True,
    )

    if st.button("🏗️ Build ATS Resume", use_container_width=True, key="btn_build"):
        if need_resume():
            pdf_bytes = uploaded_file.read()
            try:
                with st.status("🔄 Building your ATS resume...", expanded=True) as status:
                    st.write("📖 Step 1 / 2 — Extracting resume structure...")
                    pdf_text    = extract_text(pdf_bytes)
                    resume_data = extract_resume_structure(pdf_text)
                    st.write("📄 Step 2 / 2 — Generating ATS-friendly documents...")
                    pdf_out  = generate_ats_pdf(resume_data)
                    docx_out = generate_ats_docx(resume_data)
                    status.update(label="✅ Resume built!", state="complete")

                st.session_state["build_data"] = resume_data
                st.session_state["build_pdf"]  = pdf_out
                st.session_state["build_docx"] = docx_out
            except Exception as e:
                st.error(str(e))

    if "build_data" in st.session_state:
        data = st.session_state["build_data"]
        st.success(f"🎉 ATS resume ready for **{data.get('name', 'you')}**!")

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "⬇️ Download ATS PDF",
                data=st.session_state["build_pdf"],
                file_name=f"ats_resume_{data.get('name','').replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with dl2:
            st.download_button(
                "⬇️ Download Editable DOCX",
                data=st.session_state["build_docx"],
                file_name=f"ats_resume_{data.get('name','').replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

        with st.expander("🔍 Parsed Resume Preview", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**👤 Name:** {data.get('name','—')}")
                st.markdown(f"**📧 Email:** {data.get('email','—')}")
                st.markdown(f"**📍 Location:** {data.get('location','—')}")
                st.markdown(f"**🎓 Education:** {len(data.get('education',[]))} entry/entries")
            with col_b:
                st.markdown(f"**💼 Experience:** {len(data.get('experience',[]))} role(s)")
                st.markdown(f"**🚀 Projects:** {len(data.get('projects',[]))} project(s)")
                skills = data.get("skills", {})
                skill_count = sum(len(v) for v in skills.values()) if isinstance(skills, dict) else len(skills)
                st.markdown(f"**🛠️ Skills:** {skill_count} skill(s) detected")

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


# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:2rem 0 1rem;">
    <p>© 2025 ATS Resume Expert Pro &nbsp;|&nbsp; Created by Gaurang Sharma</p>
</div>
""", unsafe_allow_html=True)
