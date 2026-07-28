import requests
import sys
import os
import re

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token, clean_name

token = fetch_user_token()
if not token:
    print("获取 Token 失败。")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Origin": "https://www.hkp.com.hk",
    "Referer": "https://www.hkp.com.hk/"
}

# 1. 抓取天玺．天 (P000001212) 和 Blue Coast (P000001133)
pids = {
    "Cullinan_Sky_2": "P000001213",
    "Blue_Coast_2": "P000001232"
}

os.makedirs("scratch/inspect_pdfs", exist_ok=True)

for name, pid in pids.items():
    print(f"\n🔍 正在获取项目 {name} (ID: {pid}) 详情...")
    r = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=headers, timeout=15)
    if r.status_code != 200:
        print(f"  错误: 无法获取 {name} 详情。")
        continue
        
    print(f"  [调试] Full JSON: {r.json()}")

