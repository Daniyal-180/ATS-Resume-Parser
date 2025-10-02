# import fitz
# import statistics
# import os, collections
#
# # -----------------------------
# # Detect Resume Type
# # -----------------------------
# def detect_resume_type(pdf_path, x_bin_size=5, min_column_char_ratio=0.03, min_separation_pt=80):
#     """
#     Improved detection of one-column vs two-column resumes.
#     """
#     try:
#         doc = fitz.open(pdf_path)
#         page = doc[0]
#         blocks = page.get_text("blocks")
#         width = page.rect.width
#
#         # Collect bins with chars + raw x0 positions
#         x0_data = collections.defaultdict(lambda: {"chars": 0, "x0s": []})
#         total_chars = 0
#
#         for b in blocks:
#             x0, y0, x1, y1, text, *_ = b
#             clean_text = text.strip()
#             if not clean_text:
#                 continue
#
#             char_count = len(clean_text)
#             block_width_ratio = (x1 - x0) / width
#
#             # Keep short lines (>= 3 chars), ignore huge full-width blocks
#             if char_count < 2 or block_width_ratio > 0.8:
#                 continue
#
#             x0_binned = int(x0 / x_bin_size) * x_bin_size
#             x0_data[x0_binned]["chars"] += char_count
#             x0_data[x0_binned]["x0s"].append(x0)
#             total_chars += char_count
#
#         if total_chars == 0:
#             return "one-column"
#
#         # Merge nearby bins → clusters
#         sorted_x0s = sorted(x0_data.keys())
#         clusters = []
#         current_chars, current_x0s = 0, []
#
#         for x in sorted_x0s:
#             if not current_x0s or (x - current_x0s[-1] < x_bin_size * 2):
#                 current_chars += x0_data[x]["chars"]
#                 current_x0s.extend(x0_data[x]["x0s"])
#             else:
#                 clusters.append({"chars": current_chars, "x0": sum(current_x0s)/len(current_x0s)})
#                 current_chars = x0_data[x]["chars"]
#                 current_x0s = list(x0_data[x]["x0s"])
#
#         if current_x0s:
#             clusters.append({"chars": current_chars, "x0": sum(current_x0s)/len(current_x0s)})
#
#         # Sort clusters by size
#         clusters.sort(key=lambda c: c["chars"], reverse=True)
#
#         # Keep only dominant clusters
#         dominant = [c for c in clusters if c["chars"]/total_chars >= min_column_char_ratio]
#
#         if len(dominant) < 2:
#             return "one-column"
#
#         # Check if columns are far enough apart
#         col1, col2 = dominant[0], dominant[1]
#         if abs(col1["x0"] - col2["x0"]) >= min_separation_pt:
#             return "two-column"
#         return "one-column"
#
#     except Exception as e:
#         return f"error: {e}"
#     finally:
#         if 'doc' in locals():
#             doc.close()
#
#
# import fitz
# # import collections # Not used in the function, can be removed
# import statistics
# import os
#
#
# def detect_resume_type_hybrid_optimized(pdf_path, debug=False):
#     """
#     Detects if a PDF resume is a one-column or two-column layout using block analysis.
#     Optimized for modern, slightly unbalanced two-column layouts.
#     """
#     try:
#         doc = fitz.open(pdf_path)
#         page = doc[0]
#         blocks = page.get_text("blocks")
#         page_w, page_h = page.rect.width, page.rect.height
#
#         total_chars = 0
#         clusters_data = []
#
#         # --- Collect block info ---
#         for b in blocks:
#             x0, y0, x1, y1, text, *_ = b
#             txt = text.strip()
#             if not txt:
#                 continue
#             char_count = len(txt)
#             if char_count < 3:
#                 continue
#
#             block_w = x1 - x0
#             if block_w / page_w > 0.92:  # ignore headers/footers
#                 continue
#
#             clusters_data.append({
#                 "x0": x0,
#                 "width": block_w,
#                 "chars": char_count,
#                 "ymin": y0,
#                 "ymax": y1,
#             })
#             total_chars += char_count
#
#         if total_chars == 0:
#             return "one-column"
#
#         # --- Group by x0 (rough binning) ---
#         clusters_data.sort(key=lambda c: c["x0"])
#         grouped, cur = [], None
#         for c in clusters_data:
#             if not cur:
#                 cur = {k: [c[k]] if isinstance(c[k], (int, float)) else [c[k]] for k in c}
#                 cur["chars"] = c["chars"]
#             else:
#                 # Increased tolerance slightly to 50 for robust grouping
#                 if abs(statistics.median(cur["x0"]) - c["x0"]) < 50:
#                     for k in ["x0", "width", "ymin", "ymax"]:
#                         cur[k].append(c[k])
#                     cur["chars"] += c["chars"]
#                 else:
#                     grouped.append(cur)
#                     cur = {k: [c[k]] if isinstance(c[k], (int, float)) else [c[k]] for k in c}
#                     cur["chars"] = c["chars"]
#         if cur:
#             grouped.append(cur)
#
#         # --- Compute cluster stats ---
#         proc = []
#         for g in grouped:
#             x0 = statistics.median(g["x0"])
#             width = statistics.median(g["width"])
#             ymin, ymax = min(g["ymin"]), max(g["ymax"])
#             y_span = ymax - ymin
#
#             # Filter out clusters that are too small to be a column (less than 2% of total text)
#             char_frac = g["chars"] / total_chars
#             if char_frac < 0.02 and len(g["x0"]) < 3:  # Ignore tiny noise blocks
#                 continue
#
#             proc.append({
#                 "x0": x0,
#                 "width": width,
#                 "char_frac": char_frac,
#                 "coverage": y_span / page_h,
#                 "ymin": ymin, "ymax": ymax
#             })
#
#         # Sort by char share
#         proc.sort(key=lambda c: c["char_frac"], reverse=True)
#
#         if len(proc) < 2:
#             return "one-column"
#
#         # c1 and c2 are the two most content-dominant clusters
#         c1, c2 = proc[0], proc[1]
#
#         # Ensure c1 is always the leftmost cluster for consistent checks
#         if c1["x0"] > c2["x0"]:
#             c1, c2 = c2, c1
#
#         # --- OPTIMIZED HYBRID CONDITIONS ---
#         together_frac = c1["char_frac"] + c2["char_frac"]
#         overlap = max(0, min(c1["ymax"], c2["ymax"]) - max(c1["ymin"], c2["ymin"]))
#
#         # Check overlap against the vertical span of the shorter column
#         min_y_span = min(c1["ymax"] - c1["ymin"], c2["ymax"] - c2["ymin"])
#         overlap_frac = overlap / min_y_span if min_y_span > 0 else 0
#
#         is_two_col = (
#                 together_frac >= 0.75 and  # 1. 75%+ of text explained (Good threshold)
#
#                 c1["coverage"] >= 0.5 and  # 2. Left column must cover half the page height (The main block)
#                 c2["coverage"] >= 0.20 and  # 3. Right column/sidebar can be shorter (20% coverage) ⬅️ RELAXED
#
#                 overlap_frac >= 0.2 and  # 4. At least some vertical overlap (20%) (Good threshold)
#                 c2["x0"] >= page_w * 0.35 and  # 5. Right column must start past the 35% mark (Good separation)
#
#                 c1["char_frac"] >= 0.05 and  # 6. Left column must be at least 5% text ⬅️ RELAXED (Was 0.1)
#                 c2["char_frac"] >= 0.05 and  # 7. Right column must be at least 5% text (Was 0.05)
#
#                 # 8. CRITICAL NEW CHECK: The widest of the two columns cannot dominate the page width.
#                 # This prevents heavily indented single-column resumes from being false positives.
#                 max(c1["width"], c2["width"]) / page_w <= 0.65
#         )
#
#         result = "two-column" if is_two_col else "one-column"
#
#         if debug:
#             return {
#                 "result": result,
#                 "clusters": proc,
#                 "together_frac": together_frac,
#                 "overlap_frac": overlap_frac,
#                 "c1_width_ratio": c1["width"] / page_w,
#                 "c2_coverage": c2["coverage"]
#             }
#         return result
#
#     except Exception as e:
#         # Simple error handling for file issues
#         return f"error: {type(e).__name__}: {str(e)}"
#     finally:
#         if 'doc' in locals():
#             doc.close()
#
# def detect_resume_type_hybrid1(pdf_path, debug=False):
#     try:
#         doc = fitz.open(pdf_path)
#         page = doc[0]
#         blocks = page.get_text("blocks")
#         page_w, page_h = page.rect.width, page.rect.height
#
#         total_chars = 0
#         clusters = []
#
#         # --- Collect block info ---
#         for b in blocks:
#             x0, y0, x1, y1, text, *_ = b
#             txt = text.strip()
#             if not txt:
#                 continue
#             char_count = len(txt)
#             if char_count < 3:
#                 continue
#
#             block_w = x1 - x0
#             if block_w / page_w > 0.92:  # ignore headers/footers
#                 continue
#
#             clusters.append({
#                 "x0": x0,
#                 "width": block_w,
#                 "chars": char_count,
#                 "ymin": y0,
#                 "ymax": y1,
#             })
#             total_chars += char_count
#
#         if total_chars == 0:
#             return "one-column"
#
#         # --- Group by x0 (rough binning) ---
#         clusters.sort(key=lambda c: c["x0"])
#         grouped = []
#         cur = None
#         for c in clusters:
#             if not cur:
#                 cur = {k: [c[k]] if isinstance(c[k], (int, float)) else [c[k]] for k in c}
#                 cur["chars"] = c["chars"]
#             else:
#                 if abs(statistics.median(cur["x0"]) - c["x0"]) < 40:  # close in x
#                     for k in ["x0", "width", "ymin", "ymax"]:
#                         cur[k].append(c[k])
#                     cur["chars"] += c["chars"]
#                 else:
#                     grouped.append(cur)
#                     cur = {k: [c[k]] if isinstance(c[k], (int, float)) else [c[k]] for k in c}
#                     cur["chars"] = c["chars"]
#         if cur:
#             grouped.append(cur)
#
#         # --- Compute cluster stats ---
#         proc = []
#         for g in grouped:
#             x0 = statistics.median(g["x0"])
#             width = statistics.median(g["width"])
#             ymin, ymax = min(g["ymin"]), max(g["ymax"])
#             y_span = ymax - ymin
#             proc.append({
#                 "x0": x0,
#                 "width": width,
#                 "char_frac": g["chars"] / total_chars,
#                 "coverage": y_span / page_h,
#                 "ymin": ymin, "ymax": ymax
#             })
#
#         proc.sort(key=lambda c: c["char_frac"], reverse=True)
#
#         if len(proc) < 2:
#             return "one-column"
#
#         c1, c2 = proc[0], proc[1]
#         if c1["x0"] > c2["x0"]:
#             c1, c2 = c2, c1
#
#         # --- Scoring System ---
#         score = 0
#         together_frac = c1["char_frac"] + c2["char_frac"]
#         overlap = max(0, min(c1["ymax"], c2["ymax"]) - max(c1["ymin"], c2["ymin"]))
#         overlap_frac = overlap / min(c1["ymax"] - c1["ymin"], c2["ymax"] - c2["ymin"])
#
#         if c1["coverage"] >= 0.5 and c2["coverage"] >= 0.2:
#             score += 2
#         if together_frac >= 0.8:
#             score += 2
#         if overlap_frac >= 0.2:
#             score += 1
#         if c2["x0"] >= page_w * 0.25:
#             score += 1
#         if max(c1["width"], c2["width"]) / page_w > 0.65:
#             score -= 2  # penalty
#
#         result = "two-column" if score >= 3 else "one-column"
#
#         if debug:
#             return {
#                 "result": result,
#                 "clusters": proc,
#                 "together_frac": together_frac,
#                 "overlap_frac": overlap_frac,
#                 "score": score
#             }
#         return result
#
#     finally:
#         if 'doc' in locals():
#             doc.close()
#
# # The necessary imports are already defined by the user
# # The final code is inside the function detect_resume_type_hybrid_optimized
# import fitz
# import statistics
#
#
# def detect_resume_type_hybrid2(pdf_path, debug=False):
#     """
#     Detects if a PDF resume is a one-column or two-column layout using block analysis.
#     Uses robust, tuned conditions for high accuracy.
#     """
#     try:
#         doc = fitz.open(pdf_path)
#         page = doc[0]
#         blocks = page.get_text("blocks")
#         page_w, page_h = page.rect.width, page.rect.height
#
#         total_chars = 0
#         clusters_data = []
#
#         # --- Collect block info ---
#         for b in blocks:
#             x0, y0, x1, y1, text, *_ = b
#             txt = text.strip()
#             if not txt:
#                 continue
#             char_count = len(txt)
#             if char_count < 3:
#                 continue
#
#             block_w = x1 - x0
#             # Keep ignoring wide headers/footers
#             if block_w / page_w > 0.92:
#                 continue
#
#             clusters_data.append({
#                 "x0": x0,
#                 "width": block_w,
#                 "chars": char_count,
#                 "ymin": y0,
#                 "ymax": y1,
#             })
#             total_chars += char_count
#
#         if total_chars == 0:
#             return "one-column"
#
#         # --- Group by x0 (rough binning) ---
#         clusters_data.sort(key=lambda c: c["x0"])
#         grouped, cur = [], None
#         # Use the original 40 tolerance
#         grouping_tolerance = 40
#
#         for c in clusters_data:
#             if not cur:
#                 cur = {k: [c[k]] if isinstance(c[k], (int, float)) else [c[k]] for k in c}
#                 cur["chars"] = c["chars"]
#             else:
#                 if abs(statistics.median(cur["x0"]) - c["x0"]) < grouping_tolerance:
#                     for k in ["x0", "width", "ymin", "ymax"]:
#                         cur[k].append(c[k])
#                     cur["chars"] += c["chars"]
#                 else:
#                     grouped.append(cur)
#                     cur = {k: [c[k]] if isinstance(c[k], (int, float)) else [c[k]] for k in c}
#                     cur["chars"] = c["chars"]
#         if cur:
#             grouped.append(cur)
#
#         # --- Compute cluster stats ---
#         proc = []
#         for g in grouped:
#             # Filter out very minor clusters (less than 3% text share and few blocks)
#             char_frac = g["chars"] / total_chars
#             if char_frac < 0.03 and len(g["x0"]) < 3:
#                 continue
#
#             x0 = statistics.median(g["x0"])
#             width = statistics.median(g["width"])
#             ymin, ymax = min(g["ymin"]), max(g["ymax"])
#             y_span = ymax - ymin
#             proc.append({
#                 "x0": x0,
#                 "width": width,
#                 "char_frac": char_frac,
#                 "coverage": y_span / page_h,
#                 "ymin": ymin, "ymax": ymax
#             })
#
#         # Sort by char share
#         proc.sort(key=lambda c: c["char_frac"], reverse=True)
#
#         if len(proc) < 2:
#             return "one-column"
#
#         c1, c2 = proc[0], proc[1]
#
#         # Ensure c1 is always the leftmost cluster for consistent checks
#         if c1["x0"] > c2["x0"]:
#             c1, c2 = c2, c1
#
#         # --- ROBUST HYBRID CONDITIONS ---
#         together_frac = c1["char_frac"] + c2["char_frac"]
#         overlap = max(0, min(c1["ymax"], c2["ymax"]) - max(c1["ymin"], c2["ymin"]))
#
#         # Check overlap against the vertical span of the shorter column
#         min_y_span = min(c1["ymax"] - c1["ymin"], c2["ymax"] - c2["ymin"])
#         overlap_frac = overlap / min_y_span if min_y_span > 0 else 0
#
#         is_two_col = (
#                 together_frac >= 0.75 and  # 1. 75%+ of text explained (Same as original)
#
#                 # 2. Both columns must have significant content (This was missing/weak in scoring)
#                 c1["char_frac"] >= 0.10 and  # Main column must be ≥ 10% text
#                 c2["char_frac"] >= 0.05 and  # Sidebar must be ≥ 5% text
#
#                 c1["coverage"] >= 0.50 and  # 3. Main column must cover half the page height
#                 c2["coverage"] >= 0.20 and  # 4. Sidebar can be shorter (20% coverage) ⬅️ Relaxed for short sidebars
#
#                 overlap_frac >= 0.20 and  # 5. At least some vertical overlap (20%)
#
#                 # 6. Right column must start past the 35% mark (Stricter than your score of 25%)
#                 c2["x0"] >= page_w * 0.35 and
#
#                 # 7. CRITICAL: The widest of the two columns cannot dominate the page width.
#                 # This prevents single-column, highly-indented False Positives.
#                 max(c1["width"], c2["width"]) / page_w <= 0.65
#         )
#
#         result = "two-column" if is_two_col else "one-column"
#
#         if debug:
#             return {
#                 "result": result,
#                 "clusters": proc,
#                 "together_frac": together_frac,
#                 "overlap_frac": overlap_frac,
#                 "c1_char_frac": c1["char_frac"],
#                 "c2_coverage": c2["coverage"],
#                 "max_width_ratio": max(c1["width"], c2["width"]) / page_w
#             }
#         return result
#
#     finally:
#         if 'doc' in locals():
#             doc.close()
#
#
# import fitz
# import statistics
#
#
# def detect_resume_type_hybrid3(pdf_path, debug=False):
#     """
#     Detects if a PDF resume is a one-column or two-column layout using block analysis.
#     Uses robust, tuned conditions for high accuracy, with a focus on distinguishing
#     true columns from indented one-column layouts.
#     """
#     doc = None
#     try:
#         doc = fitz.open(pdf_path)
#         page = doc[0]
#         blocks = page.get_text("blocks")
#         page_w, page_h = page.rect.width, page.rect.height
#
#         total_chars = 0
#         clusters_data = []
#
#         # --- Collect block info and filter noise ---
#         for b in blocks:
#             x0, y0, x1, y1, text, *_ = b
#             txt = text.strip()
#             if not txt:
#                 continue
#
#             char_count = len(txt)
#             # Filter out very short blocks (e.g., single letters, icons)
#             if char_count < 5:
#                 continue
#
#             block_w = x1 - x0
#             # Ignore very wide blocks (likely headers/footers spanning the page)
#             if block_w / page_w > 0.95:
#                 continue
#
#             clusters_data.append({
#                 "x0": x0,
#                 "x1": x1,  # Store x1 for gap calculation
#                 "width": block_w,
#                 "chars": char_count,
#                 "ymin": y0,
#                 "ymax": y1,
#                 "mid_y": (y0 + y1) / 2
#             })
#             total_chars += char_count
#
#         if total_chars == 0:
#             return "one-column"
#
#         # --- Group by x0 (binning) ---
#         clusters_data.sort(key=lambda c: c["x0"])
#         grouped, cur = [], None
#         # Increased tolerance to handle minor misalignments
#         grouping_tolerance = 50
#
#         for c in clusters_data:
#             if not cur:
#                 cur = {k: [c[k]] for k in c}
#                 cur["chars"] = c["chars"]
#             else:
#                 # Group if the current block's start is close to the median start of the cluster
#                 if abs(statistics.median(cur["x0"]) - c["x0"]) < grouping_tolerance:
#                     for k in ["x0", "x1", "width", "ymin", "ymax", "mid_y"]:
#                         cur[k].append(c[k])
#                     cur["chars"] += c["chars"]
#                 else:
#                     grouped.append(cur)
#                     cur = {k: [c[k]] for k in c}
#                     cur["chars"] = c["chars"]
#         if cur:
#             grouped.append(cur)
#
#         # --- Compute cluster stats ---
#         proc = []
#         for g in grouped:
#             char_frac = g["chars"] / total_chars
#             # Filter out minor clusters that don't contribute much text
#             if char_frac < 0.03 and len(g["x0"]) < 3:
#                 continue
#
#             x0 = statistics.median(g["x0"])
#             x1 = statistics.median(g["x1"])
#             width = statistics.median(g["width"])
#             ymin, ymax = min(g["ymin"]), max(g["ymax"])
#             y_span = ymax - ymin
#
#             # Weighted average for better representation of overall cluster width
#             weighted_width = sum(w * c['chars'] for w, c in zip(g["width"], clusters_data) if c['x0'] in g['x0']) / g[
#                 "chars"]
#
#             proc.append({
#                 "x0": x0,
#                 "x1": x1,
#                 "width": width,
#                 "char_frac": char_frac,
#                 "coverage": y_span / page_h,
#                 "ymin": ymin, "ymax": ymax
#             })
#
#         # Sort by char share
#         proc.sort(key=lambda c: c["char_frac"], reverse=True)
#
#         # We need at least two significant clusters
#         if len(proc) < 2:
#             return "one-column"
#
#         c1, c2 = proc[0], proc[1]
#
#         # Ensure c1 is always the leftmost cluster
#         if c1["x0"] > c2["x0"]:
#             c1, c2 = c2, c1
#
#         # Calculate horizontal gap between columns
#         # c1 ends at c1["x1"], c2 starts at c2["x0"]
#         # Ensure c1 is truly on the left
#         gap = c2["x0"] - c1["x1"]
#
#         # Check overlap
#         overlap = max(0, min(c1["ymax"], c2["ymax"]) - max(c1["ymin"], c2["ymin"]))
#         min_y_span = min(c1["ymax"] - c1["ymin"], c2["ymax"] - c2["ymin"])
#         overlap_frac = overlap / min_y_span if min_y_span > 0 else 0
#
#         # --- ROBUST HYBRID CONDITIONS (V3) ---
#         is_two_col = (
#             # 1. Sufficient total text explained by the two main clusters
#                 (c1["char_frac"] + c2["char_frac"]) >= 0.60 and
#
#                 # 2. Both columns must have significant, even if small, content
#                 c1["char_frac"] >= 0.05 and  # Main column must be ≥ 5% text
#                 c2["char_frac"] >= 0.03 and  # Sidebar must be ≥ 3% text
#
#                 # 3. Main column must cover a decent portion of the page height
#                 c1["coverage"] >= 0.40 and
#
#                 # 4. At least some vertical overlap (20%)
#                 overlap_frac >= 0.20 and
#
#                 # 5. Right column must start past the 30% mark to be considered a column
#                 c2["x0"] >= page_w * 0.30 and
#
#                 # 6. CRITICAL: The horizontal gap must be large (e.g., 5% of page width)
#                 # This distinguishes true columns from slight indentations.
#                 gap / page_w >= 0.05 and
#
#                 # 7. CRITICAL: Max width constraint to prevent one-column resumes with deep indentation
#                 # from being split into two clusters, where one cluster (the body) is very wide.
#                 max(c1["width"], c2["width"]) / page_w <= 0.70
#         )
#
#         result = "two-column" if is_two_col else "one-column"
#
#         if debug:
#             return {
#                 "result": result,
#                 "clusters": proc,
#                 "together_frac": c1["char_frac"] + c2["char_frac"],
#                 "overlap_frac": overlap_frac,
#                 "c1_char_frac": c1["char_frac"],
#                 "c2_coverage": c2["coverage"],
#                 "gap_ratio": gap / page_w,
#                 "max_width_ratio": max(c1["width"], c2["width"]) / page_w
#             }
#         return result
#
#     finally:
#         if doc:
#             doc.close()
#
#
# import fitz
# import statistics
#
#
# def detect_resume_type_hybrid4(pdf_path, debug=False):
#     """
#     Detects if a PDF resume is a one-column or two-column layout using block analysis.
#     V4 is tuned for robust detection of sidebar/main-content two-column layouts.
#     """
#     doc = None
#     try:
#         doc = fitz.open(pdf_path)
#         page = doc[0]
#         blocks = page.get_text("blocks")
#         page_w, page_h = page.rect.width, page.rect.height
#
#         total_chars = 0
#         clusters_data = []
#
#         # --- Collect block info and filter noise ---
#         for b in blocks:
#             x0, y0, x1, y1, text, *_ = b
#             txt = text.strip()
#             if not txt:
#                 continue
#
#             char_count = len(txt)
#             # Filter out very short blocks (e.g., single letters, icons)
#             if char_count < 5:
#                 continue
#
#             block_w = x1 - x0
#             # Ignore very wide blocks (likely headers/footers spanning the page)
#             if block_w / page_w > 0.95:
#                 continue
#
#             clusters_data.append({
#                 "x0": x0,
#                 "x1": x1,  # Store x1 for gap calculation
#                 "width": block_w,
#                 "chars": char_count,
#                 "ymin": y0,
#                 "ymax": y1,
#                 "mid_y": (y0 + y1) / 2
#             })
#             total_chars += char_count
#
#         if total_chars == 0:
#             return "one-column"
#
#         # --- Group by x0 (binning) ---
#         clusters_data.sort(key=lambda c: c["x0"])
#         grouped, cur = [], None
#
#         # V4 Change: Increased tolerance to handle minor misalignments
#         grouping_tolerance = 60
#
#         for c in clusters_data:
#             if not cur:
#                 cur = {k: [c[k]] for k in c}
#                 cur["chars"] = c["chars"]
#             else:
#                 if abs(statistics.median(cur["x0"]) - c["x0"]) < grouping_tolerance:
#                     for k in ["x0", "x1", "width", "ymin", "ymax", "mid_y"]:
#                         cur[k].append(c[k])
#                     cur["chars"] += c["chars"]
#                 else:
#                     grouped.append(cur)
#                     cur = {k: [c[k]] for k in c}
#                     cur["chars"] = c["chars"]
#         if cur:
#             grouped.append(cur)
#
#         # --- Compute cluster stats ---
#         proc = []
#         for g in grouped:
#             char_frac = g["chars"] / total_chars
#             # Filter out minor clusters that don't contribute much text
#             if char_frac < 0.03 and len(g["x0"]) < 3:
#                 continue
#
#             x0 = statistics.median(g["x0"])
#             x1 = statistics.median(g["x1"])
#             width = statistics.median(g["width"])
#             ymin, ymax = min(g["ymin"]), max(g["ymax"])
#             y_span = ymax - ymin
#
#             proc.append({
#                 "x0": x0,
#                 "x1": x1,
#                 "width": width,
#                 "char_frac": char_frac,
#                 "coverage": y_span / page_h,
#                 "ymin": ymin, "ymax": ymax
#             })
#
#         # Sort by char share
#         proc.sort(key=lambda c: c["char_frac"], reverse=True)
#
#         if len(proc) < 2:
#             return "one-column"
#
#         c1, c2 = proc[0], proc[1]
#
#         # Ensure c1 is always the leftmost cluster
#         if c1["x0"] > c2["x0"]:
#             c1, c2 = c2, c1
#
#         # Calculate horizontal gap between columns
#         gap = c2["x0"] - c1["x1"]
#
#         # Check overlap
#         overlap = max(0, min(c1["ymax"], c2["ymax"]) - max(c1["ymin"], c2["ymin"]))
#         min_y_span = min(c1["ymax"] - c1["ymin"], c2["ymax"] - c2["ymin"])
#         overlap_frac = overlap / min_y_span if min_y_span > 0 else 0
#
#         # --- ROBUST HYBRID CONDITIONS (V4) ---
#         is_two_col = (
#             # 1. Sufficient total text explained by the two main clusters
#                 (c1["char_frac"] + c2["char_frac"]) >= 0.60 and
#
#                 # 2. Both columns must have significant, even if small, content
#                 c1["char_frac"] >= 0.05 and  # Leftmost column must be ≥ 5% text
#                 c2["char_frac"] >= 0.03 and  # Rightmost column must be ≥ 3% text
#
#                 # 3. V4 CHANGE: At least ONE of the two columns must cover half the page height.
#                 max(c1["coverage"], c2["coverage"]) >= 0.50 and
#
#                 # 4. At least some vertical overlap (20%)
#                 overlap_frac >= 0.20 and
#
#                 # 5. Right column must start past the 30% mark
#                 c2["x0"] >= page_w * 0.30 and
#
#                 # 6. The horizontal gap must be large (e.g., 5% of page width)
#                 gap / page_w >= 0.05 and
#
#                 # 7. Max width constraint to prevent single-column, highly-indented False Positives.
#                 max(c1["width"], c2["width"]) / page_w <= 0.70
#         )
#
#         result = "two-column" if is_two_col else "one-column"
#
#         if debug:
#             return {
#                 "result": result,
#                 "clusters": proc,
#                 "together_frac": c1["char_frac"] + c2["char_frac"],
#                 "overlap_frac": overlap_frac,
#                 "c1_char_frac": c1["char_frac"],
#                 "c2_coverage": c2["coverage"],
#                 "c1_coverage": c1["coverage"],
#                 "max_coverage": max(c1["coverage"], c2["coverage"]),
#                 "gap_ratio": gap / page_w,
#                 "max_width_ratio": max(c1["width"], c2["width"]) / page_w
#             }
#         return result
#
#     finally:
#         if doc:
#             doc.close()
#
# resume_folder = r"C:\Users\user\PycharmProjects\ATS\Resume"
#
# # Loop through all PDF files in the folder
# for file in os.listdir(resume_folder):
#     if file.lower().endswith(".pdf"):
#         pdf_path = os.path.join(resume_folder, file)
#         resume_type = detect_resume_type_hybrid4(pdf_path)
#         print(f"{file} → {resume_type}")

