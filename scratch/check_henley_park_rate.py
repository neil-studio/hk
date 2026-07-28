import requests
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token, extract_max_discount_info

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

max_rate, max_title, bonuses = extract_max_discount_info(data)
print(f"Henley Park 最高基础折扣 max_rate = {max_rate} | title = {max_title}")
