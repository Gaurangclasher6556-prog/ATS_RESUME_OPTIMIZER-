 Project Title: ATS Resume Parser & Visualizer
🔍 Description
This project is a web-based ATS (Applicant Tracking System) resume parser and visualizer built using Python and Streamlit. It allows users to upload their resumes in PDF format and automatically extracts and displays information for further analysis or review.

Originally built using pdf2image, the app converts PDFs to images for content extraction. However, for better deployability (like on Streamlit Cloud), you can optionally use PyMuPDF (pure Python) instead.

💡 Features
Upload PDF resume files

Extract and display resume content

Display parsed data in an easy-to-read format

Ready for ATS keyword analysis or NLP processing

Lightweight and fast UI with Streamlit

🛠️ Tech Stack

Tool	Purpose
Python	Core programming language
Streamlit	Web app framework
pdf2image*	(Or PyMuPDF) PDF content extraction
PIL / fitz	Image handling or PDF parsing
