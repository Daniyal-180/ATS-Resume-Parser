import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Regex pattern to catch most formats
DATE_RANGE_REGEX = re.compile(
    r"("
    r"(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})\s*[-–]\s*(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}|present|current|now|till\sdate|ongoing)"
    r"|([A-Za-z]{3,9}[\s\-]?\d{4})\s*[-–]\s*([A-Za-z]{3,9}[\s\-]?\d{4}|present|current|now|till\sdate|ongoing)"
    r"|(\d{4})\s*[-–]\s*(\d{4}|present|current|now|till\sdate|ongoing)"
    r"([A-Za-z]{3,9}\d{4})\s*[-–]\s*([A-Za-z]{3,9}\d{4}|present|current|now|till\sdate|ongoing)"
    r"([A-Za-z]{3,9}\s+\d{4})\s*[-–]\s*([A-Za-z]{3,9}\s+\d{4}|present|current|now|till\sdate|ongoing)"
    r"\b(\d{4})(?:\s*[–-]\s*(\d{4}))?\b"
    r")",
    re.IGNORECASE
)

# Supported date formats
DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%m/%Y", "%m-%Y", "%m.%Y",
    "%b %Y", "%B %Y",
    "%Y"
]


def parse_date(date_str):
    """Convert string into datetime object."""
    date_str = date_str.strip().lower()
    if date_str in ["current", "present", "now", "till date", "ongoing"]:
        return datetime.today()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def extract_date_ranges(block):
    """Extract ALL date ranges from a block."""
    matches = DATE_RANGE_REGEX.finditer(block)
    cleaned = []
    for m in matches:
        groups = [g for g in m.groups() if g]
        if len(groups) >= 2:
            if len(groups) >= 3:
                start, end = groups[1], groups[2]
            else:
                start, end = groups[0], groups[1]
            cleaned.append((start, end))
    return cleaned


def extract_job_role(block, match):
    """Extract job role right before this date match."""
    start_idx = match.start()
    before_text = block[:start_idx].strip()
    parts = re.split(r"[.\n]", before_text)
    last_part = parts[-1].strip() if parts else ""
    last_part = re.sub(r"[\[\]\uf1ad•|]", "", last_part)  # remove icons/symbols
    last_part = re.sub(r"\s{2,}", " ", last_part)  # collapse extra spaces

    return last_part.strip() if last_part else "Role not found"


def calculate_experience(start, end):
    """Calculate duration between two dates (inclusive of start month)."""
    sd, ed = parse_date(start), parse_date(end)
    if sd and ed:
        diff = relativedelta(ed, sd)
        months = diff.years * 12 + diff.months + 1  # ✅ include start month
        return f"{months // 12} years {months % 12} months"
    return "Duration not found"


def extract_experience_dict(text):
    """Return structured dict with role and experience for all ranges."""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    exp_dict = {}
    exp_counter = 1

    for block in blocks:
        for match in DATE_RANGE_REGEX.finditer(block):
            groups = [g for g in match.groups() if g]
            if len(groups) >= 2:
                if len(groups) >= 3:
                    start, end = groups[1], groups[2]
                else:
                    start, end = groups[0], groups[1]

                role = extract_job_role(block, match)
                exp_value = calculate_experience(start, end)

                exp_dict[f"exp_{exp_counter}"] = {
                    "role": role,
                    "exp": exp_value
                }
                exp_counter += 1

    return exp_dict


def calculate_total_experience(exp_data_json):
    try:
        exp_dict = exp_data_json if isinstance(exp_data_json, dict) else json.loads(exp_data_json)
        total_months = 0
        for exp in exp_dict.values():
            months = 0
            years = 0
            if "years" in exp["exp"]:
                years = int(exp["exp"].split("years")[0].strip())
            if "months" in exp["exp"]:
                months_part = exp["exp"].split("years")[-1].replace("months", "").strip()
                if months_part.isdigit():
                    months = int(months_part)
            total_months += years * 12 + months
        return total_months / 12  # in years
    except:
        return 0


def extract_highest_education(edu_text):
    # Normalize text
    edu_text = edu_text.upper()

    # Define education levels in descending priority
    levels = ["PHD", "MASTER","MS","BS", "M.SC", "MSC", "BACHELOR", "BSCS", "BSC", "INTERMEDIATE", "HSC", "MATRIC", "O-LEVEL",
              "A-LEVEL"]

    # Search for levels in text
    found_levels = []
    for level in levels:
        if re.search(r'\b' + re.escape(level) + r'\b', edu_text):
            found_levels.append(level)

    # Return the first match (highest level)
    if found_levels:
        return found_levels[0]
    else:
        return "Not Found"