import os
import requests
import fitz

pdf_dir = "scratch/henley_pdfs"
os.makedirs(pdf_dir, exist_ok=True)

# Henley III 的 7 个价单 PDF 链接
price_lists = {
    "6B": "https://res-fh.hkp.com.hk/prod/new-property/files/262362/416725_fe29e187e03464a5a795de0d16f4344e.pdf",
    "3O": "https://res-fh.hkp.com.hk/prod/new-property/files/262362/416722_6f55d0b5cc37085ebeb02cb3ff4c6f82.pdf",
    "4M": "https://res-fh.hkp.com.hk/prod/new-property/files/262362/416723_8a7841dc9533fb5c4af05c0f6693558d.pdf",
    "5L": "https://res-fh.hkp.com.hk/prod/new-property/files/262362/416724_0cc10f4ecda1fb0f93c67cfac7aedc25.pdf",
    "1N": "https://res-fh.hkp.com.hk/prod/new-property/files/262362/416712_d971f169bc90432cc279f1e1ecdd0a7a.pdf",
    "2Q": "https://res-fh.hkp.com.hk/prod/new-property/files/262362/416713_80ecc5c981d8525793eb304f6c6f7f2d.pdf",
    "4L": "https://res-fh.hkp.com.hk/prod/new-property/files/262362/396160_d226d4359ce1aae56f92d7906eb05fa3.PDF"
}

# 1. 下载所有的 PDF
for name, url in price_lists.items():
    path = os.path.join(pdf_dir, f"price_list_{name}.pdf")
    if not os.path.exists(path):
        print(f"正在下载 價單{name}: {url}...")
        r = requests.get(url, timeout=30)
        with open(path, 'wb') as f:
            f.write(r.content)
    else:
        print(f"價單{name} 已存在于本地。")

# 2. 遍历每个价单，搜寻 3B座-15楼-B室 ( Flats B on 15/F of Tower 3B )
target_found = []
for name in price_lists.keys():
    path = os.path.join(pdf_dir, f"price_list_{name}.pdf")
    doc = fitz.open(path)
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text("text")
        
        # 精确检索 "3B" 和 "15" 和 "B" 是否同在这一页的价格表里
        # 价单大表格式通常包含: 第3B座, 15, B (或 Flat B, T3B)
        if "3B" in text and "15" in text and "B" in text:
            # 如果这一页也是房源表（通常包含 "實用面積"、"售價" 等词）
            if "售價" in text or "實用面積" in text:
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if "3B" in line and any(str(x) in line for x in [15, "15"]):
                        print(f"\n🎯 在 [價單 {name}] 第 {page_idx+1} 页匹配到了 3B座15楼 物业！附近行内容：")
                        start = max(0, i-5)
                        end = min(len(lines), i+15)
                        for j in range(start, end):
                            print(f"  [{j}] {lines[j]}")
                        target_found.append((name, page_idx+1))

print(f"\n匹配到的价单和页码列表: {target_found}")
