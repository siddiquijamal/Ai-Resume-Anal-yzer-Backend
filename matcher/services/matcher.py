import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_embedding_model = None

def _clean_for_tfidf(text):
    if text is None:
        return ""
    txt = text.lower()
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def tfidf_match(resume_text, job_text, top_k_terms=12):
    r = _clean_for_tfidf(resume_text)
    j = _clean_for_tfidf(job_text)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=1)
    mat = vectorizer.fit_transform([r, j])
    score = float(cosine_similarity(mat[0], mat[1])[0][0])

    # Explainability: terms in job text that overlap with resume weighted by tf-idf
    feats = np.array(vectorizer.get_feature_names_out())
    r_vec = mat[0].toarray().ravel()
    j_vec = mat[1].toarray().ravel()
    contrib = r_vec * j_vec  # simplistic but effective overlap signal

    top_idx = np.argsort(contrib)[::-1]
    top_terms = []
    for idx in top_idx[:top_k_terms]:
        if contrib[idx] <= 0:
            break
        top_terms.append({
            "term": str(feats[idx]),
            "contribution": float(contrib[idx])
        })

    return {
        "score": score,
        "top_terms": top_terms
    }

def embedding_match(resume_text, job_text):
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    emb = _embedding_model.encode([resume_text, job_text], normalize_embeddings=True)
    score = float(np.dot(emb[0], emb[1]))
    return {"score": score}

def missing_skills_from_job(job_text, resume_skills, skill_list_from_job=None):
    """
    You can optionally pass extracted job skills later.
    For now, quick heuristic: if you already have resume_skills, missing skills
    will be from job-extracted skills (when you implement it), else empty.
    """
    if skill_list_from_job is None:
        return []
    rs = set([s.lower() for s in resume_skills])
    missing = [s for s in skill_list_from_job if s.lower() not in rs]
    return missing

def compute_match_dual(resume_text, job_text, resume_skills=None):
    if resume_skills is None:
        resume_skills = []

    tfidf_res = tfidf_match(resume_text, job_text)
    emb_res = embedding_match(resume_text, job_text)

    # Combined score: weighted average; keep interpretable
    combined = 0.3 * tfidf_res["score"] + 0.7 * emb_res["score"]

    tips = []
    if tfidf_res["score"] < 0.35:
        tips.append("Add more role-specific keywords and tools from the job description into your Skills/Projects sections.")
    if emb_res["score"] < 0.45:
        tips.append("Your resume reads semantically different from the job description; consider rewriting bullet points to mirror responsibilities and outcomes.")

    return {
        "tfidf": {
            "score": tfidf_res["score"],
            "top_terms": tfidf_res["top_terms"]
        },
        "embedding": {
            "score": emb_res["score"]
        },
        "combined_score": combined,
        "match_percent": int(round(combined * 100)),
        "resume_skills_used": resume_skills,
        "tips": tips
    }