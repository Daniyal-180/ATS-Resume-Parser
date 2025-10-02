import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json

# ✅ Regex for date ranges only (blocks single years)

MONTHS = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
    r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)

DATE_RANGE_REGEX = re.compile(
    rf"(?P<start>"
    # --- DD/MM/YYYY ---
    r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
    r"|"
    # --- MM/YYYY ---
    r"\d{1,2}[\/\-.]\d{4}"
    r"|"
    # --- Month YYYY / Month, DD, YYYY ---
    rf"(?:{MONTHS})[.,]?\s*\d{{1,2}},?\s*\d{{2,4}}"
    r"|"
    rf"(?:{MONTHS})[.,]?\s*\d{4}"
    r"|"
    # --- Month-YYYY / MonthYYYY / Month.YYYY ---
    rf"(?:{MONTHS})[-.]?\d{{4}}"
    r"|"
    # --- Year ---
    r"\d{4}"
    r")"
    r"\s*(?:-|–|to)\s*"
    r"(?P<end>"
    # same patterns OR present/current
    r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
    r"|\d{1,2}[\/\-.]\d{4}"
    rf"|(?:{MONTHS})[.,]?\s*\d{{1,2}},?\s*\d{{2,4}}"
    rf"|(?:{MONTHS})[.,]?\s*\d{{4}}"
    rf"|(?:{MONTHS})[-.]?\d{{4}}"
    r"|\d{4}"
    r"|present|current|now|till\sdate|ongoing"
    r")",
    re.IGNORECASE
)



# Supported date formats
DATE_FORMATS = [
    # Day/Month/Year
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    # Month/Year numeric
    "%m/%Y", "%m-%Y", "%m.%Y",
    # Month name formats
    "%b %Y", "%B %Y",
    "%b. %Y", "%B. %Y",
    "%b-%Y", "%B-%Y",
    "%b%Y", "%B%Y",
    "%b.%Y", "%B.%Y",
    # Month Day, Year
    "%B %d, %Y", "%b %d, %Y",
    # Compact
    "%b%Y", "%B%Y",
    # Year only
    "%Y"
]



def parse_date(date_str):
    """Convert string into datetime object."""
    date_str = date_str.strip().lower().replace("(", "").replace(")", "")
    if date_str in ["current", "present", "now", "till date", "ongoing"]:
        return datetime.today()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def extract_job_role(block, match):
    """Extract job role right before this date match."""
    start_idx = match.start()
    before_text = block[:start_idx].strip()
    parts = re.split(r"[.\n]", before_text)
    last_part = parts[-1].strip() if parts else ""
    last_part = re.sub(r"[\[\]\uf1ad•|]", "", last_part)  # remove icons/symbols
    last_part = re.sub(r"\s{2,}", " ", last_part)  # collapse spaces
    return last_part.strip() if last_part else "Role not found"


def calculate_experience(start, end):
    """Calculate duration between two dates (inclusive of start month)."""
    sd, ed = parse_date(start), parse_date(end)
    if not sd:
        return "Duration not found"

        # If end date is missing -> fixed 1 year
    if not ed:
        return "1 years 0 months"

        # Otherwise calculate normally
    diff = relativedelta(ed, sd)
    months = diff.years * 12 + diff.months
    return f"{months // 12} years {months % 12} months"


def extract_experience_dict(text):
    """Return structured dict with role and experience for all ranges."""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

    exp_dict = {}
    exp_counter = 1

    for block in blocks:
        for match in DATE_RANGE_REGEX.finditer(block):
            start, end = match.group("start"), match.group("end")
            role = extract_job_role(block, match)
            exp_value = calculate_experience(start, end)

            exp_dict[f"exp_{exp_counter}"] = {
                "role": role,
                "start_date": start,
                "end_date": end,
                "exp": exp_value
            }
            exp_counter += 1

    for year_match in re.finditer(r"\b(19|20)\d{2}\b", block):
        year_str = year_match.group(0)
        # Skip if this year already inside a matched range
        if any(year_str in m.group(0) for m in DATE_RANGE_REGEX.finditer(block)):
            continue

        role = extract_job_role(block, year_match)
        exp_dict[f"exp_{exp_counter}"] = {
            "role": role,
            "start_date": year_str,
            "end_date": "",
            "exp": "1 years 0 months"  # ✅ auto-assign 1 year
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
        return total_months / 12
    except:
        return 0


def extract_highest_education(edu_text):
    edu_text = edu_text.upper()
    levels = [
        "PHD", "MASTER", "MS", "BS", "M.SC", "MSC",
        "BACHELOR", "BSCS", "BSC",
        "INTERMEDIATE", "HSC",
        "MATRIC", "O-LEVEL", "A-LEVEL"
    ]
    found_levels = []
    for level in levels:
        if re.search(r'\b' + re.escape(level) + r'\b', edu_text):
            found_levels.append(level)
    return found_levels[0] if found_levels else "Not Found"


# print(extract_experience_dict("""EXPERIENCE BISTARTX |AIDEVELOPMENTINTERN Feb2025–Mar2025|Remote • AssistedinbuildingAImodelsandautomatingdatapipelines. • AssigntotrainmodelsondifferentDataset AQUAFARM(GOVTSTARTUP) |ASSISTANTDATASCIENTIST 2023 • Collected,organized,andanalyzeddataforfarmyieldpredictions. • PreparedregularreportsinExcelandGoogleSheetsforstakeholders. TOPLINEMARKETINGPVTLTD |SALESEXECUTIVE Sep2021–Feb2022|Islamabad,PK • Communicatedwithcustomersthroughemailanddigitalplatforms. • FollowupswithClients"""))