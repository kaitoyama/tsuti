#!/usr/bin/env python3
"""R8 疑義解釈 accumulation: compute valid Q&A list as of target date

Usage:
  python qa_accumulate.py --as-of 2026-04-10 --corpus r8_corpus.yaml -o valid_list.yaml

Architecture:
  Issue identity: (系列, 改定年度, 号名, 日付)
  Events: issue added, issue replaced, question abolished, question corrected
  
  Apply events in date order to produce:
  - valid list: Q&A items valid on target date
  - abolishment record: past-year abolishments (年度/号/別添/問番号)
"""
import argparse
import yaml
import re
import os
import tempfile
from datetime import datetime
from collections import defaultdict
from pdf2qa import parse as pdf2qa_parse


def parse_date(date_str):
    """Parse 令和N年M月D日 to datetime"""
    m = re.match(r'令和(\d+)年(\d+)月(\d+)日', date_str)
    if not m:
        raise ValueError(f"Cannot parse date: {date_str}")
    reiwa_year, month, day = map(int, m.groups())
    gregorian_year = reiwa_year + 2018
    return datetime(gregorian_year, month, day)


def parse_date_iso(date_str):
    """Parse YYYY-MM-DD to datetime"""
    return datetime.strptime(date_str, '%Y-%m-%d')


def normalize_betten(label):
    """Normalize 別添１ / 別添1 to standard form"""
    if not label:
        return None
    # Convert full-width digits to half-width
    return label.translate(str.maketrans('０１２３４５６７８９', '0123456789'))


def question_key(item, occurrence=0):
    """Unique key for a question: (号名, 別添, 問番号, occurrence)"""
    return (
        item.get('_issue_gou', ''),
        normalize_betten(item.get('別添', '')),
        item['問番号'],
        occurrence
    )


def parse_haishi_target(haishi_text):
    """Parse 廃止 statement to extract target (年度, 号, 別添, 問番号) if it references past issues
    
    Returns None if not a past-year reference, or dict with keys: 年度, 号, 別添, 問番号
    """
    # Pattern: 令和N年...その M...別添X...問Y
    reiwa_match = re.search(r'令和(\d+)年', haishi_text)
    if not reiwa_match:
        return None  # Not a dated reference
    
    year = int(reiwa_match.group(1)) + 2018
    
    # Extract その N
    gou_match = re.search(r'その([０-９0-9１-９]+)', haishi_text)
    gou = None
    if gou_match:
        gou_num = gou_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        gou = f"その{gou_num}"
    
    # Extract 別添 N
    betten_match = re.search(r'別添([０-９0-9１-９]+)', haishi_text)
    betten = None
    if betten_match:
        betten_num = betten_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        betten = f"別添{betten_num}"
    
    # Extract 問 N
    q_match = re.search(r'問\s*([０-９0-9１-９]+)', haishi_text)
    q_num = None
    if q_match:
        q_num = q_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        q_num = f"問{q_num}"
    
    if gou or betten or q_num:
        return {
            '年度': year,
            '号': gou,
            '別添': betten,
            '問番号': q_num
        }
    
    return None


def ingest_issue(issue_spec, cache_dir):
    """Ingest one issue: download PDFs, run pdf2qa, return items + metadata
    
    Returns: (items, metadata, haishi_statements)
    """
    files = issue_spec.get('files', [])
    if not files:
        raise ValueError(f"Issue has no files: {issue_spec.get('号名', issue_spec.get('title'))}")
    
    all_items = []
    all_metadata = None
    all_haishi = []
    
    for file_spec in files:
        url = file_spec['url']
        filename = os.path.basename(url)
        local_path = os.path.join(cache_dir, filename)
        
        # Download if not cached
        if not os.path.exists(local_path):
            print(f"  Downloading {url}")
            import urllib.request
            urllib.request.urlretrieve(url, local_path)
        
        # Parse with pdf2qa
        metadata, items = pdf2qa_parse(local_path)
        
        # Merge metadata
        if all_metadata is None:
            all_metadata = metadata
        
        # Extract 廃止 statements
        if '廃止' in metadata:
            all_haishi.extend(metadata['廃止'])
        
        # Annotate items with issue metadata
        gou = issue_spec.get('号名', '')
        keiretsu = issue_spec.get('系列', '医科の疑義解釈')
        nendo = issue_spec.get('改定年度', 2026)
        for item in items:
            item['_issue_gou'] = gou
            item['_issue_date'] = issue_spec['日付']
            item['_issue_keiretsu'] = keiretsu
            item['_issue_nendo'] = nendo
        
        all_items.extend(items)
    
    return all_items, all_metadata, all_haishi


