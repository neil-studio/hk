# 香港一手新盘销控系统 - Codebase Bundle for AI

## File: scrape_hkp_sales_control.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import requests
from bs4 import BeautifulSoup
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

# ==========================================
# 1. 简繁转换辅助函数与映射
# ==========================================
# 输出文件基础目录定位到“价单”文件夹
BASE_DIR = "/Users/nb/google/Antigravity/工作/运营/价单"
# 简繁转换对照文件仍引用“楼盘字典”下的原文件
zh2hans_path = "/Users/nb/google/Antigravity/工作/运营/楼盘字典/zh2hans.json"

if os.path.exists(zh2hans_path):
    with open(zh2hans_path, 'r', encoding='utf-8') as f:
        zh2hans_dict = json.load(f)
    # 只提取单字符映射，防止包含多字词汇导致的错位对齐映射
    char_map = {k: v for k, v in zh2hans_dict.items() if len(k) == 1 and len(v) == 1}
    TRADITIONAL_CHARS = "".join(char_map.keys())
    SIMPLIFIED_CHARS  = "".join(char_map.values())
else:
    # 备用简繁字符映射
    TRADITIONAL_CHARS = "港島九龍啟德灣仔堅尼地城筲箕灣紅磡鰂魚涌鴨脷洲黃竹坑東半山西半山中半山西九龍東九龍壽臣山山頂淺水灣深水灣跑马地大坑道司徒拔道渣甸山薄扶林香港仔上環中環土瓜灣小西湾西营盘铜锣湾天后鲗鱼涌康怡太古湾仔跑马地大坑渣甸山北角半山石塘咀坚尼地城摩星岭薄扶林香港仔黄竹坑深水湾浅水湾赤柱大潭石澳峯滙"
    SIMPLIFIED_CHARS  = "港岛九龙启德湾仔坚尼地城筲箕湾红磡鲗鱼涌鸭脷洲黄竹坑东半山西半山中半山西九龙东九龙寿臣山山顶浅水湾深水湾跑马地大坑道司徒拔道渣甸山薄扶林香港仔上环中环土瓜湾小西湾西营盘铜锣湾天后鲗鱼涌康怡太古湾仔跑马地大坑渣甸山北角半山石塘咀坚尼地城摩星岭薄扶林香港仔黄竹坑深水湾浅水湾赤柱大潭石澳峰汇"

TRANS_MAP = str.maketrans(TRADITIONAL_CHARS, SIMPLIFIED_CHARS)

def t2s(text):
    if not text:
        return ""
    if isinstance(text, dict):
        return {k: t2s(v) for k, v in text.items()}
    if isinstance(text, list):
        return [t2s(x) for x in text]
    return str(text).translate(TRANS_MAP)

def clean_name(name):
    """标准化名称比对，去除空格、特殊字符并转为小写简体"""
    if not name:
        return ""
    name = t2s(name).lower()
    name = re.sub(r'[\s\-\(\)\（\）\.\,\，\。]', '', name)
    return name

def get_safe_filename(project_dir, pname):
    """生成去除特殊字符的安全 Excel 文件名"""
    safe_pname = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', pname)
    return os.path.join(project_dir, f"{safe_pname}_销控明细表.xlsx")

def normalize_bname(name):
    """标准化楼栋名称以进行比对映射"""
    if not name:
        return ""
    name = t2s(name).strip()
    name = re.sub(r'^第', '', name)
    return name

# ==========================================
# 2. 状态映射与颜色配置
# ==========================================
STATUS_MAP = {
    'pending': '待售',
    'priced': '已定价未售',
    'sale': '在售',
    'sold': '已售',
    'stopped': '暂停销售'
}

COLORS = {
    'sale': {'bg': 'A9F5A9', 'fg': '004D00'},
    'sold': {'bg': 'F5A9A9', 'fg': '660000'},
    'priced': {'bg': 'A9D0F5', 'fg': '002060'},
    'stopped': {'bg': 'FFC000', 'fg': '000000'},
    'pending': {'bg': 'FFFFFF', 'fg': '7F7F7F'}
}

# 销控单元格颜色填充配置 (Openpyxl Fills)
FILLS = {k: PatternFill(start_color=v['bg'], end_color=v['bg'], fill_type='solid') for k, v in COLORS.items()}

