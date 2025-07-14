from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import fitz  # PyMuPDF
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Gemini response generator
def get_gemini_response(prompt_intro, pdf_text, job_desc):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt_intro, pdf_text, job_desc])
    return response.text

# Extract text from PDF
def extract_text_from_pdf(uploaded_file):
    if uploaded_file is not None:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    else:
        raise FileNotFoundError("No file uploaded")

# Page Configuration
st.set_page_config(page_title="ATS Resume Expert", layout="centered")

# CSS Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        background-color: #f4f6f8;
    }

    .main-title {
        text-align: center;
        color: #4CAF50;
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .section {
        background-color: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.06);
        margin-top: 20px;
    }

    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 16px;
        font-weight: 600;
        transition: 0.3s ease;
    }

    .stButton>button:hover {
        background-color: #45a049;
        color: white;
        transform: scale(1.02);
    }

    footer {
        text-align: center;
        font-size: 14px;
        color: gray;
        margin-top: 40px;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1 class='main-title'>📄 ATS Resume Expert</h1>", unsafe_allow_html=True)

# Input Section
with st.container():
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown("### 👇 Upload your resume & paste the job description below")
    
    job_description = st.text_area("💼 Job Description", key="input")
    uploaded_file = st.file_uploader("📎 Upload your Resume (PDF only)", type=["pdf"])

    if uploaded_file:
        st.success("✅ PDF uploaded successfully!")
    st.markdown('</div>', unsafe_allow_html=True)

# Prompts
evaluation_prompt = """
You are an experienced Technical Human Resource Manager. Review the provided resume against the job description. 
Give a professional evaluation of how well the resume aligns with the role, highlighting strengths and weaknesses.
"""

match_prompt = """
You are an ATS (Applicant Tracking System) scanner with expertise in resume evaluation. Analyze the resume against the job description.
Return:
1. Percentage Match
2. Missing Keywords
3. Final Thoughts
Avoid giving percentage alone. Always follow up with detailed feedback.
"""

# Button Section
st.markdown('<div class="section">', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    submit_eval = st.button("🔍 Review Resume")

with col2:
    submit_match = st.button("📊 Match Percentage")

st.markdown('</div>', unsafe_allow_html=True)

# Output
if submit_eval or submit_match:
    if uploaded_file:
        pdf_text = extract_text_from_pdf(uploaded_file)
        if submit_eval:
            response = get_gemini_response(evaluation_prompt, pdf_text, job_description)
            st.markdown('<div class="section">', unsafe_allow_html=True)
            st.subheader("📄 Evaluation Result")
            st.write(response)
            st.markdown('</div>', unsafe_allow_html=True)
        elif submit_match:
            response = get_gemini_response(match_prompt, pdf_text, job_description)
            st.markdown('<div class="section">', unsafe_allow_html=True)
            st.subheader("📊 Match Analysis")
            st.write(response)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Please upload your resume to proceed.")

# Footer
st.markdown("---")
st.markdown("""
    <footer>
    © 2025 All rights reserved by <strong>Gaurang Sharma</strong>
    </footer>
""", unsafe_allow_html=True)