import re
from difflib import get_close_matches

HEADINGS = {
    "profile": ["profile", "summary", "objective", "career objective", "about me", "about myself",
                "profile info", "professional summary"],
    "experience": ["experience", "professional experience", "work experience", "work experiences",
                   "projects & experiences", "employment history", "career history", "internship experience"],
    "education": ["education", "education background", "academic background", "academic history",
                  "academic experience", "qualifications", "education and training", "educational background"],
    "skills": ["skills", "technical skills", "key skills", "expertise skills", "core competencies",
               "soft skills", "expertise", "digital skills"],
    "projects": ["projects", "project", "academic projects", "personal projects", "project experience"],
    "certifications": ["certifications", "certification", "certificates", "licenses & certifications",
                       "training & certifications", "certifications and licenses", "certifications and courses",
                       "certifications & licenses", "training and certifications", "training"],
    "languages": ["languages", "language", "language proficiency"],
    "awards": ["awards", "honors and awards", "honors & awards", "achievements", "accomplishments"],
    "publications": ["publications", "research work", "articles"],
    "volunteer": ["volunteer", "volunteer experience", "community service"],
    "contact": ["contact", "contact information", "personal information", "details"],
    "references": ["references", "reference", "referees", "recommendations"],
    "interests": ["interests", "hobbies", "leisure activities"],
    "portfolio": ["portfolio"],
    "additional information": ["additional information"]
}

