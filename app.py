from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import fitz  # PyMuPDF
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_gemini_response(prompt_intro, pdf_text, job_desc):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt_intro, pdf_text, job_desc])
    return response.text

def extract_text_from_pdf(uploaded_file):
    if uploaded_file is not None:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    else:
        raise FileNotFoundError("No file uploaded")

# Custom CSS for attractive UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif;
    }
    
    .header {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .file-uploader {
        border: 2px dashed #4CAF50;
        border-radius: 10px;
        padding: 2rem;
        background-color: rgba(76, 175, 80, 0.05);
        margin-bottom: 1.5rem;
    }
    
    .result-box {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-top: 1.5rem;
        border-left: 5px solid #4CAF50;
    }
    
    .footer {
        margin-top: 3rem;
        text-align: center;
        color: #666;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# App Layout
st.set_page_config(page_title="ATS Resume Expert", page_icon="📄", layout="wide")

# Header Section
st.markdown("""
<div class="header">
    <h1 style="margin:0; font-size:2.5rem;">📄 ATS Resume Expert</h1>
    <p style="margin:0; font-size:1.1rem;">Optimize your resume to beat Applicant Tracking Systems</p>
</div>
""", unsafe_allow_html=True)

# Main Content
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 💼 Job Description")
    job_description = st.text_area(
        "Paste the job description here...", 
        height=250,
        label_visibility="collapsed",
        placeholder="Enter the job description you're applying for..."
    )

with col2:
    st.markdown("### 📎 Upload Resume")
    with st.container(border=True):
        uploaded_file = st.file_uploader(
            "Choose a PDF file", 
            type=["pdf"],
            label_visibility="collapsed"
        )
    
    if uploaded_file:
        st.success("✅ Resume uploaded successfully!")
        st.caption(f"File: {uploaded_file.name}")

# Action Buttons
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🔍 **Get Detailed Review**", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner("Analyzing your resume..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
                response = get_gemini_response("""
                    You are an experienced HR professional. Review this resume against the job description.
                    Provide:
                    1. Strengths that match the job
                    2. Areas needing improvement
                    3. Specific optimization suggestions
                    4. Overall recommendation
                    Use bullet points and clear headings.
                """, pdf_text, job_description)
                
                with st.container(border=True):
                    st.markdown("### 📝 Professional Evaluation")
                    st.markdown(response)
        else:
            st.warning("Please upload your resume and provide the job description")

with col2:
    if st.button("📊 **Check ATS Match Score**", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner("Calculating match score..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
                response = get_gemini_response("""
                    You are an ATS scanner. Analyze this resume against the job description.
                    Provide:
                    1. Match percentage (0-100%)
                    2. Missing keywords
                    3. Suggestions to improve score
                    4. Final thoughts
                    Present in a structured format.
                """, pdf_text, job_description)
                
                with st.container(border=True):
                    st.markdown("### 📈 ATS Compatibility Report")
                    st.markdown(response)
        else:
            st.warning("Please upload your resume and provide the job description")

# Footer
st.markdown("""
<div class="footer">
    <hr>
    <p>© 2025 ATS Resume Expert | Created  by Gaurang Sharma</p>
</div>
""", unsafe_allow_html=True)

