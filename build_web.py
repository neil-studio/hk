#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import shutil
import urllib.parse
from datetime import datetime
import openpyxl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
FILES_DIR = os.path.join(WEB_DIR, "files")

def ensure_dirs():
    """确保网页输出目录和文件存储目录存在，并清空旧的 files 目录以防遗留售罄项目"""
    os.makedirs(WEB_DIR, exist_ok=True)
    if os.path.exists(FILES_DIR):
        shutil.rmtree(FILES_DIR)
    os.makedirs(FILES_DIR, exist_ok=True)

def parse_project_stats(file_path):
    """
    通过只读模式打开 Excel，读取'销控汇总明细'表，计算项目销控状态统计。
    """
    stats = {
        'total': 0,
        'sold': 0,
        'sale': 0,
        'priced': 0,
        'stopped': 0,
        'pending': 0,
        'sold_rate': 0.0
    }
    
    if not os.path.exists(file_path):
        return stats
        
    try:
        # 使用 read_only=True 极速读取
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        if "销控汇总明细" in wb.sheetnames:
            ws = wb["销控汇总明细"]
            # 找到状态列的索引 (第一行可能是标题，第二行是表头)
            # 表头是：["楼栋", "楼层", "房号", "户型", "实用面积 (平方呎)", "销控状态", "成交日期", "总价 (港币)", "实用呎价 (港币/呎)", "是否招标"]
            # 销控状态在第 6 列 (index 5)
            
            row_count = 0
            for row in ws.iter_rows(min_row=3, max_col=6, values_only=True):
                # 检查是否是空行 (第一列"楼栋"为空则视为结束)
                if not row or row[0] is None:
                    break
                
                status_val = row[5] if len(row) >= 6 else None
                if status_val:
                    status_str = str(status_val).strip()
                    row_count += 1
                    
                    if status_str == '已售':
                        stats['sold'] += 1
                    elif status_str == '在售':
                        stats['sale'] += 1
                    elif status_str == '已定价未售':
                        stats['priced'] += 1
                    elif status_str == '暂停销售':
                        stats['stopped'] += 1
                    elif status_str == '待售':
                        stats['pending'] += 1
                    else:
                        if '已售' in status_str:
                            stats['sold'] += 1
                        else:
                            stats['pending'] += 1
            
            stats['total'] = row_count
            if stats['total'] > 0:
                stats['sold_rate'] = round((stats['sold'] / stats['total']) * 100, 1)
        wb.close()
    except Exception as e:
        print(f"警告: 读取 Excel {file_path} 统计信息失败: {e}")
        
    return stats

def fetch_hkp_status_map():
    """从 HKP 接口拉取项目级销售状态 (sell_status & sell_status_detail) 映射"""
    status_map = {}
    try:
        import sys, requests, urllib3
        urllib3.disable_warnings()
        sys.path.append(BASE_DIR)
        import scrape_hkp_sales_control as scraper
        
        token = scraper.fetch_user_token()
        headers = {'Authorization': f'Bearer {token}'}
        r = requests.get('https://data.hkp.com.hk/search/v2/new-properties?limit=1000', headers=headers, verify=False, timeout=10)
        if r.status_code == 200:
            for p in r.json().get('result', []):
                pname = scraper.t2s(p.get('name'))
                st = p.get('sell_status', 'on_sale')
                st_detail = p.get('sell_status_detail', {})
                st_cn = st_detail.get('name') if isinstance(st_detail, dict) else '出售中'
                status_map[pname] = {
                    'sell_status': st,
                    'sell_status_cn': st_cn
                }
    except Exception as e:
        print(f"提示: 获取 HKP 状态映射失败: {e}，将使用项目统计保底。")
    return status_map

