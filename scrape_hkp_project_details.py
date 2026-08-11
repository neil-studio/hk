#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
香港一手新盘项目基础信息全量抓取与持久化沉淀模块 (scrape_hkp_project_details.py)
用于自动获取 HKP 官方全量新盘项目的开发商、预计落成日期、大小学校网、详细门牌地址、GPS坐标、
物业管理公司、售楼处地址、官方网站、卖方控权结构、付款办法折扣、楼书 PDF 链接等全量基础数据。

防反爬机制：
1. 动态 Token 自动续期
2. 0.3s - 0.5s 人类行为休眠与温和频次控制
3. 指数退避重试机制 (Retries & Backoff)
4. 本地数据库 UNIQUE KEY 增量校验与零丢失沉淀
"""

import os
import re
import sys
import json
import time
import sqlite3
import random
import urllib3
import requests
from datetime import datetime

urllib3.disable_warnings()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

import scrape_hkp_sales_control as scraper

DB_PATH = os.path.join(BASE_DIR, "楼盘基础信息数据库.db")

def init_db():
    """初始化楼盘基础信息 SQLite 数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS project_details (
        hkp_pid TEXT PRIMARY KEY,               -- HKP 项目 ID (如 P000001272)
        project_name TEXT,                      -- 项目中文名称
        clean_project_name TEXT,                -- 规范化无期数项目名 (用于盘源库精准对号)
        phase_name TEXT,                        -- 期数名称
        developer TEXT,                         -- 开发商名称
        key_date TEXT,                          -- 预计落成/关键日期 (YYYY-MM-DD)
        first_price_list_date TEXT,             -- 首张价单公布日期
        first_sale_date TEXT,                   -- 首次开盘发售日期
        primary_school_net TEXT,                -- 小学校网 (如 80校网)
        secondary_school_net TEXT,              -- 中学校网 (如 北区校网)
        kindergarten_school_net TEXT,           -- 幼儿园学区 (如 北区)
        total_flats INTEGER,                    -- 规划总套数
        no_of_blocks TEXT,                      -- 楼栋座数 (如 2座)
        address TEXT,                           -- 详细门牌地址
        latitude REAL,                          -- GPS 纬度坐标
        longitude REAL,                         -- GPS 经度坐标
        management_co TEXT,                     -- 物业管理公司名称
        sales_addr TEXT,                        -- 售楼处展销厅地址
        project_url TEXT,                       -- 项目官方网站 URL
        vender TEXT,                            -- 卖方与母公司控权结构
        min_net_area INTEGER,                   -- 最小实用面积 (平方呎)
        max_net_area INTEGER,                   -- 最大实用面积 (平方呎)
        min_price REAL,                         -- 最低原价总价 (港币)
        discount_price REAL,                    -- 最低折实总价 (港币)
        discount_sale_min_psf REAL,             -- 最低折实呎价 (港币/呎)
        discount_sale_max_psf REAL,             -- 最高折实呎价 (港币/呎)
        discount_remark TEXT,                   -- 折实价计算公式与对应单位明细
        payment_json TEXT,                      -- 付款办法与折扣明细 JSON
        timeline_json TEXT,                     -- 盘源生命周期时间轴 JSON
        attachments_json TEXT,                  -- 官方楼书 PDF/价单 PDF 链接 JSON
        floorplan_json TEXT,                    -- 官方户型平面图链接 JSON
        raw_json TEXT,                          -- 完整原始 JSON 响应 (备用沉淀，100% 零丢失)
        updated_at TEXT                         -- 抓取更新时间戳
    );
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_proj_clean_name ON project_details (clean_project_name);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_proj_developer ON project_details (developer);")
    conn.commit()
    conn.close()

def parse_num(val):
    if val is None:
        return None
    s = str(val).strip().replace(',', '')
    try:
        return float(s)
    except:
        return None

