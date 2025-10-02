import fitz  # PyMuPDF
import pdfplumber
import collections
import re
from collections import defaultdict
from experience_calculator import extract_experience_dict, extract_highest_education, calculate_total_experience
import statistics
from difflib import get_close_matches


# -----------------------------
# Detect Resume Type
# -----------------------------
def detect_resume_type(pdf_path, debug=False):
    """
    Detects if a PDF resume is a one-column or two-column layout using block analysis.
    V4 is tuned for robust detection of sidebar/main-content two-column layouts.
    """
    doc = None
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        blocks = page.get_text("blocks")
        page_w, page_h = page.rect.width, page.rect.height

        total_chars = 0
        clusters_data = []

        # --- Collect block info and filter noise ---
        for b in blocks:
            x0, y0, x1, y1, text, *_ = b
            txt = text.strip()
            if not txt:
                continue

            char_count = len(txt)
            # Filter out very short blocks (e.g., single letters, icons)
            if char_count < 5:
                continue

            block_w = x1 - x0
            # Ignore very wide blocks (likely headers/footers spanning the page)
            if block_w / page_w > 0.95:
                continue

            clusters_data.append({
                "x0": x0,
                "x1": x1,  # Store x1 for gap calculation
                "width": block_w,
                "chars": char_count,
                "ymin": y0,
                "ymax": y1,
                "mid_y": (y0 + y1) / 2
            })
            total_chars += char_count

        if total_chars == 0:
            return "one-column"

        # --- Group by x0 (binning) ---
        clusters_data.sort(key=lambda c: c["x0"])
        grouped, cur = [], None

        # V4 Change: Increased tolerance to handle minor misalignments
        grouping_tolerance = 60

        for c in clusters_data:
            if not cur:
                cur = {k: [c[k]] for k in c}
                cur["chars"] = c["chars"]
            else:
                if abs(statistics.median(cur["x0"]) - c["x0"]) < grouping_tolerance:
                    for k in ["x0", "x1", "width", "ymin", "ymax", "mid_y"]:
                        cur[k].append(c[k])
                    cur["chars"] += c["chars"]
                else:
                    grouped.append(cur)
                    cur = {k: [c[k]] for k in c}
                    cur["chars"] = c["chars"]
        if cur:
            grouped.append(cur)

        # --- Compute cluster stats ---
        proc = []
        for g in grouped:
            char_frac = g["chars"] / total_chars
            # Filter out minor clusters that don't contribute much text
            if char_frac < 0.03 and len(g["x0"]) < 3:
                continue

            x0 = statistics.median(g["x0"])
            x1 = statistics.median(g["x1"])
            width = statistics.median(g["width"])
            ymin, ymax = min(g["ymin"]), max(g["ymax"])
            y_span = ymax - ymin

            proc.append({
                "x0": x0,
                "x1": x1,
                "width": width,
                "char_frac": char_frac,
                "coverage": y_span / page_h,
                "ymin": ymin, "ymax": ymax
            })

        # Sort by char share
        proc.sort(key=lambda c: c["char_frac"], reverse=True)

        if len(proc) < 2:
            return "one-column"

        c1, c2 = proc[0], proc[1]

        # Ensure c1 is always the leftmost cluster
        if c1["x0"] > c2["x0"]:
            c1, c2 = c2, c1

        # Calculate horizontal gap between columns
        gap = c2["x0"] - c1["x1"]

        # Check overlap
        overlap = max(0, min(c1["ymax"], c2["ymax"]) - max(c1["ymin"], c2["ymin"]))
        min_y_span = min(c1["ymax"] - c1["ymin"], c2["ymax"] - c2["ymin"])
        overlap_frac = overlap / min_y_span if min_y_span > 0 else 0

        # --- ROBUST HYBRID CONDITIONS (V4) ---
        is_two_col = (
            # 1. Sufficient total text explained by the two main clusters
                (c1["char_frac"] + c2["char_frac"]) >= 0.60 and

                # 2. Both columns must have significant, even if small, content
                c1["char_frac"] >= 0.05 and  # Leftmost column must be ≥ 5% text
                c2["char_frac"] >= 0.03 and  # Rightmost column must be ≥ 3% text

                # 3. V4 CHANGE: At least ONE of the two columns must cover half the page height.
                max(c1["coverage"], c2["coverage"]) >= 0.50 and

                # 4. At least some vertical overlap (20%)
                overlap_frac >= 0.20 and

                # 5. Right column must start past the 30% mark
                c2["x0"] >= page_w * 0.30 and

                # 6. The horizontal gap must be large (e.g., 5% of page width)
                gap / page_w >= 0.05 and

                # 7. Max width constraint to prevent single-column, highly-indented False Positives.
                max(c1["width"], c2["width"]) / page_w <= 0.70
        )

        result = "two-column" if is_two_col else "one-column"

        if debug:
            return {
                "result": result,
                "clusters": proc,
                "together_frac": c1["char_frac"] + c2["char_frac"],
                "overlap_frac": overlap_frac,
                "c1_char_frac": c1["char_frac"],
                "c2_coverage": c2["coverage"],
                "c1_coverage": c1["coverage"],
                "max_coverage": max(c1["coverage"], c2["coverage"]),
                "gap_ratio": gap / page_w,
                "max_width_ratio": max(c1["width"], c2["width"]) / page_w
            }
        return result

    finally:
        if doc:
            doc.close()

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
    "experience": ["experience", "professional experience", "Work Experience", "work experiences","Projects & Experiences"
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


def fix_spaced_words(text: str) -> str:
    """Fix words like 'E D U C A T I O N' -> 'EDUCATION' (keeps case)."""
    return re.sub(r'(?:[A-Za-z]\s){2,}[A-Za-z]', lambda m: m.group(0).replace(" ", ""), text)

def normalize_headings(text: str) -> str:
    """Normalize headings with inconsistent spacing (e.g. 'Work   Experience')
       but keep original case/formatting.
    """
    for section, variants in resume_headings_base.items():
        for variant in variants:
            # Build regex allowing multiple spaces inside variant
            words = variant.split()
            pattern = r"\s*".join(re.escape(w) for w in words)
            text = re.sub(pattern, lambda m: re.sub(r"\s+", " ", m.group(0)), text, flags=re.I)
    return text

def fix_stuck_headings(text: str) -> str:
    """Fix stuck headings like 'WORKEXPERIENCE' -> 'WORK EXPERIENCE' or
       'WorkExperience' -> 'Work Experience', preserving case style.
    """
    all_headings = sum(resume_headings_base.values(), [])
    normalized_map = {h.lower().replace(" ", ""): h for h in all_headings}

    lines = text.splitlines()
    fixed_lines = []

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            fixed_lines.append(line)
            continue

        # try fuzzy match against normalized headings
        match = get_close_matches(clean_line.lower(), normalized_map.keys(), n=1, cutoff=0.85)
        if match:
            fixed = normalized_map[match[0]]

            # --- preserve formatting style ---
            if clean_line.isupper():
                fixed = fixed.upper()
            elif clean_line.istitle():
                fixed = fixed.title()
            elif clean_line.islower():
                fixed = fixed.lower()
            # else keep mixed formatting as dictionary version

            fixed_lines.append(fixed)
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)

