"""
resume_knowledge_base.py – Curated knowledge base of proven resume patterns.

This acts as a RAG-style reference layer: instead of a vector DB (too heavy
for Streamlit Cloud), we inject curated, domain-specific "gold standard"
examples directly into each optimization pass so the LLM has concrete
reference material to learn from — not just instructions.
"""

# ═══════════════════════════════════════════════════════════════════════════
#  POWER VERBS — categorized by impact type
# ═══════════════════════════════════════════════════════════════════════════

POWER_VERBS = {
    "leadership": [
        "Spearheaded", "Orchestrated", "Championed", "Directed", "Mentored",
        "Mobilized", "Pioneered", "Galvanized", "Steered", "Cultivated",
    ],
    "technical": [
        "Architected", "Engineered", "Automated", "Optimized", "Refactored",
        "Integrated", "Deployed", "Migrated", "Containerized", "Instrumented",
    ],
    "impact": [
        "Accelerated", "Boosted", "Drove", "Elevated", "Slashed",
        "Reduced", "Amplified", "Transformed", "Streamlined", "Revitalized",
    ],
    "analytical": [
        "Diagnosed", "Dissected", "Investigated", "Quantified", "Evaluated",
        "Benchmarked", "Modeled", "Forecasted", "Synthesized", "Validated",
    ],
    "collaboration": [
        "Partnered", "Coordinated", "Facilitated", "Aligned", "Unified",
        "Bridged", "Liaised", "Co-developed", "Negotiated", "Consolidated",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
#  STAR BULLET EXAMPLES — Gold standard bullets from real FAANG resumes
# ═══════════════════════════════════════════════════════════════════════════

STAR_BULLET_EXAMPLES = {
    "software_engineering": [
        "Architected and deployed a real-time event processing pipeline using Apache Kafka and Flink, reducing data ingestion latency from 12s to 450ms (96% improvement) and enabling sub-second analytics for 2M+ daily active users.",
        "Spearheaded migration of a monolithic Django application to a microservices architecture using Kubernetes and gRPC, cutting deployment time from 4 hours to 12 minutes and improving system uptime from 99.2% to 99.97%.",
        "Engineered an automated CI/CD pipeline with GitHub Actions, Docker, and Terraform that reduced release cycles from bi-weekly to daily, eliminating 15 hours/week of manual deployment effort across a team of 8 engineers.",
        "Optimized PostgreSQL query performance by implementing materialized views, composite indexes, and connection pooling, reducing average API response time from 2.3s to 180ms across 50+ endpoints.",
        "Designed and implemented a feature flag system serving 10M+ requests/day with <5ms P99 latency, enabling safe rollouts that reduced production incidents by 73% quarter-over-quarter.",
    ],
    "data_science": [
        "Built an XGBoost-based churn prediction model achieving 94.2% AUC-ROC, enabling the retention team to proactively target high-risk customers and reduce quarterly churn by 18% ($2.4M ARR saved).",
        "Developed an end-to-end NLP pipeline using BERT fine-tuning and spaCy for automated ticket classification, achieving 91% accuracy and reducing manual triage time by 6 hours/day for the support team.",
        "Architected a real-time recommendation engine using collaborative filtering and TensorFlow Serving, increasing click-through rates by 34% and driving $1.2M in incremental quarterly revenue.",
        "Designed A/B testing framework with Bayesian statistical methods, reducing experiment duration by 40% while maintaining 95% confidence intervals, enabling 3x more experiments per quarter.",
    ],
    "product_management": [
        "Led cross-functional team of 12 engineers, 3 designers, and 2 data scientists to launch a self-service analytics dashboard, increasing user engagement by 47% and reducing support tickets by 2,100/month.",
        "Defined and executed product roadmap for a $15M revenue feature, conducting 200+ customer interviews to identify pain points and prioritizing features that drove 28% increase in Net Promoter Score.",
        "Spearheaded integration of AI-powered search using vector embeddings, resulting in 52% improvement in search relevance scores and a 23% reduction in time-to-task-completion for enterprise users.",
    ],
    "general": [
        "Streamlined the quarterly reporting process by automating data collection with Python scripts and building interactive Tableau dashboards, reducing report generation time from 3 days to 2 hours.",
        "Mentored 5 junior engineers through structured 1:1 sessions and code review programs, resulting in 3 promotions within 12 months and a 40% improvement in team code quality metrics.",
        "Negotiated vendor contracts worth $800K annually, achieving 22% cost reduction while improving SLA guarantees from 99.5% to 99.9% uptime.",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
#  ATS KEYWORD PATTERNS — Common patterns ATS scanners look for
# ═══════════════════════════════════════════════════════════════════════════

ATS_PATTERNS = {
    "must_have_sections": [
        "Professional Summary / Summary",
        "Work Experience / Professional Experience",
        "Education",
        "Technical Skills / Skills",
        "Projects (especially for new grads)",
    ],
    "formatting_rules": [
        "Use standard section headers (Education, Experience, Skills) — not creative names",
        "No tables, columns, or text boxes — ATS cannot parse them",
        "No headers/footers — ATS often skips them",
        "Use standard fonts: Times New Roman, Arial, Calibri",
        "File format: PDF (preferred) or DOCX",
        "No images, icons, or graphics",
        "Use bullet points (•) not arrows or custom symbols",
    ],
    "keyword_strategies": [
        "Mirror exact phrases from the job description — ATS uses exact string matching",
        "Include both acronyms AND full forms: 'Machine Learning (ML)'",
        "Place critical keywords in Summary, Experience bullets, AND Skills sections",
        "Use the JD's exact phrasing: if JD says 'Object-Oriented Programming', don't write 'OOP'",
        "Include industry-specific certifications by their official names",
    ],
    "quantification_patterns": [
        "Revenue impact: 'Drove $X in revenue' or 'Increased revenue by X%'",
        "Efficiency: 'Reduced [metric] by X%' or 'Saved X hours/week'",
        "Scale: 'Served X users' or 'Processed X requests/day'",
        "Speed: 'Improved latency from Xms to Yms (Z% improvement)'",
        "Quality: 'Achieved X% accuracy' or 'Reduced errors by X%'",
        "Team: 'Led team of X engineers' or 'Mentored X junior developers'",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
#  SUMMARY TEMPLATES — Proven professional summary structures
# ═══════════════════════════════════════════════════════════════════════════

SUMMARY_TEMPLATES = {
    "experienced": (
        "Results-driven {role} with {years}+ years of experience in {domain}. "
        "Proven track record of {achievement_1} and {achievement_2}. "
        "Expertise in {skill_1}, {skill_2}, and {skill_3}. "
        "Passionate about {passion} with a focus on {focus_area}."
    ),
    "new_grad": (
        "Detail-oriented {degree} graduate from {university} with hands-on "
        "experience in {skill_1}, {skill_2}, and {skill_3} through {project_count}+ "
        "projects and {internship_info}. "
        "Seeking to leverage strong foundation in {domain} to drive impact as a {role}."
    ),
    "career_changer": (
        "Versatile professional transitioning from {old_field} to {new_field}, "
        "bringing {years}+ years of transferable expertise in {transferable_1} "
        "and {transferable_2}. Recently completed {certification_or_project} "
        "to build technical proficiency in {skill_1} and {skill_2}."
    ),
}

# ═══════════════════════════════════════════════════════════════════════════
#  WEAK → STRONG BULLET TRANSFORMATIONS — Teaching examples
# ═══════════════════════════════════════════════════════════════════════════

WEAK_TO_STRONG_EXAMPLES = [
    {
        "weak": "Worked on the backend of the application",
        "strong": "Engineered RESTful API backend using Node.js and Express, serving 50K+ daily requests with 99.9% uptime and <200ms average response time",
        "why": "Added specifics: technology, scale, and measurable outcomes",
    },
    {
        "weak": "Helped improve the website",
        "strong": "Optimized front-end performance by implementing lazy loading, code splitting, and CDN caching, reducing page load time from 4.2s to 1.1s and improving Core Web Vitals score by 62%",
        "why": "Replaced vague 'helped improve' with specific actions, techniques, and quantified results",
    },
    {
        "weak": "Responsible for testing software",
        "strong": "Designed and executed comprehensive test automation framework using Pytest and Selenium, achieving 94% code coverage and catching 40+ critical bugs before production release",
        "why": "Changed passive 'responsible for' to active achievement with measurable impact",
    },
    {
        "weak": "Used Python for data analysis",
        "strong": "Built automated data pipeline using Python (Pandas, NumPy) and Apache Airflow to process 2TB of daily transaction data, reducing manual analysis time from 8 hours to 15 minutes",
        "why": "Specifics: tools, scale, time savings — tells a story of real impact",
    },
    {
        "weak": "Part of a team that launched a new feature",
        "strong": "Co-led cross-functional launch of real-time collaboration feature, coordinating with 4 engineering pods and driving 23% increase in daily active users within first month post-launch",
        "why": "Ownership language, scope clarity, and measurable business impact",
    },
    {
        "weak": "Did machine learning projects",
        "strong": "Developed and deployed a gradient-boosted classification model (XGBoost) achieving 92% F1-score for fraud detection, preventing an estimated $1.8M in annual fraudulent transactions",
        "why": "Named the algorithm, the metric, and the business dollar impact",
    },
    {
        "weak": "Made a website using React",
        "strong": "Architected a responsive single-page application using React, Redux, and TypeScript, implementing component-level code splitting that reduced initial bundle size by 58% and improved Lighthouse performance score from 43 to 91",
        "why": "Full tech stack, specific optimization technique, and before/after metrics",
    },
    {
        "weak": "Managed databases",
        "strong": "Administered and optimized PostgreSQL cluster handling 500M+ records, implementing partitioning and index optimization strategies that reduced average query execution time by 78%",
        "why": "Scale, specific techniques, quantified improvement",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  INDUSTRY KEYWORD MAPS — Common keywords by industry/role
# ═══════════════════════════════════════════════════════════════════════════

INDUSTRY_KEYWORDS = {
    "software_engineering": [
        "Agile/Scrum", "CI/CD", "Microservices", "RESTful APIs", "GraphQL",
        "Docker", "Kubernetes", "AWS/GCP/Azure", "System Design",
        "Unit Testing", "Integration Testing", "Code Review", "Git",
        "Object-Oriented Programming (OOP)", "Design Patterns", "SOLID Principles",
        "Data Structures", "Algorithms", "Performance Optimization", "Scalability",
    ],
    "data_science": [
        "Machine Learning", "Deep Learning", "Natural Language Processing (NLP)",
        "Computer Vision", "Statistical Analysis", "A/B Testing", "ETL Pipelines",
        "Feature Engineering", "Model Deployment", "TensorFlow", "PyTorch",
        "Scikit-learn", "Pandas", "SQL", "Tableau/Power BI", "Big Data",
        "Spark", "Hadoop", "Data Visualization", "Hypothesis Testing",
    ],
    "web_development": [
        "React", "Angular", "Vue.js", "Next.js", "Node.js", "Express",
        "TypeScript", "JavaScript", "HTML5/CSS3", "Responsive Design",
        "Progressive Web Apps (PWA)", "SEO Optimization", "Webpack",
        "REST APIs", "Authentication/Authorization", "OAuth", "JWT",
    ],
    "devops": [
        "Infrastructure as Code (IaC)", "Terraform", "Ansible", "Jenkins",
        "GitHub Actions", "GitLab CI", "Docker", "Kubernetes", "Helm",
        "Prometheus", "Grafana", "ELK Stack", "AWS CloudFormation",
        "Site Reliability Engineering (SRE)", "Monitoring", "Alerting",
        "Incident Response", "Disaster Recovery", "Load Balancing",
    ],
    "product_management": [
        "Product Roadmap", "User Research", "Stakeholder Management",
        "OKRs/KPIs", "A/B Testing", "Sprint Planning", "Backlog Grooming",
        "Customer Discovery", "Market Analysis", "Go-to-Market Strategy",
        "Cross-functional Leadership", "Data-Driven Decision Making",
        "Wireframing", "Prototyping", "User Stories", "Competitive Analysis",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
#  PROMPT BUILDERS — Functions that inject KB context into prompts
# ═══════════════════════════════════════════════════════════════════════════

def get_power_verbs_prompt() -> str:
    """Return formatted power verbs for prompt injection."""
    lines = []
    for category, verbs in POWER_VERBS.items():
        lines.append(f"  {category.title()}: {', '.join(verbs)}")
    return "\n".join(lines)


def get_star_examples_prompt(domain: str = "general") -> str:
    """Return STAR bullet examples for a given domain."""
    examples = STAR_BULLET_EXAMPLES.get(domain, STAR_BULLET_EXAMPLES["general"])
    # Always include general examples too
    if domain != "general":
        examples = examples + STAR_BULLET_EXAMPLES["general"][:2]
    return "\n".join(f"  ✓ {ex}" for ex in examples)


def get_weak_to_strong_prompt() -> str:
    """Return weak→strong transformation examples."""
    lines = []
    for i, ex in enumerate(WEAK_TO_STRONG_EXAMPLES, 1):
        lines.append(f"  Example {i}:")
        lines.append(f"    WEAK:   \"{ex['weak']}\"")
        lines.append(f"    STRONG: \"{ex['strong']}\"")
        lines.append(f"    WHY:    {ex['why']}")
        lines.append("")
    return "\n".join(lines)


def get_ats_rules_prompt() -> str:
    """Return ATS formatting and keyword rules."""
    lines = []
    lines.append("  Keyword Strategies:")
    for rule in ATS_PATTERNS["keyword_strategies"]:
        lines.append(f"    • {rule}")
    lines.append("\n  Quantification Patterns:")
    for pattern in ATS_PATTERNS["quantification_patterns"]:
        lines.append(f"    • {pattern}")
    return "\n".join(lines)


def get_industry_keywords_prompt(job_description: str) -> str:
    """Detect likely industry from JD and return relevant keywords."""
    jd_lower = job_description.lower()

    # Simple keyword-based detection
    scores = {}
    keyword_map = {
        "software_engineering": ["software engineer", "backend", "frontend", "full stack",
                                  "developer", "sde", "systems", "infrastructure"],
        "data_science": ["data scientist", "machine learning", "ml engineer", "data analyst",
                         "deep learning", "analytics", "data engineer"],
        "web_development": ["web developer", "frontend developer", "react developer",
                            "ui developer", "full stack web"],
        "devops": ["devops", "sre", "site reliability", "platform engineer",
                   "infrastructure", "cloud engineer"],
        "product_management": ["product manager", "product owner", "program manager",
                               "technical program"],
    }

    for industry, triggers in keyword_map.items():
        scores[industry] = sum(1 for t in triggers if t in jd_lower)

    # Get top industry (default to software_engineering)
    best = max(scores, key=scores.get) if max(scores.values()) > 0 else "software_engineering"
    keywords = INDUSTRY_KEYWORDS.get(best, INDUSTRY_KEYWORDS["software_engineering"])

    return f"  Industry detected: {best.replace('_', ' ').title()}\n  Relevant keywords to consider: {', '.join(keywords)}"


def get_full_knowledge_context(job_description: str) -> str:
    """Build complete knowledge base context for injection into prompts."""
    return f"""
═══ RESUME OPTIMIZATION KNOWLEDGE BASE ═══

📋 POWER VERBS (use these to start bullet points):
{get_power_verbs_prompt()}

📝 GOLD-STANDARD STAR BULLET EXAMPLES:
{get_star_examples_prompt()}

🔄 WEAK → STRONG TRANSFORMATIONS (learn from these):
{get_weak_to_strong_prompt()}

📊 ATS RULES & QUANTIFICATION PATTERNS:
{get_ats_rules_prompt()}

🏭 INDUSTRY CONTEXT:
{get_industry_keywords_prompt(job_description)}

═══ END KNOWLEDGE BASE ═══
"""
