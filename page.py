from flask import Flask, request, jsonify, render_template, send_file, abort
import io
import json
import os
from werkzeug.utils import secure_filename
from database import init_db, save_resume_to_db, fetch_all_resumes, fetch_resume_from_db
from App2 import extract_contact_info, extract_resume_text, extract_all_sections, normalize_sections, resume_headings_base, clean_section_dict, preprocess_resume_text,remove_phone_numbers
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
            text = preprocess_resume_text(text)
            sections = extract_all_sections(text) # Should return a dict
            sections = clean_section_dict(sections)
            sections = normalize_sections(sections, resume_headings_base)

            exp_text = remove_phone_numbers(sections.get("experience", ""))  # assume normalized section
            exp_dict = extract_experience_dict(exp_text)
            skills = sections.get("skills", "")
            education = extract_highest_education(sections.get("education", ""))
            exp_json = json.dumps(exp_dict) if exp_dict else None
            total_exp = round(calculate_total_experience(exp_json),2)


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
            if not any(s in row_skill.lower() for s in skill_list):
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
        "data.html",
        resumes=filtered_resumes,
        skill=skill,
        exp=exp )




@app.route("/jd_parser", methods=["GET", "POST"])
def jd_parser_view():
    jd_text = ""
    jd_dict = None
    matched_resumes = []

    if request.method == "POST":
        # --- Handle file upload ---
        file = request.files.get("jdFile")
        if file and file.filename:
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
        elif request.form.get("jdText", "").strip():
            jd_text = request.form["jdText"]

        else:
            return render_template("jd_parser.html", matched_resumes=[])

        # --- Parse JD and calculate scores ---
        jd_dict = parse_job_description(jd_text)
        matched_resumes = calculate_scores_for_all_resumes(jd_dict)

    # ✅ Always render page with data (if available)
    return render_template(
        "jd_parser.html",
        matched_resumes=matched_resumes
        # jdText=jd_text  # Keep JD text in textarea
    )


@app.route("/download_resume/<int:resume_id>")
def download_resume(resume_id):
    result = fetch_resume_from_db(resume_id)
    if result:
        file_name, file_data = result
        return send_file(
            io.BytesIO(file_data),
            as_attachment=True,
            download_name=file_name,
            mimetype="application/pdf" if file_name.endswith(".pdf") else
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        abort(404, description="Resume not found")



if __name__ == "__main__":
    app.run(debug=True)