# def fix_spaced_words(text: str) -> str:
#     """Fix words like 'E D U C A T I O N' -> 'EDUCATION' (keeps case)."""
#     return re.sub(r'(?:[A-Za-z]\s){2,}[A-Za-z]', lambda m: m.group(0).replace(" ", ""), text)
#
# def normalize_headings(text: str) -> str:
#     """Normalize headings with inconsistent spacing (e.g. 'Work   Experience')
#        but keep original case/formatting.
#     """
#     for section, variants in HEADINGS.items():
#         for variant in variants:
#             # Build regex allowing multiple spaces inside variant
#             words = variant.split()
#             pattern = r"\s*".join(re.escape(w) for w in words)
#             text = re.sub(pattern, lambda m: re.sub(r"\s+", " ", m.group(0)), text, flags=re.I)
#     return text
#
# def fix_stuck_headings(text: str) -> str:
#     """Fix stuck headings like 'WORKEXPERIENCE' -> 'WORK EXPERIENCE' or
#        'WorkExperience' -> 'Work Experience', preserving case style.
#     """
#     all_headings = sum(HEADINGS.values(), [])
#     normalized_map = {h.lower().replace(" ", ""): h for h in all_headings}
#
#     lines = text.splitlines()
#     fixed_lines = []
#
#     for line in lines:
#         clean_line = line.strip()
#         if not clean_line:
#             fixed_lines.append(line)
#             continue
#
#         # try fuzzy match against normalized headings
#         match = get_close_matches(clean_line.lower(), normalized_map.keys(), n=1, cutoff=0.85)
#         if match:
#             fixed = normalized_map[match[0]]
#
#             # --- preserve formatting style ---
#             if clean_line.isupper():
#                 fixed = fixed.upper()
#             elif clean_line.istitle():
#                 fixed = fixed.title()
#             elif clean_line.islower():
#                 fixed = fixed.lower()
#             # else keep mixed formatting as dictionary version
#
#             fixed_lines.append(fixed)
#         else:
#             fixed_lines.append(line)
#
#     return "\n".join(fixed_lines)
#
# # --- Main preprocessing pipeline (one-argument version) ---
# def preprocess_resume_text(text: str) -> str:
#     text = fix_spaced_words(text)    # "E D U C A T I O N" -> "EDUCATION"
#     text = normalize_headings(text)  # "Work   Experience" -> "Work Experience"
#     text = fix_stuck_headings(text)  # "WORKEXPERIENCE" -> "WORK EXPERIENCE"
#     return text


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



import re

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


# ----------------- Example -----------------
exp_section = """3 months Internship asaSoftware Developer Skylarks It solutions Kamra Distt Attock Junior .Net Developer PanaceaLogics 01/2023 - Present, Rawalpindi ikramkarluu@gmail.com 0304-3100853 Rawalpindi, Pakistan skills and OOP concepts, Skilled in new technical concepts in web applications."""

print(remove_phone_numbers(exp_section))




# print(extract_experience_dict("""EXPERIENCE
# 2018 – 2020 Attock, Pakistan Unico Technologies People Colony - Attock Iwas working here on HTML CSS. Also worked on WordPress. Implementeda responsive design that ensured the web application was accessible on all devices. 2021 Pakistan Internee FWO IT Department HQ 492 Engineering Group - Peshawar Iwas working here as Internee to work on project operations management processes, strategies, and methods. 2022 Pakistan Junior Web Developer Eziline Software House Askari III - Rawalpindi Iwas working here asajunior Mern Stack Developer. Implementedaresponsive design that allowed the application to be used across multiple devices with minimal modifications."""))