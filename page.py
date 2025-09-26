from flask import Flask, request, jsonify, render_template
import json
import os
from werkzeug.utils import secure_filename
from database import init_db, save_resume_to_db, fetch_all_resumes
from App2 import extract_contact_info, extract_resume_text, extract_all_sections, normalize_sections, resume_headings_base, clean_section_dict
from experience_calculator import extract_experience_dict, extract_highest_education, calculate_total_experience
from jd_parser import parse_job_description, read_pdf, read_docx
from score import calculate_scores_for_all_resumes


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

JD_FOLDER = "JD_uploads"
os.makedirs(JD_FOLDER, exist_ok=True)

init_db()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/parse", methods=["POST"])
def parse_resume():
    files = request.files.getlist("file")
    results = []

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    for f in files:
        # Only accept PDF/DOCX
        if not f.filename.lower().endswith(".pdf"):
            results.append({"filename": f.filename, "error": "Unsupported file type"})
            continue

        # Save file with unique name
        filename = f"{f.filename}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(save_path)

        contact = {}
        sections = {}


        try:
            # Extract contact info
            contact = extract_contact_info(save_path)
            name = contact.get("name", "")
            phone = contact.get("phone", "")
            email = contact.get("email", "")


            # Extract resume text and sections
            text = extract_resume_text(save_path)
            sections = extract_all_sections(text) # Should return a dict
            sections = clean_section_dict(sections)
            sections = normalize_sections(sections, resume_headings_base)

            exp_text = sections.get("experience", "")  # assume normalized section
            exp_dict = extract_experience_dict(exp_text)
            skills = sections.get("skills", "")
            education = extract_highest_education(sections.get("education", ""))
            exp_json = json.dumps(exp_dict) if exp_dict else None
            total_exp = calculate_total_experience(exp_json)


            # Save all info to database
            with open(save_path, "rb") as file_obj:
                save_resume_to_db(name, phone, email, education, f.filename, file_obj.read(), skills, exp_json, total_exp)

            results.append({
                "filename": f.filename,
                "contact": contact,
                "sections": sections
            })

        except Exception as e:
            print(f"Error processing {f.filename}: {e}")
            results.append({
                "filename": f.filename,
                "error": str(e),
                "contact": contact,
                "sections": sections
            })

    return jsonify(results)


@app.route("/data", methods=["GET"])
def resume_data():
    skill = request.args.get("skill", None)
    exp = request.args.get("exp", None)

    resumes = fetch_all_resumes()

    # Filter resumes
    filtered_resumes = []
    for row in resumes:
        row_skill = row["skills"] or ""
        row_exp_json = row["exp_data"] or "{}"
        total_exp = calculate_total_experience(row_exp_json) # Apply only the provided filter
        if skill:
            skill_list = [s.strip().lower() for s in skill.split(",")]
            if not all(s in row_skill.lower() for s in skill_list):
                continue
                # === Experience filter ===
        if exp:
            try:
                if total_exp < float(exp):
                    continue
            except ValueError:
                pass
        filtered_resumes.append(row)

    return render_template(
        "tables.html",
        resumes=filtered_resumes,
        skill=skill,
        exp=exp )



@app.route("/jd_parser", methods=["GET", "POST"])
def jd_parser_view():
    jd_dict = None  # Initialize
    matched_resumes = []
    if request.method == "POST":
        jd_text = ""

        # --- Handle file upload ---
        file = request.files.get("jdFile")
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            temp_path = os.path.join(JD_FOLDER, filename)
            file.save(temp_path)  # Save temporarily

            if filename.lower().endswith(".pdf"):
                jd_text = read_pdf(temp_path)
            elif filename.lower().endswith(".docx"):
                jd_text = read_docx(temp_path)
            else:
                return jsonify({"error": "Unsupported file format"}), 400

        # --- Handle text input ---
        elif "jdText" in request.form and request.form["jdText"].strip() != "":
            jd_text = request.form["jdText"]

        else:
            return jsonify({"error": "No JD provided"}), 400

        # --- Parse JD ---
        jd_dict = parse_job_description(jd_text)

        matched_resumes = calculate_scores_for_all_resumes(jd_dict)

    # GET method will just render the page without data
    return render_template("jd_parser.html", matched_resumes = matched_resumes)


if __name__ == "__main__":
    app.run(debug=True)
