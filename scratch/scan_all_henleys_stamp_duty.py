import fitz
import os
import glob
import re

henley_dirs = [
    "九龙-启德-The Henley I",
    "九龙-启德-The Henley II",
    "九龙-启德-The Henley III"
]

print("🔍 启动 The Henley 1、2、3期 全量价单 PDF 印花税条款大扫描...")

for hdir in henley_dirs:
    print(f"\n📂 正在扫描目录: {hdir}")
    pdf_files = glob.glob(os.path.join(hdir, "pdfs", "*.pdf"))
    if not pdf_files:
        print("  未找到任何已下载的 PDF 文件。")
        continue
        
    for pdf_path in sorted(pdf_files):
        filename = os.path.basename(pdf_path)
        try:
            doc = fitz.open(pdf_path)
            for page_idx in range(len(doc)):
                page = doc.load_page(page_idx)
                text = page.get_text("text")
                if "代繳從價印花稅" in text or "Ad Valorem Stamp Duty" in text:
                    # 提取包含 "座" 或者 "Tower" 以及紧随其后的楼层和单位的上下文
                    lines = text.split("\n")
                    printed_pl = False
                    for idx, line in enumerate(lines):
                        if "座" in line or "Tower" in line or "樓" in line or "Floor" in line or "Flat" in line:
                            # 打印相关的 10 行
                            if not printed_pl:
                                print(f"  📄 价单 PDF: {filename} (页面 {page_idx+1}) 发现印花税条款:")
                                printed_pl = True
                            
                            chunk = lines[max(0, idx-2): min(len(lines), idx+8)]
                            chunk_str = " | ".join([c.strip() for c in chunk if c.strip()])
                            if "標準" not in chunk_str and "合約" not in chunk_str and "買方" not in chunk_str:
                                print(f"    行 {idx}: {chunk_str}")
        except Exception as e:
            print(f"  解析 {filename} 出错: {e}")