def load_real_history_analytics():
    """从 SQLite 数据库 成交历史数据库.db 抽取 3.7万+ 条真实历史成交数据并按项目、年、月、周聚合"""
    db_path = os.path.join(BASE_DIR, "成交历史数据库.db")
    if not os.path.exists(db_path):
        print("提示: 未找到 成交历史数据库.db，无法生成真实成交分析。")
        return {}

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('SELECT project_name, district, region, sold_date, price, disc_price, unit_price, disc_unit_price, layout, area FROM sold_history WHERE sold_date IS NOT NULL AND sold_date != ""')
        rows = c.fetchall()
        conn.close()

        print(f"成功从 SQLite 抽取 {len(rows)} 条真实成交历史记录。")
        projects_analytics = {}

        def parse_num(val):
            if not val:
                return 0.0
            val_str = str(val).strip()
            if val_str in ('-', '暂无', 'null', 'None', '', '招标单位'):
                return 0.0
            try:
                return float(val_str.replace(',', ''))
            except:
                return 0.0

        for row in rows:
            pname, dist, reg, sdate, price, dprice, uprice, duprice, layout, area = row
            if not pname: continue

            # 真实成交价与实用呎价 (含保底倒算)
            f_price = parse_num(dprice) or parse_num(price)
            f_uprice = parse_num(duprice) or parse_num(uprice)
            f_area = parse_num(area)

            if f_uprice == 0 and f_price > 0 and f_area > 0:
                f_uprice = round(f_price / f_area)

            # 统一项目名称
            pname = pname.strip()
            if pname not in projects_analytics:
                projects_analytics[pname] = {
                    'region': reg,
                    'district': dist,
                    'yearly': {},
                    'monthly': {},
                    'weekly': {},
                    'layouts': {'开放式': 0, '1房': 0, '2房': 0, '3房': 0, '4房+': 0},
                    'price_ranges': {'500万下': 0, '500-1000万': 0, '1000-2000万': 0, '2000-5000万': 0, '5000万+': 0}
                }

            pa = projects_analytics[pname]
            sdate_clean = str(sdate).strip()

            # 归类年、月、周
            try:
                year = sdate_clean[:4]
                month = sdate_clean[:7]
                # 计算 ISO 周度
                dt_parts = [int(p) for p in sdate_clean[:10].split('-')]
                dt_obj = datetime(dt_parts[0], dt_parts[1], dt_parts[2])
                iso_yr, iso_wk, _ = dt_obj.isocalendar()
                week = f"{iso_yr}-W{iso_wk:02d}"
            except:
                continue

            # 统计年度
            if year not in pa['yearly']:
                pa['yearly'][year] = {'volume': 0, 'total_price': 0.0, 'total_uprice': 0.0, 'uprices': []}
            pa['yearly'][year]['volume'] += 1
            pa['yearly'][year]['total_price'] += f_price
            if f_uprice > 0:
                pa['yearly'][year]['total_uprice'] += f_uprice
                pa['yearly'][year]['uprices'].append(f_uprice)

            # 统计月度
            if month not in pa['monthly']:
                pa['monthly'][month] = {'volume': 0, 'total_price': 0.0, 'total_uprice': 0.0, 'uprices': []}
            pa['monthly'][month]['volume'] += 1
            pa['monthly'][month]['total_price'] += f_price
            if f_uprice > 0:
                pa['monthly'][month]['total_uprice'] += f_uprice
                pa['monthly'][month]['uprices'].append(f_uprice)

            # 统计周度
            if week:
                if week not in pa['weekly']:
                    pa['weekly'][week] = {'volume': 0, 'total_price': 0.0, 'total_uprice': 0.0, 'uprices': []}
                pa['weekly'][week]['volume'] += 1
                pa['weekly'][week]['total_price'] += f_price
                if f_uprice > 0:
                    pa['weekly'][week]['total_uprice'] += f_uprice
                    pa['weekly'][week]['uprices'].append(f_uprice)

            # 统计户型分布
            l_str = str(layout) if layout else ''
            if '开放式' in l_str or '开放' in l_str: pa['layouts']['开放式'] += 1
            elif '1房' in l_str or '一房' in l_str: pa['layouts']['1房'] += 1
            elif '2房' in l_str or '两房' in l_str or '二房' in l_str: pa['layouts']['2房'] += 1
            elif '3房' in l_str or '三房' in l_str: pa['layouts']['3房'] += 1
            else: pa['layouts']['4房+'] += 1

            # 统计总价区间
            if f_price < 5000000: pa['price_ranges']['500万下'] += 1
            elif f_price < 10000000: pa['price_ranges']['500-1000万'] += 1
            elif f_price < 20000000: pa['price_ranges']['1000-2000万'] += 1
            elif f_price < 50000000: pa['price_ranges']['2000-5000万'] += 1
            else: pa['price_ranges']['5000万+'] += 1

        # 计算平均与最大最小值
        for pname, pa in projects_analytics.items():
            for t_dict in [pa['yearly'], pa['monthly'], pa['weekly']]:
                for key, val in t_dict.items():
                    vol = val['volume']
                    val['avg_price'] = round(val['total_price'] / vol, 2) if vol > 0 else 0
                    u_list = val['uprices']
                    val['avg_uprice'] = round(sum(u_list) / len(u_list), 1) if u_list else 0
                    val['min_uprice'] = round(min(u_list), 1) if u_list else 0
                    val['max_uprice'] = round(max(u_list), 1) if u_list else 0
                    del val['total_price']
                    del val['total_uprice']
                    del val['uprices']

        return projects_analytics
    except Exception as e:
        print(f"处理真实成交分析失败: {e}")
        return {}

