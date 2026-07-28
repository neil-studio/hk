import os
import fitz
import re

pdf_dir = "九龙-启德-The Henley III/pdfs"
price_lists = ["1N", "2Q", "3O", "4L", "4M", "5L", "6B"]

def is_floor_in_chunk(floor, chunk):
    c_clean = chunk.replace(" ", "").replace("楼", "樓").upper()
    floor_str = str(floor).strip()
    range_pattern = r'(\d+)(?:樓|/F)(?:至|至|-|–|—)(\d+)(?:樓|/F)'
    ranges = re.findall(range_pattern, c_clean)
    if ranges:
        for r_min, r_max in ranges:
            try:
                if int(r_min) <= int(floor) <= int(r_max):
                    return True
            except ValueError:
                pass
    if "所有樓" in c_clean or "各樓" in c_clean or "所有單位" in c_clean:
        return True
    num_matches = re.findall(r'\d+', c_clean)
    if floor_str in num_matches:
        return True
    return False

for pl in price_lists:
    pdf_path = os.path.join(pdf_dir, f"price_list_{pl}.pdf")
    if not os.path.exists(pdf_path):
        print(f"價單 {pl} 不存在于本地。")
        continue
    doc = fitz.open(pdf_path)
    
    print(f"\n價單 {pl} 號:")
    sd_rules = []
    
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text("text")
        if "代繳從價印花稅" in text or "Ad Valorem Stamp Duty" in text:
            # 找到印花税条款页面，寻找 tower and units
            lines = text.split("\n")
            for idx, line in enumerate(lines):
                if "第3B座" in line or "Tower 3B" in line:
                    # 查找前后 10 行以组合完整的信息
                    chunk = "\n".join(lines[max(0, idx-5): min(len(lines), idx+30)])
                    # 我们希望打印出这个 chunk 中可能包含的 Flat and Floors
                    # 比如 Flat B, Floor 16, 17, 33, 35楼 等
                    sd_rules.append((page_idx+1, chunk))
                    
    if not sd_rules:
        print("  - 未发现代缴印花税条款或不适用")
    else:
        # 整理和去重
        processed_rules = []
        for pnum, rule_txt in sd_rules:
            # 查找 Flat (A, B, C, D, E, F 等) 和楼层
            flats = re.findall(r'\b[A-G]\b', rule_txt)
            # 查找数字
            numbers = re.findall(r'\d+', rule_txt)
            clean_rule = rule_txt.replace('\n', ' | ')
            # 只保留关于 3B座 的关键句
            print(f"  - 页面 {pnum}: ... {clean_rule[:300]} ...")
            
    doc.close()