# --- Main preprocessing pipeline (one-argument version) ---
def preprocess_resume_text(text: str) -> str:
    text = fix_spaced_words(text)    # "E D U C A T I O N" -> "EDUCATION"
    text = normalize_headings(text)  # "Work   Experience" -> "Work Experience"
    text = fix_stuck_headings(text)  # "WORKEXPERIENCE" -> "WORK EXPERIENCE"
    return text

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


def remove_phone_numbers(text: str) -> str:
    """
    Removes phone numbers from text (to avoid confusion with years in date extraction).
    """
    # Covers formats like:
    # 0321-1234567, (123) 456-7890, +92 321 1234567, 1234567890
    phone_pattern = r"\+?\d[\d\s().-]{7,}\d"

    # Remove phone numbers
    cleaned = re.sub(phone_pattern, "", text)

    # Clean extra spaces
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    return cleaned


# -----------------------------
# Run as Script
# -----------------------------
if __name__ == "__main__":
    pdf_path = r"C:\Users\user\PycharmProjects\ATS\Resume\Ikram ul haq- resume.pdf"  # Replace with your PDF path
    contact_info = extract_contact_info(pdf_path)
    print("=== Contact Info ===")
    print(f"Name: {contact_info['name']}")
    print(f"Email: {contact_info['email']}")
    print(f"Phone: {contact_info['phone']}")

    text_to_search = extract_resume_text(pdf_path)
    text = preprocess_resume_text(text_to_search)
    # print(text)
    sections = extract_all_sections(text)

    sections = clean_section_dict(sections)
    sections = normalize_sections(sections, resume_headings_base)
    exp = remove_phone_numbers(sections.get("experience"))
    exp = extract_experience_dict(exp)
    print(exp)
    edu = extract_highest_education(sections.get("education"))


    # # # #
    # print("=== Extracted Resume Sections ===")
    # for sec, content in sections.items():
    #     print(f"\n{sec.upper()}\n{content if content else 'No content found.'}")