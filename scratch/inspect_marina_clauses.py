import fitz
import re

pdfs = [
    {"path": "九龙-启德-启德海湾 1/pdfs/price_list_5N.pdf", "name": "启德海湾 1 - 5N"},
    {"path": "九龙-启德-启德海湾 2/pdfs/price_list_1A.pdf", "name": "启德海湾 2 - 1A"}
]

print("🔍 正在扫描启德海湾 PDF 条款字样...")

for p_info in pdfs:
    print(f"\n📄 正在分析: {p_info['name']}")
    try:
        doc = fitz.open(p_info['path'])
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            text = page.get_text("text")
            lines = text.split("\n")
            
            # 搜索匹配
            matched_lines = []
            for i, line in enumerate(lines):
                if any(x in line for x in ["印花稅", "回贈", "代繳", "代缴", "回赠", "付款", "優惠", "折扣"]):
                    matched_lines.append((i, line.strip()))
                    
            if matched_lines:
                print(f"  [页面 {page_idx+1}] 找到关键字句共 {len(matched_lines)} 行:")
                # 打印前 15 个匹配句
                for idx, line_text in matched_lines[:15]:
                    print(f"    行 {idx}: {line_text}")
    except Exception as e:
        print(f"  分析出错: {e}")
