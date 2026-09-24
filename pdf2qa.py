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
        
        return meta
    
    # Standard 事務連絡 cover (疑義解釈)
    text = text0
    lines = [l.strip() for l in text.split("\n")]
    
    # Extract expected 別添 count from body text (e.g., "別添１から別添６までのとおり")
    betten_range_match = re.search(r"別添([０-９0-9１-９]+)から別添([０-９0-9１-９]+)まで", text)
    if betten_range_match:
        start_num = betten_range_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        end_num = betten_range_match.group(2).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        meta["_expected_betten_count"] = int(end_num) - int(start_num) + 1
    
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
                # Extract 番号 from subject (with optional space after その)
                num_match = re.search(r"[（(]その\s*[０-９0-9１-９]+[）)]", line)
                if num_match:
                    meta["番号"] = re.sub(r"[（(）)\s]", "", num_match.group(0))
                meta["種別"] = "疑義解釈"
                break
    
    return meta


def extract_haishi_statements(pdf):
    """Extract all 廃止 (abolishment) statements from the PDF
    
    Returns list of dicts: {原文: str, 別添: str or None, 頁: int}
    """
    statements = []
    seen_statements = set()  # To avoid duplicates from overlapping regex matches
    
    # First pass: find where the first explicit 別添 marker appears
    first_explicit_betten = None
    first_explicit_page = None
    for page_num, page in enumerate(pdf.pages):
        if page_num == 0:  # Skip cover page
            continue
        text = page.extract_text() or ""
        for line in text.split('\n'):
            betten_match = re.match(r'^[（(]別添([０-９0-9１-９]+)[）)]', line.strip())
            if betten_match:
                num = int(betten_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789')))
                first_explicit_betten = num
                first_explicit_page = page_num
                break
        if first_explicit_betten:
            break
    
    # Second pass: extract statements with proper 別添 tracking
    current_betten = None
    
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        
        # Track which 別添 we're in
        for line in text.split('\n'):
            betten_match = re.match(r'^[（(]別添([０-９0-9１-９]+)[）)]', line.strip())
            if betten_match:
                num = int(betten_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789')))
                current_betten = f"別添{num}"
        
        # Determine effective 別添 for this page
        effective_betten = current_betten
        if page_num > 0 and effective_betten is None and first_explicit_betten and first_explicit_betten > 1:
            # This page is before the first explicit 別添 marker, so assign implicit 別添(N-1)
            if page_num < first_explicit_page:
                effective_betten = f"別添{first_explicit_betten - 1}"
        
        # Join lines for this page to capture multi-line statements
        full_text = ' '.join(text.split('\n'))
        
        # Pattern: Find sentences ending with 廃止...。
        # Split by periods and look for 廃止 in each sentence
        sentences = full_text.split('。')
        for i, sentence in enumerate(sentences):
            if '廃止' not in sentence:
                continue
            
            # Add period back
            sentence = sentence + '。'
            
            # Check if this is an abolishment statement
            # Pattern 1: Document abolishment with quotes
            if re.search(r'「[^」]+」[^。]*は廃止', sentence):
                # Remove leading context to find the start of the statement
                # Try to start from "なお" or "これに伴い" if present
                cleaned = sentence
                for prefix in ['なお、これに伴い、', 'これに伴い、', 'なお、']:
                    if prefix in sentence:
                        idx = sentence.index(prefix)
                        cleaned = sentence[idx:]
                        break
                
                # Create a key to deduplicate
                key = (page_num + 1, cleaned[-100:])  # Use last 100 chars as key
                if key not in seen_statements:
                    statements.append({
                        '原文': cleaned,
                        '別添': effective_betten if page_num > 0 else None,  # Cover page always None
                        '頁': page_num + 1
                    })
                    seen_statements.add(key)
            
            # Pattern 2: Question-specific abolishment
            elif re.search(r'別添[０-９0-9１-９]*の問\s*[０-９0-9１-９]+[^。]*(は廃止|については廃止|については、廃止)', sentence):
                # Clean up the sentence start
                cleaned = sentence
                for prefix in ['なお、これに伴い、', 'これに伴い、', 'なお、']:
                    if prefix in sentence:
                        idx = sentence.index(prefix)
                        cleaned = sentence[idx:]
                        break
                
                key = (page_num + 1, cleaned[-100:])
                if key not in seen_statements:
                    statements.append({
                        '原文': cleaned,
                        '別添': effective_betten,
                        '頁': page_num + 1
                    })
                    seen_statements.add(key)
    
    return statements


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
        
        # Question start (問N, QN, or 問N－M format, with optional space)
        q_match = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.*)$", line)
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
                # Stop at new question (but not references like "問122 の③")
                q_start = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.)", next_line)
                if q_start and q_start.group(2) != 'の':
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
                        # Stop at next question (but not references like "問122 の③")
                        q_start = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.)", next_line)
                        if q_start and q_start.group(2) != 'の':
                            break
                        if re.match(r"^【[^】]+】$", next_line):
                            break
                        if re.match(r"^[（(]?別添[０-９0-9１-９]+[）)]?$", next_line):
                            break
                        # ○ markers can be bullet points in answers, only break if we already have content
                        if re.match(r"^○\s+", next_line) and (current_para or a_paras):
                            # Check if this looks like a new section header (short, ends with certain chars)
                            if len(next_line) < 30 or next_line.endswith(("について", "関係", "加算")):
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
    
    # Post-process: assign implicit 別添 to items without explicit 別添
    # Strategy: questions before the first explicit 別添N get assigned 別添(N-1)
    # Find first explicit 別添
    first_explicit_betten = None
    first_explicit_idx = None
    for i, item in enumerate(items):
        if item.get("別添"):
            # Extract number from 別添N
            match = re.search(r"別添([０-９0-9１-９]+)", item["別添"])
            if match:
                num = int(match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789')))
                first_explicit_betten = num
                first_explicit_idx = i
                break
    
    if first_explicit_betten is not None and first_explicit_betten > 1:
        # Assign 別添(N-1) to all items before the first explicit 別添N
        implicit_betten = f"別添{first_explicit_betten - 1}"
        for i in range(first_explicit_idx):
            if not items[i].get("別添"):
                items[i]["別添"] = implicit_betten
    
    return items


def parse(pdf_path):
    """Parse Q&A/疑義解釈 PDF"""
    pdf = pdfplumber.open(pdf_path)
    
    metadata = extract_metadata(pdf)
    haishi_statements = extract_haishi_statements(pdf)
    
    # Add haishi statements to metadata if any
    if haishi_statements:
        metadata["廃止"] = haishi_statements
    
    # Determine start page (skip 介護保険最新情報 cover if present)
    start_page = 1
    first_text = pdf.pages[0].extract_text() or ""
    if "介護保険最新情報" in first_text:
        start_page = 2
    
    items = extract_items(pdf, start_page)
    
    pdf.close()
    return metadata, items


def normalize_q_num(q_num):
    """Normalize question number for duplicate comparison (NFKC + remove spaces)"""
    import unicodedata
    # Remove spaces
    normalized = q_num.replace(' ', '')
    # NFKC normalization (full-width -> half-width)
    normalized = unicodedata.normalize('NFKC', normalized)
    return normalized


def save(output_path, metadata, items):
    """Save to YAML"""
    # Build output dict with specific key order
    output = {}
    expected_betten_count = metadata.pop("_expected_betten_count", None)
    
    for key in ["種別", "番号", "日付", "発出元", "件名", "廃止"]:
        if key in metadata and metadata[key]:
            output[key] = metadata[key]
    output["items"] = items
    
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(output, f, allow_unicode=True, sort_keys=False, width=200, default_flow_style=False)
    
    # Check for duplicates and warn
    from collections import defaultdict
    betten_groups = defaultdict(list)
    for item in items:
        betten = item.get("別添", "なし")
        betten_groups[betten].append(item["問番号"])
    
    warnings = []
    
    # Check 別添 count
    if expected_betten_count:
        actual_betten_count = len([k for k in betten_groups.keys() if k != "なし"])
        if actual_betten_count != expected_betten_count:
            warnings.append(f"⚠ Expected {expected_betten_count} 別添 from body text, but extracted {actual_betten_count}")
    
    # Check for duplicates (normalize for comparison, but report original notation)
    for betten, q_nums in betten_groups.items():
        # Build normalized -> original mapping
        normalized_map = defaultdict(list)
        for q_num in q_nums:
            normalized = normalize_q_num(q_num)
            normalized_map[normalized].append(q_num)
        
        # Find duplicates
        for normalized, originals in normalized_map.items():
            if len(originals) > 1:
                # Use the first original notation for the warning
                warnings.append(f"⚠ Duplicate {originals[0]} in {betten} ({len(originals)} instances - kept as-is from source)")
    
    return warnings


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Convert MHLW Q&A/疑義解釈 PDF to YAML")
    ap.add_argument("pdf", help="Input PDF path")
    ap.add_argument("-o", "--output", required=True, help="Output YAML file path")
    
    args = ap.parse_args()
    
    metadata, items = parse(args.pdf)
    warnings = save(args.output, metadata, items)
    
    print(f"Extracted {metadata.get('種別', 'Q&A')}:")
    print(f"  種別: {metadata.get('種別', '(未検出)')}")
    print(f"  番号: {metadata.get('番号', '(未検出)')}")
    print(f"  日付: {metadata.get('日付', '(未検出)')}")
    print(f"  発出元: {metadata.get('発出元', '(未検出)')}")
    print(f"  件名: {metadata.get('件名', '(未検出)')[:80]}..." if metadata.get('件名') and len(metadata.get('件名', '')) > 80 else f"  件名: {metadata.get('件名', '(未検出)')}")
    if metadata.get('廃止'):
        print(f"  廃止: {metadata.get('廃止', '')[:80]}...")
    print(f"  Items: {len(items)}")
    
    if warnings:
        print()
        for warning in warnings:
            print(warning)
    
    print(f"\nSaved to: {args.output}")
