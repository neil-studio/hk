import json
import os
import requests
import sys

sys.path.append("/Users/nb/google/Antigravity/工作/运营/价单")
from scrape_hkp_sales_control import fetch_user_token, clean_name

# 1. 获取最新 API 开发商关联
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

# 2. 读取 web/data.json
with open("web/data.json", 'r', encoding='utf-8') as f:
    web_data = json.load(f)

projects = web_data.get("projects", [])

# 已经确认过操盘手的项目，不再重复列出
already_confirmed = {
    "Double Coast I", "Double Coast III", "Miami Quay I", "Miami Quay II",
    "天泷", "维港．湾畔第1A期", "维港．湾畔第1B期", "维港．湾畔第2B期",
    "首岸第1期", "首岸第3期", "首岸第4期", "Kennedy 38"
}

joint_ventures = []
for p in projects:
    pname = p["name"]
    if pname in already_confirmed:
        continue
        
    dev_name = api_dev_map.get(clean_name(pname), "无")
    
    # 联合开发商特征：开发商名称中含有 "/" 或者是 "、" 或者是 "及" 或者是 "合作"
    is_jv = "/" in dev_name or "、" in dev_name or "及" in dev_name or "和" in dev_name
    
    stats = p.get("stats", {})
    sale_count = stats.get("sale", 0)
    priced_count = stats.get("priced", 0)
    total_active = sale_count + priced_count
    
    if is_jv:
        joint_ventures.append({
            "name": pname,
            "region": p["region"],
            "district": p["district"],
            "developer": dev_name,
            "total_active": total_active
        })

# 降序排列
joint_ventures = sorted(joint_ventures, key=lambda x: x["total_active"], reverse=True)

# 写入 Artifact report
artifact_dir = "/Users/nb/.gemini/antigravity/brain/4977a979-cde7-4c64-993d-eb1f3f91ccb4"
os.makedirs(artifact_dir, exist_ok=True)
report_path = os.path.join(artifact_dir, "joint_venture_projects.md")

with open(report_path, 'w', encoding='utf-8') as rf:
    rf.write("# 全港联合/合作开发一手新盘操盘手待确认表\n\n")
    rf.write("为了协助您彻底圈定后续非恒基项目的 PDF 真实折算操盘手归属，以下列出了 152 个过滤后项目中**所有合作开发的新盘项目**（已排除了已确认的恒基、会德丰、中海项目）：\n\n")
    rf.write("| 序号 | 区域 | 商圈 | 项目名称 | 登记的合作开发商 (Co-Developers) | 定价在售数 | 推荐/建议操盘手 (供参考) |\n")
    rf.write("| :---: | :--- | :--- | :--- | :--- | :---: | :--- |\n")
    for idx, j in enumerate(joint_ventures):
        # 简单给出参考意见
        rec_operator = "待确认"
        devs = j["developer"]
        if "港鐵" in devs or "地铁" in devs:
            # 港铁一般不主导日常销售价单排版，主导方通常是前几个合作方之一
            rec_operator = devs.split("/")[0].strip() + " (港铁合作)"
        elif "信和" in devs:
            rec_operator = "信和置业 (建议)"
        elif "新世界" in devs:
            rec_operator = "新世界发展 (建议)"
        elif "嘉里" in devs:
            rec_operator = "嘉里建设 (建议)"
            
        rf.write(f"| {idx+1} | {j['region']} | {j['district']} | {j['name']} | {devs} | **{j['total_active']}** | {rec_operator} |\n")

print(f"统计完成！共筛选出 {len(joint_ventures)} 个联合开发活跃新盘项目。")
