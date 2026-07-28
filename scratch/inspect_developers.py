import sys
import requests
sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token

token = fetch_user_token()
if not token:
    print("获取 Token 失败。")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0"
}
r = requests.get("https://data.hkp.com.hk/search/v2/new-properties", params={'limit': 1000}, headers=headers, timeout=15)
data = r.json()
projects = data.get('result', [])

print(f"共获取到 {len(projects)} 个项目:")
for p in projects[:15]:
    dev_name = p.get('developer', {}).get('name', '无') if p.get('developer') else '无'
    print(f"  - {p.get('name')} | 开发商: {dev_name}")