# ==========================================
# 3. 网络请求基础配置与 Token 获取
# ==========================================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_user_token():
    """从主列表页的 __NEXT_DATA__ 中解析最新的 Bearer Token"""
    url = "https://www.hkp.com.hk/zh-hk/list/new-property/"
    print("正在从主页获取最新 Token...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
        if match:
            data = json.loads(match.group(1))
            token = data.get('props', {}).get('pageProps', {}).get('userToken')
            if token:
                print(f"Token 获取成功! 长度: {len(token)}")
                return token
        raise ValueError("__NEXT_DATA__ 中未找到 userToken")
    except Exception as e:
        print(f"错误: 无法获取 Token: {e}", file=sys.stderr)
        sys.exit(1)

# ==========================================
# 4. 全局目录扫描与映射
# ==========================================
def scan_existing_folders():
    """扫描已有文件夹（包含价单和原楼盘字典目录），以防止命名拼写差异导致创建重复文件夹"""
    mapping = {}
    folders_to_scan = [BASE_DIR, "/Users/nb/google/Antigravity/工作/运营/楼盘字典"]
    for folder in folders_to_scan:
        if not os.path.exists(folder):
            continue
        for d in os.listdir(folder):
            path = os.path.join(folder, d)
            if os.path.isdir(path):
                parts = d.split('-')
                if len(parts) >= 3:
                    proj_name = parts[-1]
                    mapping[clean_name(proj_name)] = d
    return mapping

def load_existing_project_data(pname, pid, region, district, developer, existing_folders, global_units):
    """
    如果抓取失败，尝试从已有的本地 Excel 文件中加载数据并合并到 global_units 中。
    """
    clean_proj_name = clean_name(pname)
    if clean_proj_name not in existing_folders:
        return False
        
    folder_name = existing_folders[clean_proj_name]
    project_dir = os.path.join(BASE_DIR, folder_name)
    excel_filename = get_safe_filename(project_dir, pname)
    
    if not os.path.exists(excel_filename):
        return False
        
    print(f"  [历史沿用] 正在从本地历史数据加载: {excel_filename}")
    try:
        # 使用 read_only=True 加速读取
        wb = openpyxl.load_workbook(excel_filename, read_only=True, data_only=True)
        if "销控汇总明细" in wb.sheetnames:
            ws = wb["销控汇总明细"]
            count = 0
            for row in ws.iter_rows(min_row=3, values_only=True):
                # 检查是否是空行 (第一列"楼栋"为空则视为结束)
                if not row or row[0] is None:
                    break
                
                global_units.append({
                    '项目ID': pid,
                    '项目名称': pname,
                    '区域': region,
                    '商圈': district,
                    '开发商': developer,
                    '楼栋名称': row[0],
                    '楼层': row[1],
                    '房号': row[2],
                    '户型': row[3],
                    '实用面积': row[4],
                    '销控状态': row[5],
                    '成交日期': row[6],
                    '总价': row[7],
                    '呎价': row[8],
                    '是否招标': row[9]
                })
                count += 1
            print(f"  [成功] 从本地历史数据恢复了 {count} 条单位数据。")
            wb.close()
            return True
        wb.close()
    except Exception as e:
        print(f"  [警告] 读取本地历史 Excel 失败: {e}")
    return False

def is_project_sold_out(excel_filename):
    """
    检查已有的本地 Excel 文件是否显示该项目已售罄 (100%)。
    """
    if not os.path.exists(excel_filename):
        return False
    try:
        wb = openpyxl.load_workbook(excel_filename, read_only=True, data_only=True)
        if "销控汇总明细" in wb.sheetnames:
            ws = wb["销控汇总明细"]
            total = 0
            sold = 0
            for row in ws.iter_rows(min_row=3, max_col=6, values_only=True):
                if not row or row[0] is None:
                    break
                total += 1
                status_str = str(row[5]).strip() if len(row) >= 6 and row[5] is not None else ""
                if status_str == '已售' or ('售' in status_str and '未售' not in status_str and '待售' not in status_str and '暂停' not in status_str):
                    sold += 1
            wb.close()
            return total > 0 and sold == total
        wb.close()
    except Exception as e:
        print(f"  [警告] 读取本地 Excel 判断是否售罄时失败: {e}")
    return False


def extract_floor_number(floor_str):
    """从楼层字符串提取用于数字排序的数值"""
    if not floor_str:
        return -99
    floor_str = str(floor_str).upper().strip()
    match = re.search(r'(\d+)', floor_str)
    if match:
        val = int(match.group(1))
        if 'R' in floor_str:
            val += 0.5
        return val
    if 'G' in floor_str or 'UG' in floor_str:
        return 0
    if 'B' in floor_str:
        return -1
    return -99

# ==========================================
# 5. Excel 写入辅助逻辑 (使用 Openpyxl)
# ==========================================
def write_project_excel(filepath, project_name, buildings_data):
    """
    为单个项目写入 Excel 销控表，包含：
    - Tab 1: "销控汇总明细" (扁平表形式，包含所有楼栋的所有单位)
    - 之后的 Tabs: 每个楼栋单独一页，采用 "销控网格图 (Grid)" 形式展示
    """
    wb = openpyxl.Workbook()
    
    # ----------------------------------------
    # Tab 1: 销控汇总明细
    # ----------------------------------------
    ws_detail = wb.active
    ws_detail.title = "销控汇总明细"
    
    font_title = Font(name='Microsoft YaHei', size=14, bold=True)
    font_header = Font(name='Microsoft YaHei', size=10, bold=True)
    font_data = Font(name='Microsoft YaHei', size=10)
    align_center = Alignment(horizontal='center', vertical='center')
    border_thin = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )
    fill_header = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

    # 写标题
    ws_detail.merge_cells("A1:J1")
    ws_detail['A1'] = f"{project_name} - 一手销控汇总明细"
    ws_detail['A1'].font = font_title
    ws_detail['A1'].alignment = align_center
    ws_detail.row_dimensions[1].height = 40
    
    # 写表头 (包含了户型和成交日期)
    headers = ["楼栋", "楼层", "房号", "户型", "实用面积 (平方呎)", "销控状态", "成交日期", "总价 (港币)", "实用呎价 (港币/呎)", "是否招标"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws_detail.cell(row=2, column=col_idx, value=h)
        cell.font = font_header
        cell.alignment = align_center
        cell.fill = fill_header
        cell.border = border_thin
    ws_detail.row_dimensions[2].height = 25

    # 填充明细数据
    row_idx = 3
    for bname, units in buildings_data.items():
        sorted_units = sorted(units, key=lambda x: (extract_floor_number(x['floor']), x['flat']), reverse=True)
        for u in sorted_units:
            ws_detail.cell(row=row_idx, column=1, value=bname)
            ws_detail.cell(row=row_idx, column=2, value=u['floor'])
            ws_detail.cell(row=row_idx, column=3, value=u['flat'])
            ws_detail.cell(row=row_idx, column=4, value=u['room_layout'])
            ws_detail.cell(row=row_idx, column=5, value=u['net_area'] if u['net_area'] > 0 else '暂无')
            ws_detail.cell(row=row_idx, column=6, value=u['status'])
            ws_detail.cell(row=row_idx, column=7, value=u['sold_date'])
            
            is_tender = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']
            
            # 如果是招标且未售，总价显示招标
            if is_tender and u['status_raw'] != 'sold':
                ws_detail.cell(row=row_idx, column=8, value='招标单位')
                ws_detail.cell(row=row_idx, column=9, value='-')
            else:
                ws_detail.cell(row=row_idx, column=8, value=u['price'] if u['price'] else '暂无')
                ws_detail.cell(row=row_idx, column=9, value=u['price_per_sq_ft'] if u['price_per_sq_ft'] else '暂无')
                
            ws_detail.cell(row=row_idx, column=10, value='是' if is_tender else '否')
            
            for col in range(1, 11):
                c = ws_detail.cell(row=row_idx, column=col)
                c.font = font_data
                c.alignment = align_center
                c.border = border_thin
                
                # 数字格式化
                if col == 8 and isinstance(c.value, (int, float)):
                    c.number_format = '$#,##0'
                elif col == 9 and isinstance(c.value, (int, float)):
                    c.number_format = '$#,##0'
                elif col == 5 and isinstance(c.value, (int, float)):
                    c.number_format = '#,##0'

            row_idx += 1

    # 自动列宽
    for col in ws_detail.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_detail.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # 设置打印自适应：单页宽度，高度自动（纵向打印）
    ws_detail.sheet_properties.pageSetUpPr.fitToPage = True
    ws_detail.page_setup.fitToWidth = 1
    ws_detail.page_setup.fitToHeight = 0
    ws_detail.page_setup.orientation = ws_detail.ORIENTATION_PORTRAIT
    ws_detail.page_setup.paperSize = ws_detail.PAPERSIZE_A4

    # 设置窄页边距 (0.25 英寸)
    ws_detail.page_margins.left = 0.25
    ws_detail.page_margins.right = 0.25
    ws_detail.page_margins.top = 0.25
    ws_detail.page_margins.bottom = 0.25
    ws_detail.page_margins.header = 0.1
    ws_detail.page_margins.footer = 0.1

    # ----------------------------------------
    # Tab 2+: 每个楼栋生成可视化销控网格 (Grid)
    # ----------------------------------------
    multi_buildings = {}
    villa_buildings = {}
    
    if buildings_data:
        for bname, units in buildings_data.items():
            # 判断是否为独栋 (如果该楼栋单位数 <= 2 或是 HOUSE 类型)
            has_house_type = any(u.get('unit_type') == 'HOUSE' for u in units)
            if len(units) <= 2 or has_house_type:
                villa_buildings[bname] = units
            else:
                multi_buildings[bname] = units

    # 1. 多个单位 of 楼栋，每个楼栋放在单独的工作表
    for bname, units in multi_buildings.items():
        _write_building_grid(wb, bname, units, font_data, font_header, font_title, align_center, border_thin, fill_header)

    # 2. 独栋楼，集合放在一个工作表
    if villa_buildings:
        _write_villa_grid(wb, project_name, villa_buildings, font_data, align_center, border_thin)

    wb.save(filepath)

def update_global_excel_with_retry(filepath, new_units):
    """
    更新全局汇总 Excel，替换并追加重试项目的最新数据（采用极速读取与重写机制）。
    """
    if not os.path.exists(filepath):
        write_global_excel(filepath, new_units)
        return
        
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active
        
        replaced_pids = set(u['项目ID'] for u in new_units)
        
        # 1. 保留未被替换的行数据
        keep_rows = []
        max_r = ws.max_row
        
        # 从第3行开始读取
        for r in range(3, max_r + 1):
            row_vals = [ws.cell(row=r, column=c).value for c in range(1, 17)]
            # 检查空行
            if not any(row_vals):
                continue
            # 判断项目ID是否在需要替换的集合中
            cell_pid = row_vals[1] # 第二列是项目ID
            if cell_pid not in replaced_pids:
                keep_rows.append(row_vals)
                
        wb.close()
        
        # 2. 重新组合所有数据 (保留的行 + 新重试的行)
        combined_rows = []
        # 先放入原先保留的行
        for idx, row in enumerate(keep_rows, 1):
            row[0] = idx # 重新生成序号
            combined_rows.append(row)
            
        # 再追加新重试的行
        start_idx = len(combined_rows) + 1
        for idx, d in enumerate(new_units, start_idx):
            combined_rows.append([
                idx,
                d['项目ID'],
                d['项目名称'],
                d['区域'],
                d['商圈'],
                d['开发商'],
                d['楼栋名称'],
                d['楼层'],
                d['房号'],
                d['户型'],
                d['实用面积'],
                d['销控状态'],
                d['成交日期'],
                d['总价'],
                d['呎价'],
                d['是否招标']
            ])
            
        # 3. 完全重建全局汇总表以获得极高写入速度
        new_wb = openpyxl.Workbook()
        new_ws = new_wb.active
        new_ws.title = "一手新盘销控汇总"
        
        # 写入表头 (和 write_global_excel 保持一致)
        headers = [
            "序号", "项目ID", "项目名称", "区域", "商圈", "开发商", 
            "楼栋名称", "楼层", "房号", "户型", "实用面积 (平方呎)", 
            "销控状态", "成交日期", "总价 (港币)", "实用呎价 (港币/呎)", "是否招标"
        ]
        
        # 标题行
        font_title = Font(name='Microsoft YaHei', size=14, bold=True, color='FFFFFF')
        fill_title = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
        align_center = Alignment(horizontal='center', vertical='center')
        
        new_ws.merge_cells("A1:P1")
        title_cell = new_ws.cell(row=1, column=1, value="香港一手新盘销控汇总分析表")
        title_cell.font = font_title
        title_cell.fill = fill_title
        title_cell.alignment = align_center
        new_ws.row_dimensions[1].height = 40
        
        # 表头行
        font_header = Font(name='Microsoft YaHei', size=11, bold=True, color='FFFFFF')
        fill_header = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
        
        new_ws.row_dimensions[2].height = 28
        for col_idx, text in enumerate(headers, 1):
            c = new_ws.cell(row=2, column=col_idx, value=text)
            c.font = font_header
            c.fill = fill_header
            c.alignment = align_center
            
        # 写入所有行数据
        font_data = Font(name='Microsoft YaHei', size=10)
        border_thin = Border(
            left=Side(style='thin', color='BFBFBF'),
            right=Side(style='thin', color='BFBFBF'),
            top=Side(style='thin', color='BFBFBF'),
            bottom=Side(style='thin', color='BFBFBF')
        )
        
        for r_idx, row_data in enumerate(combined_rows, 3):
            new_ws.row_dimensions[r_idx].height = 20
            for c_idx, val in enumerate(row_data, 1):
                c = new_ws.cell(row=r_idx, column=c_idx, value=val)
                c.font = font_data
                c.alignment = align_center
                c.border = border_thin
                
                # 格式化数值
                if c_idx in [14, 15] and isinstance(c.value, (int, float)):
                    c.number_format = '$#,##0'
                elif c_idx == 11 and isinstance(c.value, (int, float)):
                    c.number_format = '#,##0'
                    
        # 列宽自适应
        for col in new_ws.columns:
            max_len = 0
            for cell in col:
                if cell.row == 1:
                    continue
                val_str = str(cell.value or '')
                # 计算近似字符长度
                length = sum(2 if ord(char) > 256 else 1 for char in val_str)
                if length > max_len:
                    max_len = length
            col_letter = get_column_letter(col[0].column)
            new_ws.column_dimensions[col_letter].width = max(max_len + 3, 10)
            
        # 设置页面自适应打印
        new_ws.sheet_properties.pageSetUpPr.fitToPage = True
        new_ws.page_setup.orientation = new_ws.ORIENTATION_PORTRAIT
        new_ws.page_setup.paperSize = new_ws.PAPERSIZE_A4
        new_ws.page_setup.fitToWidth = 1
        new_ws.page_setup.fitToHeight = 0
        
        new_ws.page_margins.left = 0.25
        new_ws.page_margins.right = 0.25
        new_ws.page_margins.top = 0.25
        new_ws.page_margins.bottom = 0.25
        new_ws.page_margins.header = 0.1
        new_ws.page_margins.footer = 0.1
        
        new_wb.save(filepath)
        print(f"  [成功] 采用极速重写机制，已更新并追加 {len(new_units)} 条新重试数据到全局汇总表中。")
    except Exception as e:
        print(f"  [错误] 极速重载更新全局汇总 Excel 失败: {e}")

def write_global_excel(filepath, data_list):
    """写入全局汇总 Excel 数据"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "一手新盘销控汇总"
    
    font_title = Font(name='Microsoft YaHei', size=14, bold=True)
    font_header = Font(name='Microsoft YaHei', size=10, bold=True)
    font_data = Font(name='Microsoft YaHei', size=10)
    align_center = Alignment(horizontal='center', vertical='center')
    border_thin = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )
    fill_header = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

    # 写标题
    ws.merge_cells("A1:P1")
    ws['A1'] = "香港港岛、九龙一手新盘单位销控明细汇总表"
    ws['A1'].font = font_title
    ws['A1'].alignment = align_center
    ws.row_dimensions[1].height = 40

    # 写表头
    headers = ["序号", "项目ID", "项目名称", "区域", "商圈", "开发商", "楼栋名称", "楼层", "房号", "户型", "实用面积 (平方呎)", "销控状态", "成交日期", "单位总价 (港币)", "实用呎价 (港币/呎)", "是否招标"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_idx, value=h)
        cell.font = font_header
        cell.alignment = align_center
        cell.fill = fill_header
        cell.border = border_thin
    ws.row_dimensions[2].height = 25

    # 填充数据
    row_idx = 3
    for idx, d in enumerate(data_list, 1):
        ws.cell(row=row_idx, column=1, value=idx)
        ws.cell(row=row_idx, column=2, value=d['项目ID'])
        ws.cell(row=row_idx, column=3, value=d['项目名称'])
        ws.cell(row=row_idx, column=4, value=d['区域'])
        ws.cell(row=row_idx, column=5, value=d['商圈'])
        ws.cell(row=row_idx, column=6, value=d['开发商'])
        ws.cell(row=row_idx, column=7, value=d['楼栋名称'])
        ws.cell(row=row_idx, column=8, value=d['楼层'])
        ws.cell(row=row_idx, column=9, value=d['房号'])
        ws.cell(row=row_idx, column=10, value=d['户型'])
        ws.cell(row=row_idx, column=11, value=d['实用面积'])
        ws.cell(row=row_idx, column=12, value=d['销控状态'])
        ws.cell(row=row_idx, column=13, value=d['成交日期'])
        ws.cell(row=row_idx, column=14, value=d['总价'])
        ws.cell(row=row_idx, column=15, value=d['呎价'])
        ws.cell(row=row_idx, column=16, value=d['是否招标'])

        # 数据行格式化与样式
        for col in range(1, 17):
            c = ws.cell(row=row_idx, column=col)
            c.font = font_data
            c.alignment = align_center
            c.border = border_thin
            
            # 数字格式
            if col == 14 and isinstance(c.value, (int, float)):
                c.number_format = '$#,##0'
            elif col == 15 and isinstance(c.value, (int, float)):
                c.number_format = '$#,##0'
            elif col == 11 and isinstance(c.value, (int, float)):
                c.number_format = '#,##0'

        row_idx += 1

    # 自动列宽
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(filepath)

# ==========================================
# 6. 主程序逻辑
# ==========================================
def main():
    token = fetch_user_token()
    api_headers = {
        'User-Agent': HEADERS['User-Agent'],
        'Authorization': f'Bearer {token}',
        'Origin': 'https://www.hkp.com.hk',
        'Referer': 'https://www.hkp.com.hk/'
    }

    # 6.1 获取项目列表 (如果是重试模式，直接从本地文件载入失败项目)
    is_retry = "--retry" in sys.argv
    failed_projects_file = os.path.join(BASE_DIR, "failed_projects.json")

    if is_retry:
        print("\n==========================================")
        print("      正在以 [重试模式] 重新运行爬取        ")
        print("==========================================")
        if not os.path.exists(failed_projects_file):
            print("提示: 未找到失败项目记录文件 failed_projects.json，无需重试。")
            return
        try:
            with open(failed_projects_file, 'r', encoding='utf-8') as f:
                filtered_projects = json.load(f)
            print(f"成功载入需要重试的项目数: {len(filtered_projects)}")
            if not filtered_projects:
                print("提示: 失败项目记录为空，无需重试。")
                return
        except Exception as e:
            print(f"错误: 载入失败项目记录文件异常: {e}")
            return
    else:
        print("\n[Step 1] 正在请求项目列表 API...")
        try:
            r = requests.get("https://data.hkp.com.hk/search/v2/new-properties", params={'limit': 1000}, headers=api_headers, timeout=15)
            r.raise_for_status()
            projects_data = r.json()
        except Exception as e:
            print(f"错误: 无法请求项目列表 API: {e}", file=sys.stderr)
            return

        all_projects = projects_data.get('result', [])
        print(f"API 返回项目总数: {len(all_projects)}")

        # 过滤出港岛和九龙项目
        target_regions = ['港岛', '九龙']
        filtered_projects = []
        for p in all_projects:
            region_raw = p.get('region', {}).get('name', '')
            region_cn = t2s(region_raw)
            if region_cn in target_regions:
                filtered_projects.append({
                    'id': p.get('id'),
                    'name': t2s(p.get('name')),
                    'region': region_cn,
                    'district': t2s(p.get('district')),
                    'developer': t2s(p.get('developer', {}).get('name', ''))
                })

        print(f"港岛/九龙一手新盘数量: {len(filtered_projects)}")

    # 确保保存价单的主目录存在
    os.makedirs(BASE_DIR, exist_ok=True)

    # 扫描已有文件夹映射 (包含价单目录和原楼盘字典目录，复用文件夹名)
    existing_folders = scan_existing_folders()
    
    # 汇总数据列表，用于生成全局汇总表
    global_units = []
    
    # 用于记录和报告未成功抓取最新数据的项目
    restored_projects = []
    totally_failed_projects = []

    # 6.2 循环遍历每个项目
    for idx, proj in enumerate(filtered_projects):
        pid = proj['id']
        pname = proj['name']
        region = proj['region']
        district = proj['district']
        
        # 检查本地是否已售罄，若售罄则不再爬取
        clean_proj_name = clean_name(pname)
        excel_filename = None
        if clean_proj_name in existing_folders:
            folder_name = existing_folders[clean_proj_name]
            excel_filename = get_safe_filename(os.path.join(BASE_DIR, folder_name), pname)
            
        if excel_filename and is_project_sold_out(excel_filename):
            print(f"\n({idx+1}/{len(filtered_projects)}) 正在处理: {pname} (ID: {pid}, 区域: {region}-{district})")
            print(f"  [已售罄] 该项目去化率已达 100%，无需重复爬取，直接沿用并合并本地数据。")
            load_existing_project_data(pname, pid, region, district, proj.get('developer', ''), existing_folders, global_units)
            continue
            
        print(f"\n({idx+1}/{len(filtered_projects)}) 正在处理: {pname} (ID: {pid}, 区域: {region}-{district})")

        # 6.2.1 预载全局历史成交记录以作日期备用补充
        tx_lookup = {}
        try:
            tx_url = "https://data.hkp.com.hk/search/v2/transactions"
            tx_params = {'phase_ids': pid, 'limit': 2000}
            tx_res = requests.get(tx_url, params=tx_params, headers=api_headers, timeout=12)
            if tx_res.status_code == 200:
                tx_data = tx_res.json().get('result', [])
                for tx in tx_data:
                    tx_bname = normalize_bname(tx.get('building', {}).get('name'))
                    tx_floor = str(tx.get('floor', '')).strip()
                    tx_flat = str(tx.get('flat', '')).strip()
                    tx_date_raw = tx.get('tx_date')
                    if tx_date_raw:
                        tx_lookup[(tx_bname, tx_floor, tx_flat)] = tx_date_raw[:10]
                print(f"  成功载入已登记的一手成交纪录 {len(tx_lookup)} 条。")
        except Exception as e:
            print(f"  提示: 预载一手历史成交纪录异常 ({e})。将只使用销控接口默认日期。")

        # 6.2.2 获取项目详情（以提取楼栋列表）
        try:
            detail_res = requests.get(f"https://data.hkp.com.hk/info/v1/new-properties/{pid}", headers=api_headers, timeout=10)
            if detail_res.status_code != 200:
                print(f"  警告: 无法获取项目详情 (Code: {detail_res.status_code})。")
                if load_existing_project_data(pname, pid, region, district, proj['developer'], existing_folders, global_units):
                    restored_projects.append(pname)
                else:
                    totally_failed_projects.append(pname)
                continue
            detail_data = detail_res.json()
        except Exception as e:
            print(f"  警告: 获取项目详情异常 ({e})。")
            if load_existing_project_data(pname, pid, region, district, proj['developer'], existing_folders, global_units):
                restored_projects.append(pname)
            else:
                totally_failed_projects.append(pname)
            continue

        # 6.2.2 收集所有可能的候选楼栋 ID 和名称 (结合 standard buildings, floorplan 以及交易记录以防错配)
        buildings_map = {}
        
        # 1) 标准 buildings
        for b in detail_data.get('buildings', []):
            bid = b.get('id')
            bname = t2s(b.get('name'))
            if bid:
                buildings_map[bid] = bname
            for sub_b in b.get('buildings', []):
                sub_bid = sub_b.get('id')
                sub_bname = t2s(sub_b.get('name'))
                if sub_bid:
                    buildings_map[sub_bid] = sub_bname

        # 2) floorplan
        for fp in detail_data.get('floorplan', []):
            b_info = fp.get('building', {})
            bid = b_info.get('id')
            bname = t2s(b_info.get('name'))
            if bid:
                buildings_map[bid] = bname

        # 3) 交易数据
        for tx in tx_data:
            b_info = tx.get('building', {})
            bid = b_info.get('id')
            bname = t2s(b_info.get('name'))
            if bid:
                # 交易数据中的楼栋名称通常非常准确
                buildings_map[bid] = bname

        if not buildings_map:
            print("  提示: 该项目没有关联楼栋信息。")
            if load_existing_project_data(pname, pid, region, district, proj['developer'], existing_folders, global_units):
                restored_projects.append(pname)
            else:
                totally_failed_projects.append(pname)
            continue

        print(f"  包含候选楼栋数: {len(buildings_map)}")
        
        # 存储当前项目的所有楼栋销控数据，用以生成项目独立明细表
        project_buildings_data = {}

        # 6.2.3 循环拉取每个楼栋的销控数据
        for bid, bname in buildings_map.items():
            print(f"    -> 楼栋: {bname} (ID: {bid})")

            try:
                units_res = requests.get(f"https://data.hkp.com.hk/info/v1/new-property/transactions/buildings/{bid}", headers=api_headers, timeout=10)
                if units_res.status_code != 200:
                    print(f"      警告: 无法拉取该楼栋的单位明细。")
                    continue
                units_data = units_res.json()
            except Exception as e:
                print(f"      警告: 请求楼栋单位明细异常 ({e})。")
                continue

            units = units_data.get('data', [])
            print(f"      获取到单位数: {len(units)}")
            
            parsed_units = []
            for u in units:
                unit_id = u.get('unit_id')
                floor = u.get('floor')
                flat = u.get('flat') or u.get('flat_name') or '-'
                net_area = u.get('net_area', 0) or 0
                status_raw = u.get('status', 'pending')
                status_cn = STATUS_MAP.get(status_raw, '待售')
                is_tender = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']
                
                # 获取总价
                price = u.get('price')
                if price is not None:
                    try:
                        price = float(price)
                    except ValueError:
                        price = None
                
                # 计算呎价
                unit_price_net = u.get('unit_price_net')
                if unit_price_net is not None:
                    try:
                        price_per_sq_ft = int(float(unit_price_net))
                    except ValueError:
                        price_per_sq_ft = None
                else:
                    if price and net_area > 0:
                        price_per_sq_ft = int(round(price / net_area))
                    else:
                        price_per_sq_ft = None

                # 1. 提取户型 (n房)
                room_layout = '暂无'
                detail_list = u.get('detail', [])
                if detail_list:
                    room_type = detail_list[0].get('room_type')
                    if room_type is not None and str(room_type) != '':
                        if str(room_type) in ['0', 0]:
                            room_layout = '开放式'
                        else:
                            room_layout = f"{room_type}房"
                
                # 2. 提取成交日期 (YYYY-MM-DD)，若销控接口返回 None，则使用历史登记记录作为补充
                sold_date_raw = u.get('sold_date') or u.get('tx_date')
                sold_date = '-'
                if status_raw == 'sold':
                    if sold_date_raw:
                        sold_date = sold_date_raw[:10]
                    else:
                        # 尝试从预载的成交记录中查找并映射
                        norm_b = normalize_bname(bname)
                        norm_floor = str(floor).strip()
                        norm_flat = str(flat).strip()
                        mapped_date = tx_lookup.get((norm_b, norm_floor, norm_flat))
                        if mapped_date:
                            sold_date = mapped_date

                unit_info = {
                    'unit_id': unit_id,
                    'floor': floor,
                    'flat': flat,
                    'net_area': net_area,
                    'status_raw': status_raw,
                    'status': status_cn,
                    'price': price,
                    'price_per_sq_ft': price_per_sq_ft,
                    'is_tender': u.get('is_tender'),
                    'room_layout': room_layout,
                    'sold_date': sold_date
                }
                parsed_units.append(unit_info)

                # 添加到全局汇总列表
                global_units.append({
                    '项目ID': pid,
                    '项目名称': pname,
                    '区域': region,
                    '商圈': district,
                    '开发商': proj['developer'],
                    '楼栋名称': bname,
                    '楼层': floor,
                    '房号': flat,
                    '户型': room_layout,
                    '实用面积': net_area if net_area > 0 else '暂无',
                    '销控状态': status_cn,
                    '成交日期': sold_date,
                    '总价': '招标单位' if (is_tender and status_raw != 'sold') else (price if price else '暂无'),
                    '呎价': '-' if (is_tender and status_raw != 'sold') else (price_per_sq_ft if price_per_sq_ft else '暂无'),
                    '是否招标': '是' if is_tender else '否'
                })

            project_buildings_data[bname] = parsed_units
            
            # 短暂限速
            time.sleep(0.3)

        # 5.2.3 如果有数据，生成该项目的独立明细表和文件夹
        if project_buildings_data:
            # 匹配或创建文件夹
            clean_proj_name = clean_name(pname)
            if clean_proj_name in existing_folders:
                folder_name = existing_folders[clean_proj_name]
            else:
                folder_name = f"{region}-{district}-{pname}"
                folder_name = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', folder_name)
                
            project_dir = os.path.join(BASE_DIR, folder_name)
            os.makedirs(project_dir, exist_ok=True)
            
            excel_filename = get_safe_filename(project_dir, pname)
            write_project_excel(excel_filename, pname, project_buildings_data)
            print(f"  [完成] 写入项目销控表: {excel_filename}")
        else:
            print("  [提示] 抓取的新数据为空，尝试沿用历史数据。")
            if load_existing_project_data(pname, pid, region, district, proj['developer'], existing_folders, global_units):
                restored_projects.append(pname)
            else:
                totally_failed_projects.append(pname)

        # 限速
        time.sleep(0.5)

    # 5.3 写入或更新全局汇总表
    if global_units:
        global_excel_path = os.path.join(BASE_DIR, "香港一手新盘销控汇总.xlsx")
        if is_retry:
            update_global_excel_with_retry(global_excel_path, global_units)
        else:
            write_global_excel(global_excel_path, global_units)
            print(f"\n[完成] 写入全局汇总表: {global_excel_path} (共 {len(global_units)} 条单位数据)")
    else:
        print("\n[警告] 未成功抓取到任何单位数据，全局汇总表未更新。")

    # 记录未抓取成功的项目到本地 json，供重试流程读取
    all_failed = restored_projects + totally_failed_projects
    if all_failed:
        failed_dicts = []
        for name in all_failed:
            for p in filtered_projects:
                if p['name'] == name:
                    failed_dicts.append(p)
                    break
        try:
            with open(failed_projects_file, 'w', encoding='utf-8') as f:
                json.dump(failed_dicts, f, ensure_ascii=False, indent=2)
            print(f"已更新失败项目列表: {failed_projects_file} (共 {len(failed_dicts)} 个项目)")
        except Exception as e:
            print(f"写入失败项目记录文件失败: {e}")
    else:
        if os.path.exists(failed_projects_file):
            try:
                os.remove(failed_projects_file)
                print(f"所有项目均已成功，已清理历史失败记录文件。")
            except Exception as e:
                pass

    # 5.4 打印并输出未抓取到数据的项目统计报告
    from datetime import datetime
    print("\n==========================================")
    print("      未抓取到最新数据的项目统计报告        ")
    print("==========================================")
    
    total_skipped = len(restored_projects) + len(totally_failed_projects)
    print(f"共有 {total_skipped} 个项目在本次抓取中未获取到最新数据：\n")
    
    if restored_projects:
        print(f"🔹 以下 {len(restored_projects)} 个项目拉取失败，但已【成功恢复并沿用】历史数据：")
        for pname in sorted(restored_projects):
            print(f"  - {pname}")
        print()
        
    if totally_failed_projects:
        print(f"❌ 以下 {len(totally_failed_projects)} 个项目拉取失败，且【无历史数据】可用：")
        for pname in sorted(totally_failed_projects):
            print(f"  - {pname}")
        print()
        
    # 将未抓取到的项目列表写入本地文件，方便查看
    report_path = os.path.join(BASE_DIR, "未抓取到最新数据项目列表.txt")
    try:
        with open(report_path, 'w', encoding='utf-8') as rf:
            rf.write("==========================================\n")
            rf.write("      未抓取到最新数据的项目统计报告        \n")
            rf.write(f"      报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            rf.write("==========================================\n\n")
            
            rf.write(f"共有 {total_skipped} 个项目未获取到最新数据。\n\n")
            
            rf.write(f"【已恢复并沿用历史数据的项目】({len(restored_projects)}个):\n")
            for pname in sorted(restored_projects):
                rf.write(f"  - {pname}\n")
            rf.write("\n")
            
            rf.write(f"【完全未获取到数据且无历史数据的项目】({len(totally_failed_projects)}个):\n")
            for pname in sorted(totally_failed_projects):
                rf.write(f"  - {pname}\n")
                
        print(f"未抓取数据项目报告已写入本地文件: {report_path}")
    except Exception as e:
        print(f"写入报告报告失败: {e}")
    print("==========================================\n")

if __name__ == '__main__':
    main()


def _write_building_grid(wb, bname, units, font_data, font_header, font_title, align_center, border_thin, fill_header):
    """为单个楼栋写入销控网格 Tab"""
    safe_tab = re.sub(r'[\\/?*\[\]:]', '', bname)[:31]
    ws = wb.create_sheet(title=safe_tab)

    # 统计面板数据
    total = len(units)
    cnt = {s: 0 for s in STATUS_MAP.keys()}
    for u in units:
        sr = u.get('status_raw', 'pending')
        if sr in cnt:
            cnt[sr] += 1

    # 汇总统计面板 (Row 1 标题，Row 2-3 数据)
    stat_labels = [
        ('总套数', str(total), 'FFFFFF', '000000', False),
        ('在售 (Sale)', str(cnt.get('sale', 0)), 'A9F5A9', '004D00', True),
        ('已定价未售', str(cnt.get('priced', 0)), 'A9D0F5', '002060', False),
        ('已售 (Sold)', str(cnt.get('sold', 0)), 'F5A9A9', '660000', False),
        ('暂停销售', str(cnt.get('stopped', 0)), 'FFC000', '000000', True),
        ('待售 (Pending)', str(cnt.get('pending', 0)), 'FFFFFF', '7F7F7F', False),
    ]

    # Row 1: 楼栋名称
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(stat_labels))
    ws['A1'] = f"{bname} 销控网格图"
    ws['A1'].font = Font(name='Microsoft YaHei', size=13, bold=True)
    ws['A1'].alignment = align_center
    ws.row_dimensions[1].height = 28

    # Row 2: 图例标签
    for col, (label, val, bg, fg, bold) in enumerate(stat_labels, 1):
        c2 = ws.cell(row=2, column=col, value=label)
        c2.font = Font(name='Microsoft YaHei', size=9, bold=bold, color=fg)
        c2.alignment = align_center
        c2.fill = PatternFill(start_color=bg, end_color=bg, fill_type='solid')
        c2.border = border_thin
        # Row 3: 数值
        c3 = ws.cell(row=3, column=col, value=val)
        c3.font = Font(name='Microsoft YaHei', size=10, bold=True, color=fg)
        c3.alignment = align_center
        c3.fill = PatternFill(start_color=bg, end_color=bg, fill_type='solid')
        c3.border = border_thin
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 20

    # 整理楼层、单位
    floors_set = set()
    flats_set = set()
    for u in units:
        floors_set.add(u['floor'])
        flats_set.add(u['flat'])

    floors_sorted = sorted(floors_set, key=extract_floor_number, reverse=True)
    flats_sorted  = sorted(flats_set)

    # 建立单位查找表 (floor, flat) -> unit
    unit_lookup = {(u['floor'], u['flat']): u for u in units}

    # 网格表头 (Row 4 = 单位列)
    ws.cell(row=4, column=1, value='楼层').font = Font(name='Microsoft YaHei', size=9, bold=True)
    ws.cell(row=4, column=1).alignment = align_center
    ws.cell(row=4, column=1).fill = fill_header
    ws.cell(row=4, column=1).border = border_thin
    ws.row_dimensions[4].height = 18

    for col_idx, flat in enumerate(flats_sorted, 2):
        c = ws.cell(row=4, column=col_idx, value=flat)
        c.font = Font(name='Microsoft YaHei', size=9, bold=True)
        c.alignment = align_center
        c.fill = fill_header
        c.border = border_thin
        ws.column_dimensions[get_column_letter(col_idx)].width = 14

    ws.column_dimensions['A'].width = 8

    # 数据行
    for row_idx, floor in enumerate(floors_sorted, 5):
        ws.cell(row=row_idx, column=1, value=floor)
        ws.cell(row=row_idx, column=1).font = Font(name='Microsoft YaHei', size=9, bold=True)
        ws.cell(row=row_idx, column=1).alignment = align_center
        ws.cell(row=row_idx, column=1).fill = fill_header
        ws.cell(row=row_idx, column=1).border = border_thin
        ws.row_dimensions[row_idx].height = 58

        for col_idx, flat in enumerate(flats_sorted, 2):
            u = unit_lookup.get((floor, flat))
            c = ws.cell(row=row_idx, column=col_idx)
            c.border = border_thin
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

            if u is None:
                c.value = ''
                c.fill = PatternFill(start_color='E8E8E8', end_color='E8E8E8', fill_type='solid')
                continue

            status_raw = u.get('status_raw', 'pending')
            color_cfg = COLORS.get(status_raw, COLORS['pending'])
            bg = color_cfg['bg']
            fg = color_cfg['fg']
            is_bold = status_raw in ('sale', 'stopped')

            # 4行文字内容
            line1 = f"{flat} | {u['net_area']}呎 ({u['room_layout']})"
            is_tender = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']
            if is_tender and status_raw != 'sold':
                line2 = "招标单位"
                line3 = "-"
            else:
                if u['price']:
                    price_wan = round(u['price'] / 10000)
                    line2 = f"${price_wan}万"
                else:
                    line2 = "-"
                if u['price_per_sq_ft']:
                    line3 = f"${u['price_per_sq_ft']:,}/呎"
                else:
                    line3 = "-"

            if status_raw == 'sold' and u['sold_date'] and u['sold_date'] != '-':
                try:
                    parts = u['sold_date'].split('-')
                    yr = parts[0][-2:]
                    mo = parts[1]
                    line4 = f"({yr}年-{mo}月)"
                except:
                    line4 = f"({u['sold_date']})"
            else:
                status_display = STATUS_MAP.get(status_raw, '待售')
                line4 = f"({status_display})"

            c.value = f"{line1}\n{line2}\n{line3}\n{line4}"
            c.font = Font(name='Microsoft YaHei', size=8, bold=is_bold, color=fg)
            c.fill = PatternFill(start_color=bg, end_color=bg, fill_type='solid')

    # 打印设置
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth  = 1
    ws.page_setup.fitToHeight = 1
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize   = ws.PAPERSIZE_A4
    for margin in ['left', 'right', 'top', 'bottom']:
        setattr(ws.page_margins, margin, 0.25)
    ws.page_margins.header = 0.1
    ws.page_margins.footer = 0.1


def _write_villa_grid(wb, project_name, buildings_data, font_data, align_center, border_thin):
    """
    独立屋项目整合为一个单一的工作表，避免分割成无数个 1x1 标签页。
    采用 5 行文字的网格卡片式布局。
    """
    ws_grid = wb.create_sheet(title="独立屋销控表")
    
    font_title  = Font(name='Microsoft YaHei', size=14, bold=True)
    font_header = Font(name='Microsoft YaHei', size=10, bold=True)
    fill_header = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

    # 展平所有独立屋单位并打上楼栋标记
    all_units = []
    for bname, units in buildings_data.items():
        for u in units:
            u_copy = u.copy()
            u_copy['_bname'] = bname
            all_units.append(u_copy)
            
    # 基于命名模式分析其网格排布 (行列定位)
    parentheses_matches = sum(1 for u in all_units if re.search(r'^.+?\s*[\(\（].+?[\)\）]$', u['_bname']))
    space_matches = sum(1 for u in all_units if ' ' in u['_bname'].strip())
    
    has_parentheses = parentheses_matches >= len(all_units) * 0.7
    has_space = space_matches >= len(all_units) * 0.7
    
    # 预设分配网格坐标
    for idx, u in enumerate(all_units):
        bname = u['_bname']
        if has_parentheses:
            m = re.search(r'^(.+?)\s*[\(\（](.+?)[\)\）]$', bname)
            if m:
                u['_grid_row'] = m.group(1).strip()
                u['_grid_col'] = m.group(2).strip()
            else:
                u['_grid_row'] = "其他"
                u['_grid_col'] = bname
        elif has_space:
            parts = bname.rsplit(' ', 1)
            u['_grid_row'] = parts[0].strip()
            u['_grid_col'] = parts[1].strip()
        else:
            # 默认横排扁平
            if len(all_units) <= 8:
                u['_grid_row'] = "独立屋"
                u['_grid_col'] = bname
            else:
                # 超过8个，默认后面按 cols_per_row = 6 排布分配
                pass
                
    # 按照大楼/别墅名进行自然排序
    def natural_key(x):
        return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', x['_bname'])]
        
    all_units = sorted(all_units, key=natural_key)
    
    # 如果是超过8个的扁平排布，在此根据自然排序顺序分配行列坐标
    if not has_parentheses and not has_space and len(all_units) > 8:
        cols_per_row = 6
        for idx, u in enumerate(all_units):
            row_num = idx // cols_per_row + 1
            col_num = idx % cols_per_row + 1
            u['_grid_row'] = f"第 {row_num} 行"
            u['_grid_col'] = f"位置 {col_num}"

    # 整理出确切的网格行、列头
    floors = sorted(list(set(u['_grid_row'] for u in all_units)))
    
    # 列头自然排序
    def col_natural_key(text):
        return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', text)]
    flats = sorted(list(set(u['_grid_col'] for u in all_units)), key=col_natural_key)
    
    unit_map = {(u['_grid_row'], u['_grid_col']): u for u in all_units}
    
    # 统计数量
    total_units = len(all_units)
    status_counts = {'sale': 0, 'sold': 0, 'priced': 0, 'stopped': 0, 'pending': 0}
    for u in all_units:
        st = u.get('status_raw', 'pending')
        status_counts[st] = status_counts.get(st, 0) + 1

    # 设置标题
    ws_grid.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(flats) + 1)
    title_cell = ws_grid.cell(row=1, column=1, value=f"{project_name} - 独立屋销控网格图")
    title_cell.font = font_title
    title_cell.alignment = align_center
    ws_grid.row_dimensions[1].height = 40

    # 展示统计面板数据
    ws_grid.row_dimensions[2].height = 20
    ws_grid.row_dimensions[3].height = 25
    
    stat_cols = [
        ("总套数", total_units, 'pending'),
        ("在售 (Sale)", status_counts['sale'], 'sale'),
        ("已定价未售", status_counts['priced'], 'priced'),
        ("已售 (Sold)", status_counts['sold'], 'sold'),
        ("暂停销售", status_counts['stopped'], 'stopped'),
        ("待售 (Pending)", status_counts['pending'], 'pending')
    ]
    
    for stat_idx, (label, val, fill_key) in enumerate(stat_cols, 1):
        cell_lbl = ws_grid.cell(row=2, column=stat_idx, value=label)
        cell_lbl.font = Font(name='Microsoft YaHei', size=9, bold=(fill_key in ['sale', 'stopped']), color=COLORS[fill_key]['fg'])
        cell_lbl.alignment = align_center
        cell_lbl.fill = FILLS[fill_key]
        cell_lbl.border = border_thin
        
        cell_val = ws_grid.cell(row=3, column=stat_idx, value=f"{val} 套")
        cell_val.font = Font(name='Microsoft YaHei', size=11, bold=True, color=COLORS[fill_key]['fg'])
        cell_val.alignment = align_center
        cell_val.fill = FILLS[fill_key]
        cell_val.border = border_thin

    # 空一行后写表头
    header_row = 5
    ws_grid.row_dimensions[header_row].height = 25
    cell_cross = ws_grid.cell(row=header_row, column=1, value="类型/位置" if not has_parentheses else "类型/屋号")
    cell_cross.font = font_header
    cell_cross.alignment = align_center
    cell_cross.border = border_thin
    cell_cross.fill = fill_header

    for col_idx, flat_name in enumerate(flats, 2):
        cell_flat = ws_grid.cell(row=header_row, column=col_idx, value=flat_name)
        cell_flat.font = font_header
        cell_flat.alignment = align_center
        cell_flat.border = border_thin
        cell_flat.fill = fill_header

    # 写入网格数据
    curr_row = header_row + 1
    for f_name in floors:
        ws_grid.row_dimensions[curr_row].height = 80 # 提高以容纳5行文字
        
        cell_floor = ws_grid.cell(row=curr_row, column=1, value=f_name)
        cell_floor.font = font_header
        cell_floor.alignment = align_center
        cell_floor.border = border_thin
        cell_floor.fill = fill_header
        
        for col_idx, flat_name in enumerate(flats, 2):
            u = unit_map.get((f_name, flat_name))
            cell_unit = ws_grid.cell(row=curr_row, column=col_idx)
            cell_unit.border = border_thin
            cell_unit.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            if u:
                status_raw = u['status_raw']
                status_cn = u['status']
                price = u['price']
                net_area = u['net_area']
                price_per_sq_ft = u['price_per_sq_ft']
                is_tender = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']
                sold_date = u.get('sold_date')
                room_layout = u.get('room_layout', '暂无')
                
                # 1. 洋房名称/编号
                line1 = u['_bname']
                
                # 2. 实用面积与户型房数
                area_str = f"{net_area}呎" if net_area > 0 else "暂无"
                layout_str = f" ({room_layout})" if room_layout != '暂无' else ""
                line2 = f"{area_str}{layout_str}"
                
                # 3. 销售状态 (已售写具体登记年份-月份)
                if status_raw == 'sold' and sold_date and sold_date != '-':
                    try:
                        parts = sold_date.split('-')
                        yr = parts[0][-2:]
                        mo = parts[1]
                        line3 = f"({yr}年-{mo}月)"
                    except:
                        line3 = f"({sold_date})"
                else:
                    line3 = f"({status_cn})"
                    
                # 4. 价格 (过亿单位显示 $X.XX亿)
                if is_tender and status_raw != 'sold':
                    line4 = "招标项目" if status_raw == 'sale' else "招标单位"
                else:
                    if price and price > 0:
                        if price >= 100000000:
                            line4 = f"${price/100000000:.2f}亿"
                        elif price >= 10000:
                            line4 = f"${price/10000:,.0f}万"
                        else:
                            line4 = f"${price:,}"
                    else:
                        line4 = "暂无价格"
                        
                # 5. 实用呎价
                if is_tender and status_raw != 'sold':
                    line5 = "-"
                elif price_per_sq_ft and price_per_sq_ft > 0:
                    line5 = f"${price_per_sq_ft:,}/呎"
                else:
                    line5 = "暂无呎价"
                    
                cell_text = f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"
                cell_unit.value = cell_text
                
                cell_unit.font = Font(name='Microsoft YaHei', size=8, bold=(status_raw in ['sale', 'stopped']), color=COLORS.get(status_raw, COLORS['pending'])['fg'])
                cell_unit.fill = FILLS.get(status_raw, FILLS['pending'])
            else:
                cell_unit.value = ""
                cell_unit.fill = PatternFill(start_color='E5E5E5', end_color='E5E5E5', fill_type='solid')
                
        curr_row += 1

    # 设置列宽
    ws_grid.column_dimensions['A'].width = 12
    for col_idx in range(2, len(flats) + 2):
        col_letter = get_column_letter(col_idx)
        ws_grid.column_dimensions[col_letter].width = 18

    # 启用单页打印自适应设置
    ws_grid.sheet_properties.pageSetUpPr.fitToPage = True
    ws_grid.page_setup.fitToWidth = 1
    ws_grid.page_setup.fitToHeight = 1
    ws_grid.page_setup.orientation = ws_grid.ORIENTATION_LANDSCAPE
    ws_grid.page_setup.paperSize = ws_grid.PAPERSIZE_A4

    # 设置窄页边距 (0.25 英寸)
    for margin in ['left', 'right', 'top', 'bottom']:
        setattr(ws_grid.page_margins, margin, 0.25)
    ws_grid.page_margins.header = 0.1
    ws_grid.page_margins.footer = 0.1


```

---

## File: scrape_midland_supplement.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美联独有新盘补充抓取脚本 (scrape_midland_supplement.py) v2.0 动态对比版

功能：
  1. 实时拉取美联（midland.com.hk）和香港置业（hkp.com.hk）的全量项目列表
  2. 自动对比，找出美联独有但 HKP 没有的港岛/九龙一手新盘
  3. 对差集项目进行销控数据抓取，生成 Excel 销控明细表
  4. 每次运行都自动发现新上的盘，无需手动维护项目列表

数据源：https://data.midland.com.hk / https://data.hkp.com.hk
"""

import os
import re
import sys
import json
import time
import requests
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

# ==========================================
# 1. 基础配置
# ==========================================
BASE_DIR = "/Users/nb/google/Antigravity/工作/运营/价单"
zh2hans_path = "/Users/nb/google/Antigravity/工作/运营/楼盘字典/zh2hans.json"

if os.path.exists(zh2hans_path):
    with open(zh2hans_path, 'r', encoding='utf-8') as f:
        zh2hans_dict = json.load(f)
    char_map = {k: v for k, v in zh2hans_dict.items() if len(k) == 1 and len(v) == 1}
    TRADITIONAL_CHARS = "".join(char_map.keys())
    SIMPLIFIED_CHARS  = "".join(char_map.values())
else:
    TRADITIONAL_CHARS = "港島九龍啟德灣仔堅尼地城筲箕灣紅磡鰂魚涌鴨脷洲黃竹坑壽臣山山頂淺水灣深水灣渣甸山薄扶林香港仔上環中環土瓜灣北角摩星嶺黃泥涌"
    SIMPLIFIED_CHARS  = "港岛九龙启德湾仔坚尼地城筲箕湾红磡鲗鱼涌鸭脷洲黄竹坑寿臣山山顶浅水湾深水湾渣甸山薄扶林香港仔上环中环土瓜湾北角摩星岭黄泥涌"

TRANS_MAP = str.maketrans(TRADITIONAL_CHARS, SIMPLIFIED_CHARS)

def t2s(text):
    if not text:
        return ""
    if isinstance(text, dict):
        return {k: t2s(v) for k, v in text.items()}
    if isinstance(text, list):
        return [t2s(x) for x in text]
    return str(text).translate(TRANS_MAP)

def clean_name(name):
    if not name:
        return ""
    name = t2s(name).lower()
    name = re.sub(r'[\s\-\(\)\（\）\.\,\，\。]', '', name)
    return name

def get_safe_filename(project_dir, pname):
    safe_pname = re.sub(r'[\/\\\:\*\?\"<>|]', '', pname)
    return os.path.join(project_dir, f"{safe_pname}_销控明细表.xlsx")

def normalize_bname(name):
    if not name:
        return ""
    name = t2s(name).strip()
    name = re.sub(r'^第', '', name)
    return name

def extract_floor_number(floor_str):
    if not floor_str:
        return -99
    floor_str = str(floor_str).upper().strip()
    match = re.search(r'(\d+)', floor_str)
    if match:
        val = int(match.group(1))
        if 'R' in floor_str:
            val += 0.5
        return val
    if 'G' in floor_str or 'UG' in floor_str:
        return 0
    if 'B' in floor_str:
        return -1
    return -99

# ==========================================
# 2. 状态映射与颜色配置
# ==========================================
STATUS_MAP = {
    'pending': '待售',
    'priced': '已定价未售',
    'sale': '在售',
    'sold': '已售',
    'stopped': '暂停销售'
}

COLORS = {
    'sale':    {'bg': 'A9F5A9', 'fg': '004D00'},
    'sold':    {'bg': 'F5A9A9', 'fg': '660000'},
    'priced':  {'bg': 'A9D0F5', 'fg': '002060'},
    'stopped': {'bg': 'FFC000', 'fg': '000000'},
    'pending': {'bg': 'FFFFFF', 'fg': '7F7F7F'}
}

FILLS = {k: PatternFill(start_color=v['bg'], end_color=v['bg'], fill_type='solid') for k, v in COLORS.items()}

# ==========================================
# 3. 区域代码映射（美联 API 区域代码）
# ==========================================
MIDLAND_REGIONS = {
    'HKI': ('港岛', ['Hong Kong Island', 'HKI']),
    'KLN': ('九龙', ['Kowloon', 'KLN']),
}

# 美联独有且不再出现在 active 列表中的历史新盘（这些项目依然在美联有详情和销控页）
STATIC_MIDLAND_PROJECTS = {
    'E000001984': {'name': '御海园', 'region': '港岛', 'district': '坚尼地城及摩星岭'},
    'E000008181': {'name': 'Shouson Peak', 'region': '港岛', 'district': '寿臣山及浅水湾'},
    'E000000456': {'name': '寿臣山道东1号', 'region': '港岛', 'district': '寿臣山及浅水湾'},
    'E000015288': {'name': 'Twelve Peaks', 'region': '港岛', 'district': '山顶区'},
    'E000016272': {'name': '大潭道45号', 'region': '港岛', 'district': '大潭及石澳'},
    'E000016270': {'name': '77/79 Peak Road', 'region': '港岛', 'district': '山顶区'},
    'E000016346': {'name': '浅水湾108', 'region': '港岛', 'district': '寿臣山及浅水湾'},
    'E000015301': {'name': '远晴', 'region': '港岛', 'district': '筲箕湾'},
    'E000015268': {'name': '339 Tai Hang Road', 'region': '港岛', 'district': '跑马地'},
    'E000015314': {'name': '喇沙汇', 'region': '九龙', 'district': '九龙塘'},
    'E000015455': {'name': '皇廷汇', 'region': '九龙', 'district': '九龙塘'},
    'E000004402': {'name': '天玺', 'region': '九龙', 'district': '九龙站'},
    'E000017140': {'name': '本木', 'region': '九龙', 'district': '尖沙咀'},
    'E000008203': {'name': '耀爵台', 'region': '九龙', 'district': '何文田'},
    'E000015299': {'name': '宾吉道3号', 'region': '港岛', 'district': '山顶区'}
}


# 港岛已知商圈关键词（含这些词语的就是港岛）
HKI_DISTRICT_KEYWORDS = [
    '北角', '半山', '坚尼地城', '摩星岭', '大潭', '石澳', '寿臣山', '浅水湾', '深水湾',
    '山顶', '赤柱', '铜锣湾', '湾仔', '筲箕湾', '薄扶林', '营盘', '上环', '中环',
    '香港仔', '鸭脷洲', '黄竹坑', '黄泥涌', '渣甸山', '鲗鱼涌', '柴湾', '岛山',
    '西区', '东区', '南区'
]
# 九龙已知商圈关键词
KLN_DISTRICT_KEYWORDS = [
    '九龙塘', '西南九龙', '尖沙咀', '何文田', '启德', '红磡', '马头角', '土瓜湾',
    '长沙湾', '深水埗', '旺角', '油麻地', '太子', '牛头角', '九龙湾', '观塘',
    '茶果岭', '油塘', '鲤鱼门', '慈云山', '钻石山', '荔枝角', '石硖尾', '新蒲岗'
]

ALL_VALID_KEYWORDS = HKI_DISTRICT_KEYWORDS + KLN_DISTRICT_KEYWORDS


# ==========================================
# 4. Token 获取（优先动态获取，失败时使用备用静态 Token）
# ==========================================
MIDLAND_BUILD_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJndWlkIjoibXItMjAyMC0xMC0yOC1LdUlFbUR5bnlfWDV0NVVDMkZwSExpdFBodGxLNWRhblV5TFo4WXY0bVJIZEhJY3lrSW1fRmYzS0NYWjlkcENiOEp0Y3hLUy1JSSIsImlhdCI6MTYwMzg3ODk2MiwiaXNzIjoiZGF0YS5taWRsYW5kLmNvbS5oayJ9."
    "O2ASPk6CIDbK4cexR1FOy-TwOOvc-o1KoGANo_ckoOVvyB7OI-sif3VwlAEHZ79dGuC1bWa-oYsbelfRnpX5HZx7cM667gjd7sXycp5j9pCbGwPJ8dzOpwHfnsMIiTnTeL0_D0_PV8-PK7nsrH8iDM7cumD-F6qDl0THXNUahqXycf6MipIAv1CENyMKI3m9wWsoWsnw3T0RGJQ4YtNZ0itackeQbnsFCwm5wxJ2nDNb_yUmN0dA8cApHNaJb8f8IZ91HOf_IXQjwy_LIm4A7VlnOKVx2tvEvK4fOdPVLPbGyHeNINESOhmqCq-Z6ZbvvAel6IySf268NuV_Olk3DUQsBeMRSXrfNEHMGKMpCawtmtZgoRlFnSBYuzgJ1-MkyEgA7Sap6fM6RRhWKi7pST0RiVYhIeQypYaKIMvbsVyvfGGrxptjJzMt8eBUxYK6mZHl2q3N2RBCmc30x7XLsgpQNdW3sQcvA9AsBPWDATFBdVy8l6phVYypD8bn-EOfEZalLle95M1Y80FWo_ek6_uUSMOmLo0YXz6-GgJaJ6GkMf1Syx90bsGjgWHhgGJvLebbwx3Fl7ecVv-afdc6oNSDjQkZID609kaxE6LqEEWQoxGOYrOZDRAhA_dTYgxmjVqhqiBDQOf4ooMvkAVwGL17c9REkNInowi9JX7RHyw"
)

