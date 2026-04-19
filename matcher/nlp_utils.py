import re
import fitz  # PyMuPDF
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SKILL_LIST = [
    "python", "django", "flask", "fastapi",
    "rest api", "api",
    "sql", "postgresql", "mysql", "mongodb",
    "javascript", "react", "node", "express",
    "html", "css", "tailwind", "bootstrap",
    "git", "github", "docker",
    "pandas", "numpy", "scikit-learn",
    "machine learning", "deep learning", "nlp",
    "tensorflow", "pytorch",
    "aws", "azure", "gcp"
]


def normalize_text(text):
    text_low = text.lower()
    text_low = re.sub(r"\s+", " ", text_low).strip()
    return text_low


def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    return "\n".join(text_parts)


def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text_parts = []
    for para in doc.paragraphs:
        text_parts.append(para.text)
    return "\n".join(text_parts)


def extract_text(file_path):
    file_path_low = file_path.lower()
    if file_path_low.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    if file_path_low.endswith(".docx"):
        return extract_text_from_docx(file_path)
    raise ValueError("Unsupported file type. Use PDF or DOCX.")


def detect_skills(text):
    text_norm = normalize_text(text)
    found = []
    for skill in SKILL_LIST:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_norm):
            found.append(skill)
    found_sorted = sorted(list(set(found)))
    return found_sorted


def compute_match(resume_text, job_text):
    resume_norm = normalize_text(resume_text)
    job_norm = normalize_text(job_text)

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    tfidf = vectorizer.fit_transform([resume_norm, job_norm])
    score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]

    percent = round(score * 100.0, 2)
    return percent


def missing_skills(resume_skills, job_skills):
    resume_set = set([s.lower() for s in resume_skills])
    job_set = set([s.lower() for s in job_skills])
    missing = sorted(list(job_set - resume_set))
    return missing


def improvement_tips(missing):
    tips = []
    if len(missing) > 0:
        tips.append("Add a Skills section that includes: " + ", ".join(missing[:8]))
        tips.append("Add 1-2 project bullets showing you used: " + ", ".join(missing[:5]))
    tips.append("Use measurable impact in bullets (reduced time by X%, built Y, improved Z).")
    tips.append("Match keywords from the job description naturally (don’t keyword-stuff).")
    return tips