#!/usr/bin/env python3
"""Scan the secondhand source folder for Midland Realty PDFs, extract listings and images,
update secondhand_data.json (+ web/secondhand_data.json), and archive processed PDFs."""

import argparse
import datetime
import json
import os
import re
import shutil
import fitz  # PyMuPDF

SOURCE_DIR = "/Users/nb/google/Antigravity/工作/运营/聚焦盘精选盘/二手房源"
ARCHIVE_DIR = os.path.join(SOURCE_DIR, "已导入")
PROJECT_DIR = "/Users/nb/google/Antigravity/工作/运营/价单_正式版"
JSON_PATHS = [
    os.path.join(PROJECT_DIR, "secondhand_data.json"),
    os.path.join(PROJECT_DIR, "web", "secondhand_data.json"),
]
IMAGE_DIRS = [
    os.path.join(PROJECT_DIR, "secondhand_images"),
    os.path.join(PROJECT_DIR, "web", "secondhand_images"),
]

def _render_full_page(doc, page_idx, fname, ref_no, dry_run=False):
    """Render an entire PDF page at 3x resolution (1785x2526 for A4) as JPEG."""
    rel_path = f"secondhand_images/{ref_no}/{fname}"
    if not dry_run:
        pix = doc[page_idx].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        for base_img_dir in IMAGE_DIRS:
            target_dir = os.path.join(base_img_dir, ref_no)
            os.makedirs(target_dir, exist_ok=True)
            pix.save(os.path.join(target_dir, fname), jpg_quality=90)
    return rel_path


def _parse_midland_pdf(pdf_path, sales_person, default_district, dry_run=False):
    """Parse a Midland Realty proposal PDF into listing dicts."""
    doc = fitz.open(pdf_path)
    listings = []
    page_texts = [doc[i].get_text("text") for i in range(len(doc))]

    i = 0
    while i < len(doc):
        txt = page_texts[i]
        m_ref = re.search(r"物業編號[:：]\s*([A-Z0-9]+)", txt)
        if not m_ref or "放盤資料" not in txt:
            i += 1
            continue

        ref_no = m_ref.group(1).strip()
        m_price = re.search(r"放售\s*([\d,.]+)\s*萬", txt)
        price_val = float(m_price.group(1).replace(",", "")) if m_price else 0
        price_text = f"{int(price_val) if price_val.is_integer() else price_val} 万" if price_val else "-"

        m_area = re.search(r"實用面積[:：]\s*([\d,]+)\s*呎\s*\(@\$([\d,]+)呎", txt)
        area = int(m_area.group(1).replace(",", "")) if m_area else 0
        psf_num = int(m_area.group(2).replace(",", "")) if m_area else 0
        psf = f"${psf_num:,}/呎" if psf_num else "-"

        m_layout = re.search(r"戶型[:：]\s*([^\n]+)", txt)
        layout = m_layout.group(1).strip() if m_layout else ""
        if not layout or layout.startswith("更新日期"):
            layout = "待补充"

        m_date = re.search(r"更新日期[:：]\s*(\d{2})/(\d{2})/(\d{4})", txt)
        confirm_date = f"{m_date.group(3)}-{m_date.group(2)}-{m_date.group(1)}" if m_date else datetime.date.today().isoformat()

        # Title line right after 單位詳情
        m_title = re.search(r"單位詳情\s*\n\s*([^\n]+)", txt)
        title_line = m_title.group(1).strip() if m_title else ref_no
        parts = title_line.split()
        estate = " ".join(parts[:2]) if len(parts) >= 3 else title_line
        unit = " ".join(parts[2:]) if len(parts) >= 3 else ""

        detail_img = _render_full_page(doc, i, "detail.jpg", ref_no, dry_run=dry_run)
        plan = detail_img
        photos = [detail_img]
        rent = ""
        status = "待确认"

        # Check if next page is 單位相片 for the same ref_no (handles CJK & Kangxi radical ⽚)
        if i + 1 < len(doc) and ref_no in page_texts[i + 1] and re.search(r"單位相[片⽚]", page_texts[i + 1]):
            photo_txt = page_texts[i + 1]
            m_rent = re.search(r"放租\s*\$([\d,]+)", photo_txt)
            if m_rent:
                rent_num = int(m_rent.group(1).replace(",", ""))
                rent = f"{rent_num / 10000:g}万/月"
                status = "可售可租" if price_val else "出租"
            photos.append(_render_full_page(doc, i + 1, "photos.jpg", ref_no, dry_run=dry_run))
            i += 2
        else:
            i += 1

        listings.append({
            "id": ref_no,
            "district": default_district,
            "estate": estate,
            "unit": unit,
            "source": "美联物业",
            "sourceType": "midland",
            "refNo": ref_no,
            "priceText": price_text,
            "price": int(price_val) if price_val and float(price_val).is_integer() else price_val,
            "psf": psf,
            "psfNum": psf_num,
            "rent": rent,
            "area": area,
            "layout": layout,
            "age": "-",
            "keyInfo": "请核对附注看房安排",
            "carpark": "-",
            "status": status,
            "salesPerson": sales_person,
            "confirmDate": confirm_date,
            "remarks": f"自动导入自 {os.path.basename(pdf_path)}",
            "photos": photos,
            "plan": plan,
        })
    return listings


def _archive_pdf(pdf_path):
    """Move a processed PDF into ARCHIVE_DIR without overwriting existing archives."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    fname = os.path.basename(pdf_path)
    dest = os.path.join(ARCHIVE_DIR, fname)
    if os.path.exists(dest):
        stem, ext = os.path.splitext(fname)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(ARCHIVE_DIR, f"{stem}_{ts}{ext}")
    shutil.move(pdf_path, dest)
    return dest


def main():
    parser = argparse.ArgumentParser(description="Import Midland secondhand PDFs into secondhand_data.json")
    parser.add_argument("--sales-person", default="美联袁新涛", help="Default salesPerson name")
    parser.add_argument("--district", default="何文田", help="Default district if not parsed")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print without writing files or moving PDFs")
    args = parser.parse_args()

    pdfs = sorted(
        os.path.join(SOURCE_DIR, f)
        for f in os.listdir(SOURCE_DIR)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(SOURCE_DIR, f))
    )
    if not pdfs:
        print("没有待导入的 PDF 文件。")
        return

    with open(JSON_PATHS[0], "r", encoding="utf-8") as f:
        existing = json.load(f)
    by_id = {item["id"]: idx for idx, item in enumerate(existing)}

    added, updated = 0, 0
    for pdf in pdfs:
        print(f"解析: {os.path.basename(pdf)}")
        items = _parse_midland_pdf(pdf, args.sales_person, args.district, dry_run=args.dry_run)
        for item in items:
            if item["id"] in by_id:
                existing[by_id[item["id"]]] = item
                updated += 1
            else:
                by_id[item["id"]] = len(existing)
                existing.append(item)
                added += 1
            print(f"  - {item['id']} | {item['estate']} {item['unit']} | {item['priceText']} | 图:{len(item['photos'])}")
        if not args.dry_run and items:
            archived = _archive_pdf(pdf)
            print(f"  -> 已归档至: {archived}")

    if not args.dry_run and (added or updated):
        for jp in JSON_PATHS:
            with open(jp, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        print(f"完成: 新增 {added} 条, 更新 {updated} 条, 总计 {len(existing)} 条。")
    elif args.dry_run:
        print(f"[DRY-RUN] 将新增 {added} 条, 更新 {updated} 条。")


if __name__ == "__main__":
    main()