MIDLAND_API_BASE = "https://data.midland.com.hk"
HEADERS_UA = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_midland_token():
    """
    尝试从 www.midland.com.hk 动态获取最新 Token。
    若失败，则使用备用静态 Build Token。
    """
    print("正在获取美联 Token...")
    # 尝试从页面提取动态 token
    for page_url in [
        "https://www.midland.com.hk/zh-cn/new-property/",
        "https://www.midland.com.hk/zh-hk/new-property/",
    ]:
        try:
            r = requests.get(page_url, headers=HEADERS_UA, timeout=15)
            if r.status_code == 200:
                # 查找 BUILD_TOKEN 或 userToken
                m = re.search(r'"BUILD_TOKEN"\s*:\s*"([^"]+)"', r.text)
                if m:
                    token = m.group(1)
                    print(f"  成功从页面提取到 BUILD_TOKEN（长度：{len(token)}）")
                    return token
                m2 = re.search(r'"userToken"\s*:\s*"([^"]+)"', r.text)
                if m2:
                    token = m2.group(1)
                    print(f"  成功从页面提取到 userToken（长度：{len(token)}）")
                    return token
        except Exception as e:
            print(f"  警告: 动态获取 Token 失败 ({e})")

    print(f"  使用备用静态 Build Token（长度：{len(MIDLAND_BUILD_TOKEN)}）")
    return MIDLAND_BUILD_TOKEN


