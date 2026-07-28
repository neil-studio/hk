import requests
import json
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token

token = fetch_user_token()
headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0",
}

# The Henley I pid
pid = "P000001126"

print(f"🔍 正在从 API 拉取 The Henley I (ID: {pid}) 的全量楼栋...")
r = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=headers, timeout=10)
data = r.json().get('result', {})

buildings = data.get('building', [])
target_b_id = None
for b in buildings:
    if "2" in b.get('name', ''):
        target_b_id = b.get('id')
        print(f"  找到楼栋: {b.get('name')} | ID: {target_b_id}")

if not target_b_id:
    print("❌ 未找到 2座 楼栋ID")
    sys.exit(1)

# 拉取 2座 的单位列表
print(f"\n🔍 正在拉取 2座 (ID: {target_b_id}) 的单位列表...")
url = f"https://data.hkp.com.hk/info/v1/new-properties/{pid}/buildings/{target_b_id}/units"
r = requests.get(url, headers=headers, timeout=10)
units = r.json().get('result', [])

print(f"  共找到单位: {len(units)} 个")
for u in units:
    floor = str(u.get('floor', '')).strip()
    flat = str(u.get('flat', '')).strip()
    if floor == "10" and flat == "A":
        print("\n🎉 成功找到 2座 10A 单位的 API 完整属性：")
        print(json.dumps(u, indent=2, ensure_ascii=False))
        break
else:
    print("❌ 未找到 2座 10A 单位")
