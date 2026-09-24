#!/usr/bin/env python3
"""基発PDF → 簡易テキスト。初回の取り込み専用（結果は人が確認する前提）

対応範囲：MHLW 基発（labor-standards bureau circulars）
対応範囲外：階層的な通知（→ pdf2tsuchi.py）、事務連絡（→ pdf2jimu.py）、Q&A/疑義解釈（→ pdf2qa.py）

  python pdf2kihatsu.py data/kihatsu_samples/K1.pdf -o K1.kihatsu.txt

基発の構造：
  - 文書番号：基発形式（スペース入り、例：「基　発　0　7　3　1　第　7　号」）
  - 日付
  - 宛先：都道府県労働局長 殿
  - 発出元：厚生労働省労働基準局長
  - 件名：（公 印 省 略）の次の行
  - 本文段落
"""
import argparse
import re
import pdfplumber


def normalize_number_string(s):
    """全角数字を半角に変換し、空白を削除"""
    # 全角数字→半角
    s = s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    # スペースを削除
    s = re.sub(r'\s+', '', s)
    return s


def extract_metadata(pdf):
    """Extract metadata from first page"""
    meta = {"種別": "基発"}
    
    if len(pdf.pages) == 0:
        return meta
    
    text = pdf.pages[0].extract_text() or ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # 番号：最初の行（基発形式）
    # Pattern: 基発 MMDD 第 N 号 or 基 発 MMDD第 N 号
    if lines:
        first_line = lines[0]
        # 正規化して「基発」で始まるかチェック
        normalized = normalize_number_string(first_line)
        if normalized.startswith('基発'):
            meta["番号"] = normalized
    
    # 日付：2行目付近
    for i in range(min(3, len(lines))):
        line = lines[i]
        # スペース除去して日付パターンを探す
        line_norm = re.sub(r'\s+', '', line)
        date_match = re.search(r'令和[０-９0-9]+年[０-９0-9]+月[０-９0-9]+日', line_norm)
        if date_match:
            meta["日付"] = date_match.group(0)
            break
    
    # 発出元：「厚生労働省労働基準局長」を探す
    for i, line in enumerate(lines):
        if '厚生労働省労働基準局長' in line:
            meta["発出元"] = "厚生労働省労働基準局長"
            break
    
    # 件名：「（公 印 省 略）」または「（ 公 印 省 略 ）」の次の行（複数行の可能性）
    inkan_idx = None
    for i, line in enumerate(lines):
        if re.search(r'[（(]\s*公\s*印\s*省\s*略\s*[）)]', line):
            inkan_idx = i
            break
    
    if inkan_idx is not None and inkan_idx + 1 < len(lines):
        # 件名は複数行にわたる可能性がある
        # 基発の件名パターン：
        # - 単行: 「...について」で終わる
        # - 複数行: 「...について（補足説明）」のように括弧で追加説明がある
        subject_lines = []
        has_opening_paren = False
        
        for i in range(inkan_idx + 1, min(inkan_idx + 15, len(lines))):
            line = lines[i]
            subject_lines.append(line)
            
            # 括弧の追跡
            if '（' in line or '(' in line:
                has_opening_paren = True
            
            # 件名終了の判定
            # 1. 「について」で終わり、括弧が開いていない、または括弧が閉じた後
            if line.endswith('について'):
                # 括弧が開いていなければ終了
                if not has_opening_paren:
                    break
                # 括弧が閉じられていれば終了（この行に）がある）
                if '）' in line or ')' in line:
                    break
            # 2. 括弧で終わり、それが件名の最後（次行が本文）
            elif (line.endswith('）') or line.endswith(')')) and has_opening_paren:
                # 次行が明らかに本文なら終了
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # 次行が本文の開始パターン（法律名や日付で始まる、または「記」）
                    # 本文は通常、法律名の繰り返しや施行日の説明で始まる
                    if (len(next_line) > 30 or next_line == "記" or 
                        re.search(r'^[^（]*法律|^[^（]*省令|^今般、|^ついては、', next_line)):
                        break
        
        meta["件名"] = "".join(subject_lines)
    
    return meta


