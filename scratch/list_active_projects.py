import json
import os

data_path = "web/data.json"
if not os.path.exists(data_path):
    print("错误: 找不到 web/data.json 文件。")
    exit(1)

with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

projects = data.get("projects", [])

active_projects = []
for p in projects:
    stats = p.get("stats", {})
    sale_count = stats.get("sale", 0)
    priced_count = stats.get("priced", 0)
    total_active = sale_count + priced_count
    
    # 只要在售定价或已定价未售套数大于 0
    if total_active > 0:
        active_projects.append({
            "name": p["name"],
            "region": p["region"],
            "district": p["district"],
            "sale": sale_count,
            "priced": priced_count,
            "total_active": total_active,
            "total": stats.get("total", 0),
            "sold_rate": stats.get("sold_rate", 0.0)
        })

# 降序排列
active_projects = sorted(active_projects, key=lambda x: x["total_active"], reverse=True)

# 生成 Markdown Report 写入 Artifacts
artifact_dir = "/Users/nb/.gemini/antigravity/brain/4977a979-cde7-4c64-993d-eb1f3f91ccb4"
os.makedirs(artifact_dir, exist_ok=True)
report_path = os.path.join(artifact_dir, "active_projects_list.md")

with open(report_path, 'w', encoding='utf-8') as rf:
    rf.write("# 全港一手新盘定价在售活跃项目明细表\n\n")
    rf.write(f"根据最新抓取数据分析，全港目前共有 **{len(active_projects)}** 个项目包含公开在售定价房源。\n\n")
    rf.write("| 序号 | 区域 | 商圈 | 项目名称 | 定价在售 (Sale) | 已定价未售 (Priced) | 合计定价在售 | 项目总套数 | 去化率 (Sold %) |\n")
    rf.write("| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n")
    for idx, ap in enumerate(active_projects):
        rf.write(f"| {idx+1} | {ap['region']} | {ap['district']} | {ap['name']} | {ap['sale']} | {ap['priced']} | **{ap['total_active']}** | {ap['total']} | {ap['sold_rate']}% |\n")

print(f"统计完成！共筛选出 {len(active_projects)} 个活跃在售定价项目。明细已写入 Artifact。")
