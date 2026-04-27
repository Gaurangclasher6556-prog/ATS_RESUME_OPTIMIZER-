from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fitz  # PyMuPDF

from ai_handler import (
    get_ats_review, get_ats_score,
    rebuild_resume,
    generate_interview_questions,
    evaluate_interview_answer,
    research_company_interview_patterns,
    simulate_code_run
)

app = FastAPI(title="ATS Resume API")

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text(file_bytes: bytes) -> str:
    try:
        doc = fitz.open("pdf", file_bytes)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}")

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    bytes_data = await file.read()
    try:
        text = extract_text(bytes_data)
        return {"filename": file.filename, "text": text}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

class AnalyzeRequest(BaseModel):
    pdf_text: str
    job_description: str

@app.post("/api/analyze")
async def analyze_resume(req: AnalyzeRequest):
    try:
        score = get_ats_score(req.pdf_text, req.job_description)
        review = get_ats_review(req.pdf_text, req.job_description)
        return {"score": score, "review": review}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RebuildRequest(BaseModel):
    pdf_text: str

@app.post("/api/rebuild")
async def rebuild_endpoint(req: RebuildRequest):
    try:
        rebuilt = rebuild_resume(req.pdf_text)
        return {"rebuilt_resume": rebuilt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class InterviewPrepRequest(BaseModel):
    pdf_text: str
    job_description: str
    company_name: str
    target_role: str
    interview_round: str

@app.post("/api/generate-interview")
async def generate_interview(req: InterviewPrepRequest):
    try:
        research = research_company_interview_patterns(req.company_name, req.target_role, req.interview_round)
        questions = generate_interview_questions(
            req.pdf_text, 
            req.job_description, 
            req.company_name, 
            req.target_role, 
            req.interview_round,
            research
        )
        return {"research": research, "questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CodeRunRequest(BaseModel):
    question: str
    code: str

@app.post("/api/run-code")
async def run_code(req: CodeRunRequest):
    try:
        result = simulate_code_run(req.question, req.code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    job_description: str
    pdf_text: str

@app.post("/api/evaluate-answer")
async def evaluate_answer(req: EvaluateAnswerRequest):
    try:
        eval_result = evaluate_interview_answer(req.question, req.answer, req.job_description, req.pdf_text)
        return eval_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
