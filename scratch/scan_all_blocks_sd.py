import os
import fitz
import re

pdf_dir = "九龙-启德-The Henley III/pdfs"
price_lists = ["1N", "2Q", "3O", "4L", "4M", "5L", "6B"]

output_lines = []

for pl in price_lists:
    pdf_path = os.path.join(pdf_dir, f"price_list_{pl}.pdf")
    if not os.path.exists(pdf_path):
        continue
    
    doc = fitz.open(pdf_path)
    output_lines.append(f"==================================================")
    output_lines.append(f"【價單 {pl} 號】")
    output_lines.append(f"==================================================")
    
    sd_found = []
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text("text")
        if "代繳從價印花稅" in text or "Ad Valorem Stamp Duty" in text:
            # We want to scan the lines of this page
            lines = text.split("\n")
            for idx, line in enumerate(lines):
                # Search for any mention of block name
                if any(kw in line for kw in ["座", "Tower", "Block"]):
                    # Look at surrounding lines to find exact match
                    chunk = lines[max(0, idx-2): min(len(lines), idx+10)]
                    chunk_str = " | ".join([cl.strip() for cl in chunk if cl.strip()])
                    sd_found.append(f"页面 {page_idx+1}: {chunk_str}")
                    
    output_lines.append("  [印花税代缴适用范围 (Ad Valorem Stamp Duty Benefit)]:")
    if sd_found:
        # De-duplicate while preserving order
        seen = set()
        for item in sd_found:
            # Keep unique parts
            match = re.search(r'(Tower \S+|第\S+座|Block \S+)', item)
            if match:
                key = match.group(0)
            else:
                key = item[:150]
            if key not in seen:
                seen.add(key)
                output_lines.append(f"    - {item}")
    else:
        output_lines.append("    - 未发现任何印花税代缴条款")
    output_lines.append("")
    doc.close()

with open("scratch/henley3_detailed_sd.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Detailed scan complete!")