def apply_events(corpus, target_date_iso, cache_dir):
    """Apply all events up to target date and return valid list + abolishment record
    
    Returns: (valid_items, abolishment_records, stats)
    """
    target_date = parse_date_iso(target_date_iso)
    
    # Track all questions by key
    questions = {}  # key -> item
    question_occurrences = defaultdict(int)  # (gou, betten, q_num) -> count
    
    # Track abolishments
    abolishments = []
    
    # Track replacements
    issue_registry = {}  # (系列, 年度, 号名) -> latest issue
    
    # Process issues in date order
    issues = sorted(corpus['issues'], key=lambda x: parse_date(x['日付']))
    
    stats = {
        'events': [],
        'issues_added': 0,
        'issues_replaced': 0,
        'questions_abolished': 0,
        'questions_corrected': 0
    }
    
    for issue_spec in issues:
        issue_date = parse_date(issue_spec['日付'])
        if issue_date > target_date:
            break
        
        keiretsu = issue_spec.get('系列', '医科の疑義解釈')
        nendo = issue_spec.get('改定年度', 2026)
        gou = issue_spec.get('号名', '')
        
        # Check for correction document (一部訂正)
        is_correction = 'correction_target' in issue_spec
        
        if is_correction:
            # Correction event
            correction_target = issue_spec.get('correction_target', {})
            target_gou = correction_target.get('号名', '')
            target_betten = correction_target.get('別添', '')
            target_q_num = correction_target.get('問番号', '')
            
            # Ingest to get corrected text
            items, _, _ = ingest_issue(issue_spec, cache_dir)
            
            # Find and update the target question
            for item in items:
                if item.get('問番号') == target_q_num:
                    # Annotate with correct metadata
                    item['_issue_gou'] = target_gou
                    item['別添'] = target_betten  # Correction PDF may not have this
                    
                    # Find the key in questions dict and update
                    found = False
                    for key, existing_item in list(questions.items()):
                        if (key[0] == target_gou and 
                            normalize_betten(key[1]) == normalize_betten(target_betten) and 
                            key[2] == target_q_num):
                            # Update with corrected text
                            questions[key] = item
                            stats['questions_corrected'] += 1
                            stats['events'].append(f"{issue_spec['日付']}: 訂正 {target_gou} {target_betten} {target_q_num}")
                            found = True
                            break
                    
                    if not found:
                        print(f"  Warning: correction target {target_gou} {target_betten} {target_q_num} not found")
                    break
            
            continue
        
        # Check for replacement (only if 号名 is non-empty)
        registry_key = (keiretsu, nendo, gou)
        if gou and registry_key in issue_registry:
            # Replacement: remove all questions from old issue matching (系列, 年度, 号名)
            old_issue = issue_registry[registry_key]
            old_date = old_issue['日付']
            
            # Remove old questions matching the full key
            to_remove = [k for k, v in questions.items() 
                        if (v.get('_issue_gou') == gou and
                            v.get('_issue_keiretsu') == keiretsu and
                            v.get('_issue_nendo') == nendo)]
            for k in to_remove:
                del questions[k]
            
            stats['issues_replaced'] += 1
            stats['events'].append(f"{issue_spec['日付']}: 置換 {gou} (旧: {old_date})")
        
        # Register issue (only if 号名 is non-empty)
        if gou:
            issue_registry[registry_key] = issue_spec
        
        # Ingest issue
        items, metadata, haishi_stmts = ingest_issue(issue_spec, cache_dir)
        
        # Add questions
        for item in items:
            occurrence_key = (gou, normalize_betten(item.get('別添', '')), item['問番号'])
            occurrence = question_occurrences[occurrence_key]
            question_occurrences[occurrence_key] += 1
            
            key = question_key(item, occurrence)
            questions[key] = item
        
        stats['issues_added'] += 1
        stats['events'].append(f"{issue_spec['日付']}: 追加 {gou or issue_spec.get('title', '無題')} ({len(items)} questions)")
        
        # Process 廃止 statements
        for haishi in haishi_stmts:
            haishi_text = haishi['原文']
            
            # Check if it targets a past or current year issue
            target = parse_haishi_target(haishi_text)
            if target:
                # Check if target year matches current issue's 改定年度
                if target['年度'] == nendo:
                    # Same-year inter-issue abolishment: remove from live set
                    target_gou = target.get('号')
                    target_betten = target.get('別添')
                    target_q_num = target.get('問番号')
                    
                    # Find and remove the question
                    to_remove = None
                    for key, item in questions.items():
                        matches_gou = (not target_gou or item.get('_issue_gou') == target_gou)
                        matches_betten = (not target_betten or 
                                        normalize_betten(item.get('別添')) == normalize_betten(target_betten))
                        matches_q = (not target_q_num or item['問番号'] == target_q_num)
                        
                        if matches_gou and matches_betten and matches_q:
                            to_remove = key
                            break
                    
                    if to_remove:
                        del questions[to_remove]
                        stats['questions_abolished'] += 1
                        stats['events'].append(f"{issue_spec['日付']}: 廃止 (同年度) {target_gou or ''} {target_betten or ''} {target_q_num or ''}")
                else:
                    # Past-year reference: add to abolishment record only
                    abolishments.append({
                        '原文': haishi_text,
                        '年度': target['年度'],
                        '号': target['号'],
                        '別添': target['別添'],
                        '問番号': target['問番号']
                    })
            else:
                # Check if it targets a current-issue question (no year specified)
                # Pattern: 別添N の 問M
                current_match = re.search(r'別添([０-９0-9１-９]+)\s*の\s*問\s*([０-９0-9１-９]+)', haishi_text)
                if current_match:
                    target_betten_num = current_match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
                    target_q_num = current_match.group(2).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
                    target_betten = f"別添{target_betten_num}"
                    target_q = f"問{target_q_num}"
                    
                    # Find and remove the question
                    to_remove = None
                    for key in questions.keys():
                        if (key[0] == gou and 
                            normalize_betten(key[1]) == normalize_betten(target_betten) and 
                            key[2] == target_q):
                            to_remove = key
                            break
                    
                    if to_remove:
                        del questions[to_remove]
                        stats['questions_abolished'] += 1
                        stats['events'].append(f"{issue_spec['日付']}: 廃止 {gou} {target_betten} {target_q}")
    
    # Return valid items
    valid_items = list(questions.values())
    
    return valid_items, abolishments, stats