# ==========================================
# 5. Excel 写入（完整复刻 scrape_hkp_sales_control.py 的格式）
# ==========================================
def write_project_excel(filepath, project_name, buildings_data):
    """
    为单个项目写入 Excel 销控表，包含：
    - Tab 1: "销控汇总明细"
    - Tab 2+: 每个楼栋的"销控网格图 (Grid)"
    """
    wb = openpyxl.Workbook()

    # ---- Tab 1: 销控汇总明细 ----
    ws_detail = wb.active
    ws_detail.title = "销控汇总明细"

    font_title  = Font(name='Microsoft YaHei', size=14, bold=True)
    font_header = Font(name='Microsoft YaHei', size=10, bold=True)
    font_data   = Font(name='Microsoft YaHei', size=10)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    border_thin  = Border(
        left=Side(style='thin', color='BFBFBF'), right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'), bottom=Side(style='thin', color='BFBFBF')
    )
    fill_header = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

    ws_detail.merge_cells("A1:J1")
    ws_detail['A1'] = f"{project_name} - 一手销控汇总明细"
    ws_detail['A1'].font = font_title
    ws_detail['A1'].alignment = align_center
    ws_detail.row_dimensions[1].height = 40

    headers = ["楼栋", "楼层", "房号", "户型", "实用面积 (平方呎)", "销控状态", "成交日期", "总价 (港币)", "实用呎价 (港币/呎)", "是否招标"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws_detail.cell(row=2, column=col_idx, value=h)
        cell.font = font_header
        cell.alignment = align_center
        cell.fill = fill_header
        cell.border = border_thin
    ws_detail.row_dimensions[2].height = 25

    row_idx = 3
    for bname, units in buildings_data.items():
        sorted_units = sorted(units, key=lambda x: (extract_floor_number(x['floor']), x['flat']), reverse=True)
        for u in sorted_units:
            ws_detail.cell(row=row_idx, column=1, value=bname)
            ws_detail.cell(row=row_idx, column=2, value=u['floor'])
            ws_detail.cell(row=row_idx, column=3, value=u['flat'])
            ws_detail.cell(row=row_idx, column=4, value=u['room_layout'])
            ws_detail.cell(row=row_idx, column=5, value=u['net_area'] if u['net_area'] > 0 else '暂无')
            ws_detail.cell(row=row_idx, column=6, value=u['status'])
            ws_detail.cell(row=row_idx, column=7, value=u['sold_date'])

            is_tender = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']
            if is_tender and u['status_raw'] != 'sold':
                ws_detail.cell(row=row_idx, column=8, value='招标单位')
                ws_detail.cell(row=row_idx, column=9, value='-')
            else:
                ws_detail.cell(row=row_idx, column=8, value=u['price'] if u['price'] else '暂无')
                ws_detail.cell(row=row_idx, column=9, value=u['price_per_sq_ft'] if u['price_per_sq_ft'] else '暂无')
            ws_detail.cell(row=row_idx, column=10, value='是' if is_tender else '否')

            for col in range(1, 11):
                c = ws_detail.cell(row=row_idx, column=col)
                c.font = font_data
                c.alignment = align_center
                c.border = border_thin
                if col == 8 and isinstance(c.value, (int, float)):
                    c.number_format = '$#,##0'
                elif col == 9 and isinstance(c.value, (int, float)):
                    c.number_format = '$#,##0'
                elif col == 5 and isinstance(c.value, (int, float)):
                    c.number_format = '#,##0'
            row_idx += 1

    for col in ws_detail.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_detail.column_dimensions[col_letter].width = max(max_len + 3, 12)

    ws_detail.sheet_properties.pageSetUpPr.fitToPage = True
    ws_detail.page_setup.fitToWidth = 1
    ws_detail.page_setup.fitToHeight = 0
    ws_detail.page_setup.orientation = ws_detail.ORIENTATION_PORTRAIT
    ws_detail.page_setup.paperSize = ws_detail.PAPERSIZE_A4
    for margin in ['left', 'right', 'top', 'bottom']:
        setattr(ws_detail.page_margins, margin, 0.25)
    ws_detail.page_margins.header = 0.1
    ws_detail.page_margins.footer = 0.1

    multi_buildings = {}
    villa_buildings = {}
    
    if buildings_data:
        for bname, units in buildings_data.items():
            # 判断是否为独栋 (如果该楼栋单位数 <= 2 或是 HOUSE 类型)
            has_house_type = any(u.get('unit_type') == 'HOUSE' for u in units)
            if len(units) <= 2 or has_house_type:
                villa_buildings[bname] = units
            else:
                multi_buildings[bname] = units

    # 1. 多个单位的楼栋，每个楼栋放在单独的工作表
    for bname, units in multi_buildings.items():
        _write_building_grid(wb, bname, units, font_data, font_header, font_title, align_center, border_thin, fill_header)

    # 2. 独栋楼，集合放在一个工作表
    if villa_buildings:
        _write_villa_grid(wb, project_name, villa_buildings, font_data, align_center, border_thin)

    wb.save(filepath)


def _write_building_grid(wb, bname, units, font_data, font_header, font_title, align_center, border_thin, fill_header):
    """为单个楼栋写入销控网格 Tab"""
    safe_tab = re.sub(r'[\\/?*\[\]:]', '', bname)[:31]
    ws = wb.create_sheet(title=safe_tab)

    # 统计面板数据
    total = len(units)
    cnt = {s: 0 for s in STATUS_MAP.keys()}
    for u in units:
        sr = u.get('status_raw', 'pending')
        if sr in cnt:
            cnt[sr] += 1

    # 汇总统计面板 (Row 1 标题，Row 2-3 数据)
    stat_labels = [
        ('总套数', str(total), 'FFFFFF', '000000', False),
        ('在售 (Sale)', str(cnt.get('sale', 0)), 'A9F5A9', '004D00', True),
        ('已定价未售', str(cnt.get('priced', 0)), 'A9D0F5', '002060', False),
        ('已售 (Sold)', str(cnt.get('sold', 0)), 'F5A9A9', '660000', False),
        ('暂停销售', str(cnt.get('stopped', 0)), 'FFC000', '000000', True),
        ('待售 (Pending)', str(cnt.get('pending', 0)), 'FFFFFF', '7F7F7F', False),
    ]

    # Row 1: 楼栋名称
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(stat_labels))
    ws['A1'] = f"{bname} 销控网格图"
    ws['A1'].font = Font(name='Microsoft YaHei', size=13, bold=True)
    ws['A1'].alignment = align_center
    ws.row_dimensions[1].height = 28

    # Row 2: 图例标签
    for col, (label, val, bg, fg, bold) in enumerate(stat_labels, 1):
        c2 = ws.cell(row=2, column=col, value=label)
        c2.font = Font(name='Microsoft YaHei', size=9, bold=bold, color=fg)
        c2.alignment = align_center
        c2.fill = PatternFill(start_color=bg, end_color=bg, fill_type='solid')
        c2.border = border_thin
        # Row 3: 数值
        c3 = ws.cell(row=3, column=col, value=val)
        c3.font = Font(name='Microsoft YaHei', size=10, bold=True, color=fg)
        c3.alignment = align_center
        c3.fill = PatternFill(start_color=bg, end_color=bg, fill_type='solid')
        c3.border = border_thin
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 20

    # 整理楼层、单位
    floors_set = set()
    flats_set = set()
    for u in units:
        floors_set.add(u['floor'])
        flats_set.add(u['flat'])

    floors_sorted = sorted(floors_set, key=extract_floor_number, reverse=True)
    flats_sorted  = sorted(flats_set)

    # 建立单位查找表 (floor, flat) -> unit
    unit_lookup = {(u['floor'], u['flat']): u for u in units}

    # 网格表头 (Row 4 = 单位列)
    ws.cell(row=4, column=1, value='楼层').font = Font(name='Microsoft YaHei', size=9, bold=True)
    ws.cell(row=4, column=1).alignment = align_center
    ws.cell(row=4, column=1).fill = fill_header
    ws.cell(row=4, column=1).border = border_thin
    ws.row_dimensions[4].height = 18

    for col_idx, flat in enumerate(flats_sorted, 2):
        c = ws.cell(row=4, column=col_idx, value=flat)
        c.font = Font(name='Microsoft YaHei', size=9, bold=True)
        c.alignment = align_center
        c.fill = fill_header
        c.border = border_thin
        ws.column_dimensions[get_column_letter(col_idx)].width = 14

    ws.column_dimensions['A'].width = 8

    # 数据行
    for row_idx, floor in enumerate(floors_sorted, 5):
        ws.cell(row=row_idx, column=1, value=floor)
        ws.cell(row=row_idx, column=1).font = Font(name='Microsoft YaHei', size=9, bold=True)
        ws.cell(row=row_idx, column=1).alignment = align_center
        ws.cell(row=row_idx, column=1).fill = fill_header
        ws.cell(row=row_idx, column=1).border = border_thin
        ws.row_dimensions[row_idx].height = 58

        for col_idx, flat in enumerate(flats_sorted, 2):
            u = unit_lookup.get((floor, flat))
            c = ws.cell(row=row_idx, column=col_idx)
            c.border = border_thin
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

            if u is None:
                c.value = ''
                c.fill = PatternFill(start_color='E8E8E8', end_color='E8E8E8', fill_type='solid')
                continue

            status_raw = u.get('status_raw', 'pending')
            color_cfg = COLORS.get(status_raw, COLORS['pending'])
            bg = color_cfg['bg']
            fg = color_cfg['fg']
            is_bold = status_raw in ('sale', 'stopped')

            # 4行文字内容
            line1 = f"{flat} | {u['net_area']}呎 ({u['room_layout']})"
            is_tender = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']
            if is_tender and status_raw != 'sold':
                line2 = "招标单位"
                line3 = "-"
            else:
                if u['price']:
                    price_wan = round(u['price'] / 10000)
                    line2 = f"${price_wan}万"
                else:
                    line2 = "-"
                if u['price_per_sq_ft']:
                    line3 = f"${u['price_per_sq_ft']:,}/呎"
                else:
                    line3 = "-"

            if status_raw == 'sold' and u['sold_date'] and u['sold_date'] != '-':
                try:
                    parts = u['sold_date'].split('-')
                    yr = parts[0][-2:]
                    mo = parts[1]
                    line4 = f"({yr}年-{mo}月)"
                except:
                    line4 = f"({u['sold_date']})"
            else:
                status_display = STATUS_MAP.get(status_raw, '待售')
                line4 = f"({status_display})"

            c.value = f"{line1}\n{line2}\n{line3}\n{line4}"
            c.font = Font(name='Microsoft YaHei', size=8, bold=is_bold, color=fg)
            c.fill = PatternFill(start_color=bg, end_color=bg, fill_type='solid')

    # 打印设置
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth  = 1
    ws.page_setup.fitToHeight = 1
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize   = ws.PAPERSIZE_A4
    for margin in ['left', 'right', 'top', 'bottom']:
        setattr(ws.page_margins, margin, 0.25)
    ws.page_margins.header = 0.1
    ws.page_margins.footer = 0.1


