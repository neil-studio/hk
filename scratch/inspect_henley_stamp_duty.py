import requests
import sys
import fitz
import re

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token

token = fetch_user_token()
headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.hkp.com.hk",
    "Referer": "https://www.hkp.com.hk/"
}

# The Henley I ID: P000001126
pid = "P000001126"
r = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=headers, timeout=10)
data = r.json()

attachments = data.get('attachment', [])
pdf_url = None
for a in attachments:
    name = a.get('name', '')
    if "價單" in name and "7" in name:
        pdf_url = a.get('path')
        print(f"找到价单 7 号 PDF 链接: {pdf_url}")
        break

if not pdf_url:
    # 拿第一个价单
    for a in attachments:
        if a.get('pl_num') == '7':
            pdf_url = a.get('path')
            print(f"根据 pl_num=7 找到链接: {pdf_url}")
            break

if not pdf_url:
    print("未找到价单 7 号。")
    exit(1)

# 下载并读取
r_pdf = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
pdf_path = "scratch/henley_1_pl_7.pdf"
with open(pdf_path, 'wb') as f:
    f.write(r_pdf.content)

# 打印页面 12 的完整文字
page = doc.load_page(11)
text = page.get_text("text")
print("\n--- 页面 12 完整文字 ---")
print(text)
