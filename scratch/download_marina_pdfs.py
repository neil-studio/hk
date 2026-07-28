import requests
import os
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token

token = fetch_user_token()
headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.hkp.com.hk",
    "Referer": "https://www.hkp.com.hk/"
}

projects = [
    {"pid": "P000001187", "name": "启德海湾 1", "dir": "九龙-启德-启德海湾 1"},
    {"pid": "P000001188", "name": "启德海湾 2", "dir": "九龙-启德-启德海湾 2"}
]

for proj in projects:
    print(f"\n📂 正在拉取: {proj['name']} (ID: {proj['pid']}) 的附件列表...")
    r = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{proj['pid']}", headers=headers, timeout=10)
    data = r.json().get('result', r.json())
    
    attachments = data.get('attachment', [])
    pdf_dir = os.path.join(proj['dir'], "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    
    print(f"  共找到附件数量: {len(attachments)}")
    pl_count = 0
    for a in attachments:
        name = a.get('name', '')
        type_ = a.get('type', '')
        pl_num = a.get('pl_num', '')
        path = a.get('path', '')
        
        if 'pl' in str(type_).lower() or '價單' in name:
            pl_count += 1
            print(f"    - 价单编号: {pl_num} | 名字: {name} | 链接: {path}")
            
            # 下载 PDF
            pdf_path = os.path.join(pdf_dir, f"price_list_{pl_num}.pdf")
            if not os.path.exists(pdf_path):
                print(f"      -> 正在下载 {name}...")
                try:
                    dl_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
                    r_dl = requests.get(path, headers=dl_headers, timeout=30)
                    if r_dl.status_code == 200:
                        with open(pdf_path, 'wb') as f:
                            f.write(r_dl.content)
                        print(f"      ✅ 下载成功，大小: {len(r_dl.content)} 字节")
                except Exception as dl_err:
                    print(f"      ❌ 下载失败: {dl_err}")
            else:
                print(f"      [缓存] 文件已存在。")
                
    print(f"  {proj['name']} 下载完成，共有价单数: {pl_count}")
