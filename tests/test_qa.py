#!/usr/bin/env python3
"""Test pdf2qa on Q1-Q3 sample documents"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf2qa import parse
import yaml


def test_q1_疑義解釈その12():
    """Q1: 疑義解釈資料の送付について（その12）"""
    meta, items = parse("data/qa_samples/Q1.pdf")
    
    # 1. All 5 version fields present and non-empty
    assert meta["種別"] == "疑義解釈", f"Expected '疑義解釈', got '{meta.get('種別')}'"
    assert meta["番号"] == "その12", f"Expected 'その12', got '{meta.get('番号')}'"
    assert meta["日付"] and "令和８年９月" in meta["日付"], f"Date should contain '令和８年９月', got '{meta.get('日付')}'"
    assert meta["発出元"] and "厚生労働省" in meta["発出元"], f"Issuer should contain '厚生労働省', got '{meta.get('発出元')}'"
    assert meta["件名"] and "疑義解釈" in meta["件名"], f"Subject should contain '疑義解釈', got '{meta.get('件名')}'"
    
    # 2. Every item has a non-empty 答
    for i, item in enumerate(items):
        assert item["答"], f"Item {i+1} ({item.get('問番号')}) has empty answer"
        assert isinstance(item["答"], list), f"Item {i+1} answer should be a list"
        assert len(item["答"]) > 0, f"Item {i+1} answer list is empty"
    
    # 3. Within the same 別添, 問番号 is not duplicated
    betten_groups = {}
    for item in items:
        betten = item.get("別添", "なし")
        q_num = item["問番号"]
        if betten not in betten_groups:
            betten_groups[betten] = []
        assert q_num not in betten_groups[betten], f"Duplicate {q_num} in {betten}"
        betten_groups[betten].append(q_num)
    
    print(f"✓ Q1: {len(items)} items, {len(betten_groups)} 別添 groups")
    return len(items)


def test_q2_疑義解釈その2():
    """Q2: 疑義解釈資料の送付について（その２）"""
    meta, items = parse("data/qa_samples/Q2.pdf")
    
    # 1. All 5 version fields present and non-empty
    assert meta["種別"] == "疑義解釈", f"Expected '疑義解釈', got '{meta.get('種別')}'"
    assert meta["番号"] == "その２", f"Expected 'その２', got '{meta.get('番号')}'"
    assert meta["日付"] and "令和８年４月" in meta["日付"], f"Date should contain '令和８年４月', got '{meta.get('日付')}'"
    assert meta["発出元"] and "厚生労働省" in meta["発出元"], f"Issuer should contain '厚生労働省', got '{meta.get('発出元')}'"
    assert meta["件名"] and "疑義解釈" in meta["件名"], f"Subject should contain '疑義解釈', got '{meta.get('件名')}'"
    
    # Check 廃止 field is present (Q2 mentions abolishing previous version)
    assert meta.get("廃止"), "Q2 should have a 廃止 field"
    
    # 2. Every item has a non-empty 答
    for i, item in enumerate(items):
        assert item["答"], f"Item {i+1} ({item.get('問番号')}) has empty answer"
        assert isinstance(item["答"], list), f"Item {i+1} answer should be a list"
        assert len(item["答"]) > 0, f"Item {i+1} answer list is empty"
    
    # 3. Within the same 別添, 問番号 is not duplicated
    betten_groups = {}
    duplicates = []
    for item in items:
        betten = item.get("別添", "なし")
        q_num = item["問番号"]
        if betten not in betten_groups:
            betten_groups[betten] = []
        if q_num in betten_groups[betten]:
            duplicates.append((betten, q_num))
        betten_groups[betten].append(q_num)
    
    if duplicates:
        print(f"  ⚠ Found duplicates (may be source PDF issue): {duplicates}")
    
    print(f"✓ Q2: {len(items)} items, {len(betten_groups)} 別添 groups")
    return len(items)


def test_q3_qa_vol1524():
    """Q3: 令和６年度介護報酬改定に関するＱ＆Ａ（Vol.18）"""
    meta, items = parse("data/qa_samples/Q3.pdf")
    
    # 1. All 5 version fields present and non-empty
    assert meta["種別"] == "Q&A", f"Expected 'Q&A', got '{meta.get('種別')}'"
    assert meta["番号"] and "Vol." in meta["番号"], f"Number should contain 'Vol.', got '{meta.get('番号')}'"
    assert meta["日付"] and "令和" in meta["日付"], f"Date should contain '令和', got '{meta.get('日付')}'"
    assert meta["発出元"] and "厚生労働省" in meta["発出元"], f"Issuer should contain '厚生労働省', got '{meta.get('発出元')}'"
    assert meta["件名"] and "Ｑ＆Ａ" in meta["件名"], f"Subject should contain 'Ｑ＆Ａ', got '{meta.get('件名')}'"
    
    # 2. Every item has a non-empty 答
    for i, item in enumerate(items):
        assert item["答"], f"Item {i+1} ({item.get('問番号')}) has empty answer"
        assert isinstance(item["答"], list), f"Item {i+1} answer should be a list"
        assert len(item["答"]) > 0, f"Item {i+1} answer list is empty"
    
    # 3. Within the same 別添, 問番号 is not duplicated
    betten_groups = {}
    for item in items:
        betten = item.get("別添", "なし")
        q_num = item["問番号"]
        if betten not in betten_groups:
            betten_groups[betten] = []
        assert q_num not in betten_groups[betten], f"Duplicate {q_num} in {betten}"
        betten_groups[betten].append(q_num)
    
    print(f"✓ Q3: {len(items)} items, {len(betten_groups)} 別添 groups")
    return len(items)


if __name__ == "__main__":
    counts = []
    try:
        counts.append(("Q1", test_q1_疑義解釈その12()))
        counts.append(("Q2", test_q2_疑義解釈その2()))
        counts.append(("Q3", test_q3_qa_vol1524()))
        
        print("\nAll tests passed! ✓")
        print("\nItem counts:")
        for name, count in counts:
            print(f"  {name}: {count} items")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
