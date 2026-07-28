import requests
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token, normalize_bname, get_henderson_pdf_data

token = fetch_user_token()
headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.hkp.com.hk",
    "Referer": "https://www.hkp.com.hk/"
}

# Henley Park E000018687
pid = "E000018687"
r = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=headers, timeout=10)
detail_data = r.json()

# 1. 模拟 get_henderson_pdf_data 生成 pdf_db
pname = "Henley Park"
project_dir = "九龙-启德-Henley Park"
fallback_rate = 0.06
henderson_pdf_db = get_henderson_pdf_data(detail_data, headers, project_dir, fallback_rate, pname)

print(f"pdf_db 中拥有补偿键数量: {len([k for k, v in henderson_pdf_db.items() if v.get('is_compensation')])}")

# 2. 拉取大楼明细来遍历
buildings = detail_data.get('buildings', [])
print(f"buildings 列表: {[b.get('name') for b in buildings]}")
target_b_id = None
for b in buildings:
    if "1B" in b.get('name', ''):
        target_b_id = b.get('id')
        break

print(f"target_b_id: {target_b_id}")
if not target_b_id:
    print("未找到 1B座 ID。")
    exit(1)

# 拉取单位
ur = requests.get(f"https://data.hkp.com.hk/info/v1/new-property/transactions/buildings/{target_b_id}", headers=headers, timeout=10)
print(f"Units API HTTP Status: {ur.status_code}")
print(f"Units keys: {list(ur.json().keys())}")
units = ur.json().get('data', [])

print(f"\n🔍 1B座 获取到单位数: {len(units)}")
for u in units:
    floor = u.get('floor')
    flat = u.get('flat')
    status_raw = u.get('sell_status') or u.get('status')
    price = u.get('price') or 0
    
    # 模拟主循环命名清洗
    bname = "1B座"
    norm_b = normalize_bname(bname).replace("座", "")
    norm_floor = str(floor).strip()
    norm_flat = str(flat).strip()
    pdf_key = (norm_b, norm_floor, norm_flat)
    
    if norm_floor in ["8", "15"] and norm_flat == "A":
        print(f"\n🏠 找到目标单位: {norm_floor} 楼 {norm_flat} 室")
        print(f"  status_raw = {status_raw} | price = {price}")
        print(f"  pdf_key = {pdf_key} | 是否在 pdf_db 中 = {pdf_key in henderson_pdf_db}")
        if pdf_key in henderson_pdf_db:
            info = henderson_pdf_db[pdf_key]
            print(f"  pdf_info = {info}")
