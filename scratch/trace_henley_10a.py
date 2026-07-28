import fitz
import os
import glob
import re

pdf_dir = "九龙-启德-The Henley I/pdfs"
block = "2"
floor = "10"
flat = "A"

# 查找所有下载的 PDF
pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
print(f"🔍 开始追踪 2座 {floor}楼 {flat}单位 在所有 {len(pdf_files)} 份价单 PDF 中的物理状态...")

for pdf_path in sorted(pdf_files):
    filename = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        found_in_table = False
        price_found = None
        
        # 1. 查找价格行
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            tables = page.find_tables()
            if not tables:
                continue
            for table in tables:
                df = table.to_pandas()
                if len(df.columns) < 5:
                    continue
                for _, row in df.iterrows():
                    col0 = str(row.iloc[0]).replace("\n", "").replace(" ", "").strip()
                    col1 = str(row.iloc[1]).replace("\n", "").replace(" ", "").strip()
                    col2 = str(row.iloc[2]).replace("\n", "").replace(" ", "").strip()
                    
                    if "座" in col0 and col1 == floor and col2 == flat:
                        b_match = re.search(r'(\d+)', col0)
                        bname = b_match.group(1) if b_match else col0
                        if bname == block:
                            found_in_table = True
                            price_found = str(row.iloc[4]).replace("\n", "").replace(" ", "").strip()
                            break
            if found_in_table:
                break
                
        # 2. 检查印花税条款
        has_sd_clause = False
        for page_idx in range(len(doc)):
            p_text = doc.load_page(page_idx).get_text("text")
            if "代繳從價印花稅" in p_text or "Ad Valorem Stamp Duty" in p_text:
                # 简单测试该 PDF 条款是否覆盖此房源
                from scrape_hkp_sales_control import check_stamp_duty_eligibility
                if check_stamp_duty_eligibility(pdf_path, block, int(floor), flat):
                    has_sd_clause = True
                    break
                    
        print(f"\n📄 价单: {filename}")
        print(f"  房源列表出现 = {found_in_table} (原价: {price_found})")
        print(f"  印花税条款涵盖此房源 = {has_sd_clause}")
        
    except Exception as e:
        print(f"  解析 {filename} 出错: {e}")
