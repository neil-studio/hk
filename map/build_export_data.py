#!/usr/bin/env python3
"""
销控数据与成交数据增强处理脚本
自动遍历全部 Excel 销控表，提取：
1. 项目在售户型、面积段、价格段、招标标识 (未售房源)
2. 项目所有户型最近成交的 2 套真实成交记录 (楼栋单位号、面积、总价、单价、成交日期)
3. 发展商与落成日期
更新至 sandbox/hk_project_coords.json
"""

import os, json, re, glob, sqlite3
from datetime import datetime
import openpyxl

SANDBOX_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SANDBOX_DIR, ".."))
PROD_DIR = "/Users/nb/google/Antigravity/工作/运营/价单_正式版"
FILES_DIR = os.path.join(PROD_DIR, "files")
COORDS_FILE = os.path.join(SANDBOX_DIR, "hk_project_coords.json")

DATA_FILE = os.path.join(PROD_DIR, "data.json")
if not os.path.exists(DATA_FILE) or not os.access(DATA_FILE, os.R_OK):
    DATA_FILE = os.path.join(BASE_DIR, "data.json")

BASE_INFO_FILE = os.path.join(PROD_DIR, "楼盘基础信息库.xlsx")
if not os.path.exists(BASE_INFO_FILE) or not os.access(BASE_INFO_FILE, os.R_OK):
    alt_base = "/Users/nb/google/Antigravity/工作/运营/聚焦盘精选盘/楼盘资料.xlsx"
    if os.path.exists(alt_base) and os.access(alt_base, os.R_OK):
        BASE_INFO_FILE = alt_base
    else:
        BASE_INFO_FILE = os.path.join(BASE_DIR, "楼盘基础信息库.xlsx")

DB_FILE = os.path.join(BASE_DIR, "楼盘基础信息数据库.db")
if not os.path.exists(DB_FILE) or not os.access(DB_FILE, os.R_OK):
    alt_db = os.path.join(PROD_DIR, "楼盘基础信息数据库.db")
    if os.path.exists(alt_db) and os.access(alt_db, os.R_OK):
        DB_FILE = alt_db

SELLING_POINTS_FILE = os.path.join(SANDBOX_DIR, "楼盘卖点.xlsx")
PROJECT_DESC_FILE = os.path.join(SANDBOX_DIR, "导出方案项目描述库.xlsx")
COMMUNITY_FILE = os.path.join(SANDBOX_DIR, "community_classification.json")

def load_project_descriptions():
    desc_map = {}
    target_file = PROJECT_DESC_FILE if os.path.exists(PROJECT_DESC_FILE) else SELLING_POINTS_FILE
    if not os.path.exists(target_file):
        return desc_map
    try:
        wb = openpyxl.load_workbook(target_file, data_only=True)
        ws = wb.active
        t_chars = '號峯滙敍灣瓏鑽鑄賢譽啟璽維奧滶蘊匯悅寶應羅壽淺徑賓園華遠藍語區築緹瀧澐雙鑽閣揚晉凱島輝臺連東紅臺豐環學區萬濱嶺軒廣場頭門閣薈'
        s_chars = '号峰汇叙湾珑钻铸贤誉启玺维奥滶蕴汇悦宝应罗寿浅径宾园华远蓝语区筑缇泷沄双钻阁扬晋凯岛辉台连东红台丰环学区万滨岭轩广场头门阁荟'
        trans = str.maketrans(t_chars, s_chars)
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) <= 1:
            return desc_map
        header = [str(c or '').strip() for c in rows[0]]
        def get_col(kw):
            for idx, h in enumerate(header):
                if kw in h:
                    return idx
            return -1

        idx_name = get_col('楼盘名称') if get_col('楼盘名称') != -1 else get_col('项目名称')
        idx_pos = get_col('置业定位')
        idx_sp = get_col('核心特色卖点') if get_col('核心特色卖点') != -1 else get_col('卖点')
        idx_pros = get_col('核心优势')
        idx_cons = get_col('客观考量') if get_col('客观考量') != -1 else get_col('相对劣势')
        idx_comm = get_col('交通与通勤')

        for r in rows[1:]:
            if not r or idx_name == -1 or not r[idx_name]:
                continue
            pn = str(r[idx_name]).strip()
            item = {
                'property_positioning': str(r[idx_pos]).strip() if idx_pos != -1 and r[idx_pos] else '',
                'selling_points': str(r[idx_sp]).strip() if idx_sp != -1 and r[idx_sp] else '',
                'core_pros': str(r[idx_pros]).strip() if idx_pros != -1 and r[idx_pros] else '',
                'quantified_cons': str(r[idx_cons]).strip() if idx_cons != -1 and r[idx_cons] else '',
                'commute_guidance': str(r[idx_comm]).strip() if idx_comm != -1 and r[idx_comm] else ''
            }
            norm_pn = pn.translate(trans).replace(' ', '').replace('　', '').replace('．', '.').lower()
            desc_map[pn] = item
            desc_map[norm_pn] = item
    except Exception as e:
        print("读取 导出方案项目描述库.xlsx 异常:", e)
    return desc_map

def load_selling_points():
    sp_map = {}
    if not os.path.exists(SELLING_POINTS_FILE):
        return sp_map
    try:
        wb = openpyxl.load_workbook(SELLING_POINTS_FILE, data_only=True)
        ws = wb.active
        t_chars = '號峯滙敍灣瓏鑽鑄賢譽啟璽維奧滶蘊匯悅寶應羅壽淺徑賓園華遠藍語區築緹瀧澐雙鑽閣揚晉凱島輝臺連東紅臺豐環學區萬濱嶺軒廣場頭門閣薈'
        s_chars = '号峰汇叙湾珑钻铸贤誉启玺维奥滶蕴汇悦宝应罗寿浅径宾园华远蓝语区筑缇泷沄双钻阁扬晋凯岛辉台连东红台丰环学区万滨岭轩广场头门阁荟'
        trans = str.maketrans(t_chars, s_chars)
        for r in list(ws.iter_rows(values_only=True))[1:]:
            if r and r[0] and r[1]:
                pn = str(r[0]).strip()
                sp = str(r[1]).strip()
                norm_pn = pn.translate(trans).replace(' ', '').replace('　', '').replace('．', '.').lower()
                sp_map[pn] = sp
                sp_map[norm_pn] = sp
    except Exception as e:
        print("读取 楼盘卖点.xlsx 异常:", e)
    return sp_map

KNOWN_DEVELOPERS = [
    ("新鸿基地产", ["新鸿基地产", "新鸿基", "SHKP", "Sun Hung Kai"]),
    ("恒基兆业地产", ["恒基兆业", "恒基地产", "恒基", "Henderson"]),
    ("长实集团", ["长实集团", "长江实业", "长实", "CK Asset"]),
    ("会德丰地产", ["会德丰地产", "会德丰", "Wheelock"]),
    ("新世界发展", ["新世界发展", "新世界", "New World"]),
    ("信和置业", ["信和置业", "信和", "Sino"]),
    ("嘉里建设", ["嘉里建设", "嘉里", "Kerry"]),
    ("华懋集团", ["华懋集团", "华懋", "Chinachem"]),
    ("太古地产", ["太古地产", "太古", "Swire"]),
    ("嘉华国际", ["嘉华国际", "嘉华", "K. Wah"]),
    ("九龙建业", ["九龙建业", "九建", "Kowloon Development"]),
    ("兴胜创建", ["兴胜创建", "Hanison"]),
    ("路劲地产", ["路劲地产", "路劲", "Road King"]),
    ("中国海外发展", ["中国海外", "中海", "China Overseas"]),
    ("保利置业", ["保利置业", "保利", "Poly Property"]),
    ("万科香港", ["万科香港", "万科", "Vanke"]),
    ("香港兴业", ["香港兴业", "HKR International"]),
    ("英皇国际", ["英皇国际", "英皇", "Emperor"]),
    ("远东发展", ["远东发展", "远展", "Far East"]),
    ("爪哇控股", ["爪哇控股", "爪哇"]),
    ("南丰集团", ["南丰集团", "南丰", "Nan Fung"]),
    ("资本策略", ["资本策略", "CSI Properties"]),
    ("宏安地产", ["宏安地产", "宏安", "Wang On"]),
]