def _write_villa_grid(wb, project_name, buildings_data, font_data, align_center, border_thin):
    """
    独立屋项目整合为一个单一的工作表，避免分割成无数个 1x1 标签页。
    采用 5 行文字的网格卡片式布局（与 scrape_hkp_sales_control.py 一致）。
    """
    ws_grid = wb.create_sheet(title="独立屋销控表")
    
    font_title  = Font(name='Microsoft YaHei', size=14, bold=True)
    font_header = Font(name='Microsoft YaHei', size=10, bold=True)
    fill_header = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

    # 展平所有独立屋单位并打上楼栋标记
    all_units = []
    for bname, units in buildings_data.items():
        for u in units:
            u_copy = u.copy()
            u_copy['_bname'] = bname
            all_units.append(u_copy)
            
    # 基于命名模式分析其网格排布 (行列定位)
    parentheses_matches = sum(1 for u in all_units if re.search(r'^.+?\s*[\(\（].+?[\)\）]$', u['_bname']))
    space_matches = sum(1 for u in all_units if ' ' in u['_bname'].strip())
    
    has_parentheses = parentheses_matches >= len(all_units) * 0.7
    has_space = space_matches >= len(all_units) * 0.7
    
    # 预设分配网格坐标
    for idx, u in enumerate(all_units):
        bname = u['_bname']
        if has_parentheses:
            m = re.search(r'^(.+?)\s*[\(\（](.+?)[\)\）]$', bname)
            if m:
                u['_grid_row'] = m.group(1).strip()
                u['_grid_col'] = m.group(2).strip()
            else:
                u['_grid_row'] = "其他"
                u['_grid_col'] = bname
        elif has_space:
            parts = bname.rsplit(' ', 1)
            u['_grid_row'] = parts[0].strip()
            u['_grid_col'] = parts[1].strip()
        else:
            # 默认横排扁平
            if len(all_units) <= 8:
                u['_grid_row'] = "独立屋"
                u['_grid_col'] = bname
            else:
                # 超过8个，默认后面按 cols_per_row = 6 排布分配
                pass
                
    # 按照大楼/别墅名进行自然排序
    def natural_key(x):
        return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', x['_bname'])]
        
    all_units = sorted(all_units, key=natural_key)
    
    # 如果是超过8个的扁平排布，在此根据自然排序顺序分配行列坐标
    if not has_parentheses and not has_space and len(all_units) > 8:
        cols_per_row = 6
        for idx, u in enumerate(all_units):
            row_num = idx // cols_per_row + 1
            col_num = idx % cols_per_row + 1
            u['_grid_row'] = f"第 {row_num} 行"
            u['_grid_col'] = f"位置 {col_num}"

    # 整理出确切的网格行、列头
    floors = sorted(list(set(u['_grid_row'] for u in all_units)))
    
    # 列头自然排序
    def col_natural_key(text):
        return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', text)]
    flats = sorted(list(set(u['_grid_col'] for u in all_units)), key=col_natural_key)
    
    unit_map = {(u['_grid_row'], u['_grid_col']): u for u in all_units}
    
    # 统计数量
    total_units = len(all_units)
    status_counts = {'sale': 0, 'sold': 0, 'priced': 0, 'stopped': 0, 'pending': 0}
    for u in all_units:
        st = u.get('status_raw', 'pending')
        status_counts[st] = status_counts.get(st, 0) + 1

    # 设置标题
    ws_grid.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(flats) + 1)
    title_cell = ws_grid.cell(row=1, column=1, value=f"{project_name} - 独立屋销控网格图")
    title_cell.font = font_title
    title_cell.alignment = align_center
    ws_grid.row_dimensions[1].height = 40

    # 展示统计面板数据
    ws_grid.row_dimensions[2].height = 20
    ws_grid.row_dimensions[3].height = 25
    
    stat_cols = [
        ("总套数", total_units, 'pending'),
        ("在售 (Sale)", status_counts['sale'], 'sale'),
        ("已定价未售", status_counts['priced'], 'priced'),
        ("已售 (Sold)", status_counts['sold'], 'sold'),
        ("暂停销售", status_counts['stopped'], 'stopped'),
        ("待售 (Pending)", status_counts['pending'], 'pending')
    ]
    
    for stat_idx, (label, val, fill_key) in enumerate(stat_cols, 1):
        cell_lbl = ws_grid.cell(row=2, column=stat_idx, value=label)
        cell_lbl.font = Font(name='Microsoft YaHei', size=9, bold=(fill_key in ['sale', 'stopped']), color=COLORS[fill_key]['fg'])
        cell_lbl.alignment = align_center
        cell_lbl.fill = FILLS[fill_key]
        cell_lbl.border = border_thin
        
        cell_val = ws_grid.cell(row=3, column=stat_idx, value=f"{val} 套")
        cell_val.font = Font(name='Microsoft YaHei', size=11, bold=True, color=COLORS[fill_key]['fg'])
        cell_val.alignment = align_center
        cell_val.fill = FILLS[fill_key]
        cell_val.border = border_thin

    # 空一行后写表头
    header_row = 5
    ws_grid.row_dimensions[header_row].height = 25
    cell_cross = ws_grid.cell(row=header_row, column=1, value="类型/位置" if not has_parentheses else "类型/屋号")
    cell_cross.font = font_header
    cell_cross.alignment = align_center
    cell_cross.border = border_thin
    cell_cross.fill = fill_header

    for col_idx, flat_name in enumerate(flats, 2):
        cell_flat = ws_grid.cell(row=header_row, column=col_idx, value=flat_name)
        cell_flat.font = font_header
        cell_flat.alignment = align_center
        cell_flat.border = border_thin
        cell_flat.fill = fill_header

    # 写入网格数据
    curr_row = header_row + 1
    for f_name in floors:
        ws_grid.row_dimensions[curr_row].height = 80 # 提高以容纳5行文字
        
        cell_floor = ws_grid.cell(row=curr_row, column=1, value=f_name)
        cell_floor.font = font_header
        cell_floor.alignment = align_center
        cell_floor.border = border_thin
        cell_floor.fill = fill_header
        
        for col_idx, flat_name in enumerate(flats, 2):
            u = unit_map.get((f_name, flat_name))
            cell_unit = ws_grid.cell(row=curr_row, column=col_idx)
            cell_unit.border = border_thin
            cell_unit.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            if u:
                status_raw = u['status_raw']
                status_cn = u['status']
                price = u['price']
                net_area = u['net_area']
                price_per_sq_ft = u['price_per_sq_ft']
                is_tender = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']
                sold_date = u.get('sold_date')
                room_layout = u.get('room_layout', '暂无')
                
                # 1. 洋房名称/编号
                line1 = u['_bname']
                
                # 2. 实用面积与户型房数
                area_str = f"{net_area}呎" if net_area > 0 else "暂无"
                layout_str = f" ({room_layout})" if room_layout != '暂无' else ""
                line2 = f"{area_str}{layout_str}"
                
                # 3. 销售状态 (已售写具体登记年份-月份)
                if status_raw == 'sold' and sold_date and sold_date != '-':
                    try:
                        parts = sold_date.split('-')
                        yr = parts[0][-2:]
                        mo = parts[1]
                        line3 = f"({yr}年-{mo}月)"
                    except:
                        line3 = f"({sold_date})"
                else:
                    line3 = f"({status_cn})"
                    
                # 4. 价格 (过亿单位显示 $X.XX亿)
                if is_tender and status_raw != 'sold':
                    line4 = "招标项目" if status_raw == 'sale' else "招标单位"
                else:
                    if price and price > 0:
                        if price >= 100000000:
                            line4 = f"${price/100000000:.2f}亿"
                        elif price >= 10000:
                            line4 = f"${price/10000:,.0f}万"
                        else:
                            line4 = f"${price:,}"
                    else:
                        line4 = "暂无价格"
                        
                # 5. 实用呎价
                if is_tender and status_raw != 'sold':
                    line5 = "-"
                elif price_per_sq_ft and price_per_sq_ft > 0:
                    line5 = f"${price_per_sq_ft:,}/呎"
                else:
                    line5 = "暂无呎价"
                    
                cell_text = f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"
                cell_unit.value = cell_text
                
                cell_unit.font = Font(name='Microsoft YaHei', size=8, bold=(status_raw in ['sale', 'stopped']), color=COLORS.get(status_raw, COLORS['pending'])['fg'])
                cell_unit.fill = FILLS.get(status_raw, FILLS['pending'])
            else:
                cell_unit.value = ""
                cell_unit.fill = PatternFill(start_color='E5E5E5', end_color='E5E5E5', fill_type='solid')
                
        curr_row += 1

    # 设置列宽
    ws_grid.column_dimensions['A'].width = 12
    for col_idx in range(2, len(flats) + 2):
        col_letter = get_column_letter(col_idx)
        ws_grid.column_dimensions[col_letter].width = 18

    # 启用单页打印自适应设置
    ws_grid.sheet_properties.pageSetUpPr.fitToPage = True
    ws_grid.page_setup.fitToWidth = 1
    ws_grid.page_setup.fitToHeight = 1
    ws_grid.page_setup.orientation = ws_grid.ORIENTATION_LANDSCAPE
    ws_grid.page_setup.paperSize = ws_grid.PAPERSIZE_A4

    # 设置窄页边距 (0.25 英寸)
    for margin in ['left', 'right', 'top', 'bottom']:
        setattr(ws_grid.page_margins, margin, 0.25)
    ws_grid.page_margins.header = 0.1
    ws_grid.page_margins.footer = 0.1


def is_project_sold_out(excel_filename):
    """检查本地 excel 文件是否记录为 100% 售出"""
    if not excel_filename or not os.path.exists(excel_filename):
        return False
    try:
        wb = openpyxl.load_workbook(excel_filename, data_only=True)
        if "销控汇总明细" not in wb.sheetnames:
            return False
        ws = wb["销控汇总明细"]
        total = 0
        sold = 0
        for r in range(3, ws.max_row + 1):
            val = ws.cell(row=r, column=1).value
            if not val:
                break
            total += 1
            status_val = ws.cell(row=r, column=6).value
            if status_val == "已售":
                sold += 1
        wb.close()
        if total > 0 and sold == total:
            return True
    except Exception as e:
        print(f"  警告: 检查本地售罄状态异常 ({e})。")
    return False


def load_existing_project_data(pname, pid, region, district, developer, existing_folders, global_units):
    """从本地已存 excel 中加载数据加入 global_units"""
    clean_proj = clean_name(pname)
    if clean_proj not in existing_folders:
        return False
    folder_name = existing_folders[clean_proj]
    excel_path = get_safe_filename(os.path.join(BASE_DIR, folder_name), pname)
    if not os.path.exists(excel_path):
        return False
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb["销控汇总明细"]
        for r in range(3, ws.max_row + 1):
            row_vals = [ws.cell(row=r, column=col).value for col in range(1, 11)]
            if not any(row_vals) or not row_vals[0]:
                break
            global_units.append({
                '项目ID': pid,
                '项目名称': pname,
                '区域': region,
                '商圈': district,
                '开发商': developer,
                '楼栋名称': row_vals[0],
                '楼层': row_vals[1],
                '房号': row_vals[2],
                '户型': row_vals[3],
                '实用面积': row_vals[4],
                '销控状态': row_vals[5],
                '成交日期': row_vals[6] if row_vals[6] else '-',
                '总价': row_vals[7],
                '呎价': row_vals[8],
                '是否招标': row_vals[9]
            })
        wb.close()
        return True
    except Exception as e:
        print(f"  警告: 载入本地备份数据异常 ({e})。")
    return False



# ==========================================
# 6. 主程序逻辑
# ==========================================
def is_hki_kln_district(district_str):
    """判断商圈是否属于港岛或九龙（过滤新界项目）"""
    if not district_str:
        return False
    for kw in ALL_VALID_KEYWORDS:
        if kw in district_str:
            return True
    return False


def fetch_midland_projects(api_headers):
    """
    实时从美联 API 获取港岛+九龙全量项目列表。
    使用 region=HKI/KLN 参数过滤，并以商圈关键词做二次过滤确保准确。
    返回 dict: {project_id: {'name':简体名, 'region':区域, 'district':商圈, 'id':pid}}
    """
    projects = {}
    region_map = {'HKI': '港岛', 'KLN': '九龙'}
    for region_code, region_cn in region_map.items():
        offset = 0
        limit = 200
        while True:
            try:
                r = requests.get(
                    f"{MIDLAND_API_BASE}/search/v2/new-properties",
                    params={'region': region_code, 'limit': limit, 'offset': offset,
                            'language': 'zh-cn', 'order_by': 'order'},
                    headers=api_headers, timeout=15
                )
                if r.status_code != 200:
                    print(f"  美联 {region_cn} 项目列表获取失败: HTTP {r.status_code}")
                    break
                data = r.json()
                items = data.get('result', [])
                if not items:
                    break
                for p in items:
                    pid = p.get('id') or p.get('phase_id') or p.get('project_id')
                    name_raw = (p.get('name') or p.get('name_sc') or
                                p.get('project_name') or '')
                    name = t2s(name_raw)
                    # 提取商圈
                    dist_raw = p.get('district') or p.get('area') or ''
                    if isinstance(dist_raw, dict):
                        dist_raw = dist_raw.get('name_sc') or dist_raw.get('name') or ''
                    elif isinstance(p.get('location'), dict):
                        dist_raw = p['location'].get('district', '') or dist_raw
                    district = t2s(str(dist_raw or ''))

                    if pid and name:
                        if district:
                            # 有商圈信息：用商圈判断是否港岛/九龙，过滤新界
                            if not is_hki_kln_district(district):
                                continue  # 跳过新界项目
                            # 根据商圈关键词校正 region
                            has_hki = any(kw in district for kw in HKI_DISTRICT_KEYWORDS)
                            has_kln = any(kw in district for kw in KLN_DISTRICT_KEYWORDS)
                            if has_hki and not has_kln:
                                actual_region = '港岛'
                            elif has_kln and not has_hki:
                                actual_region = '九龙'
                            else:
                                actual_region = region_cn  # 默认信任 region_code
                        else:
                            # 商圈为空：直接信任 region_code 参数
                            actual_region = region_cn
                        projects[pid] = {'id': pid, 'name': name,
                                         'region': actual_region, 'district': district}
                offset += limit
                total = data.get('total', 0)
                if total == 0 or offset >= total:
                    break
                time.sleep(0.2)
            except Exception as e:
                print(f"  美联项目列表请求异常: {e}")
                break
    return projects


def fetch_hkp_projects():
    """
    实时从 HKP API 获取港岛+九龙全量项目列表。
    返回 set: {project_id} 以及 dict: {clean_name: pid}
    """
    # 先从页面获取 HKP token
    hkp_token = None
    for ua in [
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]:
        try:
            r = requests.get('https://www.hkp.com.hk/zh-hk/list/new-property/',
                             headers={'User-Agent': ua}, timeout=15)
            if r.status_code == 200:
                m = re.search(r'"userToken"\s*:\s*"([^"]+)"', r.text)
                if m:
                    hkp_token = m.group(1)
                    break
        except Exception:
            pass

    if not hkp_token:
        print("  警告: 无法获取 HKP Token，HKP 项目列表将为空")
        return set(), {}

    hkp_headers = {
        'Authorization': f'Bearer {hkp_token}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin': 'https://www.hkp.com.hk',
        'Referer': 'https://www.hkp.com.hk/'
    }

    pid_set = set()
    name_map = {}  # clean_name -> pid
    for region_code in ['HKI', 'KLN']:
        offset = 0
        limit = 200
        while True:
            try:
                r = requests.get(
                    'https://data.hkp.com.hk/search/v2/new-properties',
                    params={'region': region_code, 'limit': limit, 'offset': offset,
                            'language': 'zh-hk', 'order_by': 'order'},
                    headers=hkp_headers, timeout=15
                )
                if r.status_code != 200:
                    break
                data = r.json()
                items = data.get('result', [])
                if not items:
                    break
                for p in items:
                    pid = p.get('id') or p.get('phase_id') or p.get('project_id')
                    name_raw = (p.get('name') or p.get('name_sc') or
                                p.get('project_name') or '')
                    name = t2s(name_raw)
                    if pid:
                        pid_set.add(pid)
                    if name:
                        name_map[clean_name(name)] = pid
                offset += limit
                if offset >= data.get('total', 0):
                    break
                time.sleep(0.2)
            except Exception as e:
                print(f"  HKP 项目列表请求异常: {e}")
                break
    return pid_set, name_map


