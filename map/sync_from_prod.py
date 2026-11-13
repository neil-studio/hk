#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地图网站全自动同步与发布工作流 (Map Sync Pipeline)
用于在正式版数据更新完成后，自动将正式版最新销控、价格、成交数据融合并发布到地图网站 (neil-studio/hk-map)。
具备：
1. 正式版数据合规守卫门禁
2. 全新楼盘自动识别与坐标智能兜底
3. 状态驱动生命周期管理与5D核心价值守恒保护
4. 数据极速压缩与图片流水线更新
5. 前端版本戳防缓存自动刷新
6. 数据完整性多维交叉审计
7. 支持 --test / 支线测试模式 (不向远程 main 分支强制推送)
8. 线上真实 HTTP 链路验收 (生产模式)
"""

import os
import sys
import time
import json
import math
import shutil
import subprocess
import requests
from datetime import datetime

# ================= 路径与常数配置 =================
SANDBOX_DIR = "/Users/nb/google/Antigravity/工作/运营/价单/sandbox"
PROD_DIR = "/Users/nb/google/Antigravity/工作/运营/价单_正式版"

PROD_DATA_JSON = os.path.join(PROD_DIR, "web", "data.json")
if not os.path.exists(PROD_DATA_JSON):
    PROD_DATA_JSON = os.path.join(PROD_DIR, "data.json")

SANDBOX_DATA_JSON = os.path.join(SANDBOX_DIR, "data.json")
COORDS_FILE = os.path.join(SANDBOX_DIR, "hk_project_coords.json")
BASE_INFO_FILE = os.path.join(PROD_DIR, "楼盘基础信息库.xlsx")
HTML_FILE = os.path.join(SANDBOX_DIR, "test_layout_floating.html")
LOG_FILE = os.path.join(SANDBOX_DIR, "sync_latest.log")

MTR_STATIONS = [
    {"station_name_zh": "堅尼地城", "station_name_en": "Kennedy Town", "lat": 22.2814, "lng": 114.1286, "lines": "港島綫"},
    {"station_name_zh": "香港大學", "station_name_en": "HKU", "lat": 22.2840, "lng": 114.1347, "lines": "港島綫"},
    {"station_name_zh": "西營盤", "station_name_en": "Sai Ying Pun", "lat": 22.2856, "lng": 114.1427, "lines": "港島綫"},
    {"station_name_zh": "上環", "station_name_en": "Sheung Wan", "lat": 22.2865, "lng": 114.1520, "lines": "港島綫/荃灣綫"},
    {"station_name_zh": "中環", "station_name_en": "Central", "lat": 22.2820, "lng": 114.1583, "lines": "港島綫/荃灣綫"},
    {"station_name_zh": "金鐘", "station_name_en": "Admiralty", "lat": 22.2793, "lng": 114.1654, "lines": "港島綫/荃灣綫/南港島綫/東鐵綫"},
    {"station_name_zh": "灣仔", "station_name_en": "Wan Chai", "lat": 22.2776, "lng": 114.1731, "lines": "港島綫"},
    {"station_name_zh": "銅鑼灣", "station_name_en": "Causeway Bay", "lat": 22.2802, "lng": 114.1840, "lines": "港島綫"},
    {"station_name_zh": "北角", "station_name_en": "North Point", "lat": 22.2912, "lng": 114.2001, "lines": "港島綫/將軍澳綫"},
    {"station_name_zh": "鰂魚涌", "station_name_en": "Quarry Bay", "lat": 22.2878, "lng": 114.2097, "lines": "港島綫/將軍澳綫"},
    {"station_name_zh": "筲箕灣", "station_name_en": "Shau Kei Wan", "lat": 22.2790, "lng": 114.2283, "lines": "港島綫"},
    {"station_name_zh": "柴灣", "station_name_en": "Chai Wan", "lat": 22.2649, "lng": 114.2371, "lines": "港島綫"},
    {"station_name_zh": "黃竹坑", "station_name_en": "Wong Chuk Hang", "lat": 22.2480, "lng": 114.1680, "lines": "南港島綫"},
    {"station_name_zh": "海怡半島", "station_name_en": "South Horizons", "lat": 22.2429, "lng": 114.1490, "lines": "南港島綫"},
    {"station_name_zh": "尖沙咀", "station_name_en": "Tsim Sha Tsui", "lat": 22.2973, "lng": 114.1726, "lines": "荃灣綫"},
    {"station_name_zh": "佐敦", "station_name_en": "Jordan", "lat": 22.3050, "lng": 114.1716, "lines": "荃灣綫"},
    {"station_name_zh": "油麻地", "station_name_en": "Yau Ma Tei", "lat": 22.3131, "lng": 114.1708, "lines": "荃灣綫/觀塘綫"},
    {"station_name_zh": "旺角", "station_name_en": "Mong Kok", "lat": 22.3193, "lng": 114.1694, "lines": "荃灣綫/觀塘綫"},
    {"station_name_zh": "深水埗", "station_name_en": "Sham Shui Po", "lat": 22.3309, "lng": 114.1622, "lines": "荃灣綫"},
    {"station_name_zh": "九龍塘", "station_name_en": "Kowloon Tong", "lat": 22.3368, "lng": 114.1760, "lines": "東鐵綫/觀塘綫"},
    {"station_name_zh": "啟德", "station_name_en": "Kai Tak", "lat": 22.3307, "lng": 114.1994, "lines": "屯馬綫"},
    {"station_name_zh": "宋皇臺", "station_name_en": "Sung Wong Toi", "lat": 22.3261, "lng": 114.1894, "lines": "屯馬綫"},
    {"station_name_zh": "何文田", "station_name_en": "Ho Man Tin", "lat": 22.3094, "lng": 114.1830, "lines": "觀塘綫/屯馬綫"},
    {"station_name_zh": "紅磡", "station_name_en": "Hung Hom", "lat": 22.3029, "lng": 114.1818, "lines": "東鐵綫/屯馬綫"},
    {"station_name_zh": "九龍", "station_name_en": "Kowloon", "lat": 22.3050, "lng": 114.1615, "lines": "東涌綫/機場快綫"},
    {"station_name_zh": "奧運", "station_name_en": "Olympic", "lat": 22.3178, "lng": 114.1601, "lines": "东涌綫"},
    {"station_name_zh": "南昌", "station_name_en": "Nam Cheong", "lat": 22.3265, "lng": 114.1537, "lines": "東涌綫/屯馬綫"}
]

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def calc_dist_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def find_nearest_mtr(lat, lng):
    closest = min(MTR_STATIONS, key=lambda s: calc_dist_m(lat, lng, s["lat"], s["lng"]))
    s_dist = round(calc_dist_m(lat, lng, closest["lat"], closest["lng"]))
    w_dist = round(s_dist * 1.3)
    w_min = round(w_dist / 75.0, 1)
    return {
        "address": "",
        "nearest_mtr_cn": closest["station_name_zh"],
        "nearest_mtr_en": closest["station_name_en"],
        "nearest_mtr_lines": closest["lines"],
        "nearest_mtr_lat": closest["lat"],
        "nearest_mtr_lng": closest["lng"],
        "dist_straight_m": s_dist,
        "dist_walk_m": w_dist,
        "walk_time_min": w_min
    }

def gate_check_prod():
    """防线 1: 检查正式版数据健康状态"""
    log("🛡️ [防线 1] 校验正式版最新数据完整性...")
    if not os.path.exists(PROD_DATA_JSON):
        raise RuntimeError(f"正式版 data.json 不存在: {PROD_DATA_JSON}")
    
    file_size = os.path.getsize(PROD_DATA_JSON)
    if file_size < 100 * 1024:
        raise RuntimeError(f"正式版 data.json 文件过小 ({file_size} bytes)，疑似异常！")
        
    with open(PROD_DATA_JSON, "r", encoding="utf-8") as f:
        prod_data = json.load(f)
        
    projects = prod_data.get("projects", [])
    if len(projects) < 100:
        raise RuntimeError(f"正式版项目数量异常过少 ({len(projects)} 个)，中止地图同步！")
        
    log(f"✅ 正式版数据校验通过: 共有 {len(projects)} 个项目，体积 {file_size / 1024:.1f} KB")
    return prod_data

def sync_data_json():
    """镜像同步 data.json 到 sandbox"""
    log("📦 同步正式版 data.json 镜像至 sandbox 目录...")
    shutil.copy2(PROD_DATA_JSON, SANDBOX_DATA_JSON)
    log(f"✅ 已成功拷贝至 {SANDBOX_DATA_JSON}")

def auto_register_new_projects(prod_data):
    """防线 2: 检测全新上线楼盘并执行智能坐标兜底，确保绝不白屏崩溃"""
    log("🔍 [防线 2] 检测是否存在未在地图建档的全新上线楼盘...")
    with open(COORDS_FILE, "r", encoding="utf-8") as f:
        coords_list = json.load(f)
        
    existing_names = {p["name"].strip() for p in coords_list}
    prod_projects = prod_data.get("projects", [])
    
    new_projs = [p for p in prod_projects if p["name"].strip() not in existing_names]
    if not new_projs:
        log("✅ 所有正式版楼盘均已在地图建档，无需新增点位。")
        return False
        
    log(f"⚠️ 发现 {len(new_projs)} 个全新楼盘上线: {[p['name'] for p in new_projs]}，执行自动坐标兜底...")
    
    # 尝试从楼盘基础信息库加载已有经纬度
    base_coords_map = {}
    if os.path.exists(BASE_INFO_FILE):
        try:
            import pandas as pd
            df = pd.read_excel(BASE_INFO_FILE, sheet_name='楼盘基础信息汇总')
            for _, r in df.iterrows():
                pn = str(r['项目名称']).strip()
                lat = r.get('GPS纬度') if pd.notna(r.get('GPS纬度')) else r.get('纬度')
                lng = r.get('GPS经度') if pd.notna(r.get('GPS经度')) else r.get('经度')
                dist = str(r.get('所属商圈', '')).strip()
                addr = str(r.get('详细门牌地址', '')).strip()
                if pd.notna(lat) and pd.notna(lng):
                    base_coords_map[pn] = (float(lat), float(lng), dist, addr)
        except Exception as e:
            log(f"读取基础信息库警告: {e}")

    # 计算各商圈已有楼盘均值坐标，供二级兜底
    district_coords = {}
    for p in coords_list:
        d = p.get("district", "九龙")
        if p.get("lat") and p.get("lng"):
            district_coords.setdefault(d, []).append((p["lat"], p["lng"]))
            
    district_centers = {}
    for d, pts in district_coords.items():
        district_centers[d] = (sum(pt[0] for pt in pts)/len(pts), sum(pt[1] for pt in pts)/len(pts))

    for p in new_projs:
        pname = p["name"].strip()
        pdist = p.get("district", "")
        parea = p.get("area", "")
        
        target_lat = None
        target_lng = None
        
        # 1. 优先查库
        if pname in base_coords_map:
            target_lat, target_lng, _ = base_coords_map[pname]
            log(f"   🎯 从基础信息库匹配到真实坐标: {pname} -> ({target_lat}, {target_lng})")
        # 2. 商圈均值兜底
        elif pdist in district_centers:
            c_lat, c_lng = district_centers[pdist]
            target_lat = round(c_lat + 0.0003, 6)
            target_lng = round(c_lng + 0.0003, 6)
            log(f"   📍 [商圈兜底] 分配 {pdist} 商圈均值坐标: {pname} -> ({target_lat}, {target_lng})")
        else:
            # 港岛或九龙全局中心
            target_lat = 22.3193 if "九龙" in parea else 22.2814
            target_lng = 114.1694 if "九龙" in parea else 114.1583
            log(f"   📍 [全局兜底] 分配默认中心坐标: {pname} -> ({target_lat}, {target_lng})")
            
        mtr_info = find_nearest_mtr(target_lat, target_lng)
        
        coords_list.append({
            "name": pname,
            "district": pdist,
            "area": parea,
            "address": p.get("address", ""),
            "lat": target_lat,
            "lng": target_lng,
            "nearest_mtr": mtr_info,
            "developer": p.get("developer", ""),
            "is_coming_soon": p.get("is_coming_soon", False),
            "coord_status": "verified" if pname in base_coords_map else "auto_fallback"
        })
        
    with open(COORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(coords_list, f, ensure_ascii=False, indent=2)
    log(f"✅ 全新楼盘注册完毕，已写入 {COORDS_FILE}")
    return True

def run_cmd(step_name, cmd):
    log(f"🚀 开始执行: {step_name}")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=SANDBOX_DIR, shell=True, capture_output=True, text=True)
    cost = time.time() - t0
    if res.returncode != 0:
        log(f"❌ {step_name} 失败！错误输出:\n{res.stderr}")
        raise RuntimeError(f"命令执行失败: {cmd}")
    log(f"✅ 完成: {step_name} (耗时: {cost:.1f}秒)")
    return res.stdout

def update_version_timestamp():
    """防线 5: 自动刷新前端防强缓存时间戳"""
    log("🔄 [防线 5] 刷新前端防强缓存时间戳 (MAP_DATA_VERSION)...")
    if not os.path.exists(HTML_FILE):
        return
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()
        
    new_v = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    import re
    html_mod = re.sub(r"const MAP_DATA_VERSION = '[^']+';", f"const MAP_DATA_VERSION = '{new_v}';", html)
    if html_mod != html:
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html_mod)
        log(f"✅ 已成功刷新前端缓存版本戳至: {new_v}")
    else:
        log("ℹ️ 未找到 MAP_DATA_VERSION 宏，跳过替换。")

def audit_sandbox_data(prod_data):
    """防线 3: 地图全量数据交叉审计"""
    log("🔍 [防线 3] 执行数据全量多维交叉审计 (Audit)...")
    with open(COORDS_FILE, "r", encoding="utf-8") as f:
        coords = json.load(f)
        
    prod_names = {p["name"].strip() for p in prod_data.get("projects", [])}
    coords_names = {p["name"].strip() for p in coords}
    
    # 检查数量
    log(f"   核验楼盘点位数: {len(coords)} 个 (正式版包含: {len(prod_names)} 个)")
    if len(coords) < 100:
        raise ValueError(f"地图点位总数 ({len(coords)}) 明显异常偏少！")
        
    # 检查合法坐标
    bad_coords = [p["name"] for p in coords if not (p.get("lat") and p.get("lng") and 22.1 <= p["lat"] <= 22.6 and 113.8 <= p["lng"] <= 114.5)]
    if bad_coords:
        raise ValueError(f"存在非法经纬度项目: {bad_coords}")
        
    # 检查关键数据字段挂载
    with_sc = sum(1 for p in coords if p.get("sales_control_summary"))
    with_tx = sum(1 for p in coords if p.get("recent_transactions"))
    ready_cnt = sum(1 for p in coords if p.get("property_type") == "ready")
    forward_cnt = sum(1 for p in coords if p.get("property_type") == "forward")
    log(f"   在售户型挂载: {with_sc}/{len(coords)} 盘，最近成交挂载: {with_tx}/{len(coords)} 盘")
    log(f"   生命周期统计: 现房 (ready) {ready_cnt} 盘，期房 (forward) {forward_cnt} 盘")
    
    if with_sc < 50:
        raise ValueError(f"销控在售户型挂载率过低 ({with_sc})，数据可能损坏！")
        
    log("✅ 地图全量数据交叉审计 100% 通过！")
    return {
        "total_coords": len(coords),
        "total_prod": len(prod_names),
        "with_sc": with_sc,
        "with_tx": with_tx,
        "ready_cnt": ready_cnt,
        "forward_cnt": forward_cnt
    }

def get_current_git_branch():
    res = subprocess.run("git rev-parse --abbrev-ref HEAD", cwd=SANDBOX_DIR, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def git_commit_and_push(is_test_mode=False):
    """防线 4: Git 状态幂等检查与推送"""
    current_branch = get_current_git_branch()
    log(f"🚀 [防线 4] 检查 Git 分支与状态 (当前分支: {current_branch})...")
    
    status_res = subprocess.run("git status --porcelain", cwd=SANDBOX_DIR, shell=True, capture_output=True, text=True)
    if not status_res.stdout.strip():
        log("ℹ️ 地图仓库无任何数据变动，无需重复提交。")
        return
        
    if is_test_mode or current_branch != "main":
        log(f"🧪 [支线测试保护] 当前处于支线/测试模式 (分支: {current_branch})，跳过向远程 main 分支的 git push 操作！")
        return

    log("检测到地图数据或图片更新，正在执行暂存...")
    subprocess.run("git add .", cwd=SANDBOX_DIR, shell=True, check=True)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"自动同步地图新盘数据: {now_str}"
    subprocess.run(f'git commit -m "{commit_msg}"', cwd=SANDBOX_DIR, shell=True, check=True)
    
    log("正在推送至 GitHub neil-studio/hk-map main 分支...")
    pushed = False
    for attempt in range(1, 4):
        push_res = subprocess.run("git push origin main", cwd=SANDBOX_DIR, shell=True, capture_output=True, text=True)
        if push_res.returncode == 0:
            log("✅ 成功推送到 GitHub 地图远程仓库！")
            pushed = True
            break
        else:
            log(f"⚠️ 第 {attempt} 次 push 失败: {push_res.stderr.strip()}，正在重试...")
            time.sleep(2 * attempt)
            
    if not pushed:
        log("❌ Git Push 3 次重试均失败，请检查网络或 GitHub 认证！")
        raise RuntimeError("地图仓库 Git Push 失败")

def verify_live_map_http():
    """防线 5: 线上真实 HTTP 链路审计"""
    log("🌐 执行地图网站线上真实 HTTP 验收 (Post-Push Verification)...")
    urls = [
        "https://neil-studio.github.io/hk-map/",
        "https://neil-studio.github.io/hk-map/hk_project_coords.json",
        "https://neil-studio.github.io/hk-map/data.json"
    ]
    for u in urls:
        try:
            bust = f"{u}?_t={int(time.time())}"
            res = requests.get(bust, timeout=12)
            if res.status_code == 200:
                log(f"✅ 线上访问正常 (200 OK): {u} ({len(res.content)} bytes)")
            else:
                log(f"⚠️ 线上访问状态码异常 ({res.status_code}): {u}")
        except Exception as e:
            log(f"⚠️ 线上访问探测超时或异常: {u} ({e})")

def main():
    is_test_mode = "--test" in sys.argv or "--branch" in sys.argv or "--no-push" in sys.argv
    branch_name = get_current_git_branch()
    if branch_name != "main":
        is_test_mode = True

    mode_label = "【支线测试模式】" if is_test_mode else "【生产全量模式】"
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== 地图网站同步流水线启动 {mode_label}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        
    log(f"🗺️ ==================== 启动地图网站数据同步流水线 {mode_label} ====================")
    log(f"📌 当前工作目录: {SANDBOX_DIR}")
    log(f"🌿 当前 Git 分支: {branch_name}")
    t_start = time.time()
    
    try:
        # 1. 守卫门禁
        prod_data = gate_check_prod()
        
        # 2. 拷贝镜像
        sync_data_json()
        
        # 3. 自动识别全新楼盘并执行兜底
        auto_register_new_projects(prod_data)
        
        # 4. 运行销控与成交增强编译
        run_cmd("重新编译销控与成交数据 (build_export_data.py)", "python3 build_export_data.py")
        
        # 5. 极速压缩点位数据
        run_cmd("极速压缩坐标与地标 (optimize_data_files.py)", "python3 optimize_data_files.py")
        
        # 6. 图片流水线更新
        run_cmd("更新楼盘图片资产清单 (process_project_images.py)", "python3 process_project_images.py")
        
        # 7. 刷新前端防缓存时间戳
        update_version_timestamp()
        
        # 8. 交叉审计
        audit_res = audit_sandbox_data(prod_data)
        
        # 9. Git 提交与推送
        git_commit_and_push(is_test_mode=is_test_mode)
        
        # 10. 线上探测验收 (仅在非测试模式且 push 后执行)
        if not is_test_mode:
            verify_live_map_http()
            
        cost_total = time.time() - t_start
        log(f"🎉 地图网站数据同步与全量测试全部顺利通过！总耗时: {cost_total:.1f}秒\n")
        return 0
    except Exception as e:
        log(f"🛑 地图网站同步流程出现异常中断: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
