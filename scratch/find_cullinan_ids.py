import requests
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token, clean_name

token = fetch_user_token()
if not token:
    print("获取 Token 失败。")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0"
}
r = requests.get("https://data.hkp.com.hk/search/v2/new-properties", params={'limit': 1000}, headers=headers, timeout=15)
projects = r.json().get('result', [])

print("🔍 匹配 Cullinan / 天玺 结果:")
for p in projects:
    name = p.get('name', '')
    if "天玺" in name or "天璽" in name or "Cullinan" in name or "Blue Coast" in name or "Sky" in name:
        dev = p.get('developer', {}).get('name', '无') if p.get('developer') else '无'
        print(f"  - 名称: {name} | ID: {p.get('id')} | 开发商: {dev}")
