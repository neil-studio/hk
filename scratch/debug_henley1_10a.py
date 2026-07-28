import requests
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token, calculate_unit_discount

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
detail_data = r.json().get('result', r.json())

# 打印所有付款计划
payments = detail_data.get('payment', [])
print("=== 付款计划列表 ===")
for p in payments:
    print(f"ID: {p.get('id')} | Name: {p.get('name_cn')} | Dispct: {p.get('dispct')}% | Rate: {p.get('rate')}")

# 获取 2座 ID
buildings = detail_data.get('buildings', [])
target_b_id = None
for b in buildings:
    if "2座" in b.get('name', ''):
        target_b_id = b.get('id')
        break

if not target_b_id:
    print("未找到 2座 ID。")
    exit(1)

# 拉取单位
ur = requests.get(f"https://data.hkp.com.hk/info/v1/new-property/transactions/buildings/{target_b_id}", headers=headers, timeout=10)
units = ur.json().get('data', [])

print(f"\n🔍 2座 获取到单位数: {len(units)}")
for u in units:
    floor = u.get('floor')
    flat = u.get('flat')
    if str(floor) == "10" and str(flat) == "A":
        print(f"\n🏠 找到 2座 10楼 A单位:")
        print(f"  原始单位数据: {u}")
        
        # 计算折扣
        max_discount_rate = 0.12 # 从日志看最高是 12%
        max_discount_title = "現金付款計劃 - 90天成交"
        u_rate, u_title = calculate_unit_discount(u, payments, max_discount_rate, max_discount_title)
        print(f"  calculate_unit_discount 返回: rate = {u_rate} | title = {u_title}")
