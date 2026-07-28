import fitz
import pandas as pd

pdf_path = "九龙-启德-启德海湾 2/pdfs/price_list_1A.pdf"
print(f"🔍 正在解析 启德海湾 2 的 price_list_1A.pdf 结构...")

doc = fitz.open(pdf_path)
print(f"PDF 总页数: {len(doc)}")

for page_idx in range(min(5, len(doc))):
    page = doc.load_page(page_idx)
    text = page.get_text("text")
    print(f"\n--- 页面 {page_idx+1} 前 200 字 ---")
    print(text[:200].replace("\n", " | "))
    
    tables = list(page.find_tables())
    print(f"  找到表格数量: {len(tables)}")
    for t_idx, table in enumerate(tables):
        df = table.to_pandas()
        print(f"    表格 {t_idx+1}: 列数 = {len(df.columns)} | 行数 = {len(df)}")
        print(f"      列名: {list(df.columns)}")
        # 打印前 3 行数据
        for idx, row in df.head(3).iterrows():
            print(f"        行 {idx}: {list(row.iloc[:6])}")
