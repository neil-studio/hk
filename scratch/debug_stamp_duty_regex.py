import fitz
import re

pdf_path = "scratch/henley_1_pl_7.pdf"
block = "2"
floor = 10
flat = "A"

def is_floor_in_chunk_debug(floor, chunk):
    if not chunk:
        return False
    c_clean = chunk.replace(" ", "").replace("楼", "樓").upper()
    floor_str = str(floor).strip()
    
    range_pattern = r'(\d+)(?:樓|/F)(?:至|至|-|–|—)(\d+)(?:樓|/F)'
    ranges = re.findall(range_pattern, c_clean)
    print(f"    [正则Ranges]: {ranges} | c_clean: {c_clean[:120]}...")
    if ranges:
        for r_min, r_max in ranges:
            try:
                if int(r_min) <= int(floor) <= int(r_max):
                    print(f"      -> 命中区间: {r_min} <= {floor} <= {r_max}")
                    return True
            except ValueError:
                pass
                
    if "所有樓" in c_clean or "各樓" in c_clean or "所有單位" in c_clean:
        print("      -> 命中全局")
        return True
        
    num_matches = re.findall(r'\d+', c_clean)
    if floor_str in num_matches:
        print(f"      -> 命中精确数字: {floor_str} in {num_matches}")
        return True
        
    return False

doc = fitz.open(pdf_path)
page = doc.load_page(11)
text = page.get_text("text")
print(f"🔍 正在测试: 2座 {floor}楼 {flat}单位 的印花税代缴资格...")
lines = text.split("\n")
block_pattern = f"第{block}座"
for idx, line in enumerate(lines):
    if block_pattern in line:
        chunk = "\n".join(lines[max(0, idx-5): min(len(lines), idx+30)])
        flat_in = flat in chunk
        print(f"\n[匹配到 {block_pattern} Line {idx}] flat_in_chunk: {flat_in}")
        if flat_in:
            res = is_floor_in_chunk_debug(floor, chunk)
            print(f"  -> result: {res}")
print(f"Total lines on Page 12: {len(lines)}")
for idx, line in enumerate(lines):
    if "第2座" in line:
        print(f"\n[第2座 命中] Line {idx}: {line}")
        start = max(0, idx-5)
        end = min(len(lines), idx+15)
        print("  周围文本:")
        for r_idx in range(start, end):
            marker = "=>" if r_idx == idx else "  "
            print(f"    {marker} {r_idx}: {lines[r_idx]}")
