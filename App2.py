import fitz  # PyMuPDF
import pdfplumber
import re
from collections import defaultdict
from experience_calculator import extract_experience_dict, extract_highest_education

# -----------------------------
# Detect Resume Type
# -----------------------------
def detect_resume_type(pdf_path, threshold_ratio=0.3):
    doc = fitz.open(pdf_path)
    page = doc[0]
    blocks = page.get_text("blocks")
    width = page.rect.width

    left_text, right_text = [], []
    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        if not text.strip():
            continue
        if (x0 + x1) / 2 < width / 2:
            left_text.append(text.strip())
        else:
            right_text.append(text.strip())

    left_chars = sum(len(t) for t in left_text)
    right_chars = sum(len(t) for t in right_text)

    if right_chars > 0 and right_chars / (left_chars + 1e-6) > threshold_ratio:
        return "two-column"
    else:
        return "one-column"

# -----------------------------
# Group Words into Lines
# -----------------------------
def group_words_by_line(words, line_tol=3):
    lines = defaultdict(list)
    for w in words:
        line_y = round(w["top"] / line_tol) * line_tol
        lines[line_y].append((w["x0"], w["text"]))

    sorted_lines = sorted(lines.items(), key=lambda kv: kv[0])
    formatted_lines = []
    for _, line_words in sorted_lines:
        line_text = " ".join(word for _, word in sorted(line_words, key=lambda t: t[0]))
        formatted_lines.append(line_text)
    return "\n".join(formatted_lines)

# -----------------------------
# Extract Columns (for 2-col resumes)
# -----------------------------
def extract_columns(pdf_path):
    left_col_text, right_col_text = "", ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            if not words:
                continue

            x0_positions = [w["x0"] for w in words]
            x1_positions = [w["x1"] for w in words]
            sorted_x0 = sorted(x0_positions)

            if len(sorted_x0) < 2:
                continue

            gaps = [
                (sorted_x0[i + 1] - sorted_x0[i], sorted_x0[i], sorted_x0[i + 1])
                for i in range(len(sorted_x0) - 1)
            ]
            biggest_gap = max(gaps, key=lambda g: g[0])
            _, _, right_edge_start = biggest_gap
            left_col_width = max(x1 for x1 in x1_positions if x1 <= right_edge_start)

            left_words = [w for w in words if w["x0"] < left_col_width]
            right_words = [w for w in words if w["x0"] >= left_col_width]

            left_col_text += group_words_by_line(left_words) + "\n\n"
            right_col_text += group_words_by_line(right_words) + "\n\n"

    return left_col_text.strip(), right_col_text.strip()

# -----------------------------
# Extract Full Resume Text
# -----------------------------
def extract_resume_text(pdf_path):
    resume_type = detect_resume_type(pdf_path)

    if resume_type == "two-column":
        left_col_text, right_col_text = extract_columns(pdf_path)
        text_to_search = left_col_text + "\n" + right_col_text
    else:  # one-column
        all_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if text:
                    all_text.append(text)
        text_to_search = "\n".join(all_text)

    return text_to_search

# -----------------------------
# Extract Name, Email, Phone
# -----------------------------
def extract_contact_info(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text()  # Only first page

    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    phone_pattern = r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}"

    email_match = re.search(email_pattern, text)
    phone_match = re.search(phone_pattern, text)

    email = email_match.group() if email_match else "Not found"
    phone = phone_match.group() if phone_match else "Not found"

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = "Not found"
    for line in lines[:5]:  # check first 5 lines
        if not re.search(r"[\d@]", line):
            name = line
            break

    return {"name": name, "email": email, "phone": phone}

# -----------------------------
# Resume Headings Base
# -----------------------------
resume_headings_base = {
    "profile": ["profile", "summary", "objective", "career objective", "about me","about myself", "PROFILE INFO" , "PROFESSIONAL SUMMARY"],
    "experience": ["experience", "professional experience", "work experience", "work experiences",
                   "employment history", "career history", "internship experience"],
    "education": ["education","education background", "academic background", "academic history", "academic experience",
                  "qualifications", "education and training", "educational background"],
    "skills": ["skills", "technical skills", "key skills", "expertise skills",
               "core competencies", "soft skills", "expertise", "digital skills"],
    "projects": ["projects","project", "academic projects", "personal projects", "project experience"],
    "certifications": ["certifications", "certification", "certificates",
                       "licenses & certifications", "training & certifications","certifications and licenses","certifications and courses",
                        "certifications & licenses",
                       "training and certifications", "training"],
    "languages": ["languages", "language", "language proficiency"],
    "awards": ["awards", "honors and awards", "honors & awards",
               "achievements", "accomplishments"],
    "publications": ["publications", "research work", "articles"],
    "volunteer": ["volunteer", "volunteer experience", "community service"],
    "contact": ["contact", "contact information", "personal information", "details"],
    "references": ["references", "reference", "referees", "recommendations"],
    "interests": ["interests", "hobbies", "leisure activities"],
    "portfolio": ["portfolio"],
    "additional information": ["additional information"]
}

