import os
import requests
import json
import re
import fitz

# 1. 模拟 Token 和详情拉取
r = requests.get('https://www.hkp.com.hk/zh-hk/list/new-property/')
token = json.loads(re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text).group(1))['props']['pageProps']['userToken']
api_headers = {'Authorization': f'Bearer {token}'}

# 拉取详情
d = requests.get('https://data.hkp.com.hk/info/v1/new-properties/P000001130', headers=api_headers).json()
detail_data = d['result'] if 'result' in d else d

# 2. 运行 PDF 提取
from scrape_hkp_sales_control import get_henley3_pdf_data, normalize_bname

henley3_pdf_db = get_henley3_pdf_data(detail_data, api_headers)
print(f"成功载入 PDF 数据库，共有 {len(henley3_pdf_db)} 条记录。")

# 3. 拉取 3B 栋的单位明细 API
# 3B栋 ID: B000096842
b_res = requests.get("https://data.hkp.com.hk/info/v1/new-property/transactions/buildings/B000096842", headers=api_headers).json()
b_units = b_res['result'] if 'result' in b_res else b_res

# 寻找 15楼 B室
for u in b_units:
    floor = u.get('floor')
    flat = u.get('flat')
    if str(floor) == "15" and flat == "B":
        print("\n找到 API 原始单位:")
        print("  floor:", floor)
        print("  flat:", flat)
        print("  price (API):", u.get('price'))
        print("  is_tender (API):", u.get('is_tender'))
        
        # 模拟爬虫里的计算
        price = u.get('price')
        net_area = u.get('area') or 0
        bname = "3B座"
        
        # 爬虫局部计算
        norm_b = normalize_bname(bname).replace("座", "")
        norm_floor = str(floor).strip()
        norm_flat = str(flat).strip()
        pdf_key = (norm_b, norm_floor, norm_flat)
        
        print(f"\n匹配 key: {pdf_key}")
        print(f"是否在 PDF 数据库中: {pdf_key in henley3_pdf_db}")
        
        if pdf_key in henley3_pdf_db:
            pdf_info = henley3_pdf_db[pdf_key]
            print("\nPDF 中的精算数据:")
            for k, v in pdf_info.items():
                print(f"  {k}: {v}")
                
            # 执行覆写
            price = pdf_info["original_price"]
            discount_price = pdf_info["discount_price"]
            discount_percent_str = pdf_info["discount_percent_str"]
            payment_method = pdf_info["payment_method"]
            
            print("\n覆写后的值:")
            print("  price:", price)
            print("  discount_price:", discount_price)
            print("  discount_percent_str:", discount_percent_str)
            print("  payment_method:", payment_method)