def find_midland_exclusive(midland_projects, hkp_pid_set, hkp_name_map):
    """
    对比美联和 HKP 项目列表，返回美联独有的项目列表。
    双重匹配机制：
    1. 项目 ID 直接匹配
    2. 清洗后项目名称匹配
    """
    exclusive = []
    for pid, proj in midland_projects.items():
        # 1. ID 直接匹配
        if pid in hkp_pid_set:
            continue
        cn = clean_name(proj['name'])
        # 2. 名称与 HKP 项目列表匹配
        if cn in hkp_name_map:
            continue
        exclusive.append(proj)
    return exclusive


def main():
    print("=" * 50)
    print("  美联独有新盘补充抓取脚本 v2.0 (动态对比版)")
    print("=" * 50)

    # 步骤 1: 获取美联 Token
    token = fetch_midland_token()
    api_headers = {
        'User-Agent': HEADERS_UA['User-Agent'],
        'Authorization': f'Bearer {token}',
        'Origin': 'https://www.midland.com.hk',
        'Referer': 'https://www.midland.com.hk/'
    }

    # 步骤 2: 实时拉取美联全量项目列表
    print("\n[1/4] 正在拉取美联项目列表...")
    midland_projects = fetch_midland_projects(api_headers)
    print(f"  美联港岛+九龙共 {len(midland_projects)} 个项目")

    # 步骤 3: 实时拉取 HKP 全量项目列表
    print("\n[2/4] 正在拉取 HKP 项目列表...")
    hkp_pid_set, hkp_name_map = fetch_hkp_projects()
    print(f"  HKP 港岛+九龙共 {len(hkp_pid_set)} 个项目")

    # 步骤 4: 对比找出差集并合并静态独有项目
    print("\n[3/4] 正在对比差集并合并静态独有项目...")
    exclusive_projects = find_midland_exclusive(midland_projects, hkp_pid_set, hkp_name_map)
    
    # 合并静态列表中的独有项目
    scraped_ids = {p['id'] for p in exclusive_projects}
    for spid, sproj in STATIC_MIDLAND_PROJECTS.items():
        if spid not in scraped_ids:
            exclusive_projects.append({
                'id': spid,
                'name': sproj['name'],
                'region': sproj['region'],
                'district': sproj['district']
            })

    print(f"  美联独有项目 (含静态追加): {len(exclusive_projects)} 个")
    for p in exclusive_projects:
        print(f"    - [{p['id']}] {p['name']} ({p['region']}-{p['district']})")

    if not exclusive_projects:
        print("\n  两家平台项目完全一致，无需补充抓取。")
        return

    # 步骤 5: 扫描已有文件夹
    existing_folders = {}
    for d in os.listdir(BASE_DIR):
        path = os.path.join(BASE_DIR, d)
        if os.path.isdir(path) and d.startswith(('港岛-', '九龙-')):
            parts = d.split('-', 2)
            if len(parts) >= 3:
                key = clean_name(parts[2])
                existing_folders[key] = d

    # 步骤 6: 准备全局汇总数据
    global_units = []
    failed_projects = []
    success_count = 0
    total = len(exclusive_projects)
    print(f"\n[4/4] 开始抓取 {total} 个美联独有项目...")

    # 6.4 逐项目抓取
    for idx, proj in enumerate(exclusive_projects):
        pid    = proj['id']
        pname  = proj['name']
        region = proj['region']
        district = proj['district']

        print(f"\n({idx+1}/{total}) 正在处理: {pname} (ID: {pid})")

        # 6.4.1 预载历史成交记录
        tx_lookup = {}
        try:
            tx_res = requests.get(
                f"{MIDLAND_API_BASE}/search/v2/transactions",
                params={'phase_ids': pid, 'limit': 2000},
                headers=api_headers, timeout=12
            )
            if tx_res.status_code == 200:
                tx_data = tx_res.json().get('result', [])
                for tx in tx_data:
                    tx_bname = normalize_bname(tx.get('building', {}).get('name'))
                    tx_floor = str(tx.get('floor', '')).strip()
                    tx_flat  = str(tx.get('flat', '')).strip()
                    tx_date_raw = tx.get('tx_date')
                    if tx_date_raw:
                        tx_lookup[(tx_bname, tx_floor, tx_flat)] = tx_date_raw[:10]
                print(f"  已载入历史成交纪录 {len(tx_lookup)} 条。")
        except Exception as e:
            print(f"  提示: 预载历史成交纪录失败 ({e})。")

        # 6.4.2 获取项目详情（楼栋列表）
        try:
            detail_res = requests.get(
                f"{MIDLAND_API_BASE}/info/v1/new-properties/{pid}",
                headers=api_headers, timeout=12
            )
            if detail_res.status_code != 200:
                print(f"  警告: 无法获取项目详情 (HTTP {detail_res.status_code})，跳过。")
                failed_projects.append(pname)
                continue
            detail_data = detail_res.json()
        except Exception as e:
            print(f"  警告: 请求项目详情异常 ({e})，跳过。")
            failed_projects.append(pname)
            continue

        # 检查本地是否已售罄，若售罄则直接加载本地备份，不再爬取
        developer = t2s(detail_data.get('developer', ''))
        clean_proj_name = clean_name(pname)
        excel_filename = None
        if clean_proj_name in existing_folders:
            folder_name = existing_folders[clean_proj_name]
            excel_filename = get_safe_filename(os.path.join(BASE_DIR, folder_name), pname)

        if excel_filename and is_project_sold_out(excel_filename):
            print(f"  [已售罄] 该项目去化率已达 100%，无需重复爬取，直接沿用并合并本地数据。")
            if load_existing_project_data(pname, pid, region, district, developer, existing_folders, global_units):
                success_count += 1
            else:
                failed_projects.append(pname)
            continue

        # 收集楼栋信息
        buildings_map = {}
        for b in detail_data.get('buildings', []):
            bid = b.get('id')
            bname = t2s(b.get('name', ''))
            if bid:
                buildings_map[bid] = bname
            for sub_b in b.get('buildings', []):
                sub_bid = sub_b.get('id')
                sub_bname = t2s(sub_b.get('name', ''))
                if sub_bid:
                    buildings_map[sub_bid] = sub_bname

        # 从 floorplan 补充楼栋
        for fp in detail_data.get('floorplan', []):
            b_info = fp.get('building', {})
            bid = b_info.get('id')
            bname = t2s(b_info.get('name', ''))
            if bid and bid not in buildings_map:
                buildings_map[bid] = bname

        # 从历史成交补充
        for tx in tx_lookup.keys():
            pass  # tx_lookup key is (bname, floor, flat) — buildings by ID sourced above

        sell_status = detail_data.get('sell_status', '')
        print(f"  楼栋数: {len(buildings_map)} | 售卖状态: {sell_status}")

        if not buildings_map:
            print(f"  提示: [{sell_status}] 该项目暂无楼栋/单位数据（可能未开售）。")
            if sell_status not in ('coming_soon',):
                failed_projects.append(pname)
            else:
                print(f"  [跳过] 尚未开售项目，无销控数据可抓取。")
            continue

        # 6.4.3 逐楼栋抓取单位销控数据
        project_buildings_data = {}

        for bid, bname in buildings_map.items():
            print(f"    -> 楼栋: {bname} (ID: {bid})")
            try:
                units_res = requests.get(
                    f"{MIDLAND_API_BASE}/info/v1/new-property/transactions/buildings/{bid}",
                    headers=api_headers, timeout=12
                )
                if units_res.status_code != 200:
                    print(f"      警告: HTTP {units_res.status_code}，跳过该楼栋。")
                    continue
                units_data = units_res.json()
            except Exception as e:
                print(f"      警告: 请求单位数据异常 ({e})，跳过该楼栋。")
                continue

            units = units_data.get('data', [])
            print(f"      获取到单位数: {len(units)}")

            parsed_units = []
            for u in units:
                floor       = u.get('floor')
                flat        = u.get('flat') or u.get('flat_name') or '-'
                net_area    = u.get('net_area', 0) or 0
                status_raw  = u.get('status', 'pending')
                status_cn   = STATUS_MAP.get(status_raw, '待售')
                is_tender   = u.get('is_tender') is True or str(u.get('is_tender')).lower() in ['true', '1']

                price = u.get('price')
                if price is not None:
                    try:
                        price = float(price)
                    except ValueError:
                        price = None

                unit_price_net = u.get('unit_price_net')
                if unit_price_net is not None:
                    try:
                        price_per_sq_ft = int(float(unit_price_net))
                    except ValueError:
                        price_per_sq_ft = None
                else:
                    price_per_sq_ft = int(round(price / net_area)) if (price and net_area > 0) else None

                # 户型提取
                room_layout = '暂无'
                detail_list = u.get('detail', [])
                if detail_list:
                    room_type = detail_list[0].get('room_type')
                    if room_type is not None and str(room_type) != '':
                        if str(room_type) in ['0', 0]:
                            room_layout = '开放式'
                        else:
                            room_layout = f"{room_type}房"

                # 成交日期
                sold_date_raw = u.get('sold_date') or u.get('tx_date')
                sold_date = '-'
                if status_raw == 'sold':
                    if sold_date_raw:
                        sold_date = sold_date_raw[:10]
                    else:
                        norm_b = normalize_bname(bname)
                        mapped_date = tx_lookup.get((norm_b, str(floor).strip(), str(flat).strip()))
                        if mapped_date:
                            sold_date = mapped_date

                unit_info = {
                    'floor': floor, 'flat': flat, 'net_area': net_area,
                    'status_raw': status_raw, 'status': status_cn,
                    'price': price, 'price_per_sq_ft': price_per_sq_ft,
                    'is_tender': u.get('is_tender'),
                    'room_layout': room_layout, 'sold_date': sold_date,
                    'unit_type': u.get('unit_type', '')
                }
                parsed_units.append(unit_info)

                # 汇总全局数据
                global_units.append({
                    '项目ID':   pid,
                    '项目名称': pname,
                    '区域':     region,
                    '商圈':     district,
                    '开发商':   t2s(detail_data.get('developer', '')),
                    '楼栋名称': bname,
                    '楼层':     floor,
                    '房号':     flat,
                    '户型':     room_layout,
                    '实用面积': net_area if net_area > 0 else '暂无',
                    '销控状态': status_cn,
                    '成交日期': sold_date,
                    '总价':    '招标单位' if (is_tender and status_raw != 'sold') else (price if price else '暂无'),
                    '呎价':    '-' if (is_tender and status_raw != 'sold') else (price_per_sq_ft if price_per_sq_ft else '暂无'),
                    '是否招标': '是' if is_tender else '否'
                })

            if parsed_units:
                project_buildings_data[bname] = parsed_units

            time.sleep(0.3)

        # 6.4.4 写入 Excel
        if project_buildings_data:
            clean_proj = clean_name(pname)
            if clean_proj in existing_folders:
                folder_name = existing_folders[clean_proj]
            else:
                folder_name = f"{region}-{district}-{pname}"
                folder_name = re.sub(r'[\/\\\:\*\?\"<>|]', '', folder_name)

            project_dir = os.path.join(BASE_DIR, folder_name)
            os.makedirs(project_dir, exist_ok=True)

            excel_path = get_safe_filename(project_dir, pname)
            write_project_excel(excel_path, pname, project_buildings_data)
            print(f"  [完成] 写入销控表: {excel_path}")
            success_count += 1
        else:
            print(f"  [提示] 未获取到有效单位数据，跳过 {pname}。")
            failed_projects.append(pname)

        time.sleep(0.5)

    # 6.5 将本次抓取的新项目数据合并更新到全局汇总表
    print(f"\n{'='*50}")
    print(f"本次成功抓取: {success_count}/{total} 个项目")
    if failed_projects:
        print(f"失败/跳过项目: {failed_projects}")

    if global_units:
        global_excel_path = os.path.join(BASE_DIR, "香港一手新盘销控汇总.xlsx")
        print(f"\n正在将 {len(global_units)} 条新数据合并到全局汇总表...")
        _append_to_global_excel(global_excel_path, global_units)
        print(f"[完成] 全局汇总表已更新: {global_excel_path}")
    else:
        print("\n[提示] 无新单位数据，全局汇总表未更新。")

    print("=" * 50)
    print("补充抓取完成！")


def _append_to_global_excel(global_path, new_units):
    """
    将新抓取的数据追加到全局汇总表。
    若文件存在，则在末尾追加行；若不存在，则新建。
    """
    if not os.path.exists(global_path):
        print("  全局汇总表不存在，将新建文件。")
        _write_global_excel_new(global_path, new_units)
        return

    try:
        wb = openpyxl.load_workbook(global_path)
    except Exception as e:
        print(f"  警告: 无法打开全局汇总表 ({e})，将新建。")
        _write_global_excel_new(global_path, new_units)
        return

    ws = wb.active
    font_data   = Font(name='Microsoft YaHei', size=9)
    align_ctr   = Alignment(horizontal='center', vertical='center', wrap_text=True)
    border_thin = Border(
        left=Side(style='thin', color='BFBFBF'), right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'), bottom=Side(style='thin', color='BFBFBF')
    )

    # 找到第一个空行
    last_row = ws.max_row
    # 检查是否已有这些项目，避免重复
    existing_keys = set()
    for row in ws.iter_rows(min_row=3, values_only=True):
        if row and row[1]:  # 项目名称在第2列
            existing_keys.add((str(row[1]), str(row[7] or ''), str(row[8] or '')))  # (pname, floor, flat)

    added = 0
    for u in new_units:
        key = (str(u['项目名称']), str(u['楼层'] or ''), str(u['房号'] or ''))
        if key in existing_keys:
            continue  # 已存在，跳过

        last_row += 1
        row_vals = [
            u['区域'], u['项目名称'], u['商圈'], u['开发商'],
            u['楼栋名称'], u['楼层'], u['房号'], u['户型'],
            u['实用面积'], u['销控状态'], u['成交日期'],
            u['总价'], u['呎价'], u['是否招标']
        ]
        for col_idx, val in enumerate(row_vals, 1):
            c = ws.cell(row=last_row, column=col_idx, value=val)
            c.font = font_data
            c.alignment = align_ctr
            c.border = border_thin

        existing_keys.add(key)
        added += 1

    wb.save(global_path)
    print(f"  成功追加 {added} 条新单位数据到全局汇总表。")