def extract_body(pdf):
    """Extract body paragraphs from all pages"""
    paragraphs = []
    
    # 1ページ目のメタデータ部分をスキップ
    first_page_text = pdf.pages[0].extract_text() or ""
    first_page_lines = first_page_text.split("\n")
    
    # 「（公 印 省 略）」を見つけて、件名の後から本文開始
    inkan_idx = None
    for i, line in enumerate(first_page_lines):
        if re.search(r'[（(]\s*公\s*印\s*省\s*略\s*[）)]', line.strip()):
            inkan_idx = i
            break
    
    # 件名の終了位置を探す（件名は複数行にわたる可能性）
    body_start_idx = None
    if inkan_idx is not None:
        has_opening_paren = False
        
        for i in range(inkan_idx + 1, min(inkan_idx + 15, len(first_page_lines))):
            line = first_page_lines[i].strip()
            if not line:
                continue
            
            # 括弧の追跡
            if '（' in line or '(' in line:
                has_opening_paren = True
            
            # 件名終了の判定
            # 1. 「について」で終わり、括弧が開いていない、または括弧が閉じた後
            if line.endswith('について'):
                # 括弧が開いていなければ終了
                if not has_opening_paren:
                    body_start_idx = i + 1
                    break
                # 括弧が閉じられていれば終了
                if '）' in line or ')' in line:
                    body_start_idx = i + 1
                    break
            # 2. 括弧で終わり、それが件名の最後（次行が本文）
            elif (line.endswith('）') or line.endswith(')')) and has_opening_paren:
                # 次行が明らかに本文なら終了
                if i + 1 < len(first_page_lines):
                    next_line = first_page_lines[i + 1].strip()
                    # 次行が本文の開始パターン
                    if (len(next_line) > 30 or next_line == "記" or 
                        re.search(r'^[^（]*法律|^[^（]*省令|^今般、|^ついては、', next_line)):
                        body_start_idx = i + 1
                        break
    
    # 1ページ目の本文を抽出
    if body_start_idx is not None:
        for i in range(body_start_idx, len(first_page_lines)):
            stripped = first_page_lines[i].strip()
            if stripped and not re.match(r'^[0-9０-９]+$', stripped):
                paragraphs.append(stripped)
    
    # 2ページ目以降を抽出
    for page_num in range(1, len(pdf.pages)):
        text = pdf.pages[page_num].extract_text() or ""
        page_lines = text.split("\n")
        
        for line in page_lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # ページ番号をスキップ（単独数字）
            if re.match(r'^[0-9０-９]+$', stripped):
                continue
            
            paragraphs.append(stripped)
    
    return paragraphs


def parse(pdf_path):
    """Parse 基発 PDF and extract metadata + body"""
    pdf = pdfplumber.open(pdf_path)
    
    metadata = extract_metadata(pdf)
    body = extract_body(pdf)
    
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
    ap = argparse.ArgumentParser(description="Convert MHLW 基発 PDF to structured text")
    ap.add_argument("pdf", help="Input PDF path")
    ap.add_argument("-o", "--output", required=True, help="Output text file path")
    ap.add_argument("--number", help="Override document number if not detected")
    ap.add_argument("--date", help="Override date if not detected")
    
    args = ap.parse_args()
    
    metadata, body = parse(args.pdf)
    
    # Apply overrides
    if args.number:
        metadata["番号"] = args.number
    if args.date:
        metadata["日付"] = args.date
    
    save(args.output, metadata, body)
    
    print(f"Extracted 基発:")
    print(f"  種別: {metadata.get('種別')}")
    print(f"  番号: {metadata.get('番号', '(未検出)')}")
    print(f"  日付: {metadata.get('日付', '(未検出)')}")
    print(f"  発出元: {metadata.get('発出元', '(未検出)')}")
    print(f"  件名: {metadata.get('件名', '(未検出)')[:50]}..." if metadata.get('件名') and len(metadata.get('件名', '')) > 50 else f"  件名: {metadata.get('件名', '(未検出)')}")
    print(f"  Body: {len(body)} paragraphs")
    print(f"\nSaved to: {args.output}")
