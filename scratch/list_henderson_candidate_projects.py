import json
import os
import requests
import re
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token, clean_name

# 1. 从 API 获取最新完整开发商映射
token = fetch_user_token()
if not token:
    print("获取 Token 失败。")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "User-Agent": "Mozilla/5.0"
}
r = requests.get("https://data.hkp.com.hk/search/v2/new-properties", params={'limit': 1000}, headers=headers, timeout=15)
projects_api = r.json().get('result', [])
api_dev_map = {}
for p in projects_api:
    pname = p.get('name', '')
    dev_name = p.get('developer', {}).get('name', '无') if p.get('developer') else '无'
    api_dev_map[clean_name(pname)] = dev_name

# 2. 读取 web/data.json 关联有在售定价的盘
with open("web/data.json", 'r', encoding='utf-8') as f:
    web_data = json.load(f)

projects = web_data.get("projects", [])

candidates = []
for p in projects:
    pname = p["name"]
    clean_pname = clean_name(pname)
    dev_name = api_dev_map.get(clean_pname, "未知开发商")
    
    # 只要开发商包含恒基或恒地
    is_candidate = "恒基" in dev_name or "恒地" in dev_name or "Henley" in pname
    
    stats = p.get("stats", {})
    sale_count = stats.get("sale", 0)
    priced_count = stats.get("priced", 0)
    total_active = sale_count + priced_count
    
    if is_candidate and total_active > 0:
        candidates.append({
            "name": pname,
            "region": p["region"],
            "district": p["district"],
            "developer": dev_name,
            "sale": sale_count,
            "priced": priced_count,
            "total_active": total_active
        })

# 写入 Artifact report
artifact_dir = "/Users/nb/.gemini/antigravity/brain/4977a979-cde7-4c64-993d-eb1f3f91ccb4"
os.makedirs(artifact_dir, exist_ok=True)
report_path = os.path.join(artifact_dir, "henderson_candidates.md")

with open(report_path, 'w', encoding='utf-8') as rf:
    rf.write("# 恒基参股/合作在售定价新盘待确认列表\n\n")
    rf.write("请在以下列表中确认，哪些新盘是由**恒基兆业实际操盘**且应套用恒基 PDF 价单模板进行精算的：\n\n")
    rf.write("| 序号 | 区域 | 商圈 | 项目名称 | 登记开发商 (Co-Developers) | 定价在售数 | 是否由恒基操盘 (建议) |\n")
    rf.write("| :---: | :--- | :--- | :--- | :--- | :---: | :---: |\n")
    for idx, c in enumerate(candidates):
        rf.write(f"| {idx+1} | {c['region']} | {c['district']} | {c['name']} | {c['developer']} | **{c['total_active']}** | [ ] 确认操盘 |\n")

print(f"统计完成！共筛选出 {len(candidates)} 个包含恒基背景的活跃在售定价盘。")
