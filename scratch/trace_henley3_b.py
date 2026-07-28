import glob
import os
import re
import fitz
import pandas as pd

pdf_dir = "九龙-启德-The Henley III/pdfs"
pdf_files = glob.glob(os.path.join(pdf_dir, "price_list_*.pdf"))

print(f"🔍 正在从物理 PDF 文件中，追踪 Henley III 3B座 16B, 17B 的印花税情况...")

def is_floor_in_chunk(floor_str, chunk):
    c_clean = re.sub(r'\s+', '', chunk)
    num_matches = re.findall(r'\d+', c_clean)
    return floor_str in num_matches

for pdf_path in sorted(pdf_files):
    pl_name = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        
        # 扫描印花税条款
        has_sd_16 = False
        has_sd_17 = False
        
        for page_idx in range(len(doc)):
            p_text = doc.load_page(page_idx).get_text("text")
            if "代繳從價印花稅" in p_text or "Ad Valorem Stamp Duty" in p_text:
                block_pattern = "第3B座"
                if block_pattern in p_text:
                    lines = p_text.split("\n")
                    for idx, line in enumerate(lines):
                        if block_pattern in line:
                            chunk = "\n".join(lines[max(0, idx-5): min(len(lines), idx+30)])
                            if "B" in chunk:
                                if is_floor_in_chunk("16", chunk):
                                    has_sd_16 = True
                                if is_floor_in_chunk("17", chunk):
                                    has_sd_17 = True
                                    
        print(f"  📄 价单: {pl_name}")
        print(f"    - 16B 印花税条款涵盖 = {has_sd_16}")
        print(f"    - 17B 印花税条款涵盖 = {has_sd_17}")
        doc.close()
        
    except Exception as e:
        print(f"  ❌ 解析 {pl_name} 出错: {e}")

def is_floor_in_chunk(floor_str, chunk):
    c_clean = re.sub(r'\s+', '', chunk)
    num_matches = re.findall(r'\d+', c_clean)
    return floor_str in num_matches
