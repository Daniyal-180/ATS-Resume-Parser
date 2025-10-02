from experience_calculator import calculate_total_experience
from database import fetch_all_resumes
from jd_parser import SKILLS_DB
import re
import json

def calculate_resume_score(jd_dict, resume):

    jd_skills = set([s.strip().lower() for s in jd_dict.get("skills", "").split(",") if s.strip()])
    resume_skill = resume.get("skills", "")
    found_skills = [
        skill for skill in SKILLS_DB
        if re.search(rf"\b{re.escape(skill)}\b", resume_skill, re.IGNORECASE)
    ]
    skills_str = ", ".join(found_skills)
    print("Skills: ", skills_str)
    resume_skills = set([s.strip().lower() for s in skills_str.split(",") if s.strip()])

    if jd_skills:
        skills_match_count = len(jd_skills & resume_skills)
        skills_score = (skills_match_count / len(jd_skills))*100
    else:
        skills_score = 0


    jd_exp = jd_dict.get("min_experience", 0)
    exp_data = resume.get("exp_data", "{}")
    if isinstance(exp_data, str):
        try:
            exp_data = json.loads(exp_data)  # convert JSON string -> dict
        except Exception:
            exp_data = {}

    total_exp = calculate_total_experience(exp_data)

    if jd_exp == 0:
        exp_score = 100
    elif total_exp >= jd_exp:
        exp_score = 100
    elif total_exp < jd_exp:
        exp_score = (total_exp/jd_exp)*100

    total_score = round(((skills_score + exp_score)/2), 2)
    return round(exp_score,2) , round(skills_score,2), total_score


def calculate_scores_for_all_resumes(jd_dict):
    resumes = fetch_all_resumes()  # fetch list of dicts from DB
    results = []

    for resume in resumes:
        exp_score, skills_score, total_score = calculate_resume_score(jd_dict, resume)
        results.append({
            "id": resume["id"],   # resume id from DB
            "name": resume.get("name", ""),
            "phone": resume.get("phone", ""),
            "email": resume.get("email", ""),
            "skills_score": skills_score,
            "experience_score": exp_score,
            "total_score": total_score,
        })

    # Sort by score descending
    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results
