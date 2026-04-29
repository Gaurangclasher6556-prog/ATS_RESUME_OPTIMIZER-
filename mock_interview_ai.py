import json
import ai_handler
from ai_handler import _call, _parse_json
from duckduckgo_search import DDGS

def gather_realtime_intelligence(company, role):
    """Fetch real-time interview questions and trends for the company and role."""
    try:
        query = f"site:leetcode.com/discuss/interview-question {company} {role} interview questions 2024 2025"
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            
        intelligence_text = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        
        prompt = f"""You are a Career Intelligence Analyst. Summarize the following real-time search results into a concise 150-word report on the current interview trends, specific questions, and difficulty level for {company} {role}.
        
        Search Results:
        {intelligence_text}
        
        Return the summary as plain text."""
        return _call(prompt)
    except Exception as e:
        print(f"Intelligence gathering failed: {e}")
        return "Real-time intelligence currently unavailable. Falling back to general company knowledge."

def generate_behavioral_question(company, role, history, jd, resume, realtime_intelligence=""):
    prompt = f"""You are a senior behavioral interviewer at {company}. Role: {role}.
REAL-TIME INTELLIGENCE (Use this for extreme accuracy!):
{realtime_intelligence}

First, leverage your internal knowledge and the real-time intelligence above...
Based on the candidate's history and resume, ask the next behavioral question. 
Make the difficulty ADAPTIVE: if their previous answers were strong, ask a highly complex, multi-layered follow-up question. If they struggled, ask a foundational question.
History of questions so far: {json.dumps(history)}
Job Description: {jd}
Resume: {resume}
Generate exactly one challenging behavioral question focused on leadership, teamwork, or problem-solving.
Return JSON:
{{
  "question": "The question text",
  "focus": "Leadership / Conflict Resolution / etc",
  "glassdoor_context": "Why {company} asks this (based on real interview reports)"
}}"""
    return _parse_json(_call(prompt))

def evaluate_behavioral(question, answer, company):
    prompt = f"""Evaluate this behavioral answer for {company}.
Question: {question}
Answer: {answer}
Evaluate out of 10 for: STAR compliance, Company value alignment, Communication clarity, Technical depth.
Return JSON:
{{
  "star_score": 8,
  "values_score": 7,
  "clarity_score": 9,
  "depth_score": 8,
  "feedback": "Overall feedback",
  "study_plan": "Specific gap to study"
}}"""
    return _parse_json(_call(prompt))

def generate_coding_problem(company, role, jd, resume, realtime_intelligence=""):
    prompt = f"""You are a technical interviewer at {company} for {role}.
REAL-TIME INTELLIGENCE (Use this for extreme accuracy!):
{realtime_intelligence}

Generate a unique coding problem (Intermediate/Hard) based on the JD, Resume, and real-time trends...
You MUST generate exactly 8-10 rigorous test cases (including edge cases) to validate the solution.
Return JSON:
{{
  "title": "Problem Title",
  "description": "Full problem description",
  "examples": ["Example 1...", "Example 2..."],
  "constraints": ["Constraint 1..."],
  "test_cases": [
      {{"input": "nums = [2,7,11,15], target = 9", "expected": "[0,1]"} }
  ]
}}"""
    return _parse_json(_call(prompt))

def generate_hint(problem, hint_level):
    levels = {1: "Conceptual nudge", 2: "Algorithm/approach", 3: "Pseudocode"}
    prompt = f"""For this problem, give a level {hint_level} hint: {levels[hint_level]}
Problem: {json.dumps(problem)}
Return just the hint text."""
    return _call(prompt)

def evaluate_coding(problem, code):
    prompt = f"""Evaluate this code for the problem.
Problem: {problem['description']}
Code:
{code}
Analyze Time/Space complexity, comparison vs optimal, and a Hire/No Hire signal.
Return JSON:
{{
  "time_complexity": "O(N)...",
  "space_optimization": "O(1) possible by...",
  "comparison": "Good but optimal is...",
  "signal": "Strong Hire / Hire / No Hire",
  "follow_up": "A quick follow up question"
}}"""
    return _parse_json(_call(prompt))

def generate_system_design(company, role):
    prompt = f"""System design interview for {company}, {role}.
Generate a scenario.
Return JSON:
{{
  "scenario": "Design Twitter...",
  "constraints": "10M DAU, 500ms latency...",
  "key_components_expected": ["Load Balancer", "Cache"]
}}"""
    return _parse_json(_call(prompt))

def evaluate_system_design(scenario, answer):
    prompt = f"""Evaluate system design.
Scenario: {scenario}
Answer: {answer}
Evaluate out of 10.
Return JSON:
{{
  "score": 8,
  "tradeoffs_eval": "Good tradeoff discussion...",
  "scalability_eval": "Missed caching...",
  "clarity_eval": "Clear architecture."
}}"""
    return _parse_json(_call(prompt))

def generate_final_report(b_scores, c_score, sd_score):
    prompt = f"""Generate a final interview report.
Behavioral avg score: {b_scores}
Coding score eval: {json.dumps(c_score)}
System Design eval: {json.dumps(sd_score)}
Return JSON:
{{
  "behavioral_score": 8,
  "coding_score": 7,
  "system_design_score": 8,
  "overall_readiness": "80%",
  "hire_signal": "Hire",
  "strengths": ["..."],
  "improvements": ["..."],
  "study_plan": ["Day 1...", "Day 2..."]
}}"""
    return _parse_json(_call(prompt))
