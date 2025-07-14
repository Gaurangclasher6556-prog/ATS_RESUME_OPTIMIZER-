from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import fitz  # PyMuPDF (lightweight PDF parser)
import google.generativeai as genai
from streamlit_extras.stylable_container import stylable_container

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Gemini response generator
def get_gemini_response(prompt_intro, pdf_text, job_desc):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([prompt_intro, pdf_text, job_desc])
    return response.text

# Extract text from PDF using PyMuPDF
def extract_text_from_pdf(uploaded_file):
    if uploaded_file is not None:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    else:
        raise FileNotFoundError("No file uploaded")

# --- Streamlit UI ---

st.set_page_config(
    page_title="ATS Resume Expert", 
    layout="centered",
    page_icon="📄"
)

# Custom CSS for enhanced styling
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        * {
            font-family: 'Poppins', sans-serif;
        }
        
        .stApp {
            background-color: #f5f7fa;
        }
        
        .title-text {
            font-family: 'Poppins', sans-serif;
            font-weight: 700;
            color: #2d3748;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        
        .subtitle-text {
            font-family: 'Poppins', sans-serif;
            font-weight: 400;
            color: #4a5568;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .stButton>button {
            border: 2px solid #4CAF50;
            color: white;
            background-color: #4CAF50;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }
        
        .stButton>button:hover {
            background-color: white;
            color: #4CAF50;
            border: 2px solid #4CAF50;
        }
        
        .file-uploader {
            border: 2px dashed #4CAF50;
            border-radius: 10px;
            padding: 2rem;
            background-color: rgba(76, 175, 80, 0.05);
        }
        
        .stTextArea>div>div>textarea {
            min-height: 150px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
        }
        
        .success-box {
            background-color: #f0fff4;
            border-left: 4px solid #48bb78;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 1rem 0;
        }
        
        .result-box {
            background-color: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin: 1rem 0;
        }
        
        .footer {
            font-size: 0.8rem;
            color: #718096;
            text-align: center;
            margin-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
    <h1 class="title-text">
        <span style="color: #4CAF50;">📄 ATS</span> Resume Expert
    </h1>
    <p class="subtitle-text">
        Optimize your resume to beat Applicant Tracking Systems and land more interviews
    </p>
""", unsafe_allow_html=True)

# Main Content
with st.container():
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("### 💼 Job Description")
        job_description = st.text_area(
            "Paste the job description here...", 
            key="input",
            label_visibility="collapsed",
            height=250
        )
        
    with col2:
        st.markdown("### 📎 Upload Resume")
        with st.container(border=True):
            uploaded_file = st.file_uploader(
                "Drag and drop your PDF resume here", 
                type=["pdf"],
                label_visibility="collapsed"
            )
        
        if uploaded_file:
            with st.container(border=True):
                st.success("✅ Resume uploaded successfully!")
                st.markdown(f"**File name:** {uploaded_file.name}")
                st.markdown(f"**File size:** {uploaded_file.size / 1024:.2f} KB")

# Action Buttons
st.markdown("---")
col1, col2, col3 = st.columns([1,1,1])

with col1:
    if st.button("🔍 **Detailed Review**", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner("Analyzing your resume..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
                response = get_gemini_response("""
                    You are an experienced Technical Human Resource Manager. Review the provided resume against the job description. 
                    Give a professional evaluation of how well the resume aligns with the role, including:
                    - Key strengths that match the job requirements
                    - Areas that need improvement
                    - Specific suggestions for optimization
                    - Overall impression and recommendation
                """, pdf_text, job_description)
                
                with st.container(border=True):
                    st.markdown("### 📝 Detailed Evaluation")
                    st.markdown(response)
        else:
            st.warning("Please upload your resume and provide the job description")

with col2:
    if st.button("📊 **ATS Match Score**", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner("Calculating ATS match..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
                response = get_gemini_response("""
                    You are an ATS (Applicant Tracking System) scanner with expertise in resume evaluation. Analyze the resume against the job description.
                    Provide:
                    1. Percentage match score (0-100%)
                    2. Missing keywords from the job description
                    3. Suggested improvements to increase match score
                    4. Final thoughts on competitiveness
                    Present this in a clear, structured format with bullet points.
                """, pdf_text, job_description)
                
                with st.container(border=True):
                    st.markdown("### 📈 ATS Match Analysis")
                    st.markdown(response)
        else:
            st.warning("Please upload your resume and provide the job description")

with col3:
    if st.button("✨ **Optimization Tips**", use_container_width=True):
        if uploaded_file and job_description:
            with st.spinner("Generating optimization tips..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
                response = get_gemini_response("""
                    You are a career coach specializing in resume optimization. Provide specific, actionable recommendations to improve this resume for the given job description:
                    - Keyword optimization suggestions
                    - Content restructuring advice
                    - Formatting improvements for ATS
                    - Any other tips to make the resume stand out
                    Organize your response with clear headings and bullet points.
                """, pdf_text, job_description)
                
                with st.container(border=True):
                    st.markdown("### 💡 Optimization Recommendations")
                    st.markdown(response)
        else:
            st.warning("Please upload your resume and provide the job description")

# Footer
st.markdown("---")
st.markdown("""
    <div class="footer">
        <p>© 2025 ATS Resume Expert | Created with ❤️ by Gaurang Sharma</p>
        <p>This tool uses AI to analyze resumes and provide optimization suggestions</p>
    </div>
""", unsafe_allow_html=True)