def clean_price(val):
    if val is None or val == '-' or val == '暂无' or str(val).strip() == '':
        return None
    s = str(val).replace(',', '').replace('$', '').replace('HKD', '').replace('港币', '').strip()
    try:
        f = float(s)
        if f > 2000000000 and len(s) >= 14:
            # 兼容历史改价拼接数字异常 (例如两个8位数拼接为16位，或两个7位数拼接为14位)
            if len(s) >= 16:
                f = float(s[:8])
            elif len(s) == 14:
                f = float(s[:7])
            else:
                f = float(s[:len(s)//2])
        return f if f > 0 else None
    except:
        return None

def fmt_currency(p):
    if not p:
        return "暂无"
    p_wan = p / 10000
    if p_wan >= 10000:
        return f"{p_wan/10000:.2f} 亿".replace(".00", "")
    return f"{round(p_wan, 1)} 万".replace(".0 万", " 万")

def format_wan_display(w, is_ref=False):
    if w is None or w <= 0:
        return ""
    if w >= 10000:
        yi = round(w / 10000.0, 2)
        yi_str = f"{yi:.2f}".rstrip("0").rstrip(".")
        return f"${yi_str}亿" + ("+" if is_ref else "")
    else:
        if is_ref and w >= 1000:
            val = int(w // 100 * 100)
        else:
            val = round(w, 2)
            if val == int(val):
                val = int(val)
        return f"${val}万" + ("+" if is_ref else "")

def fmt_uprice(u):
    if not u or u == '-' or u == '暂无':
        return "-"
    try:
        f = float(str(u).replace(',', '').replace('$', '').strip())
        return f"${round(f):,}/呎"
    except:
        return str(u)

def extract_developer(pname="", text="", dev_map=None):
    if dev_map:
        if pname and pname in dev_map:
            return dev_map[pname]
        t_chars = '號峯滙敍灣瓏鑽鑄賢譽啟璽維奧滶蘊匯悅寶應羅壽淺徑賓園華遠藍語區築緹瀧澐雙鑽閣揚晉凱島輝臺連東紅臺豐環學區萬濱嶺軒廣場頭門閣薈'
        s_chars = '号峰汇叙湾珑钻铸贤誉启玺维奥滶蕴汇悦宝应罗寿浅径宾园华远蓝语区筑缇泷沄双钻阁扬晋凯岛辉台连东红台丰环学区万滨岭轩广场头门阁荟'
        trans = str.maketrans(t_chars, s_chars)
        norm_pn = pname.translate(trans).replace(' ', '').replace('　', '').replace('．', '.').replace('·', '.').lower()
        if norm_pn in dev_map:
            return dev_map[norm_pn]
        for k, v in dev_map.items():
            if k and (k == norm_pn or k in norm_pn or norm_pn in k):
                return v
    if not text:
        return "香港品牌发展商"
    for canonical, aliases in KNOWN_DEVELOPERS:
        for alias in aliases:
            if alias in text:
                return canonical
    m = re.search(r"由([^\s，。、（]+?)(?:倾力|重磅|精心)?(?:打造|发展|兴建|营建|推出)", text)
    if m:
        dev = m.group(1).replace("**", "").strip()
        if len(dev) <= 20:
            return dev
    return "香港品牌发展商"

def extract_completion_date(text):
    if not text:
        return "现楼 / 详见项目资料"
    if "现楼" in text:
        return "现楼发售 (即买即住)"
    m = re.search(r"(202[4-9]年[^\s，。、（]*)", text)
    if m:
        return m.group(1).replace("**", "")
    return "现楼 / 详见项目资料"

def parse_excel_sales_and_tx():
    files = glob.glob(os.path.join(FILES_DIR, "*.xlsx"))
    if not files:
        files = glob.glob(os.path.join(SANDBOX_DIR, "../files", "*.xlsx"))
    if not files:
        files = glob.glob(os.path.join(SANDBOX_DIR, "../*/*_销控明细表.xlsx"))
    project_sales = {}
    project_tx = {}
    project_bounds = {}
    project_unit_stats = {}
    
    for fpath in files:
        fname = os.path.basename(fpath).replace(".xlsx", "").replace("_销控明细表", "")
        parts = fname.split("-")
        pname = parts[-1].strip()
        
        try:
            wb = openpyxl.load_workbook(fpath, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if len(rows) < 3:
                continue
            
            header = rows[1]
            header_strs = [str(h).strip() if h is not None else "" for h in header]
            
            def find_col(possible_names):
                for name in possible_names:
                    for idx, h in enumerate(header_strs):
                        if name in h:
                            return idx
                return -1

            col_block = find_col(["楼栋", "座数", "座向", "大厦"])
            col_floor = find_col(["楼层", "层数"])
            col_unit = find_col(["房号", "单位", "室"])
            col_layout = find_col(["户型", "间隔", "单位类型", "房间"])
            col_sqft = find_col(["实用面积", "面积", "呎数"])
            col_status = find_col(["销控状态", "状态", "销售状态"])
            
            # 分离折实价与基础总价/呎价列
            col_disc_price = find_col(["折实总价"])
            col_tot_price = find_col(["总价", "售价", "成交价"])
            col_disc_uprice = find_col(["折实呎价"])
            col_tot_uprice = find_col(["实用呎价", "呎价"])
            
            col_date = find_col(["成交日期", "日期"])
            col_tender = find_col(["是否招标", "招标"])

            if col_layout == -1 or col_sqft == -1 or col_status == -1:
                continue

            unsold_layout_data = {}
            sold_layout_data = {}
            excel_total_units = 0
            excel_sold_units = 0
            excel_on_sale_units = 0

            for r in rows[2:]:
                if len(r) <= max(col_layout, col_sqft, col_status):
                    continue
                
                excel_total_units += 1
                status = str(r[col_status]).strip() if r[col_status] is not None else ""
                raw_layout = str(r[col_layout]).strip() if r[col_layout] is not None else "特色单位"
                if not raw_layout or raw_layout == "None" or raw_layout == "-":
                    raw_layout = "特色单位"
                
                layout = raw_layout
                if "开放" in layout or "0房" in layout: layout = "开放式"
                elif "1" in layout or "一房" in layout or "1房" in layout: layout = "1 房"
                elif "2" in layout or "两房" in layout or "2房" in layout or "二房" in layout: layout = "2 房"
                elif "3" in layout or "三房" in layout or "3房" in layout: layout = "3 房"
                elif "4" in layout or "四房" in layout or "4房" in layout: layout = "4 房"
                elif "5" in layout or "五房" in layout or "5房" in layout: layout = "5 房 / 大宅"
                elif "洋房" in layout or "独立屋" in layout or "别墅" in layout: layout = "独立洋房"
                elif "复式" in layout: layout = "复式大宅"
                elif "特色" in layout or "天台" in layout or "花园" in layout: layout = "特色单位"
                
                sqft = r[col_sqft]
                
                # 双重回退读取总价与呎价
                p_disc = clean_price(r[col_disc_price]) if col_disc_price != -1 and col_disc_price < len(r) else None
                p_tot = clean_price(r[col_tot_price]) if col_tot_price != -1 and col_tot_price < len(r) else None
                price = p_disc if p_disc is not None else p_tot

                u_disc = r[col_disc_uprice] if col_disc_uprice != -1 and col_disc_uprice < len(r) else None
                u_tot = r[col_tot_uprice] if col_tot_uprice != -1 and col_tot_uprice < len(r) else None
                uprice = u_disc if (u_disc not in [None, '-', '暂无', '']) else u_tot

                date = str(r[col_date]).strip() if col_date != -1 and col_date < len(r) and r[col_date] is not None else ""
                if date in ["-", "None", "暂无"]: date = ""

                # 1. 已售单位 -> 存入 sold_layout_data 用于最近成交
                if status in ["已售", "已售出", "已签约", "成交"]:
                    excel_sold_units += 1
                    block = str(r[col_block]).strip() if col_block != -1 and r[col_block] is not None and str(r[col_block]) != 'None' else ''
                    floor = str(r[col_floor]).strip() if col_floor != -1 and r[col_floor] is not None and str(r[col_floor]) != 'None' else ''
                    unit = str(r[col_unit]).strip() if col_unit != -1 and r[col_unit] is not None and str(r[col_unit]) != 'None' else ''
                    
                    unit_parts = []
                    if block: unit_parts.append(block if ('座' in block or '栋' in block) else f'{block}座')
                    if floor: unit_parts.append(f'{floor}楼')
                    if unit: unit_parts.append(f'{unit}室')
                    unit_name = ' '.join(unit_parts) if unit_parts else '精选单位'

                    if layout not in sold_layout_data:
                        sold_layout_data[layout] = []
                    
                    sold_layout_data[layout].append({
                        'unit_name': unit_name,
                        'layout': layout,
                        'sqft': f'{int(sqft)} 呎' if isinstance(sqft, (int, float)) and sqft > 0 else '详见销控',
                        'price': fmt_currency(price),
                        'price_num': price,
                        'unit_price': fmt_uprice(uprice),
                        'date': date or '-'
                    })
                    continue

                # 2. 未售房源 -> 统计在售销控汇总
                is_tender = False
                if col_tender != -1 and col_tender < len(r) and r[col_tender] is not None:
                    if str(r[col_tender]).strip() in ["是", "招标", "True", "true"]:
                        is_tender = True
                if col_disc_price != -1 and col_disc_price < len(r) and str(r[col_disc_price]).strip() in ["招标", "招标单位"]:
                    is_tender = True
                if col_tot_price != -1 and col_tot_price < len(r) and str(r[col_tot_price]).strip() in ["招标", "招标单位"]:
                    is_tender = True
                
                # 判断是否属于狭义在售（已正式发售安排推售）
                is_on_sale = (status in ["在售", "出售中", "sale", "Sale", "已定价未售"])
                is_stopped = (status in ["暂停销售", "暂停发售", "stopped", "Stopped"])
                is_pending = (status in ["待售", "未推售", "pending", "Pending"])
                
                if layout not in unsold_layout_data:
                    unsold_layout_data[layout] = {
                        "sqfts": [],
                        "prices": [],
                        "active_prices": [],
                        "tender_count": 0,
                        "unsold": 0,
                        "on_sale": 0,
                        "stopped_count": 0,
                        "pending_count": 0
                    }
                
                unsold_layout_data[layout]["unsold"] += 1
                if is_on_sale:
                    excel_on_sale_units += 1
                    unsold_layout_data[layout]["on_sale"] += 1
                if is_stopped:
                    unsold_layout_data[layout]["stopped_count"] += 1
                if is_pending:
                    unsold_layout_data[layout]["pending_count"] += 1

                if isinstance(sqft, (int, float)) and sqft > 0:
                    unsold_layout_data[layout]["sqfts"].append(sqft)
                
                if is_tender:
                    unsold_layout_data[layout]["tender_count"] += 1
                elif price:
                    unsold_layout_data[layout]["prices"].append(price)
                    if is_on_sale and not is_stopped:
                        unsold_layout_data[layout]["active_prices"].append(price)

            # 整理在售房源列表
            summary_list = []
            layout_order = ["开放式", "1 房", "2 房", "3 房", "4 房", "5 房 / 大宅", "复式大宅", "特色单位", "独立洋房"]
            sorted_keys = sorted(unsold_layout_data.keys(), key=lambda k: layout_order.index(k) if k in layout_order else 99)
            
            all_unsold_prices = []
            all_active_on_sale_prices = []
            for l_name in sorted_keys:
                d = unsold_layout_data[l_name]
                if d["unsold"] == 0:
                    continue
                
                if d["sqfts"]:
                    min_s, max_s = int(min(d["sqfts"])), int(max(d["sqfts"]))
                    sqft_str = f"{min_s} 呎" if min_s == max_s else f"{min_s} - {max_s} 呎"
                else:
                    sqft_str = "详见销控"
                
                if d["prices"]:
                    all_unsold_prices.extend(d["prices"])
                if d.get("active_prices"):
                    all_active_on_sale_prices.extend(d["active_prices"])
                
                # 优先呈现真正可售单位的价格区间
                if d.get("active_prices"):
                    min_p = min(d["active_prices"])
                    max_p = max(d["active_prices"])
                    p_str1 = fmt_currency(min_p)
                    p_str2 = fmt_currency(max_p)
                    price_str = p_str1 if p_str1 == p_str2 else f"{p_str1} - {p_str2}"
                    if d["tender_count"] > 0:
                        price_str += " (含招标)"
                elif d["on_sale"] > 0 and d["tender_count"] > 0:
                    price_str = "招标"
                elif d.get("stopped_count", 0) > 0 and d["on_sale"] == 0:
                    price_str = "暂停销售"
                elif d["tender_count"] > 0:
                    price_str = "招标"
                else:
                    price_str = "待定/详见价单"
                
                summary_list.append({
                    "layout": l_name,
                    "unsold_count": d["unsold"],
                    "on_sale_count": d["on_sale"],
                    "sqft_range": sqft_str,
                    "price_range": price_str
                })
            
            towers = [s for s in wb.sheetnames if s != '销控汇总明细']
            tower_count = len(towers) if len(towers) > 0 else 1
            project_sales[pname] = summary_list
            project_unit_stats[pname] = {
                "total_units": excel_total_units,
                "sold_units": excel_sold_units,
                "sale_units": excel_on_sale_units,
                "tower_count": tower_count,
                "tower_names": towers
            }

            # 整理各户型最近2套成交列表
            recent_tx_list = []
            all_sold_prices = []
            sorted_sold_layouts = sorted(sold_layout_data.keys(), key=lambda k: layout_order.index(k) if k in layout_order else 99)
            for l_name in sorted_sold_layouts:
                tx_items = sold_layout_data[l_name]
                for item in tx_items:
                    if item.get('price_num'):
                        all_sold_prices.append(item['price_num'])
                # 按日期倒序排列，取最近 2 套
                tx_items_sorted = sorted(tx_items, key=lambda x: str(x['date']) if x['date'] and x['date'] != '-' else '0000-00-00', reverse=True)
                for tx in tx_items_sorted[:2]:
                    # 清理 price_num 临时字段
                    clean_tx = {k: v for k, v in tx.items() if k != 'price_num'}
                    recent_tx_list.append(clean_tx)

            project_tx[pname] = recent_tx_list

            # 计算项目的精准最低与最高价格 (万元)
            # 优先级 1: 真正处于可售状态 (在售/已定价且非暂停) 的公开标价
            if all_active_on_sale_prices:
                min_wan = round(min(all_active_on_sale_prices) / 10000.0, 2)
                max_wan = round(max(all_active_on_sale_prices) / 10000.0, 2)
                d1 = format_wan_display(min_wan)
                d2 = format_wan_display(max_wan)
                project_bounds[pname] = {
                    'min_price_wan': min_wan,
                    'max_price_wan': max_wan,
                    'has_price_data': True,
                    'is_tender_project': False,
                    'desc': f"{d1}起" if min_wan == max_wan else f"{d1} - {d2}"
                }
            # 优先级 2: 可售单位全部为招标发售 (提取当前可售户型的近期真实成交作为参考)
            elif excel_on_sale_units > 0 and any(d.get("tender_count", 0) > 0 for d in unsold_layout_data.values()):
                # 寻找当前在售的户型列表
                active_tender_layouts = [l for l, d in unsold_layout_data.items() if d.get("on_sale", 0) > 0]
                matched_sold_prices = []
                for l in active_tender_layouts:
                    if l in sold_layout_data:
                        tx_sorted = sorted(sold_layout_data[l], key=lambda x: str(x['date']) if x.get('date') and x['date'] != '-' else '0000-00-00', reverse=True)
                        for item in tx_sorted[:5]:
                            if item.get('price_num'):
                                matched_sold_prices.append(item['price_num'])
                ref_prices = matched_sold_prices if matched_sold_prices else all_sold_prices
                if ref_prices:
                    min_wan = round(min(ref_prices) / 10000.0, 2)
                    max_wan = round(max(ref_prices) / 10000.0, 2)
                    ref_text = format_wan_display(min_wan, is_ref=True)
                    project_bounds[pname] = {
                        'min_price_wan': min_wan,
                        'max_price_wan': max_wan,
                        'has_price_data': True,
                        'is_tender_project': True,
                        'desc': f"招标发售 (参考近期成交约{ref_text})"
                    }
                else:
                    project_bounds[pname] = {
                        'min_price_wan': None,
                        'max_price_wan': None,
                        'has_price_data': False,
                        'is_tender_project': True,
                        'desc': '招标发售'
                    }
            elif all_unsold_prices:
                min_wan = round(min(all_unsold_prices) / 10000.0, 2)
                max_wan = round(max(all_unsold_prices) / 10000.0, 2)
                d1 = format_wan_display(min_wan)
                project_bounds[pname] = {
                    'min_price_wan': min_wan,
                    'max_price_wan': max_wan,
                    'has_price_data': True,
                    'is_tender_project': False,
                    'desc': f"暂停销售 (停售前参考: {d1}起)"
                }
            elif all_sold_prices:
                min_wan = round(min(all_sold_prices) / 10000.0, 2)
                max_wan = round(max(all_sold_prices) / 10000.0, 2)
                ref_text = format_wan_display(min_wan, is_ref=True)
                project_bounds[pname] = {
                    'min_price_wan': min_wan,
                    'max_price_wan': max_wan,
                    'has_price_data': True,
                    'is_tender_project': True,
                    'desc': f"招标发售 (参考近期成交约{ref_text})"
                }
            else:
                project_bounds[pname] = {
                    'min_price_wan': None,
                    'max_price_wan': None,
                    'has_price_data': False,
                    'is_tender_project': False,
                    'desc': '招标发售 / 详见价单'
                }

        except Exception as e:
            print(f"⚠️ 解析 {fname} 失败: {e}")
            
    print(f"✅ 成功解析在售项目: {len(project_sales)} 个，成交记录项目: {len(project_tx)} 个")
    return project_sales, project_tx, project_bounds, project_unit_stats

def main():
    print("1️⃣ 开始解析销控表与成交记录...")
    sales_data, tx_data, bounds_data, unit_stats_data = parse_excel_sales_and_tx()

    print("2️⃣ 读取沙盒数据 hk_project_coords.json...")
    with open(COORDS_FILE, "r", encoding="utf-8") as f:
        projects = json.load(f)

    data_json_map = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                dj = json.load(f)
                for p in dj.get("projects", []):
                    data_json_map[p["name"].strip()] = p
        except Exception as e:
            print("读取 data.json 异常:", e)

    # 方案 C：状态驱动生命周期管理 (Soft-Delete / Status-Driven Lifecycle)
    # 绝对禁止物理删除任何项目记录！保留全部楼盘底座与坐标、5维对比、校网等沉淀资产。
    # 仅检测是否有新增入市的项目
    existing_pnames = {p["name"].strip() for p in projects}
    if data_json_map:
        # 计算各商圈已有楼盘均值坐标，供智能兜底
        district_coords = {}
        for p in projects:
            d = p.get("district")
            if d and p.get("lat") and p.get("lng"):
                district_coords.setdefault(d, []).append((p["lat"], p["lng"]))
        district_centers = {
            d: (sum(pt[0] for pt in pts)/len(pts), sum(pt[1] for pt in pts)/len(pts))
            for d, pts in district_coords.items() if pts
        }

        # 内置核心地铁站列表供快速就近匹配
        SUBWAY_STATIONS = [
            {"station_name_zh": "堅尼地城", "lat": 22.2814, "lng": 114.1286, "lines": "港島綫"},
            {"station_name_zh": "香港大學", "lat": 22.2840, "lng": 114.1347, "lines": "港島綫"},
            {"station_name_zh": "西營盤", "lat": 22.2856, "lng": 114.1427, "lines": "港島綫"},
            {"station_name_zh": "上環", "lat": 22.2865, "lng": 114.1520, "lines": "港島綫/荃灣綫"},
            {"station_name_zh": "中環", "lat": 22.2820, "lng": 114.1583, "lines": "港島綫/荃灣綫"},
            {"station_name_zh": "金鐘", "lat": 22.2793, "lng": 114.1654, "lines": "港島綫/荃灣綫/南港島綫/東鐵綫"},
            {"station_name_zh": "灣仔", "lat": 22.2776, "lng": 114.1731, "lines": "港島綫"},
            {"station_name_zh": "銅鑼灣", "lat": 22.2802, "lng": 114.1840, "lines": "港島綫"},
            {"station_name_zh": "北角", "lat": 22.2912, "lng": 114.2001, "lines": "港島綫/將軍澳綫"},
            {"station_name_zh": "鰂魚涌", "lat": 22.2878, "lng": 114.2097, "lines": "港島綫/將軍澳綫"},
            {"station_name_zh": "筲箕灣", "lat": 22.2790, "lng": 114.2283, "lines": "港島綫"},
            {"station_name_zh": "柴灣", "lat": 22.2649, "lng": 114.2371, "lines": "港島綫"},
            {"station_name_zh": "黃竹坑", "lat": 22.2480, "lng": 114.1680, "lines": "南港島綫"},
            {"station_name_zh": "海怡半島", "lat": 22.2429, "lng": 114.1490, "lines": "南港島綫"},
            {"station_name_zh": "尖沙咀", "lat": 22.2973, "lng": 114.1726, "lines": "荃灣綫"},
            {"station_name_zh": "佐敦", "lat": 22.3050, "lng": 114.1716, "lines": "荃灣綫"},
            {"station_name_zh": "油麻地", "lat": 22.3131, "lng": 114.1708, "lines": "荃灣綫/觀塘綫"},
            {"station_name_zh": "旺角", "lat": 22.3193, "lng": 114.1694, "lines": "荃灣綫/觀塘綫"},
            {"station_name_zh": "深水埗", "lat": 22.3309, "lng": 114.1622, "lines": "荃灣綫"},
            {"station_name_zh": "九龍塘", "lat": 22.3368, "lng": 114.1760, "lines": "東鐵綫/觀塘綫"},
            {"station_name_zh": "啟德", "lat": 22.3307, "lng": 114.1994, "lines": "屯馬綫"},
            {"station_name_zh": "宋皇臺", "lat": 22.3261, "lng": 114.1894, "lines": "屯馬綫"},
            {"station_name_zh": "何文田", "lat": 22.3094, "lng": 114.1830, "lines": "觀塘綫/屯馬綫"},
            {"station_name_zh": "紅磡", "lat": 22.3029, "lng": 114.1818, "lines": "東鐵綫/屯馬綫"},
            {"station_name_zh": "九龍", "lat": 22.3050, "lng": 114.1615, "lines": "東涌綫/機場快綫"},
            {"station_name_zh": "奧運", "lat": 22.3178, "lng": 114.1601, "lines": "东涌綫"},
            {"station_name_zh": "南昌", "lat": 22.3265, "lng": 114.1537, "lines": "東涌綫/屯馬綫"}
        ]

        def get_nearest_mtr_info(t_lat, t_lng):
            import math
            def d_m(la1, lo1, la2, lo2):
                R = 6371000
                dl = math.radians(la2 - la1)
                do = math.radians(lo2 - lo1)
                a = math.sin(dl/2)**2 + math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(do/2)**2
                return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            closest = min(SUBWAY_STATIONS, key=lambda s: d_m(t_lat, t_lng, s["lat"], s["lng"]))
            s_d = round(d_m(t_lat, t_lng, closest["lat"], closest["lng"]))
            w_d = round(s_d * 1.3)
            return {
                "nearest_mtr_cn": closest["station_name_zh"],
                "nearest_mtr_lines": closest["lines"],
                "dist_straight_m": s_d,
                "dist_walk_m": w_d,
                "walk_time_min": round(w_d / 75.0, 1)
            }

        for dj_name, dj_proj in data_json_map.items():
            if dj_name not in existing_pnames:
                p_dist = dj_proj.get("district", "")
                p_region = dj_proj.get("region", "")
                if p_dist in district_centers:
                    t_lat, t_lng = district_centers[p_dist]
                    t_lat = round(t_lat + 0.0002, 6)
                    t_lng = round(t_lng + 0.0002, 6)
                else:
                    t_lat = 22.3193 if "九龙" in p_region else 22.2814
                    t_lng = 114.1694 if "九龙" in p_region else 114.1583
                
                mtr_info = get_nearest_mtr_info(t_lat, t_lng)
                print(f"✨ 发现正式版新项目: {dj_name} (商圈: {p_dist})，自动收录至地图项目库底座 (坐标: {t_lat}, {t_lng}, 最近地铁: {mtr_info['nearest_mtr_cn']}站 步行约{mtr_info['walk_time_min']}分钟)")
                dj_stats = dj_proj.get("stats", {})
                dj_is_suspended = dj_proj.get("is_suspended", False) or dj_proj.get("sell_status") == "sales_suspended" or (dj_stats.get("stopped", 0) > 0 and dj_stats.get("sale", 0) == 0)
                new_item = {
                    "name": dj_name,
                    "region": p_region,
                    "district": p_dist,
                    "lat": t_lat,
                    "lng": t_lng,
                    "nearest_mtr": mtr_info,
                    "sell_status": "sales_suspended" if dj_is_suspended else dj_proj.get("sell_status", "on_sale"),
                    "sell_status_cn": "暂停销售" if dj_is_suspended else dj_proj.get("sell_status_cn", "出售中"),
                    "is_suspended": dj_is_suspended,
                    "stats": dj_stats,
                    "stopped_units": dj_stats.get("stopped", 0),
                    "is_sold_out": False,
                    "price_tier": dj_proj.get("price_tier", "1000-2000"),
                    "total_units": 0,
                    "sale_units": 0,
                    "sold_units": 0,
                    "priced_units": 0,
                    "pending_units": 0,
                    "basic_price_desc": dj_proj.get("total_price_desc", ""),
                    "excel_min_price_desc": "详见价单",
                    "min_price_wan": None,
                    "sqft_price_desc": dj_proj.get("sqft_price_desc", ""),
                    "main_layout": dj_proj.get("main_layout", ""),
                    "reason": dj_proj.get("reason", ""),
                    "mainland_selling_points": dj_proj.get("mainland_selling_points", ""),
                    "developer": dj_proj.get("developer", ""),
                    "completion_date": dj_proj.get("completion_date", ""),
                    "sales_control_summary": [],
                    "recent_transactions": [],
                    "address": dj_proj.get("address", ""),
                    "main_area": dj_proj.get("main_area", ""),
                    "micro_district": dj_proj.get("micro_district", ""),
                    "micro_district_en": dj_proj.get("micro_district_en", ""),
                    "primary_school_net": "",
                    "secondary_school_net": "",
                    "school_net": "",
                    "max_price_wan": None,
                    "has_price_data": False,
                    "tower_count": 1,
                    "selling_points": dj_proj.get("mainland_selling_points", ""),
                    "property_positioning": "🏡 自住型产品",
                    "core_pros": "",
                    "quantified_cons": "",
                    "commute_guidance": ""
                }
                projects.append(new_item)
                existing_pnames.add(dj_name)

    school_net_map = {}
    if os.path.exists(BASE_INFO_FILE):
        try:
            import pandas as pd
            df_base = pd.read_excel(BASE_INFO_FILE, sheet_name='楼盘基础信息汇总')
            for _, r in df_base.iterrows():
                pn = str(r['项目名称']).strip()
                p_net = str(r['小学校网']).strip() if pd.notna(r['小学校网']) else ''
                s_net = str(r['中学校网']).strip() if pd.notna(r['中学校网']) else ''
                school_net_map[pn.lower()] = (p_net, s_net)
                if pd.notna(r.get('规范项目名')):
                    school_net_map[str(r['规范项目名']).strip().lower()] = (p_net, s_net)
        except Exception as e:
            print("读取 楼盘基础信息库.xlsx 异常:", e)

    MANUAL_OVERRIDE = {
        '瑅海': ('35校网', '九龙城区校网'),
        '皇廷汇': ('41校网', '九龙城区校网'),
        '天玺': ('31校网', '油尖旺区校网'),
        '喇沙汇': ('41校网', '九龙城区校网'),
        '耀爵台': ('34校网', '九龙城区校网'),
        '本木': ('31校网', '油尖旺区校网'),
        'Upper Prince': ('32校网', '油尖旺区校网'),
        '利奥坊．壹隅': ('32校网', '油尖旺区校网'),
        '吉喆': ('11校网', '中西区校网'),
        'Shouson Peak': ('18校网', '南区校网'),
        '浅水湾108': ('18校网', '南区校网'),
        'Twelve Peaks': ('11校网', '中西区校网'),
        '宾吉道3号': ('11校网', '中西区校网'),
        '活道1号': ('12校网', '湾仔区校网'),
        '远晴': ('16校网', '东区校网'),
        '环角道7号、9号及11号': ('18校网', '南区校网'),
        '339 Tai Hang Road': ('12校网', '湾仔区校网'),
        '启德海湾 1': ('34校网', '九龙城区校网'),
        '启德海湾 2': ('34校网', '九龙城区校网'),
        '天铸 (第2期)': ('34校网', '九龙城区校网'),
        '朗贤峰第IIA期': ('34校网', '九龙城区校网'),
        '朗贤峰第IIB期': ('34校网', '九龙城区校网'),
        'st. george\'s mansions': ('34校网', '九龙城区校网'),
        '维港汇 I': ('40校网', '深水埗区校网'),
        '维港汇 III': ('40校网', '深水埗区校网'),
        '花语海第1期': ('34校网', '九龙城区校网'),
        '花语海第2期': ('34校网', '九龙城区校网'),
    }

    print("3️⃣ 整合发展商、落成日期、校网归属、楼盘卖点、在售明细、最近成交记录、精准价格区间与套数统计...")
    def load_project_lifecycle_data():
        """
        整合读取 楼盘基础信息数据库.db 与 项目列表.xlsx，
        建立高精度双向归一化项目生命周期关键日期与入伙纸落成日期字典。
        """
        lifecycle_map = {}
        t_chars = '號峯滙敍灣瓏鑽鑄賢譽啟璽維奧滶蘊匯悅寶應羅壽淺徑賓園華遠藍語區築緹瀧澐雙鑽閣揚晉凱島輝臺連東紅臺豐環學區萬濱嶺軒廣場頭門閣薈'
        s_chars = '号峰汇叙湾珑钻铸贤誉启玺维奥滶蕴汇悦宝应罗寿浅径宾园华远蓝语区筑缇泷沄双钻阁扬晋凯岛辉台连东红台丰环学区万滨岭轩广场头门阁荟'
        trans = str.maketrans(t_chars, s_chars)

        def norm_key(s):
            if not s:
                return ""
            return s.translate(trans).replace(" ", "").replace("　", "").replace("．", ".").replace("·", ".").lower()

        # 1. 优先读取 楼盘基础信息数据库.db
        if os.path.exists(DB_FILE):
            try:
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                cur.execute("SELECT project_name, clean_project_name, phase_name, key_date, raw_json FROM project_details;")
                for r in cur.fetchall():
                    pname, clean_name, phase_name, key_date, raw_json = r
                    raw = json.loads(raw_json) if raw_json else {}
                    op_date = raw.get("first_op_date")

                    tl = raw.get("time_line", [])
                    tl_key_date = None
                    for item in tl:
                        if item.get("id") == "key_date" and item.get("checked"):
                            tl_key_date = item.get("date")
                            break

                    kd_str = (key_date or tl_key_date or "")[:10]
                    op_str = (op_date or "")[:10]

                    val = {
                        "pname": pname,
                        "clean_name": clean_name,
                        "phase_name": phase_name,
                        "key_date": kd_str if kd_str and kd_str != "None" else "",
                        "op_date": op_str if op_str and op_str != "None" else ""
                    }

                    cand = [pname, clean_name]
                    if clean_name and phase_name:
                        cand.append(f"{clean_name}{phase_name}")
                    for k in cand:
                        if k:
                            lifecycle_map[norm_key(k)] = val
                            lifecycle_map[k] = val
                conn.close()
                print(f"✅ 从 楼盘基础信息数据库.db 成功加载 {len(lifecycle_map)} 条生命周期索引")
            except Exception as e:
                print("读取 楼盘基础信息数据库.db 异常:", e)

        # 2. 读取 楼盘字典/项目列表.xlsx 作为辅助补充
        excel_path = "/Users/nb/google/Antigravity/工作/运营/楼盘字典/项目列表.xlsx"
        if os.path.exists(excel_path):
            try:
                wb = openpyxl.load_workbook(excel_path, read_only=True)
                ws = wb["项目列表"]
                rows = list(ws.iter_rows(values_only=True))
                headers = rows[0]
                idx_date = headers.index("落成日期")
                idx_name = headers.index("新盘名称\n（中文）")
                for r in rows[1:]:
                    nm = str(r[idx_name] or "").strip()
                    dt = str(r[idx_date] or "").strip()
                    if dt and dt != "None":
                        nk = norm_key(nm)
                        if nk not in lifecycle_map:
                            lifecycle_map[nk] = {"pname": nm, "key_date": "", "op_date": "", "excel_date": dt}
                            lifecycle_map[nm] = lifecycle_map[nk]
                        else:
                            lifecycle_map[nk]["excel_date"] = dt
            except Exception as e:
                print("读取项目列表.xlsx落成日期异常:", e)

        return lifecycle_map

    def load_project_developers():
        verified_devs = {
            # 启德 / 九龙东
            'Double Coast I': '中国海外 / 会德丰 / 恒基兆业 / 新世界',
            'Double Coast III': '中国海外 / 会德丰 / 恒基兆业 / 新世界',
            'Miami Quay I': '新世界 / 会德丰 / 恒基兆业 / 帝国集团',
            'Miami Quay II': '新世界 / 会德丰 / 恒基兆业 / 帝国集团',
            '天泷': '恒基兆业 / 中国海外 / 华懋集团 / 帝国集团 / 新世界 / 会德丰',
            '柏蔚森 I': '新世界 / 远东发展',
            '柏蔚森 II': '新世界 / 远东发展',
            '柏蔚森 III': '新世界 / 远东发展',
            '启德海湾 1': '嘉华国际 / 会德丰 / 中国海外',
            '启德海湾 2': '嘉华国际 / 会德丰 / 中国海外',
            '天玺．天': '新鸿基地产',
            '天玺．天第2期': '新鸿基地产',
            '天玺．海第1期': '新鸿基地产',
            '天玺．海第2A期': '新鸿基地产',
            '天玺．海第2B期': '新鸿基地产',
            '维港1号': '中国海外',
            '维港．双钻': '中国海外',
            '维港．湾畔第1A期': '中国海外 / 恒基兆业 / 九龙仓 / 嘉华国际',
            '维港．湾畔第1B期': '中国海外 / 恒基兆业 / 九龙仓 / 嘉华国际',
            '维港．湾畔第2B期': '中国海外 / 恒基兆业 / 九龙仓 / 嘉华国际',
            '沄璟': '华润置地 / 保利置业',
            'The Henley I': '恒基兆业',
            'The Henley II': '恒基兆业',
            'The Henley III': '恒基兆业',
            'Henley Park': '恒基兆业',
            'Monaco 第1期': '会德丰',
            'Monaco One': '会德丰',
            'Monaco Marine': '会德丰',
            
            # 红磡 / 何文田 / 土瓜湾 / 西九龙
            '必嘉坊．曦汇': '恒基兆业',
            '必嘉坊．迎汇': '恒基兆业',
            '首岸第1期': '恒基兆业 / 希慎兴业 / 帝国集团',
            '首岸第2期': '恒基兆业 / 希慎兴业 / 帝国集团',
            '首岸第3期': '恒基兆业 / 希慎兴业 / 帝国集团',
            '首岸第4期': '恒基兆业 / 希慎兴业 / 帝国集团',
            '首汇': '恒基兆业',
            'The Haddon': '恒基兆业',
            '映汇': '恒基兆业',
            '壹沐第1期': '恒基兆业',
            '壹沐第2期': '恒基兆业',
            '南首': '恒基兆业',
            '文曜': '建灏地产',
            '瑧博': '新世界',
            '朗贤峰第IIA期': '鹰君集团 / 港铁',
            '朗贤峰第IIB期': '鹰君集团 / 港铁',
            '瑜一第IC期': '华懋集团 / 港铁',
            '瑜一．天海': '华懋集团 / 港铁',
            '维港汇 I': '会德丰 / 信和置业 / 嘉华国际 / 世茂 / 爪哇集团',
            '维港汇 III': '会德丰 / 信和置业 / 嘉华国际 / 世茂 / 爪哇集团',
            '汇玺III': '新鸿基地产 / 港铁',
            '天玺': '新鸿基地产',
            'st. george\'s mansions': '中电集团 / 信和',
            'St. George\'s Mansions': '中电集团 / 信和',
            '傲玟': '高银',
            '名钻': '益兆集团',
            '128 Waterloo': '莱蒙国际 / 俊和',
            'Prince Central': '新鸿基地产',
            '太子道西233号': '新鸿基地产 / 会德丰',
            '天铸 (第2期)': '新鸿基地产',
            '明寓': '佳明',
            '耀爵台': '光大控股 / 柏汇国际',
            '芳菲': '协成行',
            '誉林': '永义国际',
            '隆敍': '志德投资',
            'The Boundary': '乐风集团',
            'Upper Prince': '乐风集团',
            '利奥坊．凯岸': '恒基兆业',
            '利奥坊．壹隅': '恒基兆业',
            '利奥坊．曦岸': '恒基兆业',
            '本木': '恒基兆业',
            '映居': '建灏地产 / 市建局',
            '原舍': '东立地产',
            'VAU Residence': '万科香港',
            '悦麓': 'TKS LTD.',
            '叡璟I': '华润置地',
            '叡璟II': '华润置地',
            '泓璟': '辉宇国际',
            'Elize Park': '乐风集团',
            
            # 九龙塘 / 笔架山 / 又一村
            '缇外': '嘉里建设',
            '皇廷汇': '天滙地产',
            '喇沙汇': '汉国置业',
            'Park College': '兴胜创建 / TPG',
            'Beacon Peak 第1期': '世茂集团',
            '滶蕴': '新世界发展',

            # 港岛 - 中半山 / 西半山 / 湾仔 / 铜锣湾
            '雅盈峰': '盈大地产 / 资本策略',
            '21 Borrett Road 第1期': '长江实业',
            'Upper Central': '禹洲集团',
            '大学阁': '华懋集团',
            '天御第1期': '恒基兆业 / 新世界',
            '天御第2期': '恒基兆业 / 新世界',
            '宝峰': '泛海国际 / 资本策略 / 德祥地产',
            '帝汇豪庭': '恒基兆业',
            '应天': '长江实业',
            '罗便臣道80号': '南丰集团',
            'Kennedy 38': '新鸿基 / 会德丰 / 恒基兆业',
            '吉喆': '上海商业银行',
            '海嵎': '永义国际',
            'Woodis': '恒基兆业',
            '活道1号': '盈信控股',
            '15 Western Street': '万科香港',
            '42 Tung St.': 'The Development Studio',
            '肇辉台6号': '嘉华国际',

            # 港岛 - 跑马地 / 渣甸山 / 东区
            'Eight Kwai Fong Happy Valley': '远中集团',
            '蓝塘道23-39号': '恒隆地产',
            '皇第': '泛海国际 / 尚家生活 / 高富诺',
            '峻誉．渣甸山': '中信泰富',
            '339 Tai Hang Road': '丽新发展',
            '101 Kings Road': '宏安地产',
            '君誉峰': '恒基兆业',
            '嘉居．天后': '嘉华国际',
            '柏蔚山': '新世界 / 培新集团',
            '海璇': '新鸿基地产',
            '海璇 II': '新鸿基地产',
            '海璇 II (第2B-3期)': '新鸿基地产',
            '海德园第1期': '太古地产',
            '海德园第2期': '太古地产',
            '君豪峰': '恒基兆业',
            'One Eighty': '三顺 / 日联',
            '傲华': '协成行',
            '远晴': '协成行',

            # 港岛 - 黄竹坑 / 香港仔 / 鸭脷洲 / 薄扶林
            '晋环': '路劲地产 / 平安不动产 / 港铁',
            '扬海': '嘉里建设 / 信和置业 / 太古地产 / 港铁',
            '海盈山第4A期': '嘉里建设 / 信和置业 / 太古地产 / 港铁',
            '海盈山第4B期': '嘉里建设 / 信和置业 / 太古地产 / 港铁',
            '滶晨': '新世界 / 帝国集团 / 资本策略 / 丽新发展 / 港铁',
            '滶晨 II': '新世界 / 帝国集团 / 资本策略 / 丽新发展 / 港铁',
            'Deep Water South 第6A期': '会德丰 / 港铁',
            'Deep Water South 第6B期': '会德丰 / 港铁',
            'Blue Coast': '长江实业 / 港铁',
            'Blue Coast II': '长江实业 / 港铁',
            '花语海第1期': '长江实业 / 港铁',
            '花语海第2期': '长江实业 / 港铁',
            '凯玥': '龙光集团 / 合景泰富',
            'PORTO': '宏安地产',
            '弦岸': '庄士机构',
            '璟南': '大昌地产',
            '逸南': '恒基兆业',
            'Victoria Coast': '华懋集团',
            'Mount Pokfulam': '宏安地产 / 锦华地产',

            # 港岛 - 寿臣山 / 浅水湾 / 赤柱 / 大潭
            '寿臣山15号': '英皇国际 / 中渝置地 / 明发集团 / 尚家生活',
            '深水湾径8号': '南丰集团 / 丰资源',
            'No.3 Repulse Bay Road': '新鸿基地产',
            'Shouson Peak': '新鸿基地产',
            '浅水湾108': '大昌集团',
            '皇府湾': '新鸿基地产',
            'Twelve Peaks': '新鸿基地产',
            '宾吉道3号': '大昌集团',
            'Mount Nicholson I': '九龙仓 / 南丰集团',
            'Mount Nicholson II': '九龙仓 / 南丰集团',
            'Central Peak I': '新鸿基地产',
            'Central Peak II': '新鸿基地产',
            '博峰': '丽新集团',
            '50 Stanley Village Road': '新鸿基地产',
            'One Stanley': '建灏地产',
            'Solace': '东立地产',
            '海天径 1号, 舂磡角道 44, 46, 48, 50号': '信德集团',
            '环角道7号、9号及11号': '培新集团',
            '红山半岛 - B区': '信和 / 华懋集团 / 亚证地产',
            '红山半岛 - C区': '信和 / 华懋集团 / 亚证地产',

            # 其他
            'The Monet 第1期': '会德丰',
            'The Monet 第2期': '会德丰',
            'The Monet 第3期': '会德丰',
            '海瑅湾 I': '信和置业 / 嘉里建设 / 嘉华国际 / 招商置地 / 港铁',
            '海瑅湾 II': '信和置业 / 嘉里建设 / 嘉华国际 / 招商置地 / 港铁',
            '瑅海': '信和置业 / 招商局置地 / 市建局',
        }
        res = dict(verified_devs)
        excel_path = "/Users/nb/google/Antigravity/工作/运营/楼盘字典/项目列表.xlsx"
        if os.path.exists(excel_path):
            try:
                wb = openpyxl.load_workbook(excel_path, read_only=True)
                ws = wb["项目列表"]
                rows = list(ws.iter_rows(values_only=True))
                headers = rows[0]
                idx_dev = headers.index("开发商")
                idx_name = headers.index("新盘名称\n（中文）")
                for r in rows[1:]:
                    nm = str(r[idx_name] or "").strip()
                    dv = str(r[idx_dev] or "").strip()
                    if nm and dv and dv != "None" and nm not in res:
                        res[nm] = dv
            except Exception as e:
                print("读取项目列表.xlsx开发商异常:", e)
        return res

    project_lifecycle_map = load_project_lifecycle_data()
    project_developer_map = load_project_developers()
    selling_points_map = load_selling_points()
    descriptions_map = load_project_descriptions()
    t_chars = '號峯滙敍灣瓏鑽鑄賢譽啟璽維奧滶蘊匯悅寶應羅壽淺徑賓園華遠藍語區築緹瀧澐雙鑽閣揚晉凱島輝臺連東紅臺豐環學區萬濱嶺軒廣場頭門閣薈'
    s_chars = '号峰汇叙湾珑钻铸贤誉启玺维奥滶蕴汇悦宝应罗寿浅径宾园华远蓝语区筑缇泷沄双钻阁扬晋凯岛辉台连东红台丰环学区万滨岭轩广场头门阁荟'
    trans = str.maketrans(t_chars, s_chars)

    comm_map = {}
    if os.path.exists(COMMUNITY_FILE):
        try:
            with open(COMMUNITY_FILE, "r", encoding="utf-8") as fp:
                comm_map = json.load(fp)
            print(f"✅ 成功加载 {len(comm_map)} 条静态社区分类固化数据")
        except Exception as e:
            print("读取 community_classification.json 异常:", e)

    tx_attached = 0
    price_attached = 0
    sp_attached = 0
    desc_attached = 0
    for p in projects:
        pname = p["name"].strip()
        dj_p = data_json_map.get(pname, {})

        if comm_map and pname in comm_map:
            cm = comm_map[pname]
            p["community_type"] = cm.get("category", "")
            p["community_type_name"] = cm.get("category_name", "")
            p["is_community"] = cm.get("is_community", False)
            p["parent_community"] = cm.get("parent_community", "")
            p["volume_format"] = cm.get("volume_format", "")

        # 方案 C 状态动态校准
        if pname in data_json_map:
            prod_status = dj_p.get("sell_status", "on_sale")
            prod_status_cn = dj_p.get("sell_status_cn", "出售中")
            prod_stats = dj_p.get("stats", {})
            prod_is_suspended = dj_p.get("is_suspended", False) or prod_status == "sales_suspended" or (prod_stats.get("stopped", 0) > 0 and prod_stats.get("sale", 0) == 0)

            p["is_suspended"] = prod_is_suspended
            p["stats"] = prod_stats
            p["stopped_units"] = prod_stats.get("stopped", 0)

            if prod_status == "sold_out":
                p["sell_status"] = "sold_out"
                p["sell_status_cn"] = "已售罄"
                p["is_sold_out"] = True
                p["is_coming_soon"] = False
                p["is_suspended"] = False
            elif prod_is_suspended:
                p["sell_status"] = "sales_suspended" if prod_status == "sales_suspended" else prod_status
                p["sell_status_cn"] = "暂停销售"
                p["is_sold_out"] = False
                p["is_coming_soon"] = False
            else:
                p["sell_status"] = prod_status
                p["sell_status_cn"] = prod_status_cn
                p["is_sold_out"] = False
                p["is_coming_soon"] = (prod_status == "coming_soon")
        else:
            # 正式版已下架或不在 active 列表的项目，状态置为 sold_out，软删除保护
            p["sell_status"] = "sold_out"
            p["sell_status_cn"] = "已售罄"
            p["is_sold_out"] = True
            p["is_coming_soon"] = False
            p["is_suspended"] = False

        # 动态同步营销与楼盘资料链接（若正式版有提供）
        if "marketing_url" in dj_p and dj_p["marketing_url"]:
            p["marketing_url"] = dj_p["marketing_url"]
        if "has_marketing_materials" in dj_p:
            p["has_marketing_materials"] = dj_p["has_marketing_materials"]
        if "intro_url" in dj_p and dj_p["intro_url"]:
            p["intro_url"] = dj_p["intro_url"]

        # 方案 C 核心保护：严禁覆盖已有 5 维研判与客观考量！已有内容绝不被覆盖或简化
        desc_info = descriptions_map.get(pname)
        if not desc_info:
            norm_name = pname.translate(trans).replace(' ', '').replace('　', '').replace('．', '.').lower()
            desc_info = descriptions_map.get(norm_name)
        if desc_info:
            if desc_info.get("property_positioning"):
                p["property_positioning"] = desc_info["property_positioning"]
            if desc_info.get("selling_points"):
                p["selling_points"] = desc_info["selling_points"]
                p["mainland_selling_points"] = desc_info["selling_points"]
                sp_attached += 1
            elif not p.get("selling_points") and desc_info.get("selling_points"):
                p["selling_points"] = desc_info["selling_points"]
                p["mainland_selling_points"] = desc_info["selling_points"]
                sp_attached += 1
            if desc_info.get("core_pros"):
                p["core_pros"] = desc_info["core_pros"]
            if desc_info.get("quantified_cons"):
                p["quantified_cons"] = desc_info["quantified_cons"]
            if desc_info.get("commute_guidance"):
                cg = desc_info["commute_guidance"].strip()
                p["commute_guidance"] = cg
                c_lines = [l.strip() for l in cg.split('\n') if l.strip()]
                if len(c_lines) >= 3:
                    p["comparison_commute"] = {
                        "line1": c_lines[0],
                        "line2": c_lines[1],
                        "line3": c_lines[2]
                    }
            desc_attached += 1

        # 若描述库未提供卖点则兜底原楼盘卖点.xlsx (仅在为空时补充)
        if not p.get("selling_points"):
            sp_text = selling_points_map.get(pname)
            if not sp_text:
                norm_name = pname.translate(trans).replace(' ', '').replace('　', '').replace('．', '.').lower()
                sp_text = selling_points_map.get(norm_name)
            if sp_text:
                p["selling_points"] = sp_text
                sp_attached += 1
                if not p.get("mainland_selling_points"):
                    p["mainland_selling_points"] = sp_text
        
        full_text = " ".join(filter(None, [
            p.get("selling_points", ""),
            p.get("mainland_selling_points", ""),
            p.get("reason", ""),
            dj_p.get("mainland_selling_points", ""),
            dj_p.get("reason", "")
        ]))

        p["developer"] = extract_developer(pname, full_text, project_developer_map)

        # 🏠/⏳ 精确项目生命周期与物业类型（现房 vs 期房）动态时间判定
        norm_pn = pname.translate(trans).replace(" ", "").replace("　", "").replace("．", ".").replace("·", ".").lower()
        lc_info = project_lifecycle_map.get(norm_pn)
        if not lc_info:
            for k, v in project_lifecycle_map.items():
                if k and (k in norm_pn or norm_pn in k):
                    lc_info = v
                    break

        kd = lc_info.get("key_date", "") if lc_info else ""
        op = lc_info.get("op_date", "") if lc_info else ""
        excel_dt = lc_info.get("excel_date", "") if lc_info else ""

        is_cs = p.get("is_coming_soon", False) or p.get("sell_status") == "coming_soon"
        NOW_STR = datetime.now().strftime("%Y-%m-%d")

        is_forward = False
        pt_desc = "现房 (现楼发售)"
        comp_date = "现楼发售 (即买即住)"

        # 综合法定关键日期：优先取数据库 key_date，若空则取 Excel 中的落成入伙日期
        excel_iso = ""
        if excel_dt:
            parts = excel_dt.split("/")
            if len(parts) == 3:
                excel_iso = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            elif "202" in excel_dt:
                excel_iso = excel_dt[:10]

        effective_key_date = kd or excel_iso

        if is_cs:
            is_forward = True
            pt_desc = "期房 (即将发售)"
            comp_date = "即将发售"
        elif effective_key_date:
            if effective_key_date > NOW_STR:
                yr = effective_key_date[:4]
                is_forward = True
                pt_desc = f"期房 (预计{yr}年入伙)"
                comp_date = f"预计{yr}年入伙"
            else:
                is_forward = False
                pt_desc = "现房 (现楼发售)"
                comp_date = "现楼发售 (已入伙)"
        elif op and op <= NOW_STR:
            is_forward = False
            pt_desc = "现房 (现楼发售)"
            comp_date = "现楼发售 (即买即住)"
        elif excel_dt:
            m = re.search(r"20(2[6-9]|3[0-9])", excel_dt)
            if m and int("20" + m.group(1)) > int(NOW_STR[:4]):
                yr = "20" + m.group(1)
                is_forward = True
                pt_desc = f"期房 (预计{yr}年入伙)"
                comp_date = f"预计{yr}年入伙"
            else:
                is_forward = False
                pt_desc = "现房 (现楼发售)"
                comp_date = f"现楼 ({excel_dt})"
        else:
            # 针对极少数未收录老盘，检查是否有未到期的原有入伙年份（如皇璇）
            orig_comp = p.get("completion_date", "")
            m = re.search(r"20(2[6-9]|3[0-9])", orig_comp)
            if m and int("20" + m.group(1)) > int(NOW_STR[:4]):
                yr = "20" + m.group(1)
                is_forward = True
                pt_desc = f"期房 (预计{yr}年入伙)"
                comp_date = f"预计{yr}年入伙"
            else:
                is_forward = False
                pt_desc = "现房 (现楼发售)"
                comp_date = "现楼发售 (即买即住)"

        p["completion_date"] = comp_date
        p["property_type"] = "forward" if is_forward else "ready"
        p["property_type_desc"] = pt_desc

        # ⚖️ 5D核心价值与客观权衡（core_pros / quantified_cons）与物业类型（现房 vs 期房）严格守恒对齐
        pros_raw = str(p.get("core_pros", "") or "")
        cons_raw = str(p.get("quantified_cons", "") or "")
        if pros_raw or cons_raw:
            def is_delivery_line(line):
                return any(k in line for k in ["【交付】", "现楼发售（即买即住", "属预售楼花阶段", "属全新即将发售阶段"])

            pros_lines = [l.strip() for l in pros_raw.split("\n") if l.strip()]
            cons_lines = [l.strip() for l in cons_raw.split("\n") if l.strip()]

            clean_pros = [l for l in pros_lines if not is_delivery_line(l)]
            clean_cons = [l for l in cons_lines if not is_delivery_line(l)]

            if is_forward:
                if "即将发售" in comp_date or "即将发售" in pt_desc:
                    del_con = "⏳【交付】属全新即将发售阶段（工程施工中，需等待正式推售及竣工交付）"
                else:
                    m = re.search(r"20(2[6-9]|3[0-9])", pt_desc) or re.search(r"20(2[6-9]|3[0-9])", comp_date)
                    yr_str = f"预计{m.group(0)}年" if m else "预计交付周期超1年"
                    del_con = f"⏳【交付】属预售楼花阶段（{yr_str}交付，需等待工程竣工）"
                clean_cons.append(del_con)
            else:
                clean_pros.append("🔑【交付】现楼发售（即买即住 / 即时收租，实景所见即所得）")

            p["core_pros"] = "\n".join(clean_pros)
            p["quantified_cons"] = "\n".join(clean_cons)

        # 匹配校网归属
        sn_info = None
        if pname in MANUAL_OVERRIDE:
            sn_info = MANUAL_OVERRIDE[pname]
        elif pname.lower() in school_net_map:
            sn_info = school_net_map[pname.lower()]
        else:
            for k, val in school_net_map.items():
                if k in pname.lower() or pname.lower() in k:
                    sn_info = val
                    break
        if sn_info:
            p["primary_school_net"] = sn_info[0]
            p["secondary_school_net"] = sn_info[1]
            if sn_info[0] and sn_info[1]:
                p["school_net"] = f"{sn_info[0]} / {sn_info[1]}"
            elif sn_info[0]:
                p["school_net"] = sn_info[0]

        # 🏫 校网与卖点文案防呆交叉审计（防止非34校网误写为34名校网）
        p_net_clean = str(p.get("primary_school_net", ""))
        sp_full_text = str(p.get("selling_points", "")) + " " + str(p.get("core_pros", "")) + " " + str(p.get("mainland_selling_points", ""))
        if "34" in sp_full_text and any(x in p_net_clean for x in ["35", "32", "31", "40", "41", "11", "12", "14", "16", "18"]):
            if "34" not in p_net_clean:
                print(f"⚠️ [校网防呆警告] 项目 {pname} 归属 {p_net_clean}，但卖点文案中包含 34 校网，请检查！")

        # 匹配在售数据与物理销控套数统计
        sc = sales_data.get(pname)
        ustats = unit_stats_data.get(pname)
        if not sc or not ustats:
            for k, val in sales_data.items():
                if k in pname or pname in k:
                    sc = val
                    ustats = unit_stats_data.get(k)
                    break
        p["sales_control_summary"] = sc if sc else []
        if ustats and ustats.get("total_units", 0) > 0:
            p["total_units"] = ustats["total_units"]
            p["sold_units"] = ustats["sold_units"]
            p["sale_units"] = ustats["sale_units"]
            p["tower_count"] = ustats.get("tower_count", 1)
            p["tower_names"] = ustats.get("tower_names", [])
            # 售罄判定：若总套数大于0且已全部售出 (无在售单位)
            if ustats["sold_units"] >= ustats["total_units"] and ustats.get("sale_units", 0) == 0:
                p["sell_status"] = "sold_out"
                p["sell_status_cn"] = "已售罄"
                p["is_sold_out"] = True
        if pname == '瑅海':
            p["tower_count"] = 2
            p["tower_names"] = ["第1座", "第2座"]
        elif not p.get("tower_count"):
            p["tower_count"] = 1

        # 匹配最近成交数据
        tx = tx_data.get(pname)
        if not tx:
            for k, val in tx_data.items():
                if k in pname or pname in k:
                    tx = val
                    break
        p["recent_transactions"] = tx if tx else []
        if p["recent_transactions"]:
            tx_attached += 1

        # 匹配精准价格区间与在售最低价描述
        pb = bounds_data.get(pname)
        if not pb:
            for k, val in bounds_data.items():
                if k in pname or pname in k:
                    pb = val
                    break
        
        if pb and pb.get('has_price_data'):
            p["min_price_wan"] = pb["min_price_wan"]
            p["max_price_wan"] = pb["max_price_wan"]
            p["has_price_data"] = True
            p["is_tender_project"] = pb.get("is_tender_project", False)
            p["excel_min_price_desc"] = pb["desc"]
            price_attached += 1
        else:
            p["min_price_wan"] = None
            p["max_price_wan"] = None
            p["has_price_data"] = False
            p["is_tender_project"] = pb.get("is_tender_project", False) if pb else False
            if p.get("sell_status") == "sold_out" or p.get("is_sold_out"):
                p["excel_min_price_desc"] = "已售罄"
            elif p.get("sell_status") == "coming_soon" or p.get("is_coming_soon"):
                p["excel_min_price_desc"] = "即将发售 / 待定"
            else:
                p["excel_min_price_desc"] = "招标发售 / 详见价单"

    print(f"4️⃣ 保存更新至 {COORDS_FILE} (共 {len(projects)} 个楼盘，挂载楼盘卖点 {sp_attached} 个，挂载最近成交数据 {tx_attached} 个)...")
    with open(COORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)
    print("🎉 数据升级完成！")

if __name__ == "__main__":
    main()
