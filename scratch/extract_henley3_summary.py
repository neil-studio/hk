import os
import fitz
import re

pdf_dir = "九龙-启德-The Henley III/pdfs"
price_lists = ["1N", "2Q", "3O", "4L", "4M", "5L", "6B"]

output_lines = []

for pl in price_lists:
    pdf_path = os.path.join(pdf_dir, f"price_list_{pl}.pdf")
    if not os.path.exists(pdf_path):
        output_lines.append(f"價單 {pl} 號: 本地 PDF 不存在\n")
        continue
    
    doc = fitz.open(pdf_path)
    output_lines.append(f"==================================================")
    output_lines.append(f"【價單 {pl} 號】优惠及印花税适用范围")
    output_lines.append(f"==================================================")
    
    # 找印花税条款
    sd_found = []
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text("text")
        if "代繳從價印花稅" in text or "Ad Valorem Stamp Duty" in text:
            # 找到印花税条款页面，提取文本行
            lines = text.split("\n")
            for idx, line in enumerate(lines):
                if "第3B座" in line or "Tower 3B" in line:
                    chunk_lines = lines[max(0, idx-3): min(len(lines), idx+15)]
                    chunk_clean = " | ".join([cl.strip() for cl in chunk_lines if cl.strip()])
                    sd_found.append(f"页面 {page_idx+1}: {chunk_clean}")
                    
    output_lines.append("  [印花税代缴适用条款 (Ad Valorem Stamp Duty Benefit)]:")
    if sd_found:
        for item in sd_found:
            output_lines.append(f"    - {item}")
    else:
        output_lines.append("    - 未发现代缴从价印花税条款")
        
    output_lines.append("")
    doc.close()

with open("scratch/henley3_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Summary written to scratch/henley3_summary.txt successfully!")
