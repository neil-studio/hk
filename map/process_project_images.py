#!/usr/bin/env python3
"""
楼盘高清原图处理与缩略图流水线脚本
1. 递归扫描 images/projects/original/（支持项目子文件夹或根目录直接放图）
2. 智能匹配 hk_project_coords.json 中的楼盘项目（自动兼容期数如 The Monet 第1/2/3期）
3. 自动生成保持原始比例、无损完整展示的极速 WebP 缩略图到 images/projects/thumb/
4. 建立 project_images_manifest.json 供前端毫秒级加载
"""

import os, glob, json
from PIL import Image, ImageOps

SANDBOX_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_DIR = os.path.join(SANDBOX_DIR, "images", "projects", "original")
THUMB_DIR = os.path.join(SANDBOX_DIR, "images", "projects", "thumb")
HD_DIR = os.path.join(SANDBOX_DIR, "images", "projects", "hd")
MANIFEST_FILE = os.path.join(SANDBOX_DIR, "project_images_manifest.json")
COORDS_FILE = os.path.join(SANDBOX_DIR, "hk_project_coords.json")

os.makedirs(ORIGINAL_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(HD_DIR, exist_ok=True)

SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.tif', '.tiff')

DATA_FILE = os.path.join(SANDBOX_DIR, "data.json")

# 明确的别名与特殊规则映射表
EXPLICIT_FOLDER_MAP = {
    "128 walter": ["128 Waterloo"],
    "天玺": ["天玺"],  # 仅限九龙站天玺，不扩散到启德天玺．天/天玺．海
    "st. george's mansions": ["St. George's Mansions", "st. george's mansions"],
    "维港.双钻": ["维港．双钻"],
    "维港.湾畔": ["维港．湾畔第1A期", "维港．湾畔第1B期", "维港．湾畔第2B期"],
    "blue coast": ["Blue Coast", "Blue Coast II"],
    "滶晨": ["滶晨", "滶晨 II"],
    "天玺．天": ["天玺．天", "天玺．天第2期"],
    "天玺.天": ["天玺．天", "天玺．天第2期"],
    "海璇": ["海璇", "海璇 II", "海璇 II (第2B-3期)"],
    "天铸": ["天铸", "天铸 (第2期)"],
    "汇玺": ["汇玺", "汇玺II", "汇玺III"],
    "南津.迎岸": ["南津．迎岸"],
    "南津．迎岸": ["南津．迎岸"],
}

def load_all_project_names():
    names = set()
    if os.path.exists(COORDS_FILE):
        try:
            with open(COORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data:
                if "name" in p:
                    names.add(p["name"])
        except Exception as e:
            print("读取 hk_project_coords.json 异常:", e)
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data.get("projects", []):
                if "name" in p:
                    names.add(p["name"])
        except Exception as e:
            print("读取 data.json 异常:", e)
    return sorted(list(names))

def match_projects(candidate_name, all_projects):
    c_lower = candidate_name.strip().lower()
    for exp_k, exp_targets in EXPLICIT_FOLDER_MAP.items():
        if exp_k.lower() == c_lower:
            return exp_targets

    c_clean = candidate_name.replace(' ', '').replace('_', '').replace('-', '').replace('·', '').replace('．', '').replace('.', '').lower()
    matches = []
    # 1. 精确匹配
    for p in all_projects:
        p_clean = p.replace(' ', '').replace('_', '').replace('-', '').replace('·', '').replace('．', '').replace('.', '').lower()
        if p_clean == c_clean:
            matches.append(p)
    if matches:
        return matches

    # 2. 包含匹配 (例如 the monet 匹配 The Monet 第1期, The Monet 第2期...)
    for p in all_projects:
        p_clean = p.replace(' ', '').replace('_', '').replace('-', '').replace('·', '').replace('．', '').replace('.', '').lower()
        if c_clean in p_clean:
            matches.append(p)
    if matches:
        return matches

    # 3. 反向包含匹配
    for p in all_projects:
        p_clean = p.replace(' ', '').replace('_', '').replace('-', '').replace('·', '').replace('．', '').replace('.', '').lower()
        if p_clean in c_clean:
            matches.append(p)
    return matches

def process_images():
    print(f"🔍 扫描高清原图目录: {ORIGINAL_DIR}")
    all_projects = load_all_project_names()

    # 递归查找所有图片
    image_entries = []
    for root, dirs, files in os.walk(ORIGINAL_DIR):
        for f in files:
            if f.startswith('.') or f == 'Icon' or f.endswith('.gitkeep'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTS:
                full_path = os.path.join(root, f)
                rel_dir = os.path.relpath(root, ORIGINAL_DIR)
                folder_name = rel_dir if rel_dir != '.' else ''
                base_name = os.path.splitext(f)[0].strip()
                # 候选名称优先取子文件夹名，否则取文件名
                candidate = folder_name if folder_name else base_name
                image_entries.append((candidate, full_path, f))

    if not image_entries:
        print("ℹ️ original 目录中暂无图片，请将楼盘高清原图放入该目录（支持子文件夹或直接放图）。")
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return

    manifest = {}
    processed_count = 0

    for candidate, orig_path, fname in sorted(image_entries, key=lambda x: x[0]):
        matched = match_projects(candidate, all_projects)
        if not matched:
            matched = [candidate]

        try:
            with Image.open(orig_path) as img:
                img = ImageOps.exif_transpose(img)
                w, h = img.size

                # 处理透明度
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGBA")
                    bg = Image.new("RGBA", img.size, (15, 23, 42, 255))
                    img = Image.alpha_composite(bg, img).convert("RGB")
                else:
                    img = img.convert("RGB")

                # 1. 生成极速缩略图：最大边长 360px (用于弹窗等微型视图)
                thumb_img = img.copy()
                max_thumb_edge = 360
                if max(w, h) > max_thumb_edge:
                    thumb_img.thumbnail((max_thumb_edge, max_thumb_edge), Image.Resampling.LANCZOS)

                # 2. 生成全高清优化大图 (HD)：最大边长 1600px，保留顶级视觉震撼力但体积压缩 90%+
                hd_img = img.copy()
                max_hd_edge = 1600
                if max(w, h) > max_hd_edge:
                    hd_img.thumbnail((max_hd_edge, max_hd_edge), Image.Resampling.LANCZOS)
                hd_w, hd_h = hd_img.size

                orig_rel = os.path.relpath(orig_path, SANDBOX_DIR)
                orig_size_kb = os.path.getsize(orig_path) / 1024

                # 规范化文件名映射，防止大小写敏感系统 (Linux/GitHub Pages) 404
                CANONICAL_NAME_MAP = {
                    "st. george's mansions": "St. George's Mansions",
                    "St. George's Mansions": "St. George's Mansions",
                    "park college": "Park College",
                    "Park College": "Park College",
                }

                for proj_name in matched:
                    canonical_name = CANONICAL_NAME_MAP.get(proj_name, proj_name)
                    thumb_filename = f"{canonical_name}.webp"
                    thumb_dest = os.path.join(THUMB_DIR, thumb_filename)
                    thumb_img.save(thumb_dest, "WEBP", quality=85, method=6)
                    thumb_size_kb = os.path.getsize(thumb_dest) / 1024

                    hd_filename = f"{canonical_name}.webp"
                    hd_dest = os.path.join(HD_DIR, hd_filename)
                    hd_img.save(hd_dest, "WEBP", quality=88, method=6)
                    hd_size_kb = os.path.getsize(hd_dest) / 1024

                    manifest[proj_name] = {
                        "original": orig_rel,
                        "hd": f"images/projects/hd/{hd_filename}",
                        "thumb": f"images/projects/thumb/{thumb_filename}",
                        "width": w,
                        "height": h,
                        "hd_width": hd_w,
                        "hd_height": hd_h,
                        "aspect_ratio": round(w / h, 3)
                    }
                    processed_count += 1
                    print(f"  ✅ 映射楼盘 [{proj_name}]: 原图 {w}x{h} ({orig_size_kb:.1f} KB) ➔ HD大图 {hd_w}x{hd_h} ({hd_size_kb:.1f} KB) ➔ 缩略图 ({thumb_size_kb:.1f} KB)")

        except Exception as e:
            print(f"  ❌ 处理图片失败 [{orig_path}]: {e}")

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 处理完毕！共生成 {processed_count} 个楼盘高清与缩略图映射，已更新索引至 project_images_manifest.json")

if __name__ == "__main__":
    process_images()
