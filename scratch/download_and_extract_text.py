import os
import requests
import fitz # PyMuPDF

# 创建临时下载目录
pdf_dir = "scratch/henley_pdfs"
os.makedirs(pdf_dir, exist_ok=True)

# 價單6B號
pdf_url = "https://res-fh.hkp.com.hk/prod/new-property/files/262362/416725_fe29e187e03464a5a795de0d16f4344e.pdf"
pdf_path = os.path.join(pdf_dir, "price_list_6B.pdf")

if not os.path.exists(pdf_path):
    print(f"正在下载价单 6B: {pdf_url} ...")
    r = requests.get(pdf_url, timeout=30)
    with open(pdf_path, 'wb') as f:
        f.write(r.content)
    print("下载完成。")
else:
    print("价单 6B 已存在于本地。")

# 使用 fitz 提取文本并进行关键词检索
doc = fitz.open(pdf_path)
print(f"PDF 总页数: {len(doc)}")

# 我们搜索 3B座15楼B室、付款方法、印花税等关键词
keywords = ["3B", "15", "付款", "折扣", "印花稅", "特別折扣"]

# 查找包含关键词的页码并打印上下文
found_pages = []
for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    text = page.get_text("text")
    
    # 模糊查找是否包含 3B座 15楼 B室 的价格行
    # 在价单中通常以表格排版，如 "3B", "15", "B" 会出现在同一页
    if "3B" in text and "15" in text and "B" in text:
        print(f"\n--- [发现房源匹配] 第 {page_num + 1} 页文字片段 ---")
        lines = text.split("\n")
        # 打印匹配行附近的内容
        for idx, line in enumerate(lines):
            if "3B" in line and any(str(i) in line for i in [15, "15"]):
                start = max(0, idx - 5)
                end = min(len(lines), idx + 10)
                print("\n".join(lines[start:end]))
                print("-" * 30)

    # 查找关于折扣条款页（通常在 PDF 后半部分）
    if "付款" in text and ("折扣" in text or "印花稅" in text):
        found_pages.append(page_num + 1)

print(f"\n可能含有付款方法与折扣优惠说明的页码: {found_pages}")

# 提取并打印其中几页折扣说明（例如后半部包含“折扣”的页）
for p_num in found_pages[:3]: # 打印前3个含有折扣优惠的页的前 800 个字
    print(f"\n=================== 第 {p_num} 页 折扣说明 ===================")
    p = doc.load_page(p_num - 1)
    t = p.get_text("text")
    print(t[:1500]) # 打印前1500字
