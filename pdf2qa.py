#!/usr/bin/env python3
"""MHLW Q&A / 疑義解釈 PDF → YAML

対応範囲：Q&A・疑義解釈（問答形式）
対応範囲外：階層的な通知（→ pdf2tsuchi.py）、事務連絡（→ pdf2jimu.py）

  python pdf2qa.py Q1.pdf -o Q1.qa.yaml
"""
import argparse
import re
import pdfplumber
import yaml


def extract_metadata(pdf):
    """Extract metadata from cover page(s)"""
    meta = {}
    
    # Check first page for 介護保険最新情報 cover
    text0 = pdf.pages[0].extract_text() or ""
    text0_norm = re.sub(r"\s+", "", text0)  # Normalize spaces for pattern matching
    
    if "介護保険最新情報" in text0_norm:
        # Extract from page 1 (介護保険最新情報 cover)
        # Look for Vol number (prefer full-width numbers which are the document Vol)
        vol_match = re.search(r"Vol[．.]\s*([１-９０-０]+)", text0)
        if not vol_match:
            vol_match = re.search(r"Vol[．.]\s*([0-9]+)", text0)
        if vol_match:
            vol_num = re.sub(r"\s+", "", vol_match.group(1))
            vol_num = vol_num.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            meta["番号"] = f"Vol.{vol_num}"
        
        # Date from page 1
        date_match = re.search(r"令和[０-９0-9]+年[０-９0-9]+月[０-９0-9]+日", text0)
        if date_match:
            meta["日付"] = date_match.group(0)
        
        # Issuer from page 1
        issuer_match = re.search(r"厚生労働省[^\n\r]+", text0)
        if issuer_match:
            meta["発出元"] = issuer_match.group(0).strip()
        
        # Subject is usually on page 1 in the "今回の内容" section
        subject_match = re.search(r"「([^」]+[Ｑ＆ＡQ&A][^」]*)」", text0)
        if subject_match:
            subject = subject_match.group(1)
            # Clean up newlines in subject
            subject = re.sub(r"\s+", "", subject)
            meta["件名"] = subject
            meta["種別"] = "Q&A"
        
        # Look at page 2 for more details if needed
        if len(pdf.pages) > 1:
            text1 = pdf.pages[1].extract_text() or ""
            # Check for 廃止 notice
            haishi_match = re.search(r"「[^」]+」[^。]*は廃止[^。]*。", text1)
            if haishi_match:
                meta["廃止"] = haishi_match.group(0)
        
        return meta
    
    # Standard 事務連絡 cover (疑義解釈)
    text = text0
    lines = [l.strip() for l in text.split("\n")]
    
    # Find 事務連絡 line
    jimu_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^事\s*務\s*連\s*絡$", line):
            jimu_idx = i
            break
    
    if jimu_idx is not None:
        # Date (next line after 事務連絡)
        if jimu_idx + 1 < len(lines):
            date_line = re.sub(r"\s+", "", lines[jimu_idx + 1])
            date_match = re.search(r"令和[０-９0-9]+年[０-９0-9]+月[０-９0-9]+日", date_line)
            if date_match:
                meta["日付"] = date_match.group(0)
        
        # Issuer (look for 厚生労働省 after 御中)
        onchu_idx = None
        for i in range(jimu_idx + 2, min(jimu_idx + 15, len(lines))):
            if "御中" in lines[i]:
                onchu_idx = i
                break
        
        if onchu_idx:
            for i in range(onchu_idx + 1, min(onchu_idx + 8, len(lines))):
                line_clean = re.sub(r"\s+", "", lines[i])
                if line_clean.startswith("厚生労働省"):
                    meta["発出元"] = line_clean
                    break
        
        # Subject (look for 疑義解釈 in subject)
        for i in range(jimu_idx + 1, min(jimu_idx + 20, len(lines))):
            line = lines[i].strip()
            if "疑義解釈" in line and len(line) > 10:
                meta["件名"] = line
                # Extract 番号 from subject
                num_match = re.search(r"[（(]その[０-９0-9１-９]+[）)]", line)
                if num_match:
                    meta["番号"] = re.sub(r"[（(）)]", "", num_match.group(0))
                meta["種別"] = "疑義解釈"
                break
        
        # Check for 廃止 notice
        full_text = " ".join(lines)
        haishi_match = re.search(r"「[^」]+」[^。]*は廃止[^。]*。", full_text)
        if haishi_match:
            meta["廃止"] = haishi_match.group(0)
    
    return meta