def build_leaderboard_data():
    """从 SQLite 数据库 成交历史数据库.db 生成动态多维热销榜单数据"""
    db_path = os.path.join(BASE_DIR, "成交历史数据库.db")
    if not os.path.exists(db_path):
        return {}

    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        def query_rankings(where_clause, limit=10):
            q = f'''
                SELECT project_name, region, district, COUNT(*) as volume, 
                       AVG(CAST(COALESCE(NULLIF(disc_price,''), price) AS REAL)) as avg_price,
                       AVG(CAST(COALESCE(NULLIF(disc_unit_price,''), unit_price) AS REAL)) as avg_sqft
                FROM sold_history 
                WHERE sold_date IS NOT NULL AND sold_date != '' AND {where_clause}
                GROUP BY project_name
                ORDER BY volume DESC
                LIMIT {limit}
            '''
            c.execute(q)
            res = []
            for r in c.fetchall():
                res.append({
                    'project_name': r[0],
                    'region': r[1] or '九龙',
                    'district': r[2] or '',
                    'volume': r[3],
                    'avg_price_wan': round(r[4] / 10000, 1) if r[4] else 0,
                    'avg_sqft': round(r[5]) if r[5] else 0
                })
            return res

        def get_category_bundle(where_prefix):
            return {
                'overall': query_rankings(f"{where_prefix}", 10),
                'region_hk': query_rankings(f"{where_prefix} AND region = '港岛'", 10),
                'region_kl': query_rankings(f"{where_prefix} AND region = '九龙'", 10),
                'price_500_2000m': query_rankings(f"{where_prefix} AND CAST(COALESCE(NULLIF(disc_price,''), price) AS REAL) BETWEEN 5000000 AND 20000000", 10),
                'price_2000_5000m': query_rankings(f"{where_prefix} AND CAST(COALESCE(NULLIF(disc_price,''), price) AS REAL) BETWEEN 20000000 AND 50000000", 10),
                'price_5000_10000m': query_rankings(f"{where_prefix} AND CAST(COALESCE(NULLIF(disc_price,''), price) AS REAL) BETWEEN 50000000 AND 100000000", 10),
                'price_10000m_above': query_rankings(f"{where_prefix} AND CAST(COALESCE(NULLIF(disc_price,''), price) AS REAL) >= 100000000", 10)
            }

        # 1. 提取可用年份
        c.execute("SELECT DISTINCT substr(sold_date, 1, 4) FROM sold_history WHERE sold_date IS NOT NULL AND sold_date != '' ORDER BY sold_date DESC LIMIT 5")
        years = [r[0] for r in c.fetchall() if r[0] and len(r[0]) == 4]
        
        years_list = []
        yearly_map = {}
        for y in years:
            label = f"{y}年度累计" if y == "2026" else f"{y}全年度"
            years_list.append({'val': y, 'label': label})
            yearly_map[y] = get_category_bundle(f"substr(sold_date, 1, 4) = '{y}'")

        # 2. 提取可用月份
        c.execute("SELECT DISTINCT substr(sold_date, 1, 7) FROM sold_history WHERE sold_date IS NOT NULL AND sold_date != '' ORDER BY sold_date DESC LIMIT 12")
        months = [r[0] for r in c.fetchall() if r[0] and len(r[0]) == 7]

        months_list = []
        monthly_map = {}
        for idx, m in enumerate(months):
            parts = m.split('-')
            m_label = f"{parts[0]}年{int(parts[1])}月" + (" (最新)" if idx == 0 else "")
            months_list.append({'val': m, 'label': m_label})
            monthly_map[m] = get_category_bundle(f"substr(sold_date, 1, 7) = '{m}'")

        # 3. 提取可用周度
        c.execute("SELECT sold_date FROM sold_history WHERE sold_date >= '2026-01-01' AND sold_date IS NOT NULL AND sold_date != '' ORDER BY sold_date DESC")
        date_rows = c.fetchall()
        week_map_raw = {}
        for r in date_rows:
            dstr = str(r[0]).strip()
            try:
                dt_parts = [int(p) for p in dstr[:10].split('-')]
                dt_obj = datetime(dt_parts[0], dt_parts[1], dt_parts[2])
                iso_yr, iso_wk, _ = dt_obj.isocalendar()
                w_key = f"{iso_yr}-W{iso_wk:02d}"
                if w_key not in week_map_raw:
                    week_map_raw[w_key] = {'year': iso_yr, 'week_num': iso_wk, 'min_date': dstr[:10], 'max_date': dstr[:10]}
                else:
                    if dstr[:10] < week_map_raw[w_key]['min_date']: week_map_raw[w_key]['min_date'] = dstr[:10]
                    if dstr[:10] > week_map_raw[w_key]['max_date']: week_map_raw[w_key]['max_date'] = dstr[:10]
            except:
                continue

        sorted_weeks = sorted(week_map_raw.keys(), reverse=True)[:10]
        weeks_list = []
        weekly_map = {}
        for idx, w in enumerate(sorted_weeks):
            w_info = week_map_raw[w]
            w_label = f"{w_info['year']}年第{w_info['week_num']}周 ({w_info['min_date'][5:].replace('-','/')}-{w_info['max_date'][5:].replace('-','/')})" + (" (最新)" if idx == 0 else "")
            weeks_list.append({'val': w, 'label': w_label})
            weekly_map[w] = get_category_bundle(f"sold_date BETWEEN '{w_info['min_date']}' AND '{w_info['max_date']}'")

        conn.close()

        return {
            'options': {
                'months': months_list,
                'weeks': weeks_list,
                'years': years_list
            },
            'monthly_map': monthly_map,
            'weekly_map': weekly_map,
            'yearly_map': yearly_map
        }
    except Exception as e:
        print(f"构建动态排行榜失败: {e}")
        return {}

