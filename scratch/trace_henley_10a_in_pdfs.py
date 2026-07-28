import glob
import os
import re
import fitz
import pandas as pd

pdf_dir = "九龙-启德-The Henley I/pdfs"
pdf_files = glob.glob(os.path.join(pdf_dir, "price_list_*.pdf"))

print(f"🔍 正在从物理 PDF 文件中，追踪 2座 10A 的出现情况 (共找到 {len(pdf_files)} 个 PDF)...")

for pdf_path in sorted(pdf_files):
    pl_name = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        found_in_table = False
        found_price = None
        
        for p_idx in range(len(doc)):
            page = doc.load_page(p_idx)
            tables = list(page.find_tables())
            for t_idx, table in enumerate(tables):
                df = table.to_pandas()
                # 遍历行
                for idx, row in df.iterrows():
                    if len(row) < 5:
                        continue
                    # 楼栋
                    col0 = str(row.iloc[0]).replace("\n", "").replace(" ", "").strip()
                    # 楼层
                    col1 = str(row.iloc[1]).replace("\n", "").replace(" ", "").strip()
                    # 房号
                    col2 = str(row.iloc[2]).replace("\n", "").replace(" ", "").strip()
                    
                    if "座" not in col0:
                        continue
                        
                    floor_clean = re.sub(r'[^0-9]', '', col1)
                    flat_clean = re.sub(r'[^A-Z0-9]', '', col2.upper())
                    
                    b_match = re.search(r'(\d+)([A-Za-z]?)', col0)
                    bname = b_match.group(1) + b_match.group(2) if b_match else col0
                    
                    if bname == "2" and floor_clean == "10" and flat_clean == "A":
                        found_in_table = True
                        found_price = str(row.iloc[4]).replace("\n", "").replace(" ", "").strip()
                        print(f"  🎉 在 {pl_name} 第 {p_idx+1} 页表格中找到 2座 10A！")
                        print(f"    - 原表行: {list(row.iloc[:6])}")
                        break
                if found_in_table:
                    break
            if found_in_table:
                break
                
        # 扫描印花税条款
        has_sd_clause = False
        for p_idx in range(len(doc)):
            p_text = doc.load_page(p_idx).get_text("text")
            if "代繳從價印花稅" in p_text or "Ad Valorem Stamp Duty" in p_text:
                block_pattern = "第2座"
                if block_pattern in p_text:
                    lines = p_text.split("\n")
                    for idx, line in enumerate(lines):
                        if block_pattern in line:
                            chunk = "\n".join(lines[max(0, idx-5): min(len(lines), idx+30)])
                            if "A" in chunk:
                                # 检查楼层
                                if "10" in chunk:
                                    has_sd_clause = True
                                    break
            if has_sd_clause:
                break
                
        print(f"  📄 价单: {pl_name}")
        print(f"    - 房源表出现 = {found_in_table} (原价: {found_price})")
        print(f"    - 印花税条款涵盖此房源 = {has_sd_clause}")
        doc.close()
        
    except Exception as e:
        print(f"  ❌ 解析 {pl_name} 出错: {e}")
