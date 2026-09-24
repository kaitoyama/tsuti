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
    
    # Q1 should have exactly 22 items (including space-pattern questions)
    assert len(items) == 22, f"Expected 22 items, got {len(items)}"
    
    # Check that space-pattern questions are present
    all_q_nums = [item['問番号'] for item in items]
    assert '問 10' in all_q_nums, "問 10 (with space) should be present"
    assert '問 13' in all_q_nums, "問 13 (with space) should be present"
    assert '問 14' in all_q_nums, "問 14 (with space) should be present"
    
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
    
    # Check 廃止 field is present and has 11 entries
    assert "廃止" in meta, "Q2 should have a 廃止 field"
    assert isinstance(meta["廃止"], list), f"廃止 should be a list, got {type(meta['廃止'])}"
    
    haishi_count = len(meta["廃止"])
    if haishi_count != 11:
        print(f"\n⚠ Expected 11 廃止 entries, found {haishi_count}:")
        for i, stmt in enumerate(meta["廃止"], 1):
            print(f"  {i}. Page {stmt['頁']}, 別添={stmt['別添']}")
            print(f"     {stmt['原文'][:80]}...")
    
    assert haishi_count == 11, f"Expected 11 廃止 entries, got {haishi_count}"
    
    # Check structure of first entry
    first_haishi = meta["廃止"][0]
    assert "原文" in first_haishi, "廃止 entry should have 原文"
    assert "別添" in first_haishi, "廃止 entry should have 別添"
    assert "頁" in first_haishi, "廃止 entry should have 頁"
    assert isinstance(first_haishi["原文"], str), "原文 should be a string"
    assert isinstance(first_haishi["頁"], int), "頁 should be an int"
    
    # Check 別添 tracking: only page 1 (cover) should be null
    null_haishi = [h for h in meta["廃止"] if h["別添"] is None]
    assert len(null_haishi) == 1, f"Expected exactly 1 null 別添 (cover page), got {len(null_haishi)}"
    assert null_haishi[0]["頁"] == 1, f"Null 別添 should be on page 1, got page {null_haishi[0]['頁']}"
    
    # Check page 22 entry (問68 answer) has 別添１
    page22_haishi = [h for h in meta["廃止"] if h["頁"] == 22]
    assert len(page22_haishi) == 1, f"Expected 1 廃止 entry on page 22, got {len(page22_haishi)}"
    assert page22_haishi[0]["別添"] is not None, "Page 22 廃止 should have a 別添"
    assert "別添1" in page22_haishi[0]["別添"] or "別添１" in page22_haishi[0]["別添"], \
        f"Page 22 廃止 should be in 別添１, got {page22_haishi[0]['別添']}"
    
    # 2. Every item has a non-empty 答
    for i, item in enumerate(items):
        assert item["答"], f"Item {i+1} ({item.get('問番号')}) has empty answer"
        assert isinstance(item["答"], list), f"Item {i+1} answer should be a list"
        assert len(item["答"]) > 0, f"Item {i+1} answer list is empty"
    
    # 3. Within the same 別添, 問番号 is not duplicated (except known source issue)
    from collections import defaultdict, Counter
    betten_groups = defaultdict(list)
    for item in items:
        betten = item.get("別添")
        q_num = item["問番号"]
        betten_groups[betten].append(q_num)
    
    # Assert we have exactly 6 別添
    assert len(betten_groups) == 6, f"Expected 6 別添, got {len(betten_groups)}: {sorted(betten_groups.keys())}"
    
    # Assert exact per-別添 counts (ground truth from teammate's manual count)
    expected_counts = {
        '別添１': 145,
        '別添２': 10,
        '別添３': 133,
        '別添４': 10,
        '別添５': 25,
        '別添６': 6,
    }
    for betten, expected in expected_counts.items():
        actual = len(betten_groups[betten])
        assert actual == expected, f"{betten}: expected {expected} items, got {actual}"
    
    # Check for duplicates
    duplicates = []
    for betten, q_nums in betten_groups.items():
        q_counts = Counter(q_nums)
        for q_num, count in q_counts.items():
            if count > 1:
                duplicates.append((betten, q_num))
    
    # Known source PDF issue: 別添５ has duplicate 問４ (pages 83 and 84)
    # Evidence from original PDF:
    #   Page 83: 問４ 地域支援・医薬品供給対応体制加算１の施設基準として、「医薬品を分譲した実績」とあるが、保険医療機関への医薬品の分譲も含まれるか。
    #   Page 84: 問４ 地域支援体制加算の施設基準における「地域の多職種と連携する会議」とは、どのような会議が該当するのか。
    #   Both under heading 【地域支援・医薬品供給対応体制加算】
    if duplicates:
        assert duplicates == [('別添５', '問４')], f"Expected only known duplicate ('別添５', '問４'), got {duplicates}"
        print(f"  ⚠ Found known source PDF duplicate: 別添５ has two 問４ (pages 83 and 84)")
    
    print(f"✓ Q2: {len(items)} items, {len(betten_groups)} 別添 groups, {haishi_count} 廃止 statements")
    
    # Return per-別添 counts for reporting
    return {betten: len(q_nums) for betten, q_nums in betten_groups.items()}


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


