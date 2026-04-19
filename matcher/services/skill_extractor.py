import os
import re
import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "skills.csv")
print("CSV PATH:", DATA_DIR)

SECTION_HEADERS = {
    "skills": [
        "skills", "technical skills", "core skills", "tools", "technologies", "tech stack"
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment", "work history"
    ],
    "projects": [
        "projects", "personal projects", "project experience"
    ],
    "education": [
        "education", "academic", "certifications", "certification"
    ]
}

def _normalize_text(txt):
    if not txt:
        return ""
    txt2 = txt.replace("\r", "\n")
    txt2 = re.sub(r"[ \t]+", " ", txt2)
    txt2 = re.sub(r"\n{3,}", "\n\n", txt2)
    return txt2.strip()

def split_into_sections(text):
    """
    Very practical section splitter:
    - finds lines that look like headers (short, mostly words, often uppercase)
    - maps them to canonical section names
    """
    clean_text = _normalize_text(text)
    lines = [ln.strip() for ln in clean_text.split("\n")]
    sections = {"_full": clean_text}
    current_section = "_full"
    buf = []

    def map_header(line_lower):
        for sec_name, aliases in SECTION_HEADERS.items():
            for a in aliases:
                if line_lower == a:
                    return sec_name
        return None

    def flush():
        nonlocal buf, current_section
        if len(buf) > 0:
            joined = "\n".join(buf).strip()
            if current_section not in sections:
                sections[current_section] = joined
            else:
                sections[current_section] = (sections[current_section] + "\n" + joined).strip()
        buf = []

    for ln in lines:
        low = ln.lower().strip(":").strip()
        is_headerish = (len(low) > 0 and len(low) <= 40 and re.fullmatch(r"[a-z0-9 &/+-]+", low) is not None)

        mapped = map_header(low) if is_headerish else None
        if mapped is not None:
            flush()
            current_section = mapped
            continue

        buf.append(ln)

    flush()
    return sections

def load_skills_from_csv(csv_path=None):
    if csv_path is None:
        csv_path = DATA_DIR  

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Skills CSV not found at: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError:
        raise ValueError("skills.csv is empty. Please add skill data.")

    if "skill" not in df.columns:
        raise ValueError("CSV must contain a 'skill' column")

    df["skill_norm"] = df["skill"].astype(str).str.strip().str.lower()
    df = df.dropna(subset=["skill_norm"]).drop_duplicates(subset=["skill_norm"])

    return df

class SkillExtractor:
    def __init__(self, skills_csv_path=None):
        self.nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "lemmatizer", "textcat"])
        self.skills_df = load_skills_from_csv(skills_csv_path)
        self.skills_list = self.skills_df["skill_norm"].tolist()

        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        patterns = [self.nlp.make_doc(s) for s in self.skills_list]
        self.matcher.add("SKILLS", patterns)

    def extract(self, text):
        sections = split_into_sections(text)
        result = {
            "all_skills": [],
            "skills_section_skills": [],
            "experience_section_skills": [],
            "projects_section_skills": [],
            "section_map": {}
        }

        for sec_key, sec_text in sections.items():
            doc = self.nlp(sec_text)
            matches = self.matcher(doc)
            found = set()
            for _, start, end in matches:
                span = doc[start:end]
                found.add(span.text.strip().lower())

            found_sorted = sorted(found)
            result["section_map"][sec_key] = found_sorted

        # prioritize skills found in Skills section, then projects/experience, then full
        skills_skills = result["section_map"].get("skills", [])
        exp_skills = result["section_map"].get("experience", [])
        proj_skills = result["section_map"].get("projects", [])
        full_skills = result["section_map"].get("_full", [])

        merged = []
        seen = set()
        for group in [skills_skills, proj_skills, exp_skills, full_skills]:
            for s in group:
                if s not in seen:
                    merged.append(s)
                    seen.add(s)

        result["all_skills"] = merged
        result["skills_section_skills"] = skills_skills
        result["experience_section_skills"] = exp_skills
        result["projects_section_skills"] = proj_skills
        return result