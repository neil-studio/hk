import os
import fitz
import re

pdf_dir = "九龙-启德-The Henley III/pdfs"
price_lists = ["1N", "2Q", "3O", "4L", "4M", "5L", "6B"]

print("=========================================")
print("Analyzing Henley III Discount Conditions")
print("=========================================")

for name in price_lists:
    pdf_path = os.path.join(pdf_dir, f"price_list_{name}.pdf")
    if not os.path.exists(pdf_path):
        print(f"Warning: {pdf_path} not found.")
        continue
        
    doc = fitz.open(pdf_path)
    print(f"\n=================== Price List: {name} ===================")
    
    # 1. Look for Cash Payment Plan or other discount rates in text
    discounts_found = []
    stamp_duty_pages = []
    other_noteworthy_clauses = []
    
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text("text")
        
        # Search for payment methods and percentage
        # Let's extract lines that mention 90 days completion, cash payment, or similar
        lines = text.split("\n")
        for idx, line in enumerate(lines):
            line_clean = line.replace(" ", "")
            # Check for cash payment plan discount
            if ("現金付款" in line_clean or "Cash Payment" in line_clean) and ("%" in line_clean or "減" in line_clean):
                context = " | ".join([l.strip() for l in lines[max(0, idx-1): min(len(lines), idx+3)] if l.strip()])
                discounts_found.append(context)
            if "代繳從價印花稅" in line_clean or "Ad Valorem Stamp Duty" in line_clean:
                if page_idx+1 not in stamp_duty_pages:
                    stamp_duty_pages.append(page_idx+1)
                # Print the towers and units mentioned on this page
                chunk = "\n".join(lines[max(0, idx-5): min(len(lines), idx+35)])
                # Clean up and find tower and floor info
                other_noteworthy_clauses.append((page_idx+1, chunk))

    # Print payment options
    print("  [付款计划 / 折扣率]")
    if discounts_found:
        for d in set(discounts_found[:5]):
            print(f"    - {d}")
    else:
        print("    - No cash payment discount pattern found.")
        
    # Print stamp duty eligibility
    print(f"  [印花税代缴条款] (页面: {stamp_duty_pages})")
    if other_noteworthy_clauses:
        for pg, chunk in other_noteworthy_clauses:
            print(f"    --- 页面 {pg} 印花税适用范围片段 ---")
            lines_chunk = [l.strip() for l in chunk.split("\n") if l.strip()]
            for l in lines_chunk:
                if any(kw in l for kw in ["第3B座", "Tower 3B", "3B座", "A", "B", "C", "D", "E", "F", "樓", "Floor"]):
                    print(f"      {l}")
    else:
        print("    - No stamp duty benefit found.")
        
    doc.close()