def _write_global_excel_new(global_path, units):
    """新建全局汇总表"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "全局销控汇总"
    headers = ["区域", "项目名称", "商圈", "开发商", "楼栋名称", "楼层", "房号", "户型",
               "实用面积 (平方呎)", "销控状态", "成交日期", "总价 (港币)", "实用呎价 (港币/呎)", "是否招标"]
    for c, h in enumerate(headers, 1):
        ws.cell(row=1, column=c, value=h)
    for row_idx, u in enumerate(units, 2):
        vals = [u['区域'], u['项目名称'], u['商圈'], u['开发商'], u['楼栋名称'],
                u['楼层'], u['房号'], u['户型'], u['实用面积'], u['销控状态'],
                u['成交日期'], u['总价'], u['呎价'], u['是否招标']]
        for c, v in enumerate(vals, 1):
            ws.cell(row=row_idx, column=c, value=v)
    wb.save(global_path)


if __name__ == '__main__':
    main()

```

---

## File: build_web.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import shutil
from datetime import datetime
import openpyxl

BASE_DIR = "/Users/nb/google/Antigravity/工作/运营/价单"
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
                        # 兼容处理
                        if '售' in status_str and '未售' not in status_str and '待售' not in status_str and '暂停' not in status_str:
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

def main():
    print("开始扫描价单目录并构建网页数据库...")
    ensure_dirs()
    
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
    
    # 遍历 BASE_DIR 下的子文件夹
    for d in sorted(os.listdir(BASE_DIR)):
        dir_path = os.path.join(BASE_DIR, d)
        if not os.path.isdir(dir_path):
            continue
            
        # 忽略 .agents, web 等目录
        if d.startswith('.') or d in ['web', 'scratch']:
            continue
            
        # 解析文件夹命名：{区域}-{商圈}-{项目名称}
        parts = d.split('-')
        if len(parts) < 3:
            continue
            
        region = parts[0].strip()
        district = parts[1].strip()
        project_name = "-".join(parts[2:]).strip() # 项目名称可能有横杠
        
        # 寻找对应的 Excel 销控表：{项目名称}_销控明细表.xlsx
        excel_filename = f"{project_name}_销控明细表.xlsx"
        src_excel_path = os.path.join(dir_path, excel_filename)
        
        if not os.path.exists(src_excel_path):
            # 尝试不区分大小写或者模糊匹配
            found = False
            for file in os.listdir(dir_path):
                if file.endswith("_销控明细表.xlsx"):
                    src_excel_path = os.path.join(dir_path, file)
                    excel_filename = file
                    found = True
                    break
            if not found:
                print(f"跳过: {d} (未找到销控明细表 Excel)")
                continue
        
        print(f"处理项目: {region} -> {district} -> {project_name}")
        
        # 1. 统计数据
        stats = parse_project_stats(src_excel_path)
        
        # 1.1 过滤售罄项目 (去化率达 100% 的项目在网页端不予展示)
        if stats['total'] > 0 and stats['sold'] == stats['total']:
            print(f"  [网页过滤] 项目 {project_name} 已售罄 (100%)，不展示在网页端。")
            continue
        
        # 2. 拷贝 Excel 文件到 web/files/ 并规范重命名为 {区域}-{商圈}-{项目名称}.xlsx
        dest_filename = f"{region}-{district}-{project_name}.xlsx"
        dest_excel_path = os.path.join(FILES_DIR, dest_filename)
        
        try:
            shutil.copy2(src_excel_path, dest_excel_path)
            file_size_kb = round(os.path.getsize(dest_excel_path) / 1024, 1)
        except Exception as e:
            print(f"错误: 拷贝文件 {excel_filename} 失败: {e}")
            continue
            
        # 获取文件修改时间作为更新时间
        mtime = os.path.getmtime(src_excel_path)
        last_updated_date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        
        # 3. 收集项目信息
        proj_info = {
            'name': project_name,
            'region': region,
            'district': district,
            'filename': dest_filename,
            'file_size_kb': file_size_kb,
            'stats': stats,
            'last_updated': last_updated_date
        }
        projects_list.append(proj_info)
        
        # 累加全局统计
        global_stats['total_projects'] += 1
        global_stats['total_units'] += stats['total']
        global_stats['total_sold'] += stats['sold']
        global_stats['total_sale'] += stats['sale']
        global_stats['total_priced'] += stats['priced']
        global_stats['total_stopped'] += stats['stopped']
        global_stats['total_pending'] += stats['pending']

    # 计算全局去化率
    if global_stats['total_units'] > 0:
        global_stats['overall_sold_rate'] = round((global_stats['total_sold'] / global_stats['total_units']) * 100, 1)
    else:
        global_stats['overall_sold_rate'] = 0.0

    # 导出 json 数据库
    db_data = {
        'global_stats': global_stats,
        'projects': projects_list
    }
    
    json_path = os.path.join(WEB_DIR, "data.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n构建成功! 共处理 {global_stats['total_projects']} 个项目。")
    print(f"数据索引已写入: {json_path}")
    print(f"静态文件已整理至: {FILES_DIR}")

if __name__ == "__main__":
    main()

```

---

## File: web/index.html
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>香港一手新盘销控中心</title>
  <!-- 引入 Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
  <!-- 引入自定义样式 -->
  <link rel="stylesheet" href="style.css">
  <!-- 引入 SheetJS 用于在线解析 Excel -->
  <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
</head>
<body>
  <!-- 背景环境光效果 -->
  <div class="glow-bg">
    <div class="glow-circle circle-1"></div>
    <div class="glow-circle circle-2"></div>
  </div>

  <div class="container">
    <!-- 页头 -->
    <header class="app-header">
      <div class="logo-area">
        <h1>香港一手新盘销控中心</h1>
        <p class="subtitle">实时抓取 • 全局检索 • 楼栋销控可视化网格预览</p>
      </div>
      <div class="update-badge" id="lastUpdatedBadge">数据载入中...</div>
    </header>

    <!-- 全局统计仪表盘 -->
    <section class="dashboard-stats" id="globalStats">
      <div class="stat-card">
        <div class="stat-value" id="statProjects">-</div>
        <div class="stat-label">收录项目</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="statUnits">-</div>
        <div class="stat-label">总规划套数</div>
      </div>
      <div class="stat-card highlight-sold">
        <div class="stat-value" id="statSoldRate">-%</div>
        <div class="stat-label">整体去化率 (已售占比)</div>
      </div>
      <div class="stat-card highlight-sale">
        <div class="stat-value" id="statOnSale">-</div>
        <div class="stat-label">全港在售单位</div>
      </div>
    </section>

    <!-- 搜索与筛选面板 -->
    <section class="filter-panel">
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input type="text" id="searchInput" placeholder="输入项目名称、商圈拼音或关键字进行搜索...">
      </div>

      <div class="filter-controls">
        <div class="btn-group" id="regionFilter">
          <button class="filter-btn active" data-region="all">全部区域</button>
          <button class="filter-btn" data-region="港岛">港岛</button>
          <button class="filter-btn" data-region="九龙">九龙</button>
        </div>

        <div class="select-wrapper">
          <select id="districtSelect">
            <option value="all">所有商圈</option>
          </select>
        </div>
      </div>
    </section>

    <!-- 项目卡片网格列表 -->
    <main class="project-grid" id="projectGrid">
      <!-- 骨架屏加载状态 -->
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
    </main>
  </div>

  <!-- 在线预览模态弹窗 (Modal) -->
  <div class="modal-overlay" id="previewModal">
    <div class="modal-container">
      <header class="modal-header">
        <div class="modal-title-area">
          <h2 id="modalProjectTitle">项目名称</h2>
          <p id="modalProjectSubtitle">港岛 - 港岛区 - 销控图</p>
        </div>
        <button class="close-btn" id="closeModalBtn" aria-label="关闭弹窗">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>

      <div class="modal-content">
        <!-- 楼栋切换 Tab 栏 -->
        <div class="building-tabs-wrapper">
          <div class="building-tabs" id="buildingTabs">
            <!-- 楼栋按钮动态生成 -->
          </div>
        </div>

        <!-- 楼栋内部去化统计面板 -->
        <div class="building-stats-panel" id="buildingStatsPanel">
          <div class="building-stat-item status-total">
            <span class="dot"></span>
            <span class="label">总套数:</span>
            <span class="val" id="bStatTotal">-</span>
          </div>
          <div class="building-stat-item status-sale">
            <span class="dot"></span>
            <span class="label">在售:</span>
            <span class="val" id="bStatSale">-</span>
          </div>
          <div class="building-stat-item status-priced">
            <span class="dot"></span>
            <span class="label">已定价未售:</span>
            <span class="val" id="bStatPriced">-</span>
          </div>
          <div class="building-stat-item status-sold">
            <span class="dot"></span>
            <span class="label">已售:</span>
            <span class="val" id="bStatSold">-</span>
          </div>
          <div class="building-stat-item status-stopped">
            <span class="dot"></span>
            <span class="label">暂停销售:</span>
            <span class="val" id="bStatStopped">-</span>
          </div>
        </div>

        <!-- 网格图缩放/平移操作提示 -->
        <div class="grid-tip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="tip-icon">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path>
          </svg>
          小提示：若屏幕尺寸较小，可左右拖拽/双指缩放网格图查看完整楼栋
        </div>

        <!-- 销控矩阵渲染区 -->
        <div class="grid-render-area" id="gridRenderArea">
          <div class="loading-spinner">
            <div class="spinner"></div>
            <p>正在解析 Excel 楼栋数据，请稍候...</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 引入交互 JS -->
  <script src="app.js"></script>
</body>
</html>

```

---

## File: web/style.css
```css
/* ==========================================================================
   香港一手新盘销控中心 - 全局设计系统与样式规范
   ========================================================================== */

/* 变量声明 */
:root {
  --bg-primary: #0f111a;
  --bg-secondary: rgba(26, 29, 46, 0.65);
  --bg-tertiary: #1e2235;
  --text-primary: #f3f4f6;
  --text-secondary: #9ca3af;
  --accent-color: #10b981; /* Emerald Green */
  --accent-glow: rgba(16, 185, 129, 0.2);
  --border-color: rgba(255, 255, 255, 0.08);
  --border-focus: rgba(16, 185, 129, 0.4);
  --card-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
  --glass-effect: backdrop-filter: blur(12px);
  --font-main: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  
  /* 销控网格专属配色规范 */
  --color-sale-bg: #a9f5a9;
  --color-sale-fg: #004d00;
  
  --color-priced-bg: #a9d0f5;
  --color-priced-fg: #002060;
  
  --color-sold-bg: #f5a9a9;
  --color-sold-fg: #660000;
  
  --color-stopped-bg: #ffc000;
  --color-stopped-fg: #000000;
  
  --color-pending-bg: #ffffff;
  --color-pending-fg: #7f7f7f;
}

/* 基础重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-family: var(--font-main);
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  line-height: 1.5;
}

/* 背景发光球环境光 (Ambient Glow) */
.glow-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: -1;
  pointer-events: none;
  overflow: hidden;
}

.glow-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.15;
}

.circle-1 {
  top: -10%;
  right: 10%;
  width: 50vw;
  height: 50vw;
  background: radial-gradient(circle, #10b981 0%, transparent 70%);
}

.circle-2 {
  bottom: -10%;
  left: 5%;
  width: 60vw;
  height: 60vw;
  background: radial-gradient(circle, #3b82f6 0%, transparent 70%);
}

/* 页面容器 */
.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem;
}

/* 页头样式 */
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2.5rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 1.5rem;
}

.logo-area h1 {
  font-size: 2.2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 30%, #a7f3d0 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.025em;
  margin-bottom: 0.5rem;
}

.logo-area .subtitle {
  font-size: 0.95rem;
  color: var(--text-secondary);
  font-weight: 300;
}

.update-badge {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* 全局统计仪表盘 */
.dashboard-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2.5rem;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 1.8rem 1.5rem;
  border-radius: 16px;
  box-shadow: var(--card-shadow);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.3s;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-card:hover {
  transform: translateY(-4px);
  border-color: var(--border-focus);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 0.4rem;
  font-feature-settings: "tnum";
}

.stat-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* 强调卡片样式 */
.highlight-sold .stat-value {
  color: #fb7185; /* Soft Red */
  text-shadow: 0 0 10px rgba(251, 113, 133, 0.2);
}

.highlight-sale .stat-value {
  color: #34d399; /* Soft Green */
  text-shadow: 0 0 10px rgba(52, 211, 153, 0.2);
}

/* 搜索与筛选面板 */
.filter-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 1.5rem;
  border-radius: 16px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  margin-bottom: 2.5rem;
}

@media (min-width: 768px) {
  .filter-panel {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}

.search-box {
  position: relative;
  flex-grow: 1;
}

.search-icon {
  position: absolute;
  left: 1.2rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.2rem;
  height: 1.2rem;
  color: var(--text-secondary);
  pointer-events: none;
}

.search-box input {
  width: 100%;
  background: rgba(15, 17, 26, 0.6);
  border: 1px solid var(--border-color);
  padding: 0.9rem 1.2rem 0.9rem 3rem;
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 0.95rem;
  outline: none;
  font-family: var(--font-main);
  transition: all 0.3s;
}

.search-box input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 4px var(--accent-glow);
  background: rgba(15, 17, 26, 0.9);
}

.filter-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.btn-group {
  display: flex;
  background: rgba(15, 17, 26, 0.6);
  padding: 0.3rem;
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.filter-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 0.6rem 1.2rem;
  border-radius: 9px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  font-family: var(--font-main);
  transition: all 0.2s;
}

.filter-btn:hover {
  color: var(--text-primary);
}

.filter-btn.active {
  background: var(--accent-color);
  color: #000000;
  font-weight: 600;
}

.select-wrapper {
  position: relative;
}

.select-wrapper select {
  appearance: none;
  background: rgba(15, 17, 26, 0.6);
  border: 1px solid var(--border-color);
  padding: 0.75rem 2.5rem 0.75rem 1.2rem;
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 500;
  font-family: var(--font-main);
  outline: none;
  cursor: pointer;
  min-width: 150px;
  transition: all 0.3s;
}

.select-wrapper select:focus {
  border-color: var(--accent-color);
}

.select-wrapper::after {
  content: "";
  position: absolute;
  right: 1.1rem;
  top: 50%;
  transform: translateY(-20%);
  border: 5px solid transparent;
  border-top-color: var(--text-secondary);
  pointer-events: none;
}

/* 项目卡片网格 */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.8rem;
}

/* 项目卡片 */
.project-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--card-shadow);
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.3s, box-shadow 0.3s;
  position: relative;
}

.project-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, var(--accent-color), #3b82f6);
  opacity: 0.6;
}

.project-card:hover {
  transform: translateY(-6px);
  border-color: rgba(16, 185, 129, 0.3);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.45);
}

.card-header {
  padding: 1.5rem 1.5rem 1rem 1.5rem;
}

.card-meta {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
}

.badge {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
}

.badge-region {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.25);
}

.badge-district {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.project-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.3;
}

.card-body {
  padding: 0 1.5rem 1.5rem 1.5rem;
  flex-grow: 1;
}

/* 去化率条形图 */
.sold-progress-area {
  margin: 1.2rem 0 1.5rem 0;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-bottom: 0.4rem;
}

.progress-label {
  color: var(--text-secondary);
}

.progress-val {
  font-weight: 700;
  color: #fb7185;
}

.progress-bar-bg {
  background: rgba(255, 255, 255, 0.05);
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.progress-bar-fill {
  background: linear-gradient(90deg, #fb7185, #ec4899);
  height: 100%;
  border-radius: 4px;
  width: 0; /* JS 动态赋值 */
  transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 详细统计数据 */
.card-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.8rem;
  background: rgba(0, 0, 0, 0.15);
  padding: 0.8rem;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  font-size: 0.8rem;
  margin-bottom: 1.5rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-item .lbl {
  color: var(--text-secondary);
}

.stat-item .val {
  font-weight: 600;
  color: var(--text-primary);
}

.stat-item.sold-count .val {
  color: #fca5a5;
}

.stat-item.sale-count .val {
  color: #6ee7b7;
}

/* 卡片操作底部 */
.card-footer {
  padding: 0 1.5rem 1.5rem 1.5rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
  border-top: 1px solid var(--border-color);
  padding-top: 1.2rem;
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  font-family: var(--font-main);
  text-decoration: none;
}

.btn-primary {
  background: var(--accent-color);
  color: #000000;
  border: none;
}

.btn-primary:hover {
  background: #34d399;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
  transform: translateY(-1px);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--text-secondary);
}

.btn-icon {
  width: 1.1rem;
  height: 1.1rem;
}

/* 无搜索结果样式 */
.no-results {
  grid-column: 1 / -1;
  text-align: center;
  padding: 5rem 2rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-secondary);
}

.no-results svg {
  width: 4rem;
  height: 4rem;
  margin-bottom: 1.5rem;
  opacity: 0.3;
}

.no-results h3 {
  color: var(--text-primary);
  margin-bottom: 0.5rem;
  font-size: 1.4rem;
}

/* 骨架屏加载 */
.skeleton-card {
  height: 380px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
}

.skeleton-card::after {
  content: "";
  display: block;
  width: 100%;
  height: 100%;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.04), transparent);
  animation: loading 1.5s infinite;
}

@keyframes loading {
  100% {
    transform: translateX(100%);
  }
}

/* ==========================================================================
   模态弹窗样式 (Modal Layout & Grid Display)
   ========================================================================== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(5, 6, 10, 0.85);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 1.5rem;
}

.modal-overlay.open {
  opacity: 1;
  pointer-events: auto;
}

.modal-container {
  background: #111422;
  border: 1px solid rgba(255, 255, 255, 0.1);
  width: 100%;
  max-width: 1100px;
  max-height: 90vh;
  border-radius: 24px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transform: scale(0.96) translateY(10px);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-overlay.open .modal-container {
  transform: scale(1) translateY(0);
}

.modal-header {
  padding: 1.5rem 2rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(17, 20, 34, 0.8);
  backdrop-filter: blur(10px);
}

.modal-title-area h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.2rem;
}

.modal-title-area p {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.close-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}

.close-btn svg {
  width: 1.2rem;
  height: 1.2rem;
}

.modal-content {
  padding: 1.5rem 2rem;
  overflow-y: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* 楼栋 Tabs 样式 */
.building-tabs-wrapper {
  overflow-x: auto;
  border-bottom: 1px solid var(--border-color);
  padding-top: 0.2rem;
  padding-bottom: 0.8rem;
  scrollbar-width: thin; /* Firefox */
  flex-shrink: 0;
}

/* 楼栋 Tabs 滚动条美化 */
.building-tabs-wrapper::-webkit-scrollbar {
  height: 6px;
}
.building-tabs-wrapper::-webkit-scrollbar-track {
  background: transparent;
}
.building-tabs-wrapper::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
}
.building-tabs-wrapper::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}


.building-tabs {
  display: flex;
  gap: 0.6rem;
}

.tab-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.6rem 1.2rem;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-primary);
}

.tab-btn.active {
  background: rgba(16, 185, 129, 0.15);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

/* 楼栋去化统计面板 */
.building-stats-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  background: rgba(0, 0, 0, 0.25);
  padding: 0.8rem 1.2rem;
  border-radius: 14px;
  border: 1px solid var(--border-color);
  font-size: 0.85rem;
}

.building-stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-radius: 8px;
  padding: 0.4rem 0.8rem;
  border: 1px solid rgba(255, 255, 255, 0.03);
}

.building-stat-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.building-stat-item .label {
  font-weight: 500;
}

.building-stat-item .val {
  font-weight: 700;
}

/* 楼栋去化子项高对比度专属配色 */
.status-total {
  background-color: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
}
.status-total .dot { background-color: #9ca3af; }
.status-total .label { color: var(--text-secondary); }
.status-total .val { color: #ffffff; }

.status-sale {
  background-color: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.25);
}
.status-sale .dot { background-color: #4ade80; }
.status-sale .label { color: #a7f3d0; }
.status-sale .val { color: #4ade80; }

.status-priced {
  background-color: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.25);
}
.status-priced .dot { background-color: #60a5fa; }
.status-priced .label { color: #bfdbfe; }
.status-priced .val { color: #60a5fa; }

.status-sold {
  background-color: rgba(244, 63, 94, 0.15);
  border-color: rgba(244, 63, 94, 0.25);
}
.status-sold .dot { background-color: #fca5a5; }
.status-sold .label { color: #fecdd3; }
.status-sold .val { color: #fca5a5; }

.status-stopped {
  background-color: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.25);
}
.status-stopped .dot { background-color: #f59e0b; }
.status-stopped .label { color: #fde68a; }
.status-stopped .val { color: #f59e0b; }

.grid-tip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.tip-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

/* 销控网格图渲染大区域 */
.grid-render-area {
  flex-grow: 1;
  border: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.25);
  border-radius: 16px;
  overflow: auto;
  min-height: 350px;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  padding: 1.5rem;
}

/* 表格渲染 */
.excel-grid-table {
  border-collapse: collapse;
  margin: 0 auto;
  font-size: 0.85rem;
  color: #000; /* 网格内容主要是暗色文字 */
  font-family: var(--font-main);
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  border-radius: 8px;
  overflow: hidden;
  background-color: #f9f9f9;
}

.excel-grid-table td, .excel-grid-table th {
  border: 1px solid #bfbfbf;
  padding: 8px 10px;
  text-align: center;
  vertical-align: middle;
  min-width: 140px;
  height: 75px; /* 让四行字有足够空间 */
  white-space: pre-line; /* 允许 \n 折行 */
  font-size: 0.82rem;
  line-height: 1.4;
}

/* 单元格表头：楼层与房号 */
.excel-grid-table th,
.excel-grid-table td.grid-header-cell {
  background-color: #f2f2f2;
  color: #000000;
  font-weight: 700;
  font-size: 0.85rem;
  min-width: 90px;
  height: 40px;
}

/* 空网格状态 */
.excel-grid-table td.grid-empty-cell {
  background-color: #e5e5e5;
}

/* 五大状态颜色填充 */
.excel-grid-table td.status-sale-cell {
  background-color: var(--color-sale-bg) !important;
  color: var(--color-sale-fg) !important;
  font-weight: 700;
}

.excel-grid-table td.status-priced-cell {
  background-color: var(--color-priced-bg) !important;
  color: var(--color-priced-fg) !important;
  font-weight: 400;
}

.excel-grid-table td.status-sold-cell {
  background-color: var(--color-sold-bg) !important;
  color: var(--color-sold-fg) !important;
  font-weight: 400;
}

.excel-grid-table td.status-stopped-cell {
  background-color: var(--color-stopped-bg) !important;
  color: var(--color-stopped-fg) !important;
  font-weight: 700;
}

.excel-grid-table td.status-pending-cell {
  background-color: var(--color-pending-bg) !important;
  color: var(--color-pending-fg) !important;
  font-weight: 400;
}

/* 加载状态与加载骨架 */
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 250px;
  color: var(--text-secondary);
  gap: 1rem;
}

.spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 3px solid rgba(255, 255, 255, 0.05);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 1s infinite linear;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 移动端特殊适配 */
@media (max-width: 640px) {
  .container {
    padding: 1.5rem 1rem;
  }
  .app-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  .logo-area h1 {
    font-size: 1.8rem;
  }
  .dashboard-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .filter-controls {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
  }
  .btn-group {
    justify-content: space-between;
  }
  .filter-btn {
    flex-grow: 1;
    text-align: center;
    padding: 0.5rem;
  }
  .select-wrapper select {
    width: 100%;
  }
  .card-footer {
    grid-template-columns: 1fr;
  }
  .modal-container {
    height: 95vh;
    border-radius: 16px;
  }
  .modal-header {
    padding: 1rem 1.2rem;
  }
  .modal-content {
    padding: 1rem 1.2rem;
  }
}

```

---

## File: web/app.js
```javascript
// ==========================================================================
// 香港一手新盘销控中心 - 前端核心逻辑 (Vanilla JS)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // DOM 元素引用
  const lastUpdatedBadge = document.getElementById('lastUpdatedBadge');
  const statProjects = document.getElementById('statProjects');
  const statUnits = document.getElementById('statUnits');
  const statSoldRate = document.getElementById('statSoldRate');
  const statOnSale = document.getElementById('statOnSale');
  
  const searchInput = document.getElementById('searchInput');
  const regionButtons = document.querySelectorAll('#regionFilter .filter-btn');
  const districtSelect = document.getElementById('districtSelect');
  const projectGrid = document.getElementById('projectGrid');
  
  const previewModal = document.getElementById('previewModal');
  const modalProjectTitle = document.getElementById('modalProjectTitle');
  const modalProjectSubtitle = document.getElementById('modalProjectSubtitle');
  const closeModalBtn = document.getElementById('closeModalBtn');
  
  const buildingTabs = document.getElementById('buildingTabs');
  const gridRenderArea = document.getElementById('gridRenderArea');
  
  // 楼栋统计元素
  const bStatTotal = document.getElementById('bStatTotal');
  const bStatSale = document.getElementById('bStatSale');
  const bStatPriced = document.getElementById('bStatPriced');
  const bStatSold = document.getElementById('bStatSold');
  const bStatStopped = document.getElementById('bStatStopped');

  // 全局数据状态
  let allProjects = [];
  let globalStats = {};
  let activeRegion = 'all';
  let activeDistrict = 'all';
  let searchQuery = '';

  // 1. 初始化，获取数据索引
  async function init() {
    try {
      const response = await fetch('data.json');
      if (!response.ok) {
        throw new Error('未找到元数据文件 data.json，请先运行 build_web.py 脚本生成数据库。');
      }
      const data = await response.json();
      allProjects = data.projects || [];
      globalStats = data.global_stats || {};
      
      // 更新大屏统计数据
      updateDashboard();
      // 初始化商圈下拉列表
      populateDistricts();
      // 渲染项目卡片列表
      renderProjects();
      
      // 注册事件监听
      setupEventListeners();
    } catch (error) {
      console.error(error);
      projectGrid.innerHTML = `
        <div class="no-results">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <h3>数据加载失败</h3>
          <p>${error.message}</p>
        </div>
      `;
    }
  }

  // 2. 更新大屏看板
  function updateDashboard() {
    if (globalStats.last_updated) {
      // 格式化更新时间显示
      lastUpdatedBadge.textContent = `上次更新: ${globalStats.last_updated}`;
    }
    statProjects.textContent = globalStats.total_projects || 0;
    statUnits.textContent = (globalStats.total_units || 0).toLocaleString();
    statSoldRate.textContent = `${globalStats.overall_sold_rate || 0}%`;
    statOnSale.textContent = (globalStats.total_sale || 0).toLocaleString();
  }

  // 3. 构建商圈下拉列表
  function populateDistricts() {
    // 过滤出符合当前 Region 区域的所有商圈
    const districts = new Set();
    allProjects.forEach(proj => {
      if (activeRegion === 'all' || proj.region === activeRegion) {
        districts.add(proj.district);
      }
    });

    // 重新填充下拉框
    districtSelect.innerHTML = '<option value="all">所有商圈</option>';
    Array.from(districts).sort().forEach(dist => {
      const option = document.createElement('option');
      option.value = dist;
      option.textContent = dist;
      if (activeDistrict === dist) {
        option.selected = true;
      }
      districtSelect.appendChild(option);
    });
    
    // 如果之前选中的商圈在过滤后不存在了，重置为 all
    if (activeDistrict !== 'all' && !districts.has(activeDistrict)) {
      activeDistrict = 'all';
      districtSelect.value = 'all';
    }
  }

  // 4. 事件监听器配置
  function setupEventListeners() {
    // 搜索输入过滤
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.trim().toLowerCase();
      renderProjects();
    });

    // 区域 Tab 切换
    regionButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        regionButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeRegion = btn.dataset.region;
        
        // 区域变动时重新过滤并重置商圈列表
        populateDistricts();
        renderProjects();
      });
    });

    // 商圈下拉框切换
    districtSelect.addEventListener('change', (e) => {
      activeDistrict = e.target.value;
      renderProjects();
    });

    // 模态弹窗关闭事件
    closeModalBtn.addEventListener('click', closePreviewModal);
    
    // 点击遮罩层关闭模态弹窗
    previewModal.addEventListener('click', (e) => {
      if (e.target === previewModal) {
        closePreviewModal();
      }
    });

    // ESC 键关闭模态弹窗
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && previewModal.classList.contains('open')) {
        closePreviewModal();
      }
    });
  }

  // 5. 渲染项目列表
  function renderProjects() {
    projectGrid.innerHTML = '';

    // 执行多重交叉过滤
    const filtered = allProjects.filter(proj => {
      // 1. 区域过滤
      if (activeRegion !== 'all' && proj.region !== activeRegion) return false;
      // 2. 商圈过滤
      if (activeDistrict !== 'all' && proj.district !== activeDistrict) return false;
      // 3. 搜索框过滤（匹配名称、区域、商圈）
      if (searchQuery) {
        const matchesName = proj.name.toLowerCase().includes(searchQuery);
        const matchesRegion = proj.region.toLowerCase().includes(searchQuery);
        const matchesDistrict = proj.district.toLowerCase().includes(searchQuery);
        if (!matchesName && !matchesRegion && !matchesDistrict) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      projectGrid.innerHTML = `
        <div class="no-results">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <h3>无匹配楼盘</h3>
          <p>请尝试其他搜索词或切换区域分类</p>
        </div>
      `;
      return;
    }

    // 动态生成项目卡片
    filtered.forEach(proj => {
      const card = document.createElement('article');
      card.className = 'project-card';
      
      const stats = proj.stats || { total: 0, sold: 0, sale: 0, priced: 0, stopped: 0, pending: 0, sold_rate: 0 };
      
      card.innerHTML = `
        <div class="card-header">
          <div class="card-meta">
            <span class="badge badge-region">${proj.region}</span>
            <span class="badge badge-district">${proj.district}</span>
          </div>
          <h3 class="project-title">${proj.name}</h3>
        </div>
        
        <div class="card-body">
          <!-- 去化率进度条 -->
          <div class="sold-progress-area">
            <div class="progress-info">
              <span class="progress-label">去化进度</span>
              <span class="progress-val">${stats.sold_rate}%</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" style="width: ${stats.sold_rate}%"></div>
            </div>
          </div>
          
          <!-- 详细套数统计 -->
          <div class="card-stats">
            <div class="stat-item sold-count">
              <span class="lbl">已售单位</span>
              <span class="val">${stats.sold}套</span>
            </div>
            <div class="stat-item sale-count">
              <span class="lbl">在售 (Sale)</span>
              <span class="val">${stats.sale}套</span>
            </div>
            <div class="stat-item">
              <span class="lbl">已定价未售</span>
              <span class="val">${stats.priced}套</span>
            </div>
            <div class="stat-item">
              <span class="lbl">总规划套数</span>
              <span class="val">${stats.total}套</span>
            </div>
          </div>
        </div>
        
        <div class="card-footer">
          <button class="btn btn-primary btn-preview" data-filename="${proj.filename}" data-name="${proj.name}" data-region="${proj.region}" data-district="${proj.district}">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            在线预览
          </button>
          
          <a class="btn btn-secondary" href="files/${proj.filename}" download="${proj.filename}">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            下载 Excel
          </a>
        </div>
      `;
      
      projectGrid.appendChild(card);
    });

    // 绑定在线预览按钮事件
    const previewButtons = projectGrid.querySelectorAll('.btn-preview');
    previewButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const dataset = btn.dataset;
        openPreviewModal(dataset.filename, dataset.name, dataset.region, dataset.district);
      });
    });
  }

  // 6. 打开在线预览 Modal 弹窗
  function openPreviewModal(filename, projectName, region, district) {
    modalProjectTitle.textContent = projectName;
    modalProjectSubtitle.textContent = `${region} • ${district} • 销控数据预览`;
    
    // 清空旧数据，展示 Loading Spinner
    buildingTabs.innerHTML = '';
    gridRenderArea.innerHTML = `
      <div class="loading-spinner">
        <div class="spinner"></div>
        <p>正在解析 Excel 楼栋数据，请稍候...</p>
      </div>
    `;
    resetBuildingStatsPanel();

    previewModal.classList.add('open');
    document.body.style.overflow = 'hidden'; // 阻止背景滚动

    // 异步下载并解析 Excel 文件
    fetchExcelAndRender(`files/${filename}`);
  }

  // 7. 关闭模态弹窗
  function closePreviewModal() {
    previewModal.classList.remove('open');
    document.body.style.overflow = '';
  }

  // 重置楼栋统计仪表板
  function resetBuildingStatsPanel() {
    bStatTotal.textContent = '-';
    bStatSale.textContent = '-';
    bStatPriced.textContent = '-';
    bStatSold.textContent = '-';
    bStatStopped.textContent = '-';
  }

  // 8. Fetch Excel 文件并使用 SheetJS 解析
  async function fetchExcelAndRender(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('下载 Excel 文件失败，该文件可能不存在于服务器上。');
      }
      
      const arrayBuffer = await response.arrayBuffer();
      // 使用 SheetJS 解析 Excel
      const workbook = XLSX.read(arrayBuffer, { type: 'array' });
      
      // 过滤出除了"销控汇总明细"以外的所有 Tab 页（代表各楼栋）
      const sheetNames = workbook.SheetNames.filter(name => name !== "销控汇总明细");
      
      if (sheetNames.length === 0) {
        // 如果没有其他表，则 fallback 使用第一张表
        sheetNames.push(workbook.SheetNames[0]);
      }
      
      // 动态生成楼栋 Tab 按钮
      sheetNames.forEach((sheetName, index) => {
        const btn = document.createElement('button');
        btn.className = `tab-btn ${index === 0 ? 'active' : ''}`;
        // 去除名字末尾可能包含的“销控表”字样以精简显示
        btn.textContent = sheetName.replace(' 销控表', '');
        btn.dataset.sheet = sheetName;
        
        btn.addEventListener('click', () => {
          buildingTabs.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          renderSheetGrid(workbook.Sheets[sheetName]);
        });
        
        buildingTabs.appendChild(btn);
      });
      
      // 默认渲染第一个楼栋网格
      renderSheetGrid(workbook.Sheets[sheetNames[0]]);
      
    } catch (error) {
      console.error(error);
      gridRenderArea.innerHTML = `
        <div class="no-results" style="border: none; padding: 2rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:3rem; height:3rem;">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <h3>解析 Excel 失败</h3>
          <p>${error.message}</p>
        </div>
      `;
    }
  }

  // 9. 渲染具体的楼栋网格图 HTML 结构
  function renderSheetGrid(sheet) {
    gridRenderArea.innerHTML = '';
    
    // 转换为 2D 数组（保留空值以便定位格子）
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" });
    if (rows.length === 0) {
      gridRenderArea.innerHTML = '<p style="color:var(--text-secondary); text-align:center; width:100%;">本工作表无数据</p>';
      return;
    }

    // 楼栋销控网格解析与重构：
    // 行索引定位：
    // 1. 寻找表头行，通常在第 5 行 (index 4)，其第一个单元格是“楼层\房号”或类似的文字。
    let headerRowIndex = 4; // 默认第 5 行为表头
    for (let r = 0; r < rows.length; r++) {
      if (rows[r] && rows[r][0] && (String(rows[r][0]).includes('楼层') || String(rows[r][0]).includes('/') || String(rows[r][0]).includes('F'))) {
        headerRowIndex = r;
        break;
      }
    }

    // 2. 统计当前楼栋各状态套数 (通过扫描 headerRowIndex 以下的数据区)
    let bTotal = 0;
    let bSold = 0;
    let bSale = 0;
    let bPriced = 0;
    let bStopped = 0;

    for (let r = headerRowIndex + 1; r < rows.length; r++) {
      const row = rows[r];
      if (!row || row[0] === "" || row[0] === undefined) continue; // 空行跳过
      
      for (let c = 1; c < row.length; c++) {
        const val = String(row[c] || '').trim();
        if (!val) continue; // 空白单元格（如电梯/走道）
        
        bTotal++;
        if (val.includes('(在售)')) {
          bSale++;
        } else if (val.includes('(已定价未售)')) {
          bPriced++;
        } else if (val.includes('(暂停销售)')) {
          bStopped++;
        } else if (val.includes('(待售)')) {
          // 待售不算入这几个高亮面板，也可以并入 default
        } else {
          // 已售的特点是第四行是成交日期如 (26年-06月)
          // 只要存在内容，且不是以上几种情况，就属于已售
          bSold++;
        }
      }
    }

    // 更新楼栋去化面板值
    bStatTotal.textContent = `${bTotal} 套`;
    bStatSale.textContent = `${bSale} 套`;
    bStatPriced.textContent = `${bPriced} 套`;
    bStatSold.textContent = `${bSold} 套`;
    bStatStopped.textContent = `${bStopped} 套`;

    // 3. 构建 HTML Table
    const table = document.createElement('table');
    table.className = 'excel-grid-table';
    
    // 渲染表头 (Columns Header)
    const thead = document.createElement('thead');
    const headerRow = rows[headerRowIndex] || [];
    const trHead = document.createElement('tr');
    
    headerRow.forEach((cellVal, cIndex) => {
      // 最后一列或中间某些列如果全是空白，可能多余，这里保留全部原始定义宽度
      const th = document.createElement('th');
      th.textContent = cellVal !== undefined ? String(cellVal).trim() : '';
      trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    table.appendChild(thead);
    
    // 渲染数据行 (Body Rows)
    const tbody = document.createElement('tbody');
    for (let r = headerRowIndex + 1; r < rows.length; r++) {
      const row = rows[r];
      if (!row || row[0] === "" || row[0] === undefined) continue; // 忽略后方多余的空行
      
      const tr = document.createElement('tr');
      
      // 第一列是楼层列
      const tdFloor = document.createElement('td');
      tdFloor.className = 'grid-header-cell';
      tdFloor.textContent = String(row[0] || '').trim();
      tr.appendChild(tdFloor);
      
      // 后续列为房号单元格
      for (let c = 1; c < headerRow.length; c++) {
        const td = document.createElement('td');
        const cellVal = String(row[c] || '').trim();
        
        if (!cellVal) {
          // 没有房号，代表电梯、走道或空洞，设置置灰类名
          td.className = 'grid-empty-cell';
          td.innerHTML = '';
        } else {
          // 解析内容填充
          td.innerHTML = cellVal; // 保留换行（CSS中使用了 white-space: pre-line）
          
          // 判断销售状态分配样式类名
          if (cellVal.includes('(在售)')) {
            td.className = 'status-sale-cell';
          } else if (cellVal.includes('(已定价未售)')) {
            td.className = 'status-priced-cell';
          } else if (cellVal.includes('(暂停销售)')) {
            td.className = 'status-stopped-cell';
          } else if (cellVal.includes('(待售)')) {
            td.className = 'status-pending-cell';
          } else {
            // 已售状态 (XX年-XX月)
            td.className = 'status-sold-cell';
          }
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    gridRenderArea.appendChild(table);
  }

  // 启动应用程序
  init();
});

```

---