def expand_headings_inplace(base_dict):
    for section, headings in base_dict.items():
        variations = []
        for h in headings:
            variations.extend([h, h.upper(), h.title(), h.lower()])
        base_dict[section] = list(set(variations))
    return base_dict

resume_headings_base = expand_headings_inplace(resume_headings_base)

def build_heading_regex():
    heading_to_section = {}
    patterns = []
    for section, headings in resume_headings_base.items():
        for h in headings:
            patterns.append(re.escape(h))
            heading_to_section[h.lower()] = section
    regex = r"(?m)^\s*(?:" + "|".join(sorted(set(patterns))) + r")\s*:?\s*$"
    return regex, heading_to_section

# -----------------------------
# Extract Sections
# -----------------------------
def extract_all_sections(text):
    regex, heading_to_section = build_heading_regex()
    matches = [(m.start(), m.group()) for m in re.finditer(regex, text, re.IGNORECASE)]

    sections = {}
    for i, (start_idx, heading) in enumerate(matches):
        end_idx = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        section_text = text[start_idx:end_idx].strip()

        lines = section_text.splitlines()
        if lines:
            lines = lines[1:]
        section_text = "\n".join(lines).strip()

        section_key = heading_to_section.get(heading.lower(), heading.lower())
        sections[section_key] = section_text

    return sections

# -----------------------------
# Cleaning Helpers
# -----------------------------
def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)  # collapse multiple spaces/newlines
    return text.strip()

def clean_section_dict(sections):
    cleaned_dict = {}

    for raw_key, raw_value in sections.items():
        # ---- Clean keys ----
        key = raw_key.strip()                           # remove leading/trailing spaces/newlines
        key = re.sub(r"\s+", " ", key)                  # collapse multiple spaces/newlines to single space
        key = key.lower()                               # make consistent
        key = key.title()                               # Capitalize properly

        # ---- Clean values ----
        value = raw_value.strip()
        value = re.sub(r"\s+", " ", value)              # collapse multiple spaces/newlines

        cleaned_dict[key] = value

    return cleaned_dict

def build_heading_map(base_dict):
    heading_map = {}
    for base_key, variations in base_dict.items():
        for v in variations:
            heading_map[v.lower().strip()] = base_key
    return heading_map

def normalize_sections(sections, base_dict):
    heading_map = build_heading_map(base_dict)
    normalized = {}
    for raw_key, value in sections.items():
        key = raw_key.lower().strip()
        base_key = heading_map.get(key, key)  # fallback if no match
        # Merge if multiple headings map to same base key
        if base_key in normalized:
            normalized[base_key] += "\n" + value
        else:
            normalized[base_key] = value
    return normalized

# -----------------------------
# Run as Script
# -----------------------------
if __name__ == "__main__":
    pdf_path = r"C:\Users\user\PycharmProjects\ATS\Resume\Hadia Tassadaq - Resume.pdf"  # Replace with your PDF path
    contact_info = extract_contact_info(pdf_path)
    print("=== Contact Info ===")
    print(f"Name: {contact_info['name']}")
    print(f"Email: {contact_info['email']}")
    print(f"Phone: {contact_info['phone']}")

    text_to_search = extract_resume_text(pdf_path)
    print(f"Text to search: {text_to_search}")
    sections = extract_all_sections(text_to_search)

    sections = clean_section_dict(sections)
    sections = normalize_sections(sections, resume_headings_base)


    exp = extract_experience_dict(sections.get("experience"))
    # print(exp)
    edu = extract_highest_education(sections.get("education"))


    #
    # print("=== Extracted Resume Sections ===")
    # for sec, content in sections.items():
    #     print(f"\n{sec.upper()}\n{content if content else 'No content found.'}")