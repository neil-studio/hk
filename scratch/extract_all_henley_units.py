import os
import fitz
import re

pdf_dir = "scratch/henley_pdfs"
price_lists = ["6B", "3O", "4M", "5L", "1N", "2Q", "4L"]

def clean_str(val):
    if val is None:
        return ""
    return str(val).replace("\n", "").replace(" ", "").strip()

pdf_flat_database = {}

print("开始从 7 个价单 PDF 中提取所有房源数据...")

for name in price_lists:
    path = os.path.join(pdf_dir, f"price_list_{name}.pdf")
    if not os.path.exists(path):
        print(f"警告: 价单 {name} 不存在于本地，跳过。")
        continue
        
    doc = fitz.open(path)
    extracted_count = 0
    
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        tables = page.find_tables()
        if not tables:
            continue
            
        for table in tables:
            df = table.to_pandas()
            # 识别是否为房源大表：列数应大于等于 5
            if len(df.columns) < 5:
                continue
                
            # 遍历每一行
            for row_idx, row in df.iterrows():
                col0 = clean_str(row.iloc[0])
                col1 = clean_str(row.iloc[1])
                col2 = clean_str(row.iloc[2])
                col3 = clean_str(row.iloc[3])
                col4 = clean_str(row.iloc[4])
                
                # 如果是列头说明行（如包含 "大廈" 或是 "Block"），则跳过
                if "大廈" in col0 or "Block" in col0 or "樓層" in col1 or "Floor" in col1:
                    continue
                    
                # 校验提取出来的值是否符合房源规则：
                # 楼栋通常包含 "座"
                if "座" not in col0:
                    continue
                # 楼层通常为数字
                if not re.match(r'^\d+$', col1):
                    continue
                # 单位通常为单个或两个字母 (如 A, B, C, F1)
                if not re.match(r'^[A-Z0-9]+$', col2):
                    continue
                # 售价应能提取出数字
                price_str = col4.replace(",", "").replace("$", "").replace("元", "")
                try:
                    price = int(price_str)
                except ValueError:
                    continue
                    
                # 面积提取平方呎
                # 面积列通常包含平方米(平方呎)的复合表达，如 "33.118(356)"
                area_match = re.search(r'\((\d+)\)', col3)
                area = 0
                if area_match:
                    area = int(area_match.group(1))
                else:
                    # 有的 PDF 里可能是单独一列平方呎，或者没有括号
                    area_str = col3.replace(",", "")
                    area_nums = re.findall(r'\d+', area_str)
                    if area_nums:
                        area = int(area_nums[-1]) # 取最后一个数字作为平方呎数
                
                # 用正则提取大厦名称，如 "第3B座\nTower3B" -> "3B"
                b_match = re.search(r'(\d+)([A-Za-z]?)', col0)
                if b_match:
                    bname = b_match.group(1) + b_match.group(2)
                else:
                    bname = col0.replace("第", "").replace("座", "").strip()
                    
                floor = col1.strip()
                flat = col2.strip()
                
                key = (bname, floor, flat)
                # 价单可能会有修订版，通常最新的价单（靠前的列表元素）里包含的数据是最新有效的
                if key not in pdf_flat_database:
                    pdf_flat_database[key] = {
                        "price_list": name,
                        "original_price": price,
                        "area_sqft": area
                    }
                    extracted_count += 1

    print(f"  [完成] 从 價單{name} 中共提取了 {extracted_count} 条房源基准原价数据。")

print(f"\n全港价单 PDF 解析完成！共录入独立房源数目: {len(pdf_flat_database)}")

# 3. 检索 3B座15楼B室
target_key = ("3B", "15", "B")
if target_key in pdf_flat_database:
    print(f"\n🎉 成功在数据库中检索到目标单位 3B-15B！")
    print(f"  所属价单: 價單 {pdf_flat_database[target_key]['price_list']} 號")
    print(f"  官方售价 (原价): ${pdf_flat_database[target_key]['original_price']:,} 元")
    print(f"  实用面积: {pdf_flat_database[target_key]['area_sqft']} 平方呎")
else:
    print(f"\n❌ 未在数据库中检索到 3B-15B！")
    # 打印前 5 个房源键作为参考
    print("数据库前 5 个房源样例:")
    for k, v in list(pdf_flat_database.items())[:5]:
        print(f"  {k} -> {v}")