def main():
    print("开始扫描价单目录并构建网页数据库...")
    ensure_dirs()
    hkp_status_map = fetch_hkp_status_map()
    real_history = load_real_history_analytics()
    leaderboards = build_leaderboard_data()
    
    projects_list = []
    
    # 统计汇总
    global_stats = {
        'total_projects': 0,
        'total_units': 0,
        'total_sold': 0,
        'total_sale': 0,
        'total_priced': 0,
        'total_stopped': 0,
        'total_pending': 0,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 0. 读取 config_admin.json 配置
    admin_config = {}
    config_path = os.path.join(BASE_DIR, "config_admin.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                admin_config = json.load(f)
        except Exception as e:
            print(f"读取 config_admin.json 失败: {e}")
            
    focus_projects = admin_config.get('focus_projects', [])
    featured_by_price = admin_config.get('featured_by_price', {})
    projects_data = admin_config.get('projects_data', {})

    rental_bm_file = os.path.join(BASE_DIR, "rental_benchmarks.json")
    rental_benchmarks = {}
    if os.path.exists(rental_bm_file):
        try:
            with open(rental_bm_file, 'r', encoding='utf-8') as f:
                rental_benchmarks = json.load(f)
        except Exception as e:
            print(f"读取 rental_benchmarks.json 失败: {e}")

    # 遍历 BASE_DIR 下的子文件夹
    for d in sorted(os.listdir(BASE_DIR)):
        dir_path = os.path.join(BASE_DIR, d)
        if not os.path.isdir(dir_path):
            continue
            
        if d.startswith('.') or d in ['web', 'scratch']:
            continue
            
        parts = d.split('-')
        if len(parts) < 3:
            continue
            
        region = parts[0].strip()
        district = parts[1].strip()
        project_name = "-".join(parts[2:]).strip()
        
        EXCLUDE_DISTRICTS = {"将军澳", "茶果岭、油塘及鲤鱼门", "长沙湾", "牛头角及九龙湾", "慈云山、钻石山及新蒲岗"}
        if region == "九龙" and district in EXCLUDE_DISTRICTS:
            continue
        
        excel_filename = f"{project_name}_销控明细表.xlsx"
        src_excel_path = os.path.join(dir_path, excel_filename)
        
        if not os.path.exists(src_excel_path):
            found = False
            for file in os.listdir(dir_path):
                if file.endswith("_销控明细表.xlsx"):
                    src_excel_path = os.path.join(dir_path, file)
                    excel_filename = file
                    found = True
                    break
            if not found:
                continue
        
        stats = parse_project_stats(src_excel_path)
        
        if stats['total'] > 0 and stats['sold'] == stats['total']:
            continue
        
        dest_filename = f"{region}-{district}-{project_name}.xlsx"
        dest_excel_path = os.path.join(FILES_DIR, dest_filename)
        
        try:
            shutil.copy2(src_excel_path, dest_excel_path)
            file_size_kb = round(os.path.getsize(dest_excel_path) / 1024, 1)
        except Exception as e:
            continue
            
        mtime = os.path.getmtime(src_excel_path)
        last_updated_date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        
        hkp_st_info = hkp_status_map.get(project_name, {})
        sell_status = hkp_st_info.get('sell_status', 'on_sale')
        sell_status_cn = hkp_st_info.get('sell_status_cn', '出售中')
        
        custom_map = {
            # MONACO 全系合并
            'Monaco 第1期': ('九龙', '启德', 'MONACO'),
            'Monaco One': ('九龙', '启德', 'MONACO'),
            'Monaco Marine': ('九龙', '启德', 'MONACO'),
            'MONACO': ('九龙', '启德', 'MONACO'),
            'MONACO ONE': ('九龙', '启德', 'MONACO'),
            'MONACO MARINE': ('九龙', '启德', 'MONACO'),
            
            # 启德海湾全系合并
            '启德海湾': ('九龙', '启德', '启德海湾'),
            '启德海湾 1': ('九龙', '启德', '启德海湾'),
            '启德海湾 2': ('九龙', '启德', '启德海湾'),
            '启德海湾1期': ('九龙', '启德', '启德海湾'),
            '启德海湾2期': ('九龙', '启德', '启德海湾'),
            
            # 汇玺全系合并
            '汇玺III': ('九龙', '西南九龙', '汇玺'),
            '汇玺3期': ('九龙', '西南九龙', '汇玺'),
            '汇玺': ('九龙', '西南九龙', '汇玺'),
            
            # THE HENLEY 全系合并
            'Henley Park': ('九龙', '启德', 'THE HENLEY'),
            'The Henley I': ('九龙', '启德', 'THE HENLEY'),
            'The Henley II': ('九龙', '启德', 'THE HENLEY'),
            'The Henley III': ('九龙', '启德', 'THE HENLEY'),
            'THE HENLEY': ('九龙', '启德', 'THE HENLEY'),
            
            # Double Coast 全系合并
            'Double Coast I': ('九龙', '启德', 'Double Coast'),
            'Double Coast III': ('九龙', '启德', 'Double Coast'),

            'Mount Nicholson I': ('港岛', '山顶区', 'Mount Nicholson'),
            'Mount Nicholson II': ('港岛', '山顶区', 'Mount Nicholson'),
            'Blue Coast': ('港岛', '黄竹坑', 'Blue Coast'),
            'Blue Coast II': ('港岛', '黄竹坑', 'Blue Coast'),
            '滶晨': ('港岛', '黄竹坑', '滶晨'),
            '滶晨 II': ('港岛', '黄竹坑', '滶晨'),
            'Central Peak I': ('港岛', '半山区东部', 'Central Peak'),
            'Central Peak II': ('港岛', '半山区东部', 'Central Peak'),
            '维港汇 I': ('九龙', '西南九龙', '维港汇'),
            '维港汇 III': ('九龙', '西南九龙', '维港汇'),
            '海璇': ('港岛', '北角', '海璇'),
            '海璇 II': ('港岛', '北角', '海璇'),
            '海璇 II (第2B-3期)': ('港岛', '北角', '海璇'),
            '利奥坊．凯岸': ('九龙', '旺角', '利奥坊'),
            '利奥坊．壹隅': ('九龙', '旺角', '利奥坊'),
            '利奥坊．曦岸': ('九龙', '旺角', '利奥坊'),
            '必嘉坊．曦汇': ('九龙', '红磡', '必嘉坊'),
            '必嘉坊．迎汇': ('九龙', '红磡', '必嘉坊'),
            '瑜一': ('九龙', '何文田', '瑜一'),
            '瑜一第IC期': ('九龙', '何文田', '瑜一'),
            '瑜一．天海': ('九龙', '何文田', '瑜一'),
            'The Monet 第1期': ('九龙', '九龙塘', 'The Monet'),
            'The Monet 第2期': ('九龙', '九龙塘', 'The Monet'),
            'The Monet 第3期': ('九龙', '九龙塘', 'The Monet'),
            '朗贤峰第IIA期': ('九龙', '何文田', '朗贤峰'),
            '朗贤峰第IIB期': ('九龙', '何文田', '朗贤峰'),
            '海盈山第4A期': ('港岛', '黄竹坑', '海盈山'),
            '海盈山第4B期': ('港岛', '黄竹坑', '海盈山'),
            'Deep Water South 第6A期': ('港岛', '寿臣山及浅水湾', 'Deep Water South'),
            'Deep Water South 第6B期': ('港岛', '寿臣山及浅水湾', 'Deep Water South'),
            '天御第1期': ('港岛', '半山区西部', '天御'),
            '天御第2期': ('港岛', '半山区西部', '天御'),
            '壹沐第1期': ('九龙', '马头角', '壹沐'),
            '壹沐第2期': ('九龙', '马头角', '壹沐'),
            '首岸第1期': ('九龙', '红磡', '首岸'),
            '首岸第2期': ('九龙', '红磡', '首岸'),
            '首岸第3期': ('九龙', '红磡', '首岸'),
            '首岸第4期': ('九龙', '红磡', '首岸'),
        }

        def clean_master_folder_name(reg_val, dist_val, name_val):
            m = name_val.strip()
            if m in custom_map:
                r_c, d_c, master_n = custom_map[m]
                folder = f"{r_c}-{d_c}-{master_n}"
            else:
                m = re.sub(r'\(第.*?\)', '', m)
                m = re.sub(r'第\s*[0-9A-Za-z\-]+期.*$', '', m)
                m = re.sub(r'Phase\s*[0-9A-Za-z\-]+.*$', '', m, flags=re.IGNORECASE)
                m = re.sub(r'II\s*\(.*\)$', '', m)
                m = re.sub(r'第[I|V|X|A-Z0-9]+期', '', m)
                m = re.sub(r'\s+I{1,3}$', '', m)
                m = re.sub(r'\s+II$', '', m)
                m = re.sub(r'\s+III$', '', m)
                m = re.sub(r'\(.*?\)', '', m)
                master_name = m if m else name_val
                folder = f"{reg_val}-{dist_val}-{master_name}"
            PARENT_DRIVE_ID = "15tRwSlG1VTOKuEyj-H131zpNK6v6MY04"
            drive_q = f'parent:{PARENT_DRIVE_ID} "{folder}"'
            drive_url = f"https://drive.google.com/drive/search?q={urllib.parse.quote(drive_q)}"
            return folder, drive_url

        g_folder, g_url = clean_master_folder_name(region, district, project_name)
        
        dist_info = rental_benchmarks.get('districts', {}).get(district, rental_benchmarks.get('default_fallback', {'base_rent': 50, 'min_rent': 42, 'max_rent': 60}))
        base_rent = dist_info.get('base_rent', 50)
        min_rent = dist_info.get('min_rent', 42)
        max_rent = dist_info.get('max_rent', 60)
        
        p_hist = real_history.get(project_name, {})
        m_dict = p_hist.get('monthly', {})
        p_meta = projects_data.get(project_name, {})
        tot_vol = sum(m.get('volume', 0) for m in m_dict.values())
        tot_val = sum(m.get('volume', 0) * m.get('avg_uprice', 0) for m in m_dict.values())
        avg_uprice = int(tot_val / tot_vol) if tot_vol > 0 else 0

        if avg_uprice > 0:
            calc_roi = round((base_rent * 12 / avg_uprice) * 100, 2)
            roi_str = f"{calc_roi}%"
        else:
            roi_str = p_meta.get('roi') or "3.5%"

        estimated_rent_desc = f"${min_rent} - ${max_rent}/呎"

        proj_info = {
            'name': project_name,
            'region': region,
            'district': district,
            'filename': dest_filename,
            'file_size_kb': file_size_kb,
            'stats': stats,
            'last_updated': last_updated_date,
            'sell_status': sell_status,
            'sell_status_cn': sell_status_cn,
            'is_suspended': (sell_status == 'sales_suspended') or (stats.get('stopped', 0) > 0 and stats.get('sale', 0) == 0),
            'is_coming_soon': sell_status == 'coming_soon',
            'is_registration': sell_status == 'registration',
            'grade': p_meta.get('grade', 'C'),
            'basic_info': p_meta.get('basic_info', ''),
            'selling_points': p_meta.get('selling_points', ''),
            'mainland_selling_points': p_meta.get('mainland_selling_points', ''),
            'centaline_url': p_meta.get('centaline_url', ''),
            'intro_url': p_meta.get('intro_url', p_meta.get('centaline_url', '')),
            'price_tier': p_meta.get('price_tier', ''),
            'google_drive_folder': g_folder,
            'marketing_url': g_url,
            'main_layout': p_meta.get('main_layout', ''),
            'total_price_desc': p_meta.get('total_price', ''),
            'sqft_price_desc': p_meta.get('sqft_price', ''),
            'rent_range_desc': p_meta.get('rent_range') or estimated_rent_desc,
            'roi': roi_str if avg_uprice > 0 else (p_meta.get('roi') or roi_str),
            'avg_uprice': avg_uprice,
            'base_sqft_rent': base_rent,
            'estimated_sqft_rent_desc': estimated_rent_desc,
            'reason': p_meta.get('reason', ''),
            'is_focus': project_name in focus_projects
        }
        projects_list.append(proj_info)
        
        global_stats['total_projects'] += 1
        global_stats['total_units'] += stats['total']
        global_stats['total_sold'] += stats['sold']
        global_stats['total_sale'] += stats['sale']
        global_stats['total_priced'] += stats['priced']
        global_stats['total_stopped'] += stats['stopped']
        global_stats['total_pending'] += stats['pending']

    if global_stats['total_units'] > 0:
        global_stats['overall_sold_rate'] = round((global_stats['total_sold'] / global_stats['total_units']) * 100, 1)
    else:
        global_stats['overall_sold_rate'] = 0.0

    db_data = {
        'global_stats': global_stats,
        'projects': projects_list,
        'focus_projects': focus_projects,
        'featured_by_price': featured_by_price,
        'projects_data': projects_data,
        'real_history_analytics': real_history,
        'leaderboards': leaderboards
    }
    
    json_path = os.path.join(WEB_DIR, "data.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)

    js_path = os.path.join(WEB_DIR, "data.js")
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write("window.APP_DATA = " + json.dumps(db_data, ensure_ascii=False) + ";")
        
    # 检查是否有新增项目需要建 Google Drive 文件夹提醒
    known_folders_cache_file = os.path.join(BASE_DIR, "known_folders.json")
    known_folders = set()
    if os.path.exists(known_folders_cache_file):
        try:
            with open(known_folders_cache_file, 'r', encoding='utf-8') as f:
                known_folders = set(json.load(f))
        except:
            pass

    current_folders = set(p['google_drive_folder'] for p in projects_list if 'google_drive_folder' in p)
    new_folders = current_folders - known_folders

    if new_folders and len(known_folders) > 0:
        print("\n" + "="*70)
        print("🔔【新增盘源 Google Drive 建文件夹提醒】")
        for nf in sorted(new_folders):
            print(f" ➔ 发现新增盘源，请在 Google Drive 中新建对应的文件夹: [{nf}]")
        print("="*70 + "\n")

    # 保存最新已知文件夹缓存
    with open(known_folders_cache_file, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(current_folders)), f, ensure_ascii=False, indent=2)

    print(f"\n构建成功! 共处理 {global_stats['total_projects']} 个项目，包含 {len(real_history)} 个项目的真实成交历史统计。")
    print(f"数据索引已写入: {json_path} 及 {js_path}")

if __name__ == "__main__":
    main()