def extract_items(pdf, start_page=1):
    """Extract Q&A items from PDF"""
    items = []
    current_betten = None
    current_midashi = []
    implicit_betten_section = False
    
    # Pre-process all pages: collect full text and remove page markers
    full_text_lines = []
    for page_num in range(start_page, len(pdf.pages)):
        text = pdf.pages[page_num].extract_text() or ""
        lines = text.split("\n")
        for line in lines:
            stripped = line.strip()
            # Skip page numbers and page markers
            if re.match(r"^[0-9０-９]+$", stripped):
                continue
            if re.match(r"^[医歯調介訪看ベ][-－][0-9０-９]+$", stripped):
                continue
            full_text_lines.append(stripped)
    
    # Now parse the concatenated lines
    i = 0
    while i < len(full_text_lines):
        line = full_text_lines[i]
        
        # Explicit 別添 marker
        betten_match = re.match(r"^[（(]別添([０-９0-9１-９]+)[）)]$", line)
        if betten_match:
            current_betten = re.sub(r"[（()）]", "", line)
            current_midashi = []
            implicit_betten_section = False
            i += 1
            continue
        
        # Implicit 別添１: section header ending with 関係 at the start
        # (e.g., "医科診療報酬点数表関係" without preceding （別添１） marker)
        if not current_betten and not implicit_betten_section:
            section_match = re.match(r"^(.+関係)$", line)
            if section_match and len(line) < 60:
                # This is likely the start of implicit 別添１
                current_betten = "別添１"
                implicit_betten_section = True
                i += 1
                continue
        
        # 見出し (【...】)
        midashi_match = re.match(r"^【[^】]+】$", line)
        if midashi_match:
            current_midashi = [line]
            i += 1
            continue
        
        # Sub-heading (○ ...)
        sub_match = re.match(r"^○\s+(.+)$", line)
        if sub_match:
            if len(current_midashi) == 1:
                current_midashi.append(line)
            else:
                current_midashi = [current_midashi[0], line] if current_midashi else [line]
            i += 1
            continue
        
        # Question start (問N, QN, or 問N－M format)
        q_match = re.match(r"^(問[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.*)$", line)
        if q_match:
            q_num = q_match.group(1)
            q_text = q_match.group(2)
            
            # Collect rest of question until answer
            i += 1
            while i < len(full_text_lines):
                next_line = full_text_lines[i]
                # Check if answer starts
                if re.match(r"^[（(]答[）)]\s*", next_line):
                    break
                # Stop at new question, 見出し, or 別添
                if re.match(r"^(問[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+", next_line):
                    break
                if re.match(r"^【[^】]+】$", next_line):
                    break
                if re.match(r"^[（(]?別添[０-９0-9１-９]+[）)]?$", next_line):
                    break
                if re.match(r"^○\s+", next_line):
                    break
                if next_line:
                    q_text += next_line
                i += 1
            
            # Extract answer
            a_paras = []
            if i < len(full_text_lines):
                ans_line = full_text_lines[i]
                ans_match = re.match(r"^[（(]答[）)]\s*(.*)$", ans_line)
                if ans_match:
                    a_text = ans_match.group(1)
                    i += 1
                    
                    # Collect answer paragraphs
                    current_para = a_text
                    while i < len(full_text_lines):
                        next_line = full_text_lines[i]
                        # Stop at next question, 見出し, or 別添
                        if re.match(r"^(問[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+", next_line):
                            break
                        if re.match(r"^【[^】]+】$", next_line):
                            break
                        if re.match(r"^[（(]?別添[０-９0-9１-９]+[）)]?$", next_line):
                            break
                        if re.match(r"^○\s+", next_line):
                            break
                        
                        # Empty line indicates paragraph break
                        if not next_line:
                            if current_para:
                                a_paras.append(current_para)
                                current_para = ""
                            i += 1
                            continue
                        
                        # Continue paragraph
                        current_para += next_line
                        i += 1
                    
                    if current_para:
                        a_paras.append(current_para)
            
            # Create item
            item = {
                "問番号": q_num,
                "問": q_text,
                "答": a_paras if a_paras else []
            }
            if current_betten:
                item["別添"] = current_betten
            if current_midashi:
                item["見出し"] = current_midashi.copy()
            
            items.append(item)
            continue
        
        i += 1
    
    # Post-process: infer 別添１ for items without explicit 別添
    # If we have items with 別添２+, then items without 別添 should be 別添１
    has_explicit_betten = any(item.get("別添") for item in items)
    
    if has_explicit_betten:
        for item in items:
            if not item.get("別添"):
                item["別添"] = "別添１"
    
    return items


def parse(pdf_path):
    """Parse Q&A/疑義解釈 PDF"""
    pdf = pdfplumber.open(pdf_path)
    
    metadata = extract_metadata(pdf)
    
    # Determine start page (skip 介護保険最新情報 cover if present)
    start_page = 1
    first_text = pdf.pages[0].extract_text() or ""
    if "介護保険最新情報" in first_text:
        start_page = 2
    
    items = extract_items(pdf, start_page)
    
    pdf.close()
    return metadata, items


def save(output_path, metadata, items):
    """Save to YAML"""
    # Build output dict with specific key order
    output = {}
    for key in ["種別", "番号", "日付", "発出元", "件名", "廃止"]:
        if key in metadata and metadata[key]:
            output[key] = metadata[key]
    output["items"] = items
    
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(output, f, allow_unicode=True, sort_keys=False, width=200, default_flow_style=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Convert MHLW Q&A/疑義解釈 PDF to YAML")
    ap.add_argument("pdf", help="Input PDF path")
    ap.add_argument("-o", "--output", required=True, help="Output YAML file path")
    
    args = ap.parse_args()
    
    metadata, items = parse(args.pdf)
    save(args.output, metadata, items)
    
    print(f"Extracted {metadata.get('種別', 'Q&A')}:")
    print(f"  種別: {metadata.get('種別', '(未検出)')}")
    print(f"  番号: {metadata.get('番号', '(未検出)')}")
    print(f"  日付: {metadata.get('日付', '(未検出)')}")
    print(f"  発出元: {metadata.get('発出元', '(未検出)')}")
    print(f"  件名: {metadata.get('件名', '(未検出)')[:80]}..." if metadata.get('件名') and len(metadata.get('件名', '')) > 80 else f"  件名: {metadata.get('件名', '(未検出)')}")
    if metadata.get('廃止'):
        print(f"  廃止: {metadata.get('廃止', '')[:80]}...")
    print(f"  Items: {len(items)}")
    print(f"\nSaved to: {args.output}")