def strip_phase(n):
    s = str(n).strip()
    s = re.sub(r'\(第.*?\)', '', s)
    s = re.sub(r'第\s*[0-9A-Za-z\-]+期.*$', '', s)
    s = re.sub(r'Phase\s*[0-9A-Za-z\-]+.*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'第[I|V|X|A-Z0-9]+期', '', s)
    s = re.sub(r'第[0-9A-Za-z]+$', '', s)
    s = re.sub(r'[0-9]+[a-zA-Z]+$', '', s)
    s = re.sub(r'\s+[0-9]+$', '', s)
    s = re.sub(r'\s+I{1,3}$', '', s)
    s = re.sub(r'\s+II$', '', s)
    s = re.sub(r'\s+III$', '', s)
    s = re.sub(r'\(.*?\)', '', s)
    return s.strip()

def scrape_all_project_details():
    """全量抓取 HKP 楼盘基础信息主流程"""
    init_db()
    
    print("\n" + "="*70)
    print(" 🚀 启动 HKP 全量一手新盘项目基础信息抓取引擎")
    print("="*70)
    
    token = scraper.fetch_user_token()
    if not token:
        print("❌ 无法获取 HKP API 验证 Token，抓取中止。")
        return
        
    print(f"✅ Token 获取成功! 长度: {len(token)}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.hkp.com.hk',
        'Referer': 'https://www.hkp.com.hk/'
    }
    
    print("\n🔍 正在获取 HKP 全量一手新盘列表...")
    url_list = 'https://data.hkp.com.hk/search/v2/new-properties?limit=1000'
    try:
        r = requests.get(url_list, headers=headers, verify=False, timeout=15)
        if r.status_code != 200:
            print(f"❌ 获取新盘列表失败，状态码: {r.status_code}")
            return
        projects_list = r.json().get('result', [])
    except Exception as e:
        print(f"❌ 请求新盘列表时发生异常: {e}")
        return

    print(f"🎉 成功获取全港一手新盘列表，共计 {len(projects_list)} 个项目。")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    success_count = 0
    skip_count = 0
    err_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for idx, item in enumerate(projects_list, 1):
        pid = item.get('id')
        pname = item.get('name') or item.get('news_name') or ''
        clean_pname = scraper.t2s(strip_phase(pname))
        
        if not pid:
            continue
            
        sys.stdout.write(f"\r[{idx}/{len(projects_list)}] 正在抓取 [{pname}] (ID: {pid})...")
        sys.stdout.flush()
        
        # 指数退避重试 (Backoff Retry)
        detail_data = None
        for retry in range(3):
            try:
                # 温和休眠与随机防刷间隔 (0.2s - 0.4s)
                time.sleep(random.uniform(0.2, 0.4))
                res = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=headers, verify=False, timeout=12)
                if res.status_code == 200:
                    detail_data = res.json()
                    break
                elif res.status_code == 401:
                    # Token 过期刷新
                    token = scraper.fetch_user_token()
                    headers['Authorization'] = f'Bearer {token}'
            except Exception:
                time.sleep(1.0 * (retry + 1))
                
        if not detail_data:
            err_count += 1
            print(f"\n⚠️  [{pname}] (ID: {pid}) 明细拉取失败，跳过。")
            continue
            
        # 解析提取核心字段
        d = detail_data
        
        dev = d.get('developer') or item.get('developer') or ''
        k_date_raw = d.get('key_date') or item.get('key_date')
        k_date = k_date_raw[:10] if k_date_raw else None
        
        f_plist_raw = d.get('first_price_list_date')
        f_plist = f_plist_raw[:10] if f_plist_raw else None
        
        f_sale_raw = d.get('first_sale_date')
        f_sale = f_sale_raw[:10] if f_sale_raw else None
        
        snet = d.get('school_net') or {}
        p_net = snet.get('primary', {}).get('id') or snet.get('primary', {}).get('name')
        if p_net: p_net = f"{p_net}校网" if '校网' not in str(p_net) else str(p_net)
        
        s_net = snet.get('secondary', {}).get('name') or snet.get('secondary', {}).get('id')
        if s_net: s_net = f"{s_net}校网" if '校网' not in str(s_net) else str(s_net)
        
        k_net = snet.get('kindergarten', {}).get('name') or snet.get('kindergarten', {}).get('id')
        
        tf_num = parse_num(d.get('total_flats'))
        total_flats = int(tf_num) if tf_num is not None else None
        
        no_blocks = d.get('no_of_blocks')
        addr = d.get('address')
        lat = parse_num(d.get('latitude'))
        lng = parse_num(d.get('longitude'))
        mgt = d.get('management_co')
        s_addr = d.get('sales_addr')
        p_url = d.get('project_url')
        vender = d.get('vender')
        
        min_area = parse_num(d.get('min_net_area'))
        max_area = parse_num(d.get('max_net_area'))
        min_p = parse_num(d.get('min_price'))
        disc_p = parse_num(d.get('discount_price'))
        disc_min_psf = parse_num(d.get('discount_sale_min_price_over_area'))
        disc_max_psf = parse_num(d.get('discount_sale_max_price_over_area'))
        disc_remark = d.get('discount_price_remark')
        
        pmt_json = json.dumps(d.get('payment', []), ensure_ascii=False)
        timeline_json = json.dumps(d.get('time_line', []), ensure_ascii=False)
        attachments_json = json.dumps(d.get('attachment', []), ensure_ascii=False)
        floorplan_json = json.dumps(d.get('floorplan', []), ensure_ascii=False)
        raw_json_str = json.dumps(d, ensure_ascii=False)
        
        # 写入数据库 (REPLACE INTO 保证增量最新)
        c.execute("""
        REPLACE INTO project_details (
            hkp_pid, project_name, clean_project_name, phase_name, developer, key_date,
            first_price_list_date, first_sale_date, primary_school_net, secondary_school_net,
            kindergarten_school_net, total_flats, no_of_blocks, address, latitude, longitude,
            management_co, sales_addr, project_url, vender, min_net_area, max_net_area,
            min_price, discount_price, discount_sale_min_psf, discount_sale_max_psf,
            discount_remark, payment_json, timeline_json, attachments_json, floorplan_json,
            raw_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            pid, pname, clean_pname, d.get('phase_name') or d.get('phase_no'), dev, k_date,
            f_plist, f_sale, p_net, s_net, k_net, total_flats, no_blocks, addr, lat, lng,
            mgt, s_addr, p_url, vender, min_area, max_area, min_p, disc_p, disc_min_psf, disc_max_psf,
            disc_remark, pmt_json, timeline_json, attachments_json, floorplan_json,
            raw_json_str, now_str
        ))
        success_count += 1
        
        if idx % 20 == 0:
            conn.commit()

    conn.commit()
    conn.close()
    
    print("\n\n" + "="*70)
    print(f" ✨ 抓取完成总结:")
    print(f"  • 成功抓取并写入数据库: {success_count} 个楼盘项目")
    print(f"  • 失败/跳过项目: {err_count} 个")
    print(f"  • 数据库保存路径: {DB_PATH}")
    print("="*70 + "\n")

if __name__ == '__main__':
    scrape_all_project_details()
