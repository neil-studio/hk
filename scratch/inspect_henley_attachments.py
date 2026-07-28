import requests
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

# The Henley I ID: E000010996
pid = "E000010996"
r = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=headers, timeout=10)
data = r.json()

attachments = data.get('attachment', [])
print(f"The Henley I attachments 数量: {len(attachments)}")
for idx, a in enumerate(attachments):
    print(f"  {idx+1}: name = {a.get('name')} | pl_num = {a.get('pl_num')} | type = {a.get('type')} | path = {a.get('path')}")
