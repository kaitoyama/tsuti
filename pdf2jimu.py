#!/usr/bin/env python3
"""事務連絡PDF → 簡易テキスト。初回の取り込み専用（結果は人が確認する前提）

対応範囲：MHLW 事務連絡（administrative circulars）
対応範囲外：階層的な通知（→ pdf2tsuchi.py）、Q&A/疑義解釈

  python pdf2jimu.py data/jimu_samples/J1.pdf -o J1.jimu.txt

事務連絡の構造：
  - 1ページ目: 表紙（宛先、発出課、Vol、日付）
  - 2ページ目〜: 本文（事務連絡ヘッダー、日付、宛先、発出課、件名、本文段落）
"""
import argparse
import re
import pdfplumber


def extract_metadata(pdf):
    """Extract metadata from cover and main body pages"""
    meta = {"種別": "事務連絡"}
    
    # Page 1: Cover page
    if len(pdf.pages) > 0:
        cover = pdf.pages[0].extract_text() or ""
        
        # Vol (e.g., "Vol.1541")
        vol_match = re.search(r"Vol\.?\s*(\d+)", cover)
        if vol_match:
            meta["Vol"] = vol_match.group(1)
    
    # Page 2: Main body (事務連絡 header with structured format)
    if len(pdf.pages) > 1:
        body = pdf.pages[1].extract_text() or ""
        lines = [l.strip() for l in body.split("\n")]
        
        # Parse structured header: 事務連絡 / date / recipients / issuer / subject
        jimu_idx = None
        for i, line in enumerate(lines):
            if re.match(r"^事\s*務\s*連\s*絡$", line):
                jimu_idx = i
                break
        
        if jimu_idx is not None:
            # Line after 事務連絡 is date (may have spaces: "令 和 ８年 ９月 ８ 日")
            if jimu_idx + 1 < len(lines):
                date_line = re.sub(r"\s+", "", lines[jimu_idx + 1])
                date_match = re.search(r"令和[０-９0-9]+年[０-９0-9]+月[０-９0-9]+日", date_line)
                if date_match:
                    meta["日付"] = date_match.group(0)
            
            # Find line with 御中, then look for issuer (starts with 厚生労働省)
            onchu_idx = None
            for i in range(jimu_idx + 2, min(jimu_idx + 15, len(lines))):
                if "御中" in lines[i]:
                    onchu_idx = i
                    break
            
            if onchu_idx is not None:
                # Issuer is the line starting with "厚生労働省" after 御中
                issuer_idx = None
                for i in range(onchu_idx + 1, min(onchu_idx + 8, len(lines))):
                    line_clean = re.sub(r"\s+", "", lines[i])
                    if line_clean.startswith("厚生労働省"):
                        meta["発出課"] = line_clean
                        issuer_idx = i
                        break
                
                # Subject is next non-empty line after issuer
                if issuer_idx is not None:
                    for i in range(issuer_idx + 1, min(issuer_idx + 5, len(lines))):
                        subject = lines[i].strip()
                        # Subject should be substantial and not start with body opening phrases
                        if subject and len(subject) > 5 and not re.match(r"^(日頃|平素|今般|つきまして)", subject):
                            meta["件名"] = subject
                            break
    
    return meta


def extract_body(pdf, start_page=1):
    """Extract body paragraphs starting from specified page (0-indexed)"""
    paragraphs = []
    
    for page_num in range(start_page, len(pdf.pages)):
        text = pdf.pages[page_num].extract_text() or ""
        
        # Skip page if it's mostly the header (for page 2)
        if page_num == 1:
            # Find the start of actual content (after 件名)
            # Look for common body starters like "日頃より" or "記"
            lines = text.split("\n")
            content_start = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Start after finding typical body opening
                if re.search(r"日頃より|平素より|今般|つきましては|下記|記$", stripped):
                    content_start = i
                    break
            
            if content_start > 0:
                text = "\n".join(lines[content_start:])
        
        # Clean and split into paragraphs
        # Remove page numbers (digits at end of page)
        text = re.sub(r"\n\s*[0-9０-９]+\s*$", "", text, flags=re.MULTILINE)
        
        # Split by double newlines or significant indentation changes
        # For now, simple approach: keep original line structure
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        # Group consecutive non-empty lines into paragraphs
        current_para = ""
        for line in lines:
            # Check if this is a new paragraph marker (e.g., starts with １．or 記)
            if re.match(r"^[０-９0-9１-９]+[．\.]|^記$|^【", line) and current_para:
                paragraphs.append(current_para)
                current_para = line
            else:
                if current_para:
                    current_para += line
                else:
                    current_para = line
        
        if current_para:
            paragraphs.append(current_para)
    
    return paragraphs


def parse(pdf_path):
    """Parse 事務連絡 PDF and extract metadata + body"""
    pdf = pdfplumber.open(pdf_path)
    
    metadata = extract_metadata(pdf)
    body = extract_body(pdf, start_page=1)  # Start from page 2 (index 1)
    
    pdf.close()
    return metadata, body


def save(output_path, metadata, body):
    """Save to YAML front-matter + body text format"""
    import yaml
    
    # Filter out None/empty values
    clean_meta = {k: v for k, v in metadata.items() if v}
    
    fm = yaml.safe_dump(clean_meta, allow_unicode=True, sort_keys=False, width=200)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(fm)
        f.write("---\n\n")
        for para in body:
            f.write(para)
            f.write("\n\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Convert MHLW 事務連絡 PDF to structured text")
    ap.add_argument("pdf", help="Input PDF path")
    ap.add_argument("-o", "--output", required=True, help="Output text file path")
    ap.add_argument("--vol", help="Override Vol number if not detected")
    ap.add_argument("--date", help="Override date if not detected (e.g., 2026-09-08)")
    
    args = ap.parse_args()
    
    metadata, body = parse(args.pdf)
    
    # Apply overrides
    if args.vol:
        metadata["Vol"] = args.vol
    if args.date:
        metadata["日付"] = args.date
    
    save(args.output, metadata, body)
    
    print(f"Extracted 事務連絡:")
    print(f"  種別: {metadata.get('種別')}")
    print(f"  Vol: {metadata.get('Vol', '(未検出)')}")
    print(f"  日付: {metadata.get('日付', '(未検出)')}")
    print(f"  発出課: {metadata.get('発出課', '(未検出)')}")
    print(f"  件名: {metadata.get('件名', '(未検出)')[:50]}..." if metadata.get('件名') and len(metadata.get('件名', '')) > 50 else f"  件名: {metadata.get('件名', '(未検出)')}")
    print(f"  Body: {len(body)} paragraphs")
    print(f"\nSaved to: {args.output}")