def main():
    ap = argparse.ArgumentParser(description='R8 疑義解釈 accumulation')
    ap.add_argument('--as-of', required=True, help='Target date (YYYY-MM-DD)')
    ap.add_argument('--corpus', required=True, help='Corpus manifest YAML')
    ap.add_argument('-o', '--output', required=True, help='Output YAML (valid list)')
    ap.add_argument('--abolishment-out', help='Output YAML for abolishment records')
    ap.add_argument('--cache-dir', default='./cache/qa_pdfs', help='PDF cache directory')
    
    args = ap.parse_args()
    
    # Load corpus
    with open(args.corpus, encoding='utf-8') as f:
        corpus = yaml.safe_load(f)
    
    # Create cache dir
    os.makedirs(args.cache_dir, exist_ok=True)
    
    # Apply events
    print(f"Computing valid list as of {args.as_of}...")
    valid_items, abolishments, stats = apply_events(corpus, args.as_of, args.cache_dir)
    
    # Save valid list
    output = {
        'as_of': args.as_of,
        'items_count': len(valid_items),
        'items': valid_items
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        yaml.safe_dump(output, f, allow_unicode=True, sort_keys=False, width=200)
    
    print(f"✓ Saved {len(valid_items)} valid items to {args.output}")
    
    # Save abolishment records
    if args.abolishment_out and abolishments:
        abolishment_output = {
            'as_of': args.as_of,
            'abolishments': abolishments
        }
        with open(args.abolishment_out, 'w', encoding='utf-8') as f:
            yaml.safe_dump(abolishment_output, f, allow_unicode=True, sort_keys=False, width=200)
        print(f"✓ Saved {len(abolishments)} abolishment records to {args.abolishment_out}")
    
    # Print stats
    print("\nEvents applied:")
    for event in stats['events']:
        print(f"  {event}")
    print(f"\nSummary:")
    print(f"  Issues added: {stats['issues_added']}")
    print(f"  Issues replaced: {stats['issues_replaced']}")
    print(f"  Questions corrected: {stats['questions_corrected']}")
    print(f"  Questions abolished: {stats['questions_abolished']}")
    print(f"  Valid questions as of {args.as_of}: {len(valid_items)}")


if __name__ == '__main__':
    main()
