import pdfplumber
import fitz
pdf_path = r"Resume/Hadia Tassadaq - Resume.pdf"
def detect_resume_type(pdf_path, threshold_ratio=0.3, min_block_width_ratio=0.35):
    doc = fitz.open(pdf_path)
    page = doc[0]
    blocks = page.get_text("blocks")
    width = page.rect.width

    left_text, right_text = [], []
    left_area, right_area = 0, 0

    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        if not text.strip():
            continue

        block_width = (x1 - x0) / width

        # Ignore tiny right-aligned blocks (like "Rawalpindi, Pakistan", "2022 – Present")
        if block_width < 0.15 and (x0 > width * 0.55):
            continue

        if (x0 + x1) / 2 < width / 2:
            left_text.append(text.strip())
            left_area += (x1 - x0) * (y1 - y0)
        else:
            right_text.append(text.strip())
            right_area += (x1 - x0) * (y1 - y0)

    left_chars = sum(len(t) for t in left_text)
    right_chars = sum(len(t) for t in right_text)

    # Check both character ratio and coverage area
    if right_chars > 0 and right_chars / (left_chars + 1e-6) > threshold_ratio and right_area / (left_area + 1e-6) > 0.3:
        return "two-column"
    else:
        return "one-column"




with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
    print(text)