def test_normalization():
    """Test that question number normalization works correctly"""
    from pdf2qa import normalize_q_num
    
    # Test 1: Full-width and half-width should be treated as same
    assert normalize_q_num('問１') == normalize_q_num('問1'), "Full-width and half-width should match"
    assert normalize_q_num('問１－１') == normalize_q_num('問1-1'), "Full-width hyphenated should match half-width"
    
    # Test 2: Space should be normalized away
    assert normalize_q_num('問 10') == normalize_q_num('問10'), "Space should be removed for comparison"
    assert normalize_q_num('問 １０') == normalize_q_num('問10'), "Space and full-width should normalize to same"
    
    # Test 3: 問1-1 and 問11 should be DIFFERENT
    assert normalize_q_num('問1-1') != normalize_q_num('問11'), "問1-1 and 問11 must be different!"
    assert normalize_q_num('問１－１') != normalize_q_num('問11'), "問１－１ and 問11 must be different!"
    assert normalize_q_num('問１－１') != normalize_q_num('問１１'), "問１－１ and 問１１ must be different!"
    
    print("✓ Normalization tests passed")
    return True


def test_sono_number_extraction():
    """Test extraction of その N from subject with various spacing patterns"""
    import re
    
    # This is the regex pattern used in pdf2qa.py extract_metadata
    pattern = r"[（(]その\s*[０-９0-9１-９]+[）)]"
    
    # Test 1: No space (existing pattern that already worked)
    text1 = "令和６年度診療報酬改定に係る疑義解釈資料の送付について（その12）"
    match1 = re.search(pattern, text1)
    assert match1 is not None, "Should match その12 without space"
    result1 = re.sub(r"[（(）)\s]", "", match1.group(0))
    assert result1 == "その12", f"Expected 'その12', got '{result1}'"
    
    # Test 2: Half-width space (Bug 1 case - P4 R4 その65)
    text2 = "令和６年度診療報酬改定に係る疑義解釈資料の送付について（その 65）"
    match2 = re.search(pattern, text2)
    assert match2 is not None, "Should match その 65 with half-width space"
    result2 = re.sub(r"[（(）)\s]", "", match2.group(0))
    assert result2 == "その65", f"Expected 'その65', got '{result2}'"
    
    # Test 3: Half-width space with three-digit number (Bug 1 case - P6 R2 その101)
    text3 = "令和６年度診療報酬改定に係る疑義解釈資料の送付について（その 101）"
    match3 = re.search(pattern, text3)
    assert match3 is not None, "Should match その 101 with half-width space"
    result3 = re.sub(r"[（(）)\s]", "", match3.group(0))
    assert result3 == "その101", f"Expected 'その101', got '{result3}'"
    
    # Test 4: Full-width numbers
    text4 = "令和６年度診療報酬改定に係る疑義解釈資料の送付について（その２）"
    match4 = re.search(pattern, text4)
    assert match4 is not None, "Should match その２ with full-width number"
    result4 = re.sub(r"[（(）)\s]", "", match4.group(0))
    assert result4 == "その２", f"Expected 'その２', got '{result4}'"
    
    # Test 5: Full-width numbers with space
    text5 = "令和６年度診療報酬改定に係る疑義解釈資料の送付について（その ６５）"
    match5 = re.search(pattern, text5)
    assert match5 is not None, "Should match その ６５ with full-width number and space"
    result5 = re.sub(r"[（(）)\s]", "", match5.group(0))
    assert result5 == "その６５", f"Expected 'その６５', got '{result5}'"
    
    print("✓ その N number extraction tests passed")
    return True


def test_question_reference_handling():
    """Test that question references (like 問122 の③) within question text are not treated as new questions"""
    import re
    
    # Simulate the pattern matching used in extract_items
    # Bug 2 case: A line like "問122 の③及び④の場合について" should NOT be treated as a new question
    
    # Test 1: Question reference with の particle should not match as new question
    test_line1 = "問122 の③及び④の場合について、それぞれどのように考えればよいか。"
    q_start1 = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.)", test_line1)
    if q_start1:
        # Should detect that it starts with の
        assert q_start1.group(2) == 'の', "Should capture の as the character after question number"
    
    # Test 2: Real question start should still match
    test_line2 = "問 124 精神科救急急性期医療入院料等の施設基準について"
    q_start2 = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.)", test_line2)
    assert q_start2 is not None, "Should match real question start"
    assert q_start2.group(2) == '精', "Should capture first character of question text"
    assert q_start2.group(2) != 'の', "Real question should not start with の"
    
    # Test 3: Another real question start
    test_line3 = "問125 精神科地域包括ケア病棟入院料"
    q_start3 = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.)", test_line3)
    assert q_start3 is not None, "Should match real question start"
    assert q_start3.group(2) != 'の', "Real question should not start with の"
    
    print("✓ Question reference handling tests passed")
    return True


if __name__ == "__main__":
    counts = []
    q2_betten_counts = {}
    try:
        # Test normalization and regression tests first
        test_normalization()
        test_sono_number_extraction()
        test_question_reference_handling()
        
        counts.append(("Q1", test_q1_疑義解釈その12()))
        q2_betten_counts = test_q2_疑義解釈その2()
        counts.append(("Q2", sum(q2_betten_counts.values())))
        counts.append(("Q3", test_q3_qa_vol1524()))
        
        print("\nAll tests passed! ✓")
        print("\nItem counts:")
        for name, count in counts:
            if name == "Q2":
                print(f"  {name}: {count} items")
                print("    Per-別添:")
                for betten in sorted(q2_betten_counts.keys()):
                    print(f"      {betten}: {q2_betten_counts[betten]} items")
            else:
                print(f"  {name}: {count} items")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
