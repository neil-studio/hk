import json
import os
from collections import defaultdict

data_path = "web/data.json"
if not os.path.exists(data_path):
    print("错误: 找不到 web/data.json 文件。")
    exit(1)

with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

projects = data.get("projects", [])

# 统计每个大区 (region) 下每个商圈 (district) 的项目数量
district_stats = defaultdict(lambda: defaultdict(int))
for p in projects:
    reg = p.get("region", "未知大区")
    dist = p.get("district", "未知商圈")
    district_stats[reg][dist] += 1

# 生成 Markdown 列表并写入 Artifact
artifact_dir = "/Users/nb/.gemini/antigravity/brain/4977a979-cde7-4c64-993d-eb1f3f91ccb4"
os.makedirs(artifact_dir, exist_ok=True)
report_path = os.path.join(artifact_dir, "districts_list.md")

with open(report_path, 'w', encoding='utf-8') as rf:
    rf.write("# 全港一手新盘所归属商圈/区域统计表\n\n")
    rf.write("为了帮您精准筛选要去掉的前端商圈，以下列出了 177 个项目目前所归属的全部商圈及其项目数量分类。\n\n")
    
    total_districts = 0
    for reg, dists in sorted(district_stats.items()):
        rf.write(f"## 📍 {reg} 区域\n\n")
        rf.write("| 序号 | 商圈名称 (District) | 包含项目数 | 归属大区 |\n")
        rf.write("| :---: | :--- | :---: | :---: |\n")
        for idx, (dist, count) in enumerate(sorted(dists.items(), key=lambda x: x[1], reverse=True)):
            total_districts += 1
            rf.write(f"| {idx+1} | {dist} | {count} | {reg} |\n")
        rf.write("\n")
        
print(f"统计完成！全港共包含 {total_districts} 个不同商圈。明细已写入 Artifact。")
