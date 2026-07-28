import os
import fitz
import re

pdf_dir = "scratch/henley_pdfs"
price_lists = ["6B", "3O", "4M", "5L", "1N", "2Q", "4L"]

def clean_str(val):
    if val is None:
        return ""
    return str(val).replace("\n", "").replace(" ", "").strip()

# 1. 提取所有房源的原售价和面积
pdf_flat_database = {}
for name in price_lists:
    path = os.path.join(pdf_dir, f"price_list_{name}.pdf")
    if not os.path.exists(path):
        continue
    doc = fitz.open(path)
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        tables = page.find_tables()
        if not tables:
            continue
        for table in tables:
            df = table.to_pandas()
            if len(df.columns) < 5:
                continue
            for row_idx, row in df.iterrows():
                col0 = clean_str(row.iloc[0])
                col1 = clean_str(row.iloc[1])
                col2 = clean_str(row.iloc[2])
                col3 = clean_str(row.iloc[3])
                col4 = clean_str(row.iloc[4])
                
                if "大廈" in col0 or "Block" in col0 or "樓層" in col1 or "Floor" in col1:
                    continue
                if "座" not in col0:
                    continue
                if not re.match(r'^\d+$', col1):
                    continue
                if not re.match(r'^[A-Z0-9]+$', col2):
                    continue
                price_str = col4.replace(",", "").replace("$", "").replace("元", "")
                try:
                    price = int(price_str)
                except ValueError:
                    continue
                area_match = re.search(r'\((\d+)\)', col3)
                area = 0
                if area_match:
                    area = int(area_match.group(1))
                else:
                    area_nums = re.findall(r'\d+', col3.replace(",", ""))
                    if area_nums:
                        area = int(area_nums[-1])
                
                b_match = re.search(r'(\d+)([A-Za-z]?)', col0)
                bname = b_match.group(1) + b_match.group(2) if b_match else col0
                floor = col1.strip()
                flat = col2.strip()
                
                key = (bname, floor, flat)
                if key not in pdf_flat_database:
                    pdf_flat_database[key] = {
                        "price_list": name,
                        "original_price": price,
                        "area_sqft": area,
                        "pdf_path": path
                    }

# 从价印花税 Scale 2 计算函数 (2023年微调版本)
def calculate_scale2_stamp_duty(price):
    if price <= 3000000:
        return 100
    elif price <= 3528000:
        return 100 + (price - 3000000) * 0.10
    elif price <= 4500000:
        return price * 0.015
    elif price <= 4935000:
        return 67500 + (price - 4500000) * 0.10
    elif price <= 6000000:
        return price * 0.0225
    elif price <= 6642900:
        return 135000 + (price - 6000000) * 0.10
    elif price <= 9000000:
        return price * 0.03
    elif price <= 10080000:
        return 270000 + (price - 9000000) * 0.10
    elif price <= 20000000:
        return price * 0.0375
    elif price <= 21739000:
        return 750000 + (price - 20000000) * 0.10
    else:
        return price * 0.0425

# 2. 检查印花税代缴适用性
def check_stamp_duty_eligibility(pdf_path, block, floor, flat):
    doc = fitz.open(pdf_path)
    # 遍历后半部的优惠页
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text("text")
        # 寻找包含代缴印花税的页码
        if "代繳從價印花稅" in text or "Ad Valorem Stamp Duty" in text:
            # 检查此页是否包含特定单位段落，例如 "第3B座"
            block_pattern = f"第{block}座"
            if block_pattern in text:
                # 寻找紧邻的 Flat 和 Floor 段落以进行高保真匹配
                lines = text.split("\n")
                for idx, line in enumerate(lines):
                    if block_pattern in line:
                        # 查找附近大约 20 行，看看是否包含 flat 以及 floor 列表
                        chunk = "\n".join(lines[max(0, idx-5): min(len(lines), idx+30)])
                        # 楼层可能是一组数字，如 "12, 15, 18, 20"
                        if flat in chunk:
                            # 提取出楼层数字进行比对
                            num_matches = re.findall(r'\d+', chunk)
                            if str(floor) in num_matches:
                                return True
    return False

# 3. 对 3B-15B 进行高精折算
target = ("3B", "15", "B")
if target in pdf_flat_database:
    info = pdf_flat_database[target]
    orig_price = info["original_price"]
    area = info["area_sqft"]
    pl_name = info["price_list"]
    pdf_path = info["pdf_path"]
    
    # 3.1 基础现金折扣
    direct_discount_rate = 0.035  # 大户型 3.5%
    if pl_name == "4L":
        direct_discount_rate = 0.05
        if area <= 420:
            direct_discount_rate = 0.125
    else:
        if area <= 420:
            direct_discount_rate = 0.09  # 小户型 9%
        
    contract_price = int(orig_price * (1 - direct_discount_rate))
    # 合同价通常向下取整至百位数
    contract_price = (contract_price // 100) * 100
    
    # 3.2 印花税代缴代折
    has_stamp_duty_benefit = check_stamp_duty_eligibility(pdf_path, target[0], target[1], target[2])
    stamp_duty = 0
    if has_stamp_duty_benefit:
        stamp_duty = calculate_scale2_stamp_duty(contract_price)
        
    # 折实售价 (原售价 - 付款折扣 - 印花税代缴)
    final_disc_price = contract_price - stamp_duty
    final_disc_price_rounded = int((final_disc_price // 100) * 100)
    
    # 换算为总折扣比率
    total_benefit_amount = orig_price - final_disc_price_rounded
    total_benefit_rate = total_benefit_amount / orig_price
    
    print("\n==================================================")
    print(f"       The Henley III {target[0]}座-{target[1]}楼-{target[2]}室 精算明细")
    print("==================================================")
    print(f"  所属价单号: 價單 {pl_name} 號")
    print(f"  住宅实用面积: {area} 平方呎")
    print(f"  1. 住宅官方售价 (原价): ${orig_price:,} 元")
    print(f"  2. 现金付款计划 (减 3.5%): -${int(orig_price * direct_discount_rate):,} 元")
    print(f"  3. 合同售价 (临约签定价): ${contract_price:,} 元")
    print(f"  4. 印花税代缴代折优惠: {'是' if has_stamp_duty_benefit else '否'}")
    if has_stamp_duty_benefit:
        print(f"     -> 代缴从价印花税金 (Scale 2): -${int(stamp_duty):,} 元")
    print(f"  ------------------------------------------------")
    print(f"  🔥 最终最高折实售价: ${final_disc_price_rounded:,} 元")
    print(f"  🔥 最终折实实用呎价: ${int(final_disc_price_rounded / area):,}/呎")
    print(f"  🔥 合计最惠优惠总折扣: {total_benefit_rate * 100:.3f}%")
    print("==================================================")
else:
    print(f"未找到目标房源 {target}")
