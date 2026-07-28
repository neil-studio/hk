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

pid = "P000001150"
r = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=headers, timeout=10)
data = r.json()

payment = data.get('payment', [])
print(f"Henley Park 付款计划数量: {len(payment)}")
for idx, p in enumerate(payment):
    title = p.get('title')
    pct = p.get('percentage')
    bonuses = p.get('bonuses', [])
    b_titles = [f"{b.get('title')}({b.get('percentage')})" for b in bonuses]
    print(f"  {idx+1}: 计划 = {title} | 基础百分比 = {pct} | 附加折扣 = {b_titles}")